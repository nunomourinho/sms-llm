# sms-llm

Sistema que monitoriza uma caixa de correio IMAP, processa alertas de infraestrutura com um modelo LLM local (Qwen2.5) e envia SMS via Yeastar TG100.

```
Email de alerta (IMAP)  →  LLM local (Qwen2.5)  →  SMS (Yeastar TG100)
```

---

## Requisitos

- Docker + Docker Compose
- Acesso a um servidor IMAP
- Yeastar TG100 com API HTTP activa
- ~2 GB de espaço em disco (modelo GGUF)

> **Nota:** O servidor onde corre o Docker precisa de suporte a pelo menos SSE2 (x86-64). A imagem é compilada sem AVX/SSE3+ para compatibilidade com VMs KVM básicas.

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/nunomourinho/sms-llm.git
cd sms-llm
```

### 2. Executar o script de setup

```bash
bash setup.sh
```

O script cria as directorias necessárias (`models/`, `logs/`) com as permissões correctas e copia `config.ini.example` para `config.ini` se ainda não existir.

### 3. Preencher credenciais

Editar `config.ini`:

```ini
[imap]
server   = <servidor IMAP>
user     = <utilizador>
password = <password>

[tg100]
host     = <IP do TG100>
user     = <utilizador API>
password = <password API>
```

Editar `numeros_sms.txt` com os números de destino (um por linha):

```
+351910000000
+351920000000
```

### 4. Iniciar

```bash
docker compose up -d
```

Na primeira execução, o container descarrega automaticamente o modelo LLM (~1 GB):

```
Qwen2.5-1.5B-Instruct-Q4_K_M.gguf  →  ./models/
```

O modelo fica persistente no host e não é re-descarregado em reinícios.

---

## Funcionamento

O script corre em loop contínuo dentro do container, com o intervalo definido em `config.ini` na secção `[schedule] interval` (padrão: 900 s = 15 min):

1. Liga ao servidor IMAP e obtém emails **não lidos** (UNSEEN)
2. Extrai assunto e corpo de cada email
3. Envia ao LLM local com o prompt configurado em `[llm_prompt]`
4. Envia o resultado como SMS via API HTTP do TG100
5. Marca o email como lido para evitar reprocessamento

---

## Configuração

Todos os parâmetros estão em `config.ini`. O ficheiro **não deve ser versionado** (está no `.gitignore`).

| Secção | Parâmetro | Descrição |
|---|---|---|
| `[imap]` | `server`, `port`, `use_ssl` | Ligação ao servidor IMAP |
| `[imap]` | `user`, `password`, `mailbox` | Credenciais e pasta a monitorizar |
| `[tg100]` | `host`, `port`, `use_ssl` | Endereço do Yeastar TG100 |
| `[tg100]` | `user`, `password`, `gsm_port` | Credenciais API e porta GSM |
| `[llm]` | `model_path` | Caminho para o ficheiro `.gguf` |
| `[llm]` | `n_ctx`, `n_threads`, `temperature` | Parâmetros do modelo |
| `[sms]` | `char_limit` | Limite de caracteres por SMS (padrão: 140) |
| `[sms]` | `numeros_ficheiro` | Ficheiro com números de destino |
| `[llm_prompt]` | `system` | Prompt de sistema enviado ao LLM |
| `[schedule]` | `interval` | Intervalo entre execuções em segundos (padrão: 900) |
| `[logging]` | `level`, `logfile` | Nível de log e ficheiro de saída |

---

## Logs

Os logs são persistidos em `./logs/sms_alertas.log` (montado como volume).

```bash
docker compose logs -f          # logs do container em tempo real
tail -f logs/sms_alertas.log    # ficheiro de log no host
```

---

## Teste semi-real

Para testar com servidor IMAP simulado (email de alerta pré-carregado), LLM real e TG100 real:

```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

O ambiente de teste inclui:
- **imap_server** — servidor IMAP TCP mínimo com email de alerta CRITICAL pré-carregado
- **LLM real** — modelo GGUF carregado de `./models/` (necessário ter o ficheiro presente)
- **TG100 real** — credenciais configuradas em `config.test.ini`

Requer `config.test.ini` com as credenciais reais do TG100 (não versionado).

---

## Estrutura do projecto

```
sms-llm/
├── sms_alertas.py          # Script principal
├── Dockerfile              # Imagem Docker (compila llama-cpp sem AVX)
├── entrypoint.sh           # Corrige permissões e faz drop para appuser
├── setup.sh                # Cria directorias e ficheiros iniciais no host
├── docker-compose.yml      # Stack de produção
├── docker-compose.test.yml # Stack de teste semi-real
├── requirements.txt        # Dependências Python
├── config.ini.example      # Configuração de exemplo (copiar para config.ini)
├── config.ini              # Credenciais e configuração reais (não versionado)
├── config.test.ini         # Configuração para testes (não versionado)
├── numeros_sms.txt         # Números de destino SMS (não versionado)
├── models/                 # Modelo GGUF persistente (criado pelo setup.sh)
├── logs/                   # Logs persistentes (criado pelo setup.sh)
└── test/
    ├── imap_server.py      # Servidor IMAP TCP mínimo para testes
    ├── run_test.py         # Ponto de entrada do teste
    ├── mock_imap.py        # (legacy) mock IMAP em memória
    ├── mock_llm.py         # (legacy) mock LLM
    ├── mock_tg100.py       # (legacy) mock TG100
    └── seed_imap.py        # Utilitário para carregar emails no servidor de teste
```
