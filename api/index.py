import sys
from pathlib import Path

# Ensure project root is in sys.path so backend and ml modules import correctly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app

# Vercel ASGI / WSGI entry point
handler = app
