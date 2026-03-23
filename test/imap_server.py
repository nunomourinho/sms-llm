#!/usr/bin/env python3
"""
Servidor IMAP4 mínimo para testes.

Implementa exatamente os comandos usados por sms_alertas.py via imaplib:
    CAPABILITY, LOGIN, SELECT, SEARCH UNSEEN, FETCH, STORE, LOGOUT

Escuta em 0.0.0.0:1143 (sem TLS) e aceita qualquer utilizador/password.
Tem um email de alerta CRITICAL pré-carregado na caixa de entrada.
"""
import socket
import threading
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [IMAP] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

# Email de teste pré-carregado (RFC822, terminações CRLF obrigatórias)
TEST_EMAIL = (
    "From: monitor@example.com\r\n"
    "To: test@domain.com\r\n"
    "Subject: CRITICAL: High CPU Usage on SERVER01\r\n"
    "Date: Mon, 23 Mar 2026 12:00:00 +0000\r\n"
    "MIME-Version: 1.0\r\n"
    "Content-Type: text/plain; charset=utf-8\r\n"
    "\r\n"
    "=== IT MONITORING ALERT ===\r\n"
    "\r\n"
    "Host     : server01.example.com\r\n"
    "Check    : CPU Usage\r\n"
    "Status   : CRITICAL\r\n"
    "Value    : 95%\r\n"
    "Threshold: 80%\r\n"
    "Time     : 2026-03-23 12:00:00 UTC\r\n"
    "\r\n"
    "This alert was generated automatically.\r\n"
)
TEST_EMAIL_BYTES = TEST_EMAIL.encode("utf-8")


def handle_client(conn, addr):
    logging.info("Cliente ligado: %s:%d", *addr)
    seen = False

    def send(line: str):
        conn.sendall(line.encode("utf-8"))

    try:
        send("* OK IMAP4rev1 Service Ready\r\n")

        while True:
            raw = conn.recv(4096)
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            parts = line.split(None, 2)
            if not parts:
                continue
            tag = parts[0]
            cmd = parts[1].upper() if len(parts) > 1 else ""

            logging.info("< %s", line)

            if cmd == "CAPABILITY":
                send(f"* CAPABILITY IMAP4rev1\r\n{tag} OK CAPABILITY completed\r\n")

            elif cmd == "LOGIN":
                send(f"{tag} OK LOGIN completed\r\n")

            elif cmd == "SELECT":
                send(
                    f"* 1 EXISTS\r\n"
                    f"* 0 RECENT\r\n"
                    f"* OK [UNSEEN 1]\r\n"
                    f"* OK [UIDVALIDITY 1]\r\n"
                    f"{tag} OK [READ-WRITE] SELECT completed\r\n"
                )

            elif cmd == "SEARCH":
                if seen:
                    send(f"* SEARCH\r\n{tag} OK SEARCH completed\r\n")
                else:
                    send(f"* SEARCH 1\r\n{tag} OK SEARCH completed\r\n")

            elif cmd == "FETCH":
                size = len(TEST_EMAIL_BYTES)
                header = f"* 1 FETCH (RFC822 {{{size}}}\r\n".encode()
                footer = f")\r\n{tag} OK FETCH completed\r\n".encode()
                conn.sendall(header + TEST_EMAIL_BYTES + footer)

            elif cmd == "STORE":
                seen = True
                send(
                    f"* 1 FETCH (FLAGS (\\Seen))\r\n"
                    f"{tag} OK STORE completed\r\n"
                )

            elif cmd == "LOGOUT":
                send(f"* BYE Closing connection\r\n{tag} OK LOGOUT completed\r\n")
                break

            elif cmd == "NOOP":
                send(f"{tag} OK NOOP completed\r\n")

            else:
                send(f"{tag} BAD Unknown command\r\n")

    except Exception as exc:
        logging.warning("Ligação encerrada: %s", exc)
    finally:
        conn.close()
        logging.info("Cliente desligado: %s:%d", *addr)


def main():
    host, port = "0.0.0.0", 1143
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    logging.info("Servidor IMAP4 a escutar em %s:%d", host, port)

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    main()
