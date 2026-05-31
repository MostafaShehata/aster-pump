from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import router
from app.logging_config import configure_logging
from app.rag.service import rag_service


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    configure_logging()
    logging.info("story.startup | creating FastAPI backend application")
    app = FastAPI(
        title="Aster Pump Aftercare Backend",
        description="FastAPI service that connects the React UI to agents, RAG, MCP tools, and a local model.",
        version="0.1.0",
    )

    # Useful for local development. Replace with exact origins for real deployment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup() -> None:
        """Create the demo RAG index when the backend starts."""

        logging.info("story.startup | building RAG index from local manuals")
        rag_service.ensure_index()
        logging.info("story.startup | backend ready: API, LangGraph, RAG, MCP client, Ollama client")

    app.include_router(router)
    logging.info("story.startup | API router registered prefix=/api")
    return app
