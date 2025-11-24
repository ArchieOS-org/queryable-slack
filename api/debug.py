from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import traceback

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        debug_info = {
            "python_version": sys.version,
            "sys.path": sys.path,
            "cwd": os.getcwd(),
            "env_keys": list(os.environ.keys()),
            "modules": list(sys.modules.keys()),
            "web_api_importable": False,
            "import_errors": {}
        }
        
        # Try imports
        try:
            import web_api
            debug_info["web_api_importable"] = True
            debug_info["web_api_file"] = web_api.__file__
        except ImportError as e:
            debug_info["import_errors"]["web_api"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        except Exception as e:
            debug_info["import_errors"]["web_api_general"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            
        self.wfile.write(json.dumps(debug_info, default=str).encode('utf-8'))

