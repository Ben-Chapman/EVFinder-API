from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import genesis, hyundai

app = FastAPI()

app.include_router(genesis.router)
app.include_router(hyundai.router)

# CORS support
origins = [
    "https://theevfinder.com",
    "https://www.theevfinder.com",
    "http://dev.theevfinder.com",
    "http://bs-local.com:8080",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
