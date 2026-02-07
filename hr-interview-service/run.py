"""
Run the HR Interview Service.
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8200,
        reload=True,
        log_level="info"
    )
