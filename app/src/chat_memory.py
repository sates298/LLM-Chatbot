from os import environ
from pydantic import BaseModel, Field
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_redis import RedisChatMessageHistory
from langchain_core.messages import BaseMessage

REDIS_URL = environ.get("REDIS_URL", "redis://redis:6379")

class BufferWindowMessageHistory(BaseChatMessageHistory, BaseModel):
    messages: list[BaseMessage] = Field(default_factory=list)
    k: int = Field(default_factory=int)

    def __init__(self, k: int):
        super().__init__(k=k)

    def add_messages(self, messages: list[BaseMessage]) -> None:
        self.messages.extend(messages)
        self.messages = self.messages[-self.k:]

    def clear(self) -> None:
        """Clear the history."""
        self.messages = []


def get_chat_history(chat_map: dict, session_id: str, k: int = 4) -> BufferWindowMessageHistory:
    print(f"get_chat_history called with session_id={session_id} and k={k}")
    if session_id not in chat_map:
        # if session ID doesn't exist, create a new chat history
        chat_map[session_id] = BufferWindowMessageHistory(k=k)
    # remove anything beyond the last
    return chat_map[session_id]


def get_redis_chat_history(session_id: str) -> RedisChatMessageHistory:
    """Get a Redis chat history object for the given session ID."""
    return RedisChatMessageHistory(
        session_id=session_id,
        redis_url=REDIS_URL,
    )