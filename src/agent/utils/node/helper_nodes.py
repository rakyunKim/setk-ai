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

# Define the function that determines whether to continue or not
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    # If there are no tool calls, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"


# Define the function that calls the model
def call_model(state, config):
    messages = state["messages"]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    model_name = config.get('configurable', {}).get("model_name", "openai")
    model = _get_model(model_name)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

# Define the function to execute tools
tool_node = ToolNode(tools)
