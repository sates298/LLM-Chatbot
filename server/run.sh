#!/bin/zsh


llama-server \
-m models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf \
--port 8080 \
--host 0.0.0.0 \
--metrics
