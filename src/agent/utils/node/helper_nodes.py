from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from agent.utils.tools.tools import tools
from src.static.prompt import SYSTEM_PROMPT


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    if model_name == "openai":
        model = ChatOpenAI(temperature=0.5, model_name="gpt-4o-mini")
    elif model_name == "anthropic":
        model =  ChatAnthropic(temperature=0.5, model_name="claude-3-sonnet-20240229")
    else:
        raise Exception(f"지원하지 않는 모델입니다.: {model_name}")

    model = model.bind_tools(tools)
    return model




# Define the function to execute tools
tool_node = ToolNode(tools)
