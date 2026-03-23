#!/bin/sh
set -e

# Garantir permissões corretas no diretório de modelos (volume montado em runtime)
# O diretório é criado no host antes do mount; o chown dá acesso ao appuser.
chown appuser:appgroup /opt/models 2>/dev/null || true

exec gosu appuser "$@"
