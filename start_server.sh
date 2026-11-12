#!/usr/bin/env bash
# Inicia o Django e aquece o índice de busca antes da primeira pesquisa.
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
HOST="127.0.0.1"
PORT="${PORT:-8000}"
URL="http://${HOST}:${PORT}/warmup/"
SERVER_PID=""
RESPONSE_FILE="$(mktemp)"

cleanup() {
    trap - EXIT INT TERM
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        echo
        echo "Encerrando servidor Django (PID $SERVER_PID)..."
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$RESPONSE_FILE"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! command -v curl >/dev/null 2>&1; then
    echo "Erro: curl não está instalado." >&2
    exit 1
fi

python manage.py runserver "${HOST}:${PORT}" --noreload &
SERVER_PID=$!
echo "Aguardando o Django e o carregamento do índice..."

# Limite de 120 segundos para a inicialização (ajustável conforme o índice).
for ((attempt=1; attempt<=120; attempt++)); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "Erro: o servidor Django foi encerrado antes do aquecimento." >&2
        exit 1
    fi
    HTTP_CODE="$(curl --silent --show-error --max-time 5 --output "$RESPONSE_FILE" --write-out '%{http_code}' "$URL" 2>/dev/null)" || HTTP_CODE="000"
    if [[ "$HTTP_CODE" == "200" ]]; then
        # Limpa as mensagens de inicialização do Django.
        clear
        
        echo "SearchEngine carregado em memória: $(cat "$RESPONSE_FILE")"
        echo "Acesse http://${HOST}:${PORT}/"
        echo "Pressione Ctrl+C para encerrar o servidor."
        wait "$SERVER_PID"
        exit $?
    fi
    if [[ "$HTTP_CODE" != "000" ]]; then
        echo "Erro no aquecimento (HTTP $HTTP_CODE): $(cat "$RESPONSE_FILE")" >&2
        exit 1
    fi
    sleep 1
done

echo "Erro: tempo limite de 120 segundos excedido." >&2
exit 1
