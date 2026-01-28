"""
Run script for Technical Interview Service
Starts the server on port 8100
"""

import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Starting Technical Interview Service")
    print("=" * 60)
    print("📍 URL: http://localhost:8100")
    print("📖 API Docs: http://localhost:8100/docs")
    print("🔗 Health Check: http://localhost:8100/health")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        log_level="info"
    )
