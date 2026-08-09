import os
import pathlib
import sys

# Ensure REPO_ROOT and src/ are in sys.path
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Default environment variables for tests
os.environ.setdefault("SUBWAY_SETUP_PIN", "123456")
os.environ.setdefault("WEB_CONFIG_SECRET_KEY", "test-secret")
