# Price Search Engine

Projeto acadêmico de **recuperação de informação na Web** para coletar páginas de lojas virtuais, identificar ofertas de smartphones, construir um índice de pesquisa e consultar produtos por uma interface Django. O sistema é um **protótipo de pesquisa**, não uma plataforma comercial pronta para produção.

## Visão geral

```text
Lojas virtuais
    │
    ▼
 crawler ──► data/raw/ (HTML e metadados JSON)
    │
    ▼
 processor ─► data/processed/ (produtos normalizados em JSON)
    │
    ▼
 indexer ───► data/index/ (índice invertido e dados vetoriais)
    │
    ├────────► search (consulta booleana e ranking vetorial)
    │                    │
    └────────────────────► webapp (interface Django)
```

As etapas são executadas **separadamente**. Iniciar o servidor web não dispara a coleta, o processamento ou a indexação. Os caminhos são relativos à raiz do repositório; execute os comandos a partir dela.

## Requisitos e instalação

- Linux/Ubuntu e Python compatível com as versões fixadas em `requirements.txt` (o projeto utiliza Django 6.1.1).
- Acesso à internet para a coleta; `curl` e Bash para o script de inicialização.
- Espaço em disco suficiente para os HTMLs coletados e arquivos de índice.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Ajuste as configurações de cada etapa antes de executar uma coleta extensa. O diretório `data/` é usado para os artefatos gerados; seus conteúdos não devem ser tratados como arquivos de código-fonte.

## 1. Crawler: coleta de páginas

**Diretório:** `crawler/`.

O coletor parte de URLs de lojas configuradas no projeto, percorre páginas elegíveis e armazena o **HTML original** junto com um **JSON de metadados**. Aplica filtros de URL e domínio, controla tentativas e registra estatísticas e critérios de parada. A etapa não transforma o HTML em ofertas: isso é responsabilidade do processador.

**Configuração:** `crawler/config.py` (limites de documentos, armazenamento, tempo, requisições e parâmetros de execução) e arquivos de fontes e filtros do módulo.

```bash
python -m crawler.crawler
```

**Saída:** `data/raw/`. Verifique as políticas de acesso e `robots.txt` de cada site. Bloqueios e páginas dinâmicas podem limitar a coleta; não se deve tentar contornar mecanismos de proteção.

## 2. Processor: extração e normalização

**Diretório:** `processor/`.

Lê os pares de HTML e metadados de `data/raw/`, identifica produtos nas páginas, limpa textos, extrai atributos como fabricante, modelo, RAM, armazenamento e preço e gera registros estruturados. Inclui regras para descartar acessórios e evitar confundir **valores de parcelas** com preços à vista. A execução pode utilizar múltiplos processos; a quantidade padrão é calculada a partir dos núcleos disponíveis.

**Configuração:** `processor/config.py`, incluindo `MAX_WORKERS` e `CHUNK_SIZE`.

```bash
python -m processor.processor
```

**Saída:** `data/processed/`, com arquivos JSON dos documentos que contêm ofertas reconhecidas. Nem toda página coletada produz um documento processado.

## 3. Indexer: construção do índice

**Diretório:** `indexer/`.

Lê os produtos de `data/processed/`, tokeniza os campos e constrói um **índice invertido** para localizar rapidamente quais ofertas contêm cada termo. Cada oferta é tratada como documento lógico. Também calcula os valores de frequência inversa dos documentos (IDF) e as normas vetoriais usadas no ranqueamento.

**Configuração:** `indexer/config.py` (caminhos e regras de tokenização).

```bash
python -m indexer.indexer
```

**Saída em `data/index/`:**

| Arquivo | Finalidade |
|---|---|
| `inverted_index.json` | Termos, documentos e frequências por campo |
| `products.json` | Dados das ofertas indexadas |
| `document_map.json` | Identificação e origem dos documentos |
| `vector_index.json` | IDF, pesos de campos e normas pré-calculadas |
| `statistics.json` | Estatísticas da indexação |

Reexecute o indexador **após** qualquer novo processamento para que a pesquisa utilize os dados atualizados.

## 4. Search: recuperação e ranqueamento

**Diretório:** `search/`.

O módulo `query.py` interpreta e normaliza a consulta; `retriever.py` seleciona candidatos no índice invertido; `ranker.py` calcula a relevância vetorial; e `search.py` coordena o fluxo e oferece uma interface de linha de comando.

