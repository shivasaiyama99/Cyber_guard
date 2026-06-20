import sys
import os

# Add backend directory to the path so we can import server
backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add backend/src directory to the path so we can import cyberguard
src_dir = os.path.join(backend_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Set Vercel environment flag
os.environ["IS_VERCEL"] = "true"

from server import app

class StripApiPrefixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path.startswith("/api"):
                new_path = path[4:]
                if not new_path.startswith("/"):
                    new_path = "/" + new_path
                scope["path"] = new_path
                
                raw_path = scope.get("raw_path", b"")
                if raw_path.startswith(b"/api"):
                    new_raw_path = raw_path[4:]
                    if not new_raw_path.startswith(b"/"):
                        new_raw_path = b"/" + new_raw_path
                    scope["raw_path"] = new_raw_path
        await self.app(scope, receive, send)

app = StripApiPrefixMiddleware(app)
