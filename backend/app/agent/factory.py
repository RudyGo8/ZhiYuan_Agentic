import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.mcp.agent_tools import get_enabled_mcp_tools
from app.tools import get_current_weather, search_knowledge_base

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
AGENT_RECURSION_LIMIT = max(8, int(os.getenv("AGENT_RECURSION_LIMIT", "16")))


def create_agent_instance(extra_tools: list | None = None):
    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    tools = [get_current_weather, search_knowledge_base] + (extra_tools or [])
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "You are a helpful AI assistant named 鐭ユ簮 Assistant.You were developed by Rudy."
            "Use search_knowledge_base when the user asks about uploaded documents, project knowledge, internal knowledge, or questions that require evidence grounding.For greetings, "
            "simple reasoning, general programming knowledge, or casual questions, answer directly without calling search_knowledge_base."
            "If search_knowledge_base returns TOOL_CALL_LIMIT_REACHED or no relevant documents, do not retry it; proceed with existing evidence. "
            "When the user needs latest status/change/alerts, you may call available MCP read-only tools. "
            "Avoid repeatedly calling the same MCP source unless new evidence is required. "
            "For weather questions, use get_current_weather when current weather information is needed. "
            "If evidence is insufficient, explicitly state limitations."
        ),
    )
    return agent, model


agent, model = create_agent_instance()


def get_agent():
    return agent


def get_model():
    return model


def get_recursion_limit() -> int:
    return AGENT_RECURSION_LIMIT


def rebuild_agent_with_external_tools() -> list[str]:
    global agent, model
    extra_tools = get_enabled_mcp_tools()
    agent, model = create_agent_instance(extra_tools=extra_tools)
    return [getattr(item, "__name__", getattr(item, "name", "unknown")) for item in extra_tools]
