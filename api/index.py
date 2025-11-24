"""
Vercel serverless function entry point.

Exposes a lazy-loading ASGI app to handle requests.
Removes Mangum dependency to avoid AWS Lambda event format issues on Vercel.
Handles path stripping for /api prefix.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
import os
import sys
import logging
import traceback
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.index")

os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

# Add parent directory to Python path
try:
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
except Exception:
    pass

class LazyASGIApp:
    def __init__(self):
        self.app = None
        self.init_error = None
        
    async def __call__(self, scope, receive, send):
        # Only handle http/lifespan scopes
        if scope['type'] not in ('http', 'websocket', 'lifespan'):
            return

        # Handle path stripping for Vercel
        # Vercel passes the full path including /api prefix
        # FastAPI expects paths relative to root
        if scope['type'] == 'http':
            path = scope.get('path', '')
            original_path = path
            if path.startswith('/api'):
                path = path[4:]
                # Ensure path starts with /
                if not path.startswith('/'):
                    path = '/' + path
            scope['path'] = path
            logger.info(f"Handling request: {scope['method']} {path} (original: {original_path})")
            
            # Handle /health endpoint directly here before trying to load web_api
            # This ensures health checks work even if web_api fails to initialize
            if path == '/health' or path == '/api/health':
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'access-control-allow-origin', b'*'),
                    ],
                })
                health_response = {
                    "status": "healthy",
                    "message": "API is running",
                    "web_api_initialized": self.app is not None
                }
                if self.init_error:
                    health_response["init_error"] = self.init_error
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps(health_response).encode('utf-8'),
                })
                return

        if self.app is None:
            try:
                logger.info("Initializing web_api...")
                # Import web_api
                import web_api
                
                # Check for initialization error captured in web_api
                if getattr(web_api, 'INIT_ERROR', None):
                    error_msg = f"web_api failed to initialize: {web_api.INIT_ERROR}"
                    logger.error(error_msg)
                    self.init_error = web_api.INIT_ERROR
                    # Don't raise - let requests through to error handler
                
                if not hasattr(web_api, 'app') or web_api.app is None:
                    raise ImportError("web_api module does not have 'app' attribute or app is None")
                
                self.app = web_api.app
                logger.info("✅ web_api initialized")
            except Exception as e:
                logger.error(f"❌ Initialization failed: {e}", exc_info=True)
                self.init_error = f"Initialization Failed: {e}\n{traceback.format_exc()}"
                
                # Define error app
                async def error_app(scope, receive, send):
                    if scope['type'] == 'http':
                        # Return 200 OK to ensure the error body is visible
                        await send({
                            'type': 'http.response.start',
                            'status': 200,
                            'headers': [
                                (b'content-type', b'application/json'),
                                (b'access-control-allow-origin', b'*'),
                            ],
                        })
                        
                        # Try to find what paths are available
                        try:
                            import pkg_resources
                            installed_packages = {p.key: p.version for p in pkg_resources.working_set}
                        except:
                            installed_packages = "Could not list packages"

                        await send({
                            'type': 'http.response.body',
                            'body': json.dumps({
                                "error": "Server Initialization Error",
                                "detail": str(e),
                                "traceback": traceback.format_exc(),
                                "sys_path": sys.path,
                                "installed_packages_sample": str(installed_packages)[:1000] if isinstance(installed_packages, dict) else str(installed_packages)
                            }, default=str).encode('utf-8'),
                        })
                    elif scope['type'] == 'lifespan':
                        # Handle lifespan protocol to prevent startup crashes
                        while True:
                            message = await receive()
                            if message['type'] == 'lifespan.startup':
                                await send({'type': 'lifespan.startup.complete'})
                            elif message['type'] == 'lifespan.shutdown':
                                await send({'type': 'lifespan.shutdown.complete'})
                                return
                self.app = error_app

        await self.app(scope, receive, send)

# Expose the ASGI app
app = LazyASGIApp()
