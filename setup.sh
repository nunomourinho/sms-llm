#!/bin/bash
# =============================================================================
#  setup.sh — Prepara o ambiente local antes do primeiro docker compose up
#
#  Cria as directorias necessárias e copia os ficheiros de exemplo.
#  Deve ser executado uma vez após clonar o repositório.
# =============================================================================

set -e

APPUSER_UID=1001
APPUSER_GID=1001

# ---------------------------------------------------------------------------
# Directorias montadas como volumes pelo docker-compose.yml
# ---------------------------------------------------------------------------
echo "A criar directorias de dados..."

# Modelo LLM — o container descarrega o ficheiro .gguf aqui na primeira execução
mkdir -p models
chmod 777 models

# Logs — escritos pelo utilizador appuser (uid 1001) dentro do container
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