- **Booleano:** `AND` exige todos os termos, `OR` aceita ao menos um e `NOT` retorna o complemento dos termos informados. O modo booleano não atribui pontuação de similaridade; `NOT` deve ser usado com `--ranking boolean`.
- **Vetorial:** usa TF-IDF com logaritmo na base 2, pesos por campo e similaridade do cosseno. Os pesos são `model=5`, `name=4`, `storage_gb=3`, `ram_gb=3`, `brand=2` e `text=1`. O índice vetorial reduz os cálculos feitos a cada consulta.
- **Aspas:** grupos entre aspas simples ou duplas combinam seus termos com `AND`; quando o operador externo é `OR`, os grupos são unidos por `OR`. Não há interpretador geral de parênteses.
- **Preço ausente:** na linha de comando, ofertas sem preço são excluídas por padrão; a opção `--include-without-price` permite incluí-las.

Fórmulas empregadas:

```text
TF(freq) = 1 + log2(freq), se freq > 0; caso contrário, 0
TF_ponderado(t,d) = soma [peso_do_campo × TF(freq_do_termo_no_campo)]
IDF(t) = 1 + log2((N + 1) / (df(t) + 1))
peso(t,d) = TF_ponderado(t,d) × IDF(t)
similaridade(q,d) = (q · d) / (||q|| × ||d||)
```

Exemplos de execução, após gerar o índice:

```bash
python -m search.search "Samsung Galaxy S25 256GB"
python -m search.search "Samsung S25" --operator AND --ranking vector --limit 10
python -m search.search '"Iphone 16" "Samsung S25"' --operator OR --ranking vector
python -m search.search "Samsung" --operator NOT --ranking boolean --limit 10
python -m search.search "Galaxy" --include-without-price
```

## 5. Webapp: interface Django

**Diretórios:** `webapp/` (telas, estilos, rotas e lógica) e `config/` (configuração Django).

A interface utiliza o módulo `search` para pesquisar ofertas por nome ou modelo, escolher operadores booleanos e tipo de ranqueamento, ordenar resultados por relevância ou preço e navegar por páginas de resultados. Cada oferta apresenta dados e um link para a loja de origem. Uma pesquisa sem correspondências mostra uma mensagem específica. A interface pode incluir ofertas sem preço, que são tratadas separadamente na ordenação.

Para iniciar diretamente com o servidor de desenvolvimento:

```bash
python manage.py runserver
```

Acesse **http://127.0.0.1:8000/**. O índice precisa existir em `data/index/` antes de pesquisar.

### Inicialização recomendada: `start_server.sh`

O script Bash na raiz do repositório é uma **rotina de inicialização**, não uma macro de planilha. Ele inicia o Django em `127.0.0.1`, aguarda o endpoint `/warmup/` carregar o mecanismo de busca em memória e só então informa que a aplicação está pronta. O tempo limite de espera é de 120 segundos.

```bash
source .venv/bin/activate
chmod +x start_server.sh  # necessário apenas na primeira vez
./start_server.sh
```

Abra **http://127.0.0.1:8000/**. Para usar outra porta:

```bash
PORT=8001 ./start_server.sh
```

Para encerrar, pressione **Ctrl+C** no terminal em que o script está executando. O script encerra o processo Django iniciado por ele. É necessário ter `curl` instalado. O servidor usa `--noreload` para manter uma instância única do mecanismo em memória. O endpoint de aquecimento é destinado ao acesso local.

**Acesso remoto por SSH:** como o script escuta em `127.0.0.1` no servidor, utilize encaminhamento de porta SSH, por exemplo `ssh -L 8000:127.0.0.1:8000 usuario@servidor`, e acesse a aplicação pelo navegador do computador local. Não exponha o servidor de desenvolvimento diretamente à internet.

## Fluxo completo de execução

Quando ainda não existem dados processados ou índice:

```bash
# 1. Coletar (pode ser demorado e consumir bastante espaço)
python -m crawler.crawler

# 2. Extrair e normalizar ofertas
python -m processor.processor

# 3. Construir índice de pesquisa
python -m indexer.indexer

# 4. Consultar no terminal (opcional)
python -m search.search "Samsung Galaxy"

# 5. Iniciar a interface com aquecimento do índice
./start_server.sh
```

Se os arquivos de `data/raw/` já estiverem disponíveis, comece pelo **processor**. Se `data/processed/` já estiver atualizado, comece pelo **indexer**. Se `data/index/` já contiver um índice consistente, basta executar a busca ou iniciar o servidor. Ao alterar regras de extração de preços, reexecute **processor → indexer**; não é necessária nova coleta para corrigir HTMLs já armazenados.

