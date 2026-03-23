# =============================================================================
#  Dockerfile — sms_alertas
#
#  Imagem base: python:3.12-slim (Debian Bookworm mínimo)
#  Tamanho final estimado: ~1.5 GB (maioria do volume é o modelo GGUF)
# =============================================================================

FROM python:3.12-slim AS base

# ---------------------------------------------------------------------------
# Metadados
# ---------------------------------------------------------------------------
LABEL maintainer="sms-llm"
LABEL description="Reencaminha alertas de email para SMS via Yeastar TG100 usando LLM local"

# ---------------------------------------------------------------------------
# Variáveis de build
# ---------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Diretório de trabalho da aplicação
    APP_DIR=/app \
    # Diretório dos modelos (volume montado pelo docker-compose)
    MODELS_DIR=/opt/models

# ---------------------------------------------------------------------------
# Dependências do sistema necessárias para compilar llama-cpp-python
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libssl-dev \
        ca-certificates \
        wget \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Utilizador não-root para correr a aplicação
# ---------------------------------------------------------------------------
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# ---------------------------------------------------------------------------
# Instalar dependências Python
# ---------------------------------------------------------------------------
WORKDIR $APP_DIR

COPY requirements.txt .

RUN pip install --upgrade pip && \
    CMAKE_ARGS="-DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_F16C=OFF -DGGML_FMA=OFF -DGGML_SSE42=OFF -DGGML_NATIVE=OFF" \
    CFLAGS="-msse2 -mno-sse3 -mno-ssse3 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2" \
    CXXFLAGS="-msse2 -mno-sse3 -mno-ssse3 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2" \
    pip install --no-binary llama-cpp-python -r requirements.txt

# ---------------------------------------------------------------------------
# Copiar código da aplicação
# ---------------------------------------------------------------------------
# config.ini NÃO é copiado para a imagem — é montado como volume em runtime
COPY sms_alertas.py .

# Criar diretório de logs com permissões corretas
RUN mkdir -p /var/log && \
    mkdir -p $MODELS_DIR && \
    chown -R appuser:appgroup $APP_DIR /var/log $MODELS_DIR

# ---------------------------------------------------------------------------
# Correr como utilizador não-root
# ---------------------------------------------------------------------------
USER appuser

# ---------------------------------------------------------------------------
# Comando padrão (substituído pelo docker-compose command)
# ---------------------------------------------------------------------------
CMD ["python", "/app/sms_alertas.py"]
