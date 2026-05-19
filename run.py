import os
import sys
import atexit
import signal
import subprocess
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from app.main import create_app

load_dotenv(dotenv_path=".env.dev")

app = create_app()

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Sub-services to launch in the background alongside the main app.
# Each entry: (label, working_directory, command_args)
SUB_SERVICES = [
    ("dynamic-form", BASE_DIR / "dynamic form", [sys.executable, "main.py"]),
    ("hr-interview-service", BASE_DIR / "hr-interview-service", [sys.executable, "main.py"]),
    ("realtime-ai-interview", BASE_DIR / "realtime-ai-interview", [sys.executable, "main.py"]),
    ("aptitude-test-service", BASE_DIR / "aptitude test service", [sys.executable, "main.py"]),
    ("technical-interview-service", BASE_DIR / "technical-interview-service", [sys.executable, "run.py"]),
]

_child_processes: list[subprocess.Popen] = []


def _start_sub_services() -> None:
    """Spawn each sub-service as a background subprocess."""
    for label, cwd, cmd in SUB_SERVICES:
        if not cwd.exists():
            print(f"[run.py] SKIP {label}: directory not found at {cwd}")
            continue

        log_path = LOG_DIR / f"{label}.log"
        log_file = open(log_path, "ab", buffering=0)
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # detach so Ctrl+C only hits parent first
                env=os.environ.copy(),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[run.py] FAILED to start {label}: {exc}")
            log_file.close()
            continue

        _child_processes.append(proc)
        print(f"[run.py] started {label} (pid={proc.pid}) -> {log_path}")


def _stop_sub_services(*_args) -> None:
    """Terminate every background sub-service we launched."""
    for proc in _child_processes:
        if proc.poll() is not None:
            continue
        try:
            print(f"[run.py] stopping pid={proc.pid}")
            proc.terminate()
        except Exception as exc:  # noqa: BLE001
            print(f"[run.py] terminate failed for pid={proc.pid}: {exc}")

    for proc in _child_processes:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(f"[run.py] force killing pid={proc.pid}")
            proc.kill()


if __name__ == "__main__":
    # Only spawn sub-services in the parent process. Under uvicorn reload the
    # WATCHFILES_RELOAD child re-imports this module; we don't want duplicates.
    if os.getenv("RUN_PY_CHILD") != "1":
        os.environ["RUN_PY_CHILD"] = "1"
        _start_sub_services()
        atexit.register(_stop_sub_services)
        signal.signal(signal.SIGTERM, _stop_sub_services)
        signal.signal(signal.SIGINT, _stop_sub_services)

    reload_dirs = ["app"] if os.getenv("ENV") == "development" else None

    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=int(os.getenv("APP_PORT", "8801")),
        reload=os.getenv("ENV", "development") == "development",
        reload_dirs=reload_dirs,
        reload_excludes=["alembic/versions/*"],
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
