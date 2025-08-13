from functools import lru_cache
import os

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

# tools import 제거 - 실제로 사용하지 않음
# from agent.utils.tools.tools import tools


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    if model_name == "openai":
        model = ChatOpenAI(temperature=0.5, model_name="gpt-4o-mini")
        # model = model.bind_tools(tools)
    elif model_name == "anthropic":
        model =  ChatAnthropic(temperature=0.5, model_name="claude-3-sonnet-20240229")
        # model = model.bind_tools(tools)
    elif model_name == "ollama":
        model = ChatOllama(
            model="gpt-oss:20b",
            temperature=0.5,
            base_url="http://localhost:11434"
        )
    elif model_name == "gemini":
        # .env.local에서 GEMINI_API_KEY 읽기
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 .env.local에 설정되지 않았습니다.")
        
        model = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",  # 안정적이고 할당량 높은 모델 (15 RPM)
            temperature=0.5,
            google_api_key=api_key  # API 키 명시적 전달
        )
    else:
        raise Exception(f"지원하지 않는 모델입니다.: {model_name}")

    return model