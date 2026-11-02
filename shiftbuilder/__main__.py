"""Start the app: python -m shiftbuilder [--port 8037]"""
import sys

from .web import create_app

port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8037
create_app().serve(port)
