import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.tools.rag_tools import search_knowledge_base
from app.tools.weather_tools import get_current_weather

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
AGENT_RECURSION_LIMIT = max(8, int(os.getenv("AGENT_RECURSION_LIMIT", "16")))


def create_agent_instance(tools: list | None = None ):

    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
        stream_usage=True,
    )

    selected_tools = tools if tools is not None else [
        get_current_weather,
        search_knowledge_base,
    ]

    agent = create_agent(
        model=model,
        tools=selected_tools,
        system_prompt=(
            "You are a helpful AI assistant named 知源.You were developed by Rudy."
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


def get_agent(tools: list | None = None, extra_tools: list | None = None):
    agent, _ = create_agent_instance(tools=tools, extra_tools=extra_tools)
    return agent


def get_model():
    return model


def get_recursion_limit() -> int:
    return AGENT_RECURSION_LIMIT



