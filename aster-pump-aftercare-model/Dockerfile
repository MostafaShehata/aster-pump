FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODEL=qwen3:1.7b

COPY start-ollama.sh /usr/local/bin/start-ollama.sh
RUN chmod +x /usr/local/bin/start-ollama.sh

EXPOSE 11434

ENTRYPOINT ["/usr/local/bin/start-ollama.sh"]
