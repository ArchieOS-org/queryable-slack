"""
Minimal test handler for Vercel Python serverless function.
Context7 best practice: Start with minimal handler to verify deployment works.
"""

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "ok", "message": "Test handler works"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "ok", "message": "POST test handler works"}
        self.wfile.write(json.dumps(response).encode('utf-8'))

