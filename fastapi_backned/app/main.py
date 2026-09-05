from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
from app.core.config import settings
from app.api import routes_buyer, routes_merchant, routes_payments, routes_audit, routes_campaign


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Agent Commerce Gateway",
    description="AI-powered commerce with deterministic policy enforcement",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_buyer.router)
app.include_router(routes_merchant.router)
app.include_router(routes_payments.router)
app.include_router(routes_audit.router)
app.include_router(routes_campaign.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-commerce-gateway"}


@app.get("/")
async def root():
    return {
        "service": "Agent Commerce Gateway",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)