#!/usr/bin/env python3
"""
sms_alertas.py — Reencaminha alertas de email para SMS via Yeastar TG100.

Fluxo:
    1. Lê config.ini (credenciais e parâmetros fora do código)
    2. Liga ao servidor IMAP (SSL ou loopback) e obtém emails UNSEEN
    3. Processa cada email com um LLM local (llama-cpp-python / Qwen2.5)
    4. Envia a mensagem comprimida para um número do ficheiro de destinos
    5. Marca o email como lido para evitar reprocessamento

Dependências:
    pip install llama-cpp-python requests

Execução recomendada (cron, a cada 5 minutos):
    */5 * * * * /usr/bin/python3 /opt/sms_alertas.py >> /var/log/sms_alertas.log 2>&1
"""

import configparser
import imaplib
import email
import logging
import random
import sys
from email.header import decode_header
from pathlib import Path

import requests                      # mais seguro e moderno que urllib
from requests.exceptions import RequestException
from urllib.parse import quote as _urlencode
from llama_cpp import Llama


# ---------------------------------------------------------------------------
# Configuração e validação
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).parent / "config.ini"


def carregar_config(caminho: Path) -> configparser.ConfigParser:
    """Lê e valida o ficheiro de configuração."""
    if not caminho.is_file():
        raise FileNotFoundError(f"Ficheiro de configuração não encontrado: {caminho}")

    cfg = configparser.ConfigParser(interpolation=None)  # desativa % para passwords seguras
    cfg.read(caminho, encoding="utf-8")

    # Secções obrigatórias
    for secao in ("imap", "tg100", "llm", "sms", "llm_prompt"):
        if not cfg.has_section(secao):
            raise ValueError(f"Secção [{secao}] em falta no config.ini")

    # Avisar se ainda estão os valores placeholder
    for secao, chave in [("imap", "password"), ("tg100", "password"), ("tg100", "user")]:
        valor = cfg.get(secao, chave, fallback="")
        if "ALTERAR" in valor.upper():
            raise ValueError(
                f"[{secao}] {chave} ainda contém o valor placeholder. "
                "Edite o config.ini antes de executar."
            )

    return cfg


