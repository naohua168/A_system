"""Simple reverse proxy: serves frontend dist + proxies /api to backend"""
import http.server
import urllib.request
import os
import sys

FRONTEND_DIR = 'f:/bs/A_system/frontend/dist'
BACKEND_URL = 'http://localhost:8082'
PORT = 5173

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            # Proxy to backend
            target = BACKEND_URL + self.path
            try:
                req = urllib.request.Request(target, headers=dict(self.headers))
                resp = urllib.request.urlopen(req, timeout=10)
                self.send_response(resp.status)
                # Forward response headers
                for key, val in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'content-encoding', 'content-length'):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                for key, val in e.headers.items():
                    if key.lower() not in ('transfer-encoding', 'content-encoding', 'content-length'):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(e.read())
            except Exception as e:
                self.send_error(502, f'Proxy error: {e}')
        else:
            # Serve static files, with SPA fallback
            filepath = self.translate_path(self.path)
            if not os.path.exists(filepath) or os.path.isdir(filepath):
                self.path = '/index.html'
            super().do_GET()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def do_POST(self):
        if self.path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            target = BACKEND_URL + self.path
            try:
                req = urllib.request.Request(target, data=body, headers=dict(self.headers), method='POST')
                resp = urllib.request.urlopen(req, timeout=10)
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'content-encoding', 'content-length'):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(resp.read())
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                for key, val in e.headers.items():
                    if key.lower() not in ('transfer-encoding', 'content-encoding', 'content-length'):
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(e.read())
            except Exception as e:
                self.send_error(502, f'Proxy error: {e}')
        else:
            self.send_error(404)

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    print(f'Server: http://localhost:{PORT}')
    print(f'Static: {FRONTEND_DIR}')
    print(f'API proxy: /api/* -> {BACKEND_URL}/*')
    server.serve_forever()
