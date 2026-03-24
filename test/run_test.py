#!/usr/bin/env python3
"""
Ponto de entrada para teste completo (sem mocks).
- IMAP  : imap_server (servidor TCP real, email de alerta pré-carregado)
- LLM   : real (modelo GGUF em /opt/models/)
- SMS   : TG100 real (credenciais em config.test.ini [tg100])
"""
import sys
import logging

# ── Configurar logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TEST] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Executar script principal (sem mocks) ───────────────────────────────────
logging.info("A iniciar sms_alertas (IMAP real, LLM real, SMS real via TG100)...")
import importlib.util
spec = importlib.util.spec_from_file_location("sms_alertas", "/app/sms_alertas.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()
logging.info("Teste concluído.")
