from os import environ
import logging
from fastapi import FastAPI, Response
from pydantic import BaseModel
from prometheus_client import make_asgi_app, CONTENT_TYPE_LATEST, Counter, generate_latest
from langchain_core.runnables import ConfigurableFieldSpec, RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate
)

from src.chat_memory import get_chat_history
from src.chat_model import DockerModelRunnerChatModel


logger = logging.getLogger("APP.main")
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

chain = RunnableWithMessageHistory(
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

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
def chat(request: ChatRequest):
    response = chain.invoke(
        {"prompt": request.prompt},
        config={"configurable": {"session_id": "id_default", "k": 8}}
    )
    # print(response)
    save_metrics(response.response_metadata["timings"])
    return response
  
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