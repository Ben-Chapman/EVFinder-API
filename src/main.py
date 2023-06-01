#!/usr/bin/python3
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    audi,
    bmw,
    chevrolet,
    ford,
    genesis,
    hyundai,
    kia,
    logger,
    volkswagen,
)

app = FastAPI(docs_url=None, redoc_url=None)

app.include_router(bmw.router)
app.include_router(audi.router)
app.include_router(chevrolet.router)
app.include_router(ford.router)
app.include_router(genesis.router)
app.include_router(hyundai.router)
app.include_router(kia.router)
app.include_router(volkswagen.router)

app.include_router(logger.router)

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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    server.run()
