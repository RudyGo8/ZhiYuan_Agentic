from langchain_core.messages import SystemMessage

from app.agent.factory import get_model


def summarize_old_messages(model, messages: list) -> str:
    old_conversation = "\n".join(
        [f"{'用户' if msg.type == 'human' else 'AI'}: {msg.content}" for msg in messages]
    )

    summary_prompt = (
        "请总结以下对话关键信息（用户偏好、重要事实、待办事项）。\n\n"
        f"{old_conversation}\n\n"
        "请输出简洁摘要。"
    )

    summary = model.invoke(summary_prompt).content
    return summary


def prepare_messages(messages: list) -> list:
    if len(messages) <= 50:
        return messages
    summary = summarize_old_messages(get_model(), messages[:40])
    return [SystemMessage(content=f"之前的对话摘要：\n{summary}")] + messages[40:]
