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

### 1. Clonar e configurar

```bash
git clone git@github.com:nunomourinho/sms-llm.git
cd sms-llm
cp config.ini.example config.ini
```

### 2. Preencher credenciais

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

### 3. Iniciar

```bash
docker compose up -d
```

Na primeira execução, o container descarrega automaticamente o modelo LLM (~1 GB):

```
Qwen2.5-1.5B-Instruct-Q4_K_M.gguf  →  /opt/models/
```

O modelo fica persistente no host e não é re-descarregado em reinícios.

---

## Funcionamento

O script corre em loop contínuo (a cada 5 minutos) dentro do container:

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
| `[logging]` | `level`, `logfile` | Nível de log e ficheiro de saída |

---

## Logs

Os logs são persistidos em `./logs/sms_alertas.log` (montado como volume).

```bash
docker compose logs -f          # logs do container em tempo real
tail -f logs/sms_alertas.log    # ficheiro de log no host
```

---

## Teste simulado

Para testar sem servidor IMAP real nem TG100:

```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

O ambiente de teste inclui:
- **mock IMAP** — email de alerta pré-carregado em memória
- **mock LLM** — resposta fixa sem necessidade de modelo GGUF
- **mock TG100** — servidor HTTP que regista os SMS recebidos

Saída esperada:

```
[TEST] 1 email(s) não lido(s) encontrado(s).
[TEST] A enviar SMS para +351960000000: S: SERVER01 | T: CPU Alert | L: CRITICAL | D: CPU 95%
[TG100-MOCK] *** SMS RECEBIDO ***
[TG100-MOCK]   Destino  : +351960000000
[TG100-MOCK]   Conteúdo : S: SERVER01 | T: CPU Alert | L: CRITICAL | D: CPU 95%
```

---

## Estrutura do projecto

```
sms-llm/
├── sms_alertas.py          # Script principal
├── Dockerfile              # Imagem Docker (compila llama-cpp sem AVX)
├── docker-compose.yml      # Stack de produção
├── docker-compose.test.yml # Stack de teste simulado
├── requirements.txt        # Dependências Python
├── config.ini.example      # Configuração de exemplo (copiar para config.ini)
├── config.ini              # Credenciais e configuração reais (não versionado)
├── config.test.ini         # Configuração para testes
├── .env.example            # Variáveis de ambiente de exemplo
├── numeros_sms.txt         # Números de destino SMS
├── logs/                   # Logs persistentes
└── test/
    ├── mock_imap.py        # Mock do servidor IMAP
    ├── mock_llm.py         # Mock do modelo LLM
    ├── mock_tg100.py       # Mock da API do TG100
    └── run_test.py         # Ponto de entrada do teste
```
