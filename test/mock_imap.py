"""
Mock do imaplib.IMAP4/IMAP4_SSL — simula uma caixa com um email de alerta não lido.
Importar ANTES de qualquer import de sms_alertas.
"""
import imaplib
import email
from email.mime.text import MIMEText
from unittest.mock import MagicMock

# ── Construir email de teste ─────────────────────────────────────────────────
msg = MIMEText("""\
=== IT MONITORING ALERT ===

Host    : server01.example.com
Check   : CPU Usage
Status  : CRITICAL
Value   : 95%
Threshold: 80%
Time    : 2026-03-23 12:00:00 UTC

This alert was generated automatically.
""")
msg["Subject"] = "CRITICAL: High CPU Usage on SERVER01"
msg["From"] = "monitor@example.com"
msg["To"] = "test@example.com"

_raw_email = msg.as_bytes()

# ── Mock do objeto de ligação IMAP ───────────────────────────────────────────
_mock_conn = MagicMock()
_mock_conn.login.return_value = ("OK", [b"Logged in"])
_mock_conn.select.return_value = ("OK", [b"1"])
_mock_conn.search.return_value = ("OK", [b"1"])
_mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822)", _raw_email)])
_mock_conn.store.return_value = ("OK", [b"1"])
_mock_conn.logout.return_value = ("BYE", [b"Logged out"])

# ── Substituir classes IMAP ──────────────────────────────────────────────────
imaplib.IMAP4 = MagicMock(return_value=_mock_conn)
imaplib.IMAP4_SSL = MagicMock(return_value=_mock_conn)

import logging
logging.info("[MOCK IMAP] imaplib.IMAP4/IMAP4_SSL substituídos por mock com 1 email de teste")