## Testes

```bash
# Testes unitários do projeto
python -m unittest discover -s tests -v

# Testes da aplicação Django
python manage.py test webapp
```

Os testes de extração incluem cenários de parcelamento. Resultados podem depender das dependências instaladas e dos dados de teste disponíveis; os comandos acima não substituem testes de integração e carga em ambiente de implantação.

## Melhorias futuras do projeto acadêmico

1. **Coleta incremental e recoleta:** detectar alterações nas páginas, atualizar ofertas existentes e definir periodicidade por loja, reduzindo processamento desnecessário.
2. **Monitoramento de preços e alertas:** permitir que o usuário acompanhe um modelo, estabeleça um preço-alvo e receba notificações quando uma oferta atingir o valor definido.
3. **Filtros avançados:** refinar resultados por loja, faixa de preço, fabricante e modelo; considerar também RAM e armazenamento.
4. **Histórico de preços:** registrar alterações por oferta e apresentar gráficos de evolução para apoiar decisões de compra.
5. **Comparação entre lojas:** identificar ofertas equivalentes do mesmo produto, evitando misturar variantes com capacidades ou condições comerciais diferentes.
6. **Qualidade da extração e da busca:** ampliar testes com HTMLs de diferentes lojas, aprimorar identificação de atributos e preços e avaliar precisão, revocação e qualidade do ranqueamento.

## Evolução de protótipo acadêmico para produto

A transformação em produto comercial exige uma nova etapa de levantamento de requisitos, arquitetura, segurança e operação. Os tópicos abaixo são **propostas**, não funcionalidades implementadas.

### Requisitos e experiência do usuário

- Levantar requisitos funcionais com usuários: cadastro, listas de acompanhamento, filtros, comparações, alertas, preferências de notificação e histórico de preços.
- Definir requisitos não funcionais mensuráveis: atualização dos preços, disponibilidade, latência de pesquisa, acessibilidade, escalabilidade, retenção de dados e observabilidade.
- Prototipar e validar fluxos da interface com usuários, incluindo uso em celulares, acessibilidade, mensagens de erro, filtros e transparência sobre preço à vista, parcelamento, frete e data da última atualização.
- Especificar regras de negócio para distinguir o mesmo modelo de variantes diferentes, preços promocionais, produtos indisponíveis e ofertas duplicadas.

### Arquitetura e operação

- Separar **coleta e processamento assíncronos** da API de pesquisa e da interface, com agendamento de tarefas, filas, controle de concorrência e tentativas com limites.
- Avaliar banco de dados para produtos, histórico de preços, usuários e alertas, além de um mecanismo de indexação adequado ao volume de dados; definir contratos e versionamento entre etapas.
- Planejar implantação com servidor de aplicação apropriado para produção, proxy reverso, HTTPS, armazenamento persistente, backups, recuperação de falhas e ambientes separados de desenvolvimento, teste e produção.
- Adotar monitoramento de erros, métricas, logs estruturados, testes automatizados, integração contínua e procedimentos de atualização e reversão.

### Segurança, privacidade e conformidade

- **Não publicar a configuração Django atual em produção:** `config/settings.py` contém `DEBUG=True` e uma `SECRET_KEY` fixa de desenvolvimento. Externalizar segredos, desativar o modo de depuração e configurar corretamente `ALLOWED_HOSTS` e cabeçalhos de segurança.
- Projetar autenticação, autorização e controle de acesso para contas, preferências e notificações; proteger sessões e formulários contra ataques comuns, validar entradas e limitar requisições.
- Aplicar princípios da **LGPD** ao tratamento de dados pessoais: finalidade, minimização, transparência, retenção, exclusão e medidas de segurança, conforme os recursos que forem implementados.
- Tratar páginas coletadas como conteúdo externo não confiável: validar URLs e redirecionamentos, evitar SSRF, limitar tamanho de respostas, impedir injeção de HTML/script na interface e não executar código extraído de páginas.
- Respeitar `robots.txt`, termos aplicáveis e limites de acesso às lojas. Definir política para uso, armazenamento e atualização de dados de terceiros antes de qualquer exploração comercial.

## Situação do projeto

Este repositório demonstra um fluxo acadêmico completo de **coleta → processamento → indexação → recuperação → interface**. A disponibilidade de preços depende da qualidade e da data da coleta; resultados não representam garantia de estoque ou preço vigente na loja. A evolução comercial requer validação técnica, jurídica e de produto antes de disponibilização pública.
