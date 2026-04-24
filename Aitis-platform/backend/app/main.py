import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.database import Base, engine

app = FastAPI(
    title="AI Test Intelligence API",
    version="0.1.0",
)

# CORS configuration - support both local development and Docker deployment
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://frontend:3000",  # Docker internal network
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Add environment-specific origins
env = os.getenv("ENV", "development")
if env == "production":
    # Add your production domain here
    origins.extend([
        "https://your-domain.com",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(router, prefix="/api")