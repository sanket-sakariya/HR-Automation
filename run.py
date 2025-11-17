import os
import uvicorn

from dotenv import load_dotenv

from app.main import create_app

load_dotenv(dotenv_path='.env.dev')

app = create_app()

if __name__ == "__main__":

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