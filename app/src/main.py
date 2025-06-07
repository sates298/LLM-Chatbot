from os import environ
from fastapi import FastAPI, Response
from pydantic import BaseModel
from prometheus_client import make_asgi_app, CONTENT_TYPE_LATEST, Counter, generate_latest
from src.chat_model import DockerModelRunnerChatModel


app = FastAPI()
# metrics_app = make_asgi_app()
# app.mount("/metrics", metrics_app)
metrics = {}
reset_counter = 0

llm_server_url = environ.get("LLM_SERVER_URL", "http://localhost:12434/engines/llama.cpp/v1")
llm_model = environ.get("LLM_SERVER_MODEL", "hf.co/bartowski/meta-llama-3.1-8b-instruct-gguf:q6_k")

llm = DockerModelRunnerChatModel(
    model=llm_model,
    openai_api_base=llm_server_url, 
    openai_api_key="sk-fake-key",
)

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
def chat(prompt: ChatRequest):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt.prompt}
    ]
    response = llm.invoke(messages)
    # print(response)
    save_metrics(response.response_metadata["timings"])
    return response
    
def save_metrics(timings):
    """
    Save the metrics to Prometheus.
    """
    if timings:
        for key, value in timings.items():
            if isinstance(value, (int, float)):
                if key not in metrics:
                    metrics[key] = Counter(key, f"LLM {key} timing")
                metrics[key].inc(value)
            else:
                print(f"Skipping non-numeric timing value: {value}")

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