def configurar_logging(cfg: configparser.ConfigParser) -> None:
    """Configura logging para consola e, opcionalmente, para ficheiro."""
    nivel = cfg.get("logging", "level", fallback="INFO").upper()
    logfile = cfg.get("logging", "logfile", fallback="").strip()

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if logfile:
        handlers.append(logging.FileHandler(logfile, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, nivel, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    # Forçar o nível mesmo se basicConfig foi no-op (handlers já existentes)
    logging.getLogger().setLevel(getattr(logging, nivel, logging.INFO))


# ---------------------------------------------------------------------------
# Leitura de números de destino
# ---------------------------------------------------------------------------

def obter_numeros(caminho: str) -> list[str]:
    """Lê os números de telefone a partir de um ficheiro, um por linha."""
    ficheiro = Path(caminho)
    if not ficheiro.is_file():
        raise FileNotFoundError(f"Ficheiro de números não encontrado: {ficheiro}")

    numeros = [
        linha.strip()
        for linha in ficheiro.read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.startswith("#")
    ]

    if not numeros:
        raise ValueError(f"O ficheiro {ficheiro} não contém nenhum número válido.")

    return numeros


# ---------------------------------------------------------------------------
# Ligação IMAP
# ---------------------------------------------------------------------------

def ligar_imap(cfg: configparser.ConfigParser) -> imaplib.IMAP4:
    """Cria e devolve uma ligação IMAP autenticada."""
    servidor = cfg.get("imap", "server")
    porta = cfg.getint("imap", "port", fallback=993)
    usar_ssl = cfg.getboolean("imap", "use_ssl", fallback=True)
    utilizador = cfg.get("imap", "user")
    password = cfg.get("imap", "password")
    mailbox = cfg.get("imap", "mailbox", fallback="INBOX")

    if usar_ssl:
        # Ligação cifrada — recomendada para qualquer servidor não-loopback
        mail = imaplib.IMAP4_SSL(servidor, porta)
        logging.debug("Ligado ao IMAP via SSL (%s:%s)", servidor, porta)
    else:
        # Apenas para Dovecot em loopback sem TLS (127.0.0.1)
        mail = imaplib.IMAP4(servidor, porta)
        logging.warning(
            "Ligação IMAP sem SSL. Recomendado apenas em loopback local."
        )

    mail.login(utilizador, password)
    mail.select(mailbox)
    logging.debug("Autenticado como %s, mailbox: %s", utilizador, mailbox)
    return mail


def obter_emails_nao_lidos(mail: imaplib.IMAP4) -> list[bytes]:
    """Devolve os IDs dos emails UNSEEN na pasta selecionada."""
    status, mensagens = mail.search(None, "UNSEEN")
    if status != "OK" or not mensagens[0]:
        return []
    return mensagens[0].split()


# ---------------------------------------------------------------------------
# Extração do conteúdo do email
# ---------------------------------------------------------------------------

def _descodificar_cabecalho(valor: str | None) -> str:
    """Descodifica um cabeçalho MIME (assunto, remetente, etc.)."""
    if not valor:
        return ""
    fragmentos = decode_header(valor)
    resultado = ""
    for texto, codificacao in fragmentos:
        if isinstance(texto, bytes):
            enc = codificacao or "utf-8"
            resultado += texto.decode(enc, errors="replace")
        else:
            resultado += texto
    return resultado.strip()


def extrair_texto_email(mensagem_raw: bytes) -> tuple[str, str]:
    """
    Extrai assunto e corpo (text/plain) de uma mensagem raw RFC822.
    Devolve (assunto, corpo).
    """
    msg = email.message_from_bytes(mensagem_raw)
    assunto = _descodificar_cabecalho(msg.get("Subject")) or "Sem Assunto"

    corpo = ""
    if msg.is_multipart():
        for parte in msg.walk():
            if (
                parte.get_content_type() == "text/plain"
                and "attachment" not in str(parte.get("Content-Disposition", ""))
            ):
                payload = parte.get_payload(decode=True)
                charset = parte.get_content_charset() or "utf-8"
                corpo = payload.decode(charset, errors="replace")
                break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            corpo = payload.decode(charset, errors="replace")

    # Colapsar espaços e quebras de linha desnecessárias
    corpo = " ".join(corpo.split())
    return assunto, corpo


# ---------------------------------------------------------------------------
# Modelo LLM
# ---------------------------------------------------------------------------

def carregar_modelo(cfg: configparser.ConfigParser) -> Llama:
    """Inicializa o modelo Qwen2.5 na RAM."""
    model_path = cfg.get("llm", "model_path")
    if not Path(model_path).is_file():
        raise FileNotFoundError(f"Modelo LLM não encontrado: {model_path}")

    logging.info("A carregar modelo LLM: %s", model_path)
    return Llama(
        model_path=model_path,
        n_ctx=cfg.getint("llm", "n_ctx", fallback=1024),
        n_threads=cfg.getint("llm", "n_threads", fallback=2),
        verbose=False,
        chat_format="chatml",
    )


def processar_email_com_llm(
    llm: Llama,
    assunto: str,
    corpo: str,
    cfg: configparser.ConfigParser,
) -> str:
    """
    Envia o email ao LLM e devolve uma string comprimida para SMS.
    Garante o limite de caracteres definido na configuração.
    """
    limite = cfg.getint("sms", "char_limit", fallback=140)
    temperatura = cfg.getfloat("llm", "temperature", fallback=0.1)
    max_tokens = cfg.getint("llm", "max_tokens", fallback=60)

    # O prompt de sistema vem do config, com {char_limit} substituído
    prompt_sistema = cfg.get("llm_prompt", "system").format(char_limit=limite)

    texto_email = f"Subject: {assunto}\n\nBody: {corpo}"

    resposta = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user",   "content": f"Email:\n{texto_email}"},
        ],
        max_tokens=max_tokens,
        temperature=temperatura,
    )

    texto = resposta["choices"][0]["message"]["content"].strip()

    # Truncar com reticências se exceder o limite
    if len(texto) > limite:
        texto = texto[: limite - 3] + "..."

    return texto


# ---------------------------------------------------------------------------
# Envio de SMS via Yeastar TG100
# ---------------------------------------------------------------------------

