import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_PATH = os.path.join(ROOT, "backend")

for candidate in ["/app", BACKEND_PATH]:
    if candidate not in sys.path and os.path.exists(candidate):
        sys.path.insert(0, candidate)
