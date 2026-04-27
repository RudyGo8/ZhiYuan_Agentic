from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


class ConversationStorage:
    @staticmethod
    def _messages_cache_key(user_id: str, session_id: str) -> str:
        return f"chat_messages:{user_id}:{session_id}"

    @staticmethod
    def _sessions_cache_key(user_id: str) -> str:
        return f"chat_sessions:{user_id}"

    @staticmethod
    def _to_langchain_messages(records: list[dict]) -> list:
        messages = []
        for msg_data in records:
            msg_type = msg_data.get("type")
            content = msg_data.get("content", "")
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
        return messages

    def save(
        self,
        user_id: str,
        session_id: str,
        messages: list,
        metadata: dict | None = None,
        extra_message_data: list | None = None,
    ):
        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_chat_message import ChatMessage
        from app.models.db_chat_session import ChatSession
        from app.models.db_user import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return

            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                session = ChatSession(user_id=user.id, session_id=session_id, metadata_json=metadata or {})
                db.add(session)
                db.flush()
            else:
                session.metadata_json = metadata or {}

            incoming_rows: list[dict] = []
            for idx, msg in enumerate(messages):
                rag_trace = None
                if extra_message_data and idx < len(extra_message_data):
                    extra = extra_message_data[idx] or {}
                    rag_trace = extra.get("rag_trace")
                incoming_rows.append(
                    {
                        "message_type": msg.type,
                        "content": str(msg.content),
                        "rag_trace": rag_trace,
                    }
                )

            existing_rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_ref_id == session.id)
                .order_by(ChatMessage.id.asc())
                .all()
            )

            def _same_message(lhs: dict, rhs: ChatMessage) -> bool:
                return lhs["message_type"] == rhs.message_type and lhs["content"] == rhs.content

            can_append = (
                len(existing_rows) <= len(incoming_rows)
                and all(_same_message(incoming_rows[idx], row) for idx, row in enumerate(existing_rows))
            )

            now = datetime.now()
            if can_append:
                for idx in range(len(existing_rows), len(incoming_rows)):
                    payload = incoming_rows[idx]
                    db.add(
                        ChatMessage(
                            session_ref_id=session.id,
                            message_type=payload["message_type"],
                            content=payload["content"],
                            rag_trace=payload["rag_trace"],
                        )
                    )
            else:
                db.query(ChatMessage).filter(ChatMessage.session_ref_id == session.id).delete(synchronize_session=False)
                for payload in incoming_rows:
                    db.add(
                        ChatMessage(
                            session_ref_id=session.id,
                            message_type=payload["message_type"],
                            content=payload["content"],
                            rag_trace=payload["rag_trace"],
                        )
                    )

            session.update_time = now
            db.commit()
            cache.delete(self._messages_cache_key(user_id, session_id))
            cache.delete(self._sessions_cache_key(user_id))
        finally:
            db.close()

    def load(self, user_id: str, session_id: str) -> list:
        from app.cache import cache

        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return self._to_langchain_messages(cached)

        records = self.get_session_messages(user_id, session_id)
        return self._to_langchain_messages(records)

    def list_sessions(self, user_id: str) -> list:
        return [item["session_id"] for item in self.list_session_infos(user_id)]

    def list_session_infos(self, user_id: str) -> list[dict]:
        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_chat_message import ChatMessage
        from app.models.db_chat_session import ChatSession
        from app.models.db_user import User

        cached = cache.get_json(self._sessions_cache_key(user_id))
        if cached is not None:
            return cached

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []

            sessions = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id)
                .order_by(ChatSession.update_time.desc())
                .all()
            )
            result = []
            for session in sessions:
                count = db.query(ChatMessage).filter(ChatMessage.session_ref_id == session.id).count()
                result.append(
                    {
                        "session_id": session.session_id,
                        "updated_at": session.update_time.isoformat() if session.update_time else "",
                        "message_count": count,
                    }
                )
            cache.set_json(self._sessions_cache_key(user_id), result)
            return result
        finally:
            db.close()

    def get_session_messages(self, user_id: str, session_id: str) -> list[dict]:
        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_chat_message import ChatMessage
        from app.models.db_chat_session import ChatSession
        from app.models.db_user import User

        cached = cache.get_json(self._messages_cache_key(user_id, session_id))
        if cached is not None:
            return cached

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return []
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return []

            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_ref_id == session.id)
                .order_by(ChatMessage.id.asc())
                .all()
            )
            result = [
                {
                    "type": row.message_type,
                    "content": row.content,
                    "timestamp": row.create_time.isoformat() if row.create_time else "",
                    "rag_trace": row.rag_trace,
                }
                for row in rows
            ]
            cache.set_json(self._messages_cache_key(user_id, session_id), result)
            return result
        finally:
            db.close()

    def delete_session(self, user_id: str, session_id: str) -> bool:
        from app.cache import cache
        from app.database import SessionLocal
        from app.models.db_chat_session import ChatSession
        from app.models.db_user import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == user_id).first()
            if not user:
                return False
            session = (
                db.query(ChatSession)
                .filter(ChatSession.user_id == user.id, ChatSession.session_id == session_id)
                .first()
            )
            if not session:
                return False

            db.delete(session)
            db.commit()
            cache.delete(self._messages_cache_key(user_id, session_id))
            cache.delete(self._sessions_cache_key(user_id))
            return True
        finally:
            db.close()


conversation_service = ConversationStorage()
