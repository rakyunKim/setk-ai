import os

from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict

# 기본 AI 모델 설정
DEFAULT_MODEL = os.getenv("AI_MODEL", "openai")

class CustomConfigParam(TypedDict):
    model_name: str  # "openai", "anthropic", or "ollama"

class CustomConfig(RunnableConfig):
    configurable: CustomConfigParam