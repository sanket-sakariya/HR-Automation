import os
import uvicorn

from app.main import create_app

app = create_app()

if __name__ == "__main__":

    reload_dirs = ["app"] if os.getenv("ENV") == "development" else None

    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8801")),
        reload=os.getenv("ENV", "development") == "development",
        reload_dirs=reload_dirs,
        reload_excludes=["alembic/versions/*"],
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    ) 