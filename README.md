# price-search-engine
Sistema de recuperação de informação para coleta, processamento, indexação e pesquisa de preços de produtos na Web, desenvolvido em Python e Django.

## Recuperação de informação (search)

A busca lê os arquivos `data/index/inverted_index.json`, `document_map.json` e
`products.json` da mesma execução do indexador.

```bash
python -m search.search "Samsung Galaxy S25 256GB"
python -m search.search "Samsung S25 256GB" --operator AND --ranking vector --limit 10
python -m search.search "Samsung" --operator NOT --ranking boolean --limit 10
python -m search.search "Galaxy" --operator OR --ranking boolean
```

- `AND`: interseção; `OR`: união (padrão); `NOT`: complemento da união dos termos
  (somente com `--ranking boolean`). Não há parser de expressões com parênteses.
- `vector` (padrão): TF `1 + ln(tf)`, IDF `ln((N+1)/(df+1))+1`, pesos por campo
  e similaridade do cosseno.
- Pesos: model=5, name=4, storage_gb=3, ram_gb=3, brand=2, text=1.
- `boolean`: resultados por `doc_id`, sem pontuação de relevância.
- Retorna JSON com `doc_id`, `product_id`, `source_file`, `score` e atributos.
- A interface Django ainda não está integrada ao módulo `search`.
- Não são necessárias dependências adicionais.

Testes: `python -m unittest tests.test_search -v`


## Interface web Django

Coloque os quatro JSONs gerados pelo indexador em `data/index/` e execute:

```bash
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. Pesquise por nome ou modelo, selecione AND/OR/NOT e ranking vetorial/booleano. Clique no nome para expandir a descrição e em **Visitar loja** para abrir a URL original da oferta. A descrição usa `text` (ou `description`, quando disponível); registros sem esses campos exibem uma mensagem. O índice é carregado uma vez por processo. A paginação mostra 10 itens por página, com limite de 1.000 resultados por consulta.

Execute os testes da interface com `python manage.py test webapp`.


## Inicialização com aquecimento do índice (Linux)

Com o ambiente virtual ativado, execute:

```bash
chmod +x start_server.sh
./start_server.sh
```

O script inicia o Django em `127.0.0.1:8000` com `--noreload`, chama
`GET /warmup/` e aguarda a criação da instância em cache do `SearchEngine`.
O endpoint só aceita requisições provenientes do próprio computador.
A inicialização pode levar alguns segundos, conforme o tamanho do índice.

**Para encerrar:** pressione `Ctrl+C` no mesmo terminal. O script envia
`SIGTERM` ao processo Django e aguarda seu encerramento. Não é necessário
um script de finalização.

O comando `PORT=8001 ./start_server.sh` permite utilizar outra porta.
Esse procedimento foi projetado para desenvolvimento com um processo Django;
servidores com vários processos precisam aquecer cada processo separadamente.
