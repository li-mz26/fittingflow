#!/usr/bin/env python3
"""简单的 HTTP 服务器，不依赖外部包"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class SimpleHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>FittingFlow</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 50px auto; text-align: center; }
        h1 { color: #667eea; }
        .status { padding: 20px; background: #f0f0f0; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>FittingFlow</h1>
    <div class="status">
        <p>Minimal Workflow Orchestration</p>
        <p>Server running...</p>
    </div>
    <p>Check <a href="https://github.com/li-mz26/fittingflow">GitHub</a> for more</p>
</body>
</html>
            """
            self.wfile.write(html.encode('utf-8'))
        elif self.path == "/workflows":
            self._send_json({"workflows": []})
        else:
            self._send_json({"name": "FittingFlow", "version": "0.1.0"})
    
    def do_POST(self):
        self._send_json({"message": "OK"})


def main():
    port = 8000
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"🚀 FittingFlow simple server starting at http://localhost:{port}")
    print("   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
