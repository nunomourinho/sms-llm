#!/usr/bin/env python3
"""
Mock do Yeastar TG100 — regista SMS recebidos e responde com sucesso.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TG100-MOCK] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TG100Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/cgi/WebCGI" and "1500101" in params:
            payload = unquote(params["1500101"][0])
            kv = dict(p.split("=", 1) for p in payload.split("&") if "=" in p)

            logging.info("=" * 45)
            logging.info("  *** SMS RECEBIDO ***")
            logging.info("  Destino  : %s", kv.get("destination", "?"))
            logging.info("  Conteúdo : %s", kv.get("content", "?"))
            logging.info("  Porta GSM: %s", kv.get("port", "?"))
            logging.info("=" * 45)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"result": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suprimir logs HTTP por defeito


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), TG100Handler)
    logging.info("Mock TG100 a escutar em :8080")
    server.serve_forever()
