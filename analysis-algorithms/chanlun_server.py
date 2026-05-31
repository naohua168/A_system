#!/usr/bin/env python3
"""缠论 HTTP API 服务 — 绕过 Java 直接从 Redis 读取正确的 K 线数据"""
import http.server
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# 添加算法路径
sys.path.insert(0, '/analysis-algorithms')
from chanlun_bridge import get_chanlun_data

REDIS_HOST = os.environ.get('SPRING_REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('SPRING_REDIS_PORT', '6379'))


class ChanlunHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) >= 2 and path_parts[-1] == 'chanlun':
            code = path_parts[-2]
            days = int(params.get('days', [365])[0])
            req_type = params.get('type', ['stock'])[0]
            prefer_index = req_type == 'index'

            try:
                result = get_chanlun_data(code, days, prefer_index=prefer_index)
                self._json_response(200, result)
            except Exception as e:
                self._json_response(500, {"error": str(e)})
        else:
            self._json_response(404, {"error": "not found"})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def log_message(self, format, *args):
        pass  # 静默


if __name__ == '__main__':
    port = 8899
    server = http.server.HTTPServer(('0.0.0.0', port), ChanlunHandler)
    print(f"缠论HTTP服务启动在端口 {port}")
    server.serve_forever()
