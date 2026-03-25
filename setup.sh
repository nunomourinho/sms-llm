#!/bin/bash
# =============================================================================
#  setup.sh — Prepara o ambiente local antes do primeiro docker compose up
#
#  Cria as directorias necessárias e copia os ficheiros de exemplo.
#  Deve ser executado uma vez após clonar o repositório.
# =============================================================================

set -e

APPUSER_UID=$(id -u)
APPUSER_GID=$(id -g)

# ---------------------------------------------------------------------------
# Escrever UID/GID no .env para o docker-compose passar ao build do Dockerfile
# ---------------------------------------------------------------------------
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    cp .env.example "$ENV_FILE"
fi

# Actualizar ou adicionar APPUSER_UID e APPUSER_GID
if grep -q "^APPUSER_UID=" "$ENV_FILE"; then
    sed -i "s/^APPUSER_UID=.*/APPUSER_UID=${APPUSER_UID}/" "$ENV_FILE"
else
    echo "APPUSER_UID=${APPUSER_UID}" >> "$ENV_FILE"
fi

if grep -q "^APPUSER_GID=" "$ENV_FILE"; then
    sed -i "s/^APPUSER_GID=.*/APPUSER_GID=${APPUSER_GID}/" "$ENV_FILE"
else
    echo "APPUSER_GID=${APPUSER_GID}" >> "$ENV_FILE"
fi

echo "  UID/GID detectados: ${APPUSER_UID}:${APPUSER_GID} → escritos em ${ENV_FILE}"

# ---------------------------------------------------------------------------
# Directorias montadas como volumes pelo docker-compose.yml
# ---------------------------------------------------------------------------
echo "A criar directorias de dados..."

# Modelo LLM — o container descarrega o ficheiro .gguf aqui na primeira execução
mkdir -p models
chmod 777 models

# Logs — escritos pelo utilizador appuser dentro do container
mkdir -p logs
chown "${APPUSER_UID}:${APPUSER_GID}" logs 2>/dev/null || chmod 777 logs

echo "  models/  OK"
echo "  logs/    OK"

# ---------------------------------------------------------------------------
# Ficheiros de configuração
# ---------------------------------------------------------------------------
if [ ! -f config.ini ]; then
    cp config.ini.example config.ini
    echo ""
    echo "  config.ini criado a partir de config.ini.example"
    echo "  >>> Edita config.ini com as credenciais reais antes de continuar <<<"
else
    echo "  config.ini já existe — mantido sem alterações"
fi

if [ ! -f numeros_sms.txt ]; then
    echo "+351910000000" > numeros_sms.txt
    echo "  numeros_sms.txt criado com número de exemplo — edita com os números reais"
else
    echo "  numeros_sms.txt já existe — mantido sem alterações"
fi

echo ""
echo "Setup concluído. Passos seguintes:"
echo "  1. Edita config.ini com as credenciais IMAP e TG100"
echo "  2. Edita numeros_sms.txt com os números de destino"
echo "  3. docker compose up -d"
