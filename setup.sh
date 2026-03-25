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

# ---------------------------------------------------------------------------
# Servidor de email interno (opcional)
# Só configurado se MAIL_ACCOUNT e MAIL_PASSWORD estiverem definidos no .env
# ---------------------------------------------------------------------------

# Carregar variáveis do .env para verificar se o mail interno está configurado
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

if [ -n "${MAIL_ACCOUNT:-}" ] && [ -n "${MAIL_PASSWORD:-}" ]; then
    if ! command -v openssl &>/dev/null; then
        echo "AVISO: openssl não encontrado — conta de email interno não configurada."
        echo "       Instala openssl e corre setup.sh novamente."
    else
        mkdir -p mailconfig
        MAIL_HASH=$(openssl passwd -6 "${MAIL_PASSWORD}")
        echo "${MAIL_ACCOUNT}|{SHA512-CRYPT}${MAIL_HASH}" > mailconfig/postfix-accounts.cf
        echo ""
        echo "  mailconfig/postfix-accounts.cf criado"
        echo "  Conta interna: ${MAIL_ACCOUNT}"
        echo "  Domínio: ${MAIL_DOMAIN:-alertas.local}"
        INTERNAL_MAIL=true
    fi
else
    echo ""
    echo "  Servidor de email interno não configurado (MAIL_ACCOUNT/MAIL_PASSWORD não definidos no .env)"
    echo "  Para activar: preenche MAIL_ACCOUNT e MAIL_PASSWORD no .env e volta a correr setup.sh"
    INTERNAL_MAIL=false
fi

echo ""
echo "Setup concluído. Passos seguintes:"
if [ "${INTERNAL_MAIL:-false}" = "true" ]; then
    echo "  Modo: servidor de email INTERNO"
    echo "  1. Edita config.ini [imap]: server=127.0.0.1 port=143 use_ssl=false user=${MAIL_ACCOUNT}"
    echo "  2. Edita config.ini [tg100] com as credenciais do TG100"
    echo "  3. Edita numeros_sms.txt com os números de destino"
    echo "  4. docker compose --profile mailserver up -d"
    echo ""
    echo "  Os sistemas externos enviam emails para SMTP deste servidor na porta 25."
else
    echo "  Modo: servidor de email EXTERNO"
    echo "  1. Edita config.ini com as credenciais IMAP e TG100"
    echo "  2. Edita numeros_sms.txt com os números de destino"
    echo "  3. docker compose up -d"
fi
