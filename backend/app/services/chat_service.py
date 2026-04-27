'''
@create_time: 2025/09/27
@Author: GeChao
@File: chat_service.py
'''
from app.agent import chat_with_agent_stream, storage


class ChatService:
    """聊天业务编排层。"""
    @staticmethod
    def stream_chat(user_text: str, user_id: str, session_id: str):
        return chat_with_agent_stream(user_text, user_id, session_id)

    @staticmethod
    def get_session_messages(user_id: str, session_id: str) -> list[dict]:
        return storage.get_session_messages(user_id, session_id)

    @staticmethod
    def get_session_list(user_id: str) -> list[dict]:
        return storage.list_session_infos(user_id)

    @staticmethod
    def delete_session(user_id: str, session_id: str) -> bool:
        return storage.delete_session(user_id, session_id)


chat_service = ChatService()
