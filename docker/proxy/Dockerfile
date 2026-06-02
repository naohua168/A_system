FROM stock-data-collector:latest
COPY proxy_server.py /app/proxy.py
EXPOSE 8899
CMD ["python3", "/app/proxy.py", "8899"]
