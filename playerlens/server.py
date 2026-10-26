"""Start Agora's production ASGI server locally or in Azure Container Apps."""
import os


def main():
    import uvicorn
    uvicorn.run("playerlens.api:create_app",factory=True,host="0.0.0.0",port=int(os.getenv("PORT","8080")),
                access_log=False,proxy_headers=False,timeout_keep_alive=5,limit_concurrency=128)


if __name__ == "__main__":
    main()
