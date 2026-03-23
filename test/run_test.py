#!/usr/bin/env python3
"""
Ponto de entrada para teste simulado.
Aplica mocks de IMAP e LLM antes de importar sms_alertas,
depois corre o script principal contra o mock_tg100.
"""
import sys
import logging
from pathlib import Path

# ── Configurar logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TEST] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Aplicar mocks ANTES de qualquer import de sms_alertas ──────────────────
sys.path.insert(0, "/test")
import mock_imap   # noqa: F401 — substitui imaplib.IMAP4 por mock
import mock_llm    # noqa: F401 — substitui llama_cpp.Llama por mock

# Ficheiro dummy para o model_path (verificado por sms_alertas antes de instanciar Llama)
Path("/tmp/test.gguf").touch(exist_ok=True)

# ── Executar script principal ───────────────────────────────────────────────
logging.info("A iniciar sms_alertas com mocks ativos...")
import importlib.util
spec = importlib.util.spec_from_file_location("sms_alertas", "/app/sms_alertas.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()
logging.info("Teste concluído.")