def enviar_sms(numero: str, mensagem: str, cfg: configparser.ConfigParser) -> str:
    """
    Envia mensagem via API HTTP do Yeastar TG100.
    Usa requests em vez de urllib para melhor tratamento de erros e timeouts.
    """
    esquema = "https" if cfg.getboolean("tg100", "use_ssl", fallback=False) else "http"
    host    = cfg.get("tg100", "host")
    porta   = cfg.getint("tg100", "port", fallback=80)
    user    = cfg.get("tg100", "user")
    passwd  = cfg.get("tg100", "password")
    gsm_port = cfg.getint("tg100", "gsm_port", fallback=1)
    timeout = cfg.getint("tg100", "timeout", fallback=10)

    # A API do TG100 usa um formato não-standard: o parâmetro "1500101" contém
    # "account=USER" e os restantes campos são parâmetros separados na query string.
    # O requests.get(params=...) codificaria os '=' e '&' — construir a URL à mão.
    query = (
        f"1500101=account={_urlencode(user, safe='')}"
        f"&password={_urlencode(passwd, safe='')}"
        f"&port={gsm_port}"
        f"&destination={_urlencode(numero, safe='')}"
        f"&content={_urlencode(mensagem, safe='')}"
    )
    url = f"{esquema}://{host}:{porta}/cgi/WebCGI?{query}"
    logging.info("TG100 URL: %s", url)

    try:
        # verify=True → valida certificado SSL se use_ssl=true
        resposta = requests.get(
            url,
            timeout=timeout,
            verify=cfg.getboolean("tg100", "use_ssl", fallback=False),
        )
        resposta.raise_for_status()
        return resposta.text.strip()
    except RequestException as exc:
        logging.error("Falha ao contactar o TG100: %s", exc)
        return f"ERRO: {exc}"


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    # ── 1. Configuração ──────────────────────────────────────────────────────
    try:
        cfg = carregar_config(CONFIG_PATH)
    except (FileNotFoundError, ValueError) as exc:
        # Ainda não há logger — imprimir direto para stderr
        print(f"[ERRO DE CONFIGURAÇÃO] {exc}", file=sys.stderr)
        sys.exit(1)

    configurar_logging(cfg)

    # ── 2. Números de destino ────────────────────────────────────────────────
    try:
        numeros = obter_numeros(cfg.get("sms", "numeros_ficheiro"))
    except (FileNotFoundError, ValueError) as exc:
        logging.critical("Impossível carregar números: %s", exc)
        sys.exit(1)

    # ── 3. Ligação IMAP ──────────────────────────────────────────────────────
    try:
        mail = ligar_imap(cfg)
    except imaplib.IMAP4.error as exc:
        logging.critical("Falha na autenticação IMAP: %s", exc)
        sys.exit(1)
    except OSError as exc:
        logging.critical("Não foi possível ligar ao servidor IMAP: %s", exc)
        sys.exit(1)

    # ── 4. Verificar emails não lidos ────────────────────────────────────────
    ids_nao_lidos = obter_emails_nao_lidos(mail)

    if not ids_nao_lidos:
        logging.info("Nenhum email novo.")
        mail.logout()
        return

    logging.info("%d email(s) não lido(s) encontrado(s).", len(ids_nao_lidos))

    # Carregar o modelo LLM apenas quando há emails para processar
    try:
        llm = carregar_modelo(cfg)
    except (FileNotFoundError, RuntimeError) as exc:
        logging.critical("Não foi possível carregar o modelo LLM: %s", exc)
        mail.logout()
        sys.exit(1)

    # ── 5. Processar cada email ──────────────────────────────────────────────
    for num_id in ids_nao_lidos:
        try:
            res, msg_data = mail.fetch(num_id, "(RFC822)")
            if res != "OK" or not msg_data:
                logging.warning("Não foi possível obter email ID %s.", num_id)
                continue

            for resposta in msg_data:
                if not isinstance(resposta, tuple):
                    continue

                assunto, corpo = extrair_texto_email(resposta[1])
                logging.debug("Email recebido — Assunto: %s", assunto)

                mensagem_sms = processar_email_com_llm(llm, assunto, corpo, cfg)

                for numero_destino in numeros:
                    logging.info(
                        "A enviar SMS para %s: %s", numero_destino, mensagem_sms
                    )
                    resultado = enviar_sms(numero_destino, mensagem_sms, cfg)
                    logging.info("Resposta TG100: %s", resultado)

        except Exception as exc:  # noqa: BLE001 — continuar com os restantes emails
            logging.error("Erro ao processar email ID %s: %s", num_id, exc)
        finally:
            # Marcar como LIDO mesmo em caso de erro de envio (evita ciclos)
            mail.store(num_id, "+FLAGS", "\\Seen")

    mail.logout()
    logging.info("Processamento concluído.")


if __name__ == "__main__":
    main()
