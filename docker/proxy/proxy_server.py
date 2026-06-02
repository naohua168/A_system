"""Minimal HTTP forward proxy for API access"""
import socketserver, http.server, urllib.request
import socket, sys, threading

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req = urllib.request.Request(self.path, headers=dict(self.headers))
            resp = urllib.request.urlopen(req, timeout=30)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as e:
            self.send_error(502, str(e))

    def do_CONNECT(self):
        host, port = self.path.split(':')
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(30)
            s.connect((host, int(port)))
            self.send_response(200, 'Connection Established')
            self.end_headers()
            t1 = threading.Thread(target=self._tunnel, args=(self.rfile, s), daemon=True)
            t2 = threading.Thread(target=self._tunnel, args=(s, self.wfile), daemon=True)
            t1.start(); t2.start()
            t1.join(); t2.join()
            s.close()
        except Exception as e:
            try: self.send_error(502, str(e))
            except: pass

    def _tunnel(self, src, dst):
        try:
            while True:
                data = src.read(65536)
                if not data: break
                dst.sendall(data)
        except: pass

    def log_message(self, *a): pass

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    s = socketserver.ThreadingTCPServer(('0.0.0.0', port), ProxyHandler)
    s.allow_reuse_address = True
    print(f'Proxy running on port {port}')
    s.serve_forever()
