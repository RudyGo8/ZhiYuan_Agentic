from app.config import logger


def build_turn_prompt(user_text: str, user_id: str) -> str:
    question = (user_text or "").strip()
    if not question:
        logger.warning("empty_turn_prompt user_id=%s", user_id)

    turn_prompt = "\n".join(
        [
            f"User question: {question}",
        ]
    )
    return turn_prompt
