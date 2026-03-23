"""
Mock do llama_cpp.Llama — resposta fixa sem necessidade de modelo GGUF.
Importar ANTES de qualquer import de sms_alertas.
"""
import logging
import llama_cpp as _llama_cpp


class _MockLlama:
    def __init__(self, model_path, **kwargs):
        logging.info("[MOCK LLM] Modelo simulado carregado (sem ficheiro GGUF)")

    def create_chat_completion(self, messages, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "S: SERVER01 | T: CPU Alert | L: CRITICAL | D: CPU 95%"
                        )
                    }
                }
            ]
        }


# Substituir a classe real pelo mock
_llama_cpp.Llama = _MockLlama
logging.info("[MOCK LLM] llama_cpp.Llama substituído por mock")
