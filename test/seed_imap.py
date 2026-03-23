#!/usr/bin/env python3
"""
Injeta um email de alerta de teste no mailpit via SMTP.
"""
import smtplib
import time
import sys
from email.mime.text import MIMEText

SMTP_HOST = "mailpit"
SMTP_PORT = 1025
TO = "test@example.com"

EMAIL_SUBJECT = "CRITICAL: High CPU Usage on SERVER01"
EMAIL_BODY = """\
=== IT MONITORING ALERT ===

Host    : server01.example.com
Check   : CPU Usage
Status  : CRITICAL
Value   : 95%
Threshold: 80%
Time    : 2026-03-23 12:00:00 UTC

This alert was generated automatically.
"""

# Aguardar que o mailpit esteja pronto
print("[seed] A aguardar mailpit...", flush=True)
for attempt in range(10):
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=3) as s:
            msg = MIMEText(EMAIL_BODY)
            msg["Subject"] = EMAIL_SUBJECT
            msg["From"] = "monitor@example.com"
            msg["To"] = TO
            s.send_message(msg)
            print(f"[seed] Email de teste enviado para {TO}", flush=True)
            sys.exit(0)
    except Exception as e:
        print(f"[seed] Tentativa {attempt + 1}/10 falhou: {e}", flush=True)
        time.sleep(2)

print("[seed] ERRO: Não foi possível conectar ao mailpit", flush=True)
sys.exit(1)
