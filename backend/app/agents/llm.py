import os
import time
import threading

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


_call_lock = threading.Lock()
_last_call_time = 0.0

# Free tier của bạn đang báo quota 5 request/phút.
# 60 / 5 = 12 giây. Để an toàn, mình để 13 giây.
MIN_SECONDS_BETWEEN_CALLS = 5.0


class RateLimitedLLM:
    def __init__(self, llm):
        self.llm = llm

    def invoke(self, messages):
        global _last_call_time

        with _call_lock:
            now = time.time()
            elapsed = now - _last_call_time
            wait_time = MIN_SECONDS_BETWEEN_CALLS - elapsed

            if wait_time > 0:
                print(f"[Gemini Rate Limit] Waiting {wait_time:.1f}s before next request...")
                time.sleep(wait_time)

            _last_call_time = time.time()

        return self.llm.invoke(messages)


def get_llm(temperature: float = 0.2):
    """
    Return Gemini model from Google AI Studio.
    If GOOGLE_API_KEY is missing, return None so nodes can use fallback demo logic.
    """
    if not settings.google_api_key:
        return None

    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=temperature,
        max_retries=2,
    )

    return RateLimitedLLM(llm)