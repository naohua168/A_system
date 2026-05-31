FROM stock-data-collector:latest

# 复制所有缠论相关代码
COPY analysis-algorithms/chanlun_server.py /app/chanlun_server.py
COPY analysis-algorithms/chanlun_bridge.py /app/chanlun_bridge.py
COPY analysis-algorithms/chanlun/ /app/chanlun/
COPY analysis-algorithms/data/ /app/data/

EXPOSE 8899

ENTRYPOINT ["python3", "/app/chanlun_server.py"]
