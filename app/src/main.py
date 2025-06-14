from os import environ
import logging
import uuid
from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from prometheus_client import make_asgi_app, CONTENT_TYPE_LATEST, Counter, generate_latest
from langchain_core.runnables import ConfigurableFieldSpec, RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate
)

from src.chat_memory import get_chat_history, get_redis_chat_history, get_redis_chat_ids
from src.chat_model import DockerModelRunnerChatModel


logger = logging.getLogger("APP.main")
logger.setLevel(logging.DEBUG)
app = FastAPI()
# metrics_app = make_asgi_app()
# app.mount("/metrics", metrics_app)
metrics = {}
reset_counter = 0

llm_server_url = environ.get("LLM_SERVER_URL", "http://localhost:12434/engines/llama.cpp/v1")
llm_model = environ.get("LLM_SERVER_MODEL", "hf.co/bartowski/meta-llama-3.1-8b-instruct-gguf:q6_k")

chat_map = {}


llm = DockerModelRunnerChatModel(
    model=llm_model,
    openai_api_base=llm_server_url, 
    openai_api_key="sk-fake-key",
)

prompt = ChatPromptTemplate(
    [
        SystemMessagePromptTemplate.from_template(
            "You are a helpful assistant. You will answer questions based on the provided context."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessagePromptTemplate.from_template("{prompt}"),
    ]
)

chain = prompt | llm

chain_short_buffer = RunnableWithMessageHistory(
    chain,
    get_session_history=lambda session_id, k: get_chat_history(chat_map, session_id, k),
    input_messages_key="prompt",
    history_messages_key="chat_history",
    history_factory_config=[
        ConfigurableFieldSpec(
            id="session_id",
            annotation=str,
            name="Session ID",
            description="The session ID to use for the chat history",
            default="id_default",
        ),
        ConfigurableFieldSpec(
            id="k",
            annotation=int,
            name="k",
            description="The number of messages to keep in the history",
            default=8,
        )
    ]
)

chain = RunnableWithMessageHistory(
    chain, get_redis_chat_history, input_messages_key="prompt", history_messages_key="chat_history"
)
class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat/{chat_id}")
def chat_with_id(chat_id: str, request: ChatRequest):
    logger.debug(request)
    response = chain.invoke(
        {"prompt": request.prompt},
        config={"configurable": {"session_id": chat_id}}
    )
    save_metrics(response.response_metadata["timings"])
    return {"response": response, "session_id": chat_id}


@app.post("/chat")
def chat(request: ChatRequest):
    chat_id = str(uuid.uuid4())
    return chat_with_id(chat_id, request)


@app.post("/chat/short/{k}")
def chat(request: ChatRequest, k: int = 8):
    response = chain_short_buffer.invoke(
        {"prompt": request.prompt},
        config={"configurable": {"session_id": "id_default", "k": k}}
    )
    save_metrics(response.response_metadata["timings"])
    return response


@app.get("/clear/{chat_id}")
def clear_chat_history(chat_id: str):
    chat_history = get_redis_chat_history(chat_id)
    chat_history.clear()
    return {"message": "Chat history cleared"}


@app.get("/chats")
def list_chat_histories():
    ids = get_redis_chat_ids()
    logger.debug(ids)
    if not ids:
        return {"message": "No chat histories found"}
    return {"chat_ids": ids}


def save_metrics(timings):
    global metrics
    if timings:
        for key, value in timings.items():
            if isinstance(value, (int, float)):
                if key not in metrics:
                    metrics[key] = Counter(key, f"LLM {key} timing")
                metrics[key].inc(value)
            else:
                logging.warning(f"Skipping non-numeric timing value: {value}")

# It would be unneccessary if it wasn't docker model runner, but i.e. llama.cpp server
@app.get("/metrics")
def get_metrics():
    global metrics, reset_counter
    response = Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
    # if reset_counter > 3:
    for v in metrics.values():
        v.reset()
    #     reset_counter = 0
    # else:
    #     reset_counter += 1
    return response