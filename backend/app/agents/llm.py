from types import SimpleNamespace

from openai import OpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import settings


class QwenLLM:
    def __init__(self, temperature: float = 0.2):
        self.temperature = temperature
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )

    def invoke(self, messages):
        converted_messages = []

        if isinstance(messages, str):
            converted_messages.append({
                "role": "user",
                "content": messages
            })
        else:
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    role = "system"
                elif isinstance(msg, AIMessage):
                    role = "assistant"
                elif isinstance(msg, HumanMessage):
                    role = "user"
                else:
                    role = "user"

                converted_messages.append({
                    "role": role,
                    "content": str(getattr(msg, "content", msg))
                })

        response = self.client.chat.completions.create(
            model=settings.qwen_model,
            messages=converted_messages,
            temperature=self.temperature,
        )

        content = response.choices[0].message.content
        return SimpleNamespace(content=content)


def get_llm(temperature: float = 0.2):
    if not settings.dashscope_api_key:
        return None

    return QwenLLM(temperature=temperature)