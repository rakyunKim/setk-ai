from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langgraph.prebuilt import ToolNode

from agent.utils.tools.tools import tools


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    if model_name == "openai":
        model = ChatOpenAI(temperature=0.5, model_name="gpt-4o-mini")
        model = model.bind_tools(tools)
    elif model_name == "anthropic":
        model =  ChatAnthropic(temperature=0.5, model_name="claude-3-sonnet-20240229")
        model = model.bind_tools(tools)
    elif model_name == "ollama":
        model = ChatOllama(
            model="gpt-oss:20b",
            temperature=0.5,
            base_url="http://localhost:11434"
        )
        # Ollama는 도구 바인딩 없이 사용
    else:
        raise Exception(f"지원하지 않는 모델입니다.: {model_name}")

    return model




# Define the function to execute tools
tool_node = ToolNode(tools)
