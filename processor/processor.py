"""Processamento de documentos HTML com execução sequencial ou multiprocessos."""
import json
import logging
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from processor.cleaner import clean_html
from processor.products import extract_products, product_id
from processor.config import RAW_DIR, PROCESSED_DIR, MAX_WORKERS, CHUNK_SIZE
from processor.normalizer import normalize_capacities

logger = logging.getLogger(__name__)
COUNTERS = ('read', 'processed', 'products', 'skipped', 'irrelevant', 'errors')


def physical_cores() -> int:
    """Obtém núcleos físicos, com fallback conservador quando indisponível."""
    try:
        import psutil
        cores = psutil.cpu_count(logical=False)
    except ImportError:
        cores = None
    return cores or os.cpu_count() or 1


def worker_count(workers: int | None = None) -> int:
    """Usa N-1 núcleos por padrão; permite sobrescrita explícita."""
    value = workers if workers is not None else MAX_WORKERS
    if value is None:
        value = max(1, physical_cores() - 1)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError('workers deve ser inteiro positivo')
    return value


def process_document(metadata_path: Path, raw_dir: Path, processed_dir: Path) -> dict[str, int]:
    """Processa um documento e retorna contadores locais; não compartilha estado."""
    stats = Counter({'read': 1})
    try:
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        document_id = metadata['document_id']
        # Evita caminhos arbitrários e colisões com nomes inválidos.
        if not isinstance(document_id, str) or not document_id or Path(document_id).name != document_id or '/' in document_id or "\\" in document_id:
            raise ValueError('Identificador inválido')
        html_path = raw_dir / metadata['html_file']
        if html_path.resolve().parent != raw_dir.resolve():
            raise ValueError('Caminho de HTML inválido')
        html = html_path.read_text(encoding='utf-8')
        products = extract_products(html, metadata['url'])
        if not products:
            stats['irrelevant'] += 1
            return dict(stats)
        cleaned = clean_html(html)
        title = normalize_capacities(cleaned['title'])
        for product in products:
            product['product_id'] = product_id(document_id, product)
        index_text = ' '.join([title] + [p['text'] for p in products]).strip()
        result = {
            'document_id': document_id,
            'url': metadata['url'],
            'collected_at': metadata.get('collected_at'),
            'title': title,
            'text': index_text,
            'products': products,
        }
        target = processed_dir / f'{document_id}.json'
        # Gravação atômica, mesmo se um processo for interrompido.
        temporary = processed_dir / f'.{document_id}.{os.getpid()}.tmp'
        try:
            temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        stats['processed'] += 1
        stats['products'] += len(products)
    except Exception as exc:
        logger.warning('Erro ao processar %s: %s', metadata_path, exc)
        stats['errors'] += 1
    return dict(stats)


def _task(args):
    """Função de nível de módulo para ser serializável pelo multiprocessing."""
    return process_document(*args)


def process_documents(raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR,
                      workers: int | None = None) -> dict:
    """Distribui documentos dinamicamente e consolida estatísticas no pai."""
    raw_dir, processed_dir = Path(raw_dir), Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(raw_dir.glob('*.json'))
    count = worker_count(workers)
    if CHUNK_SIZE < 1:
        raise ValueError('CHUNK_SIZE deve ser positivo')
    stats = Counter({key: 0 for key in COUNTERS})
    started = time.perf_counter()
    tasks = ((path, raw_dir, processed_dir) for path in paths)
    if count == 1:
        results = map(_task, tasks)
        for result in results:
            stats.update(result)
    else:
        # executor.map distribui tarefas conforme os processos ficam disponíveis.
        # Os argumentos são caminhos, nunca o conteúdo completo do HTML.
        with ProcessPoolExecutor(max_workers=count) as executor:
            for result in executor.map(_task, tasks, chunksize=CHUNK_SIZE):
                stats.update(result)
    elapsed = time.perf_counter() - started
    output = {key: stats[key] for key in COUNTERS}
    output.update(workers=count, elapsed_seconds=round(elapsed, 3),
                  documents_per_second=round(stats['read'] / elapsed, 3) if elapsed else 0.0)
    return output


def print_report(stats: dict) -> None:
    """Exibe o relatório final do processamento."""

    print("\n" + "=" * 50)
    print("RELATÓRIO DE PROCESSAMENTO")
    print("=" * 50)

    print(f"Arquivos lidos:       {stats.get('read', 0)}")
    print(f"Processados (JSONs):  {stats.get('processed', 0)}")
    print(f"Produtos extraídos:   {stats.get('products', 0)}")
    print(f"Irrelevantes:         {stats.get('irrelevant', 0)}")
    print(f"Ignorados:            {stats.get('skipped', 0)}")
    print(f"Erros:                {stats.get('errors', 0)}")

    print("-" * 50)

    print(f"Processos utilizados: {stats.get('workers', 1)}")
    print(f"Tempo de execução:    {stats.get('elapsed_seconds', 0):.2f} segundos")
    print(f"Documentos/segundo:   {stats.get('documents_per_second', 0):.2f}")

    print("=" * 50)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    stats = process_documents()
    print_report(stats)
