import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())
# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from server import app
    print("Routes registered on app:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"{route.methods if hasattr(route, 'methods') else 'SSE'} - {route.path}")
except Exception as e:
    print(f"Error: {e}")
