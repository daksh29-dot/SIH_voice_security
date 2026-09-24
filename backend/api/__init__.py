"""
API subpackage for Project VISOR.
Includes FastAPI WebSocket endpoints for streaming audio ingest.
"""

from backend.api.websocket import router, app

__all__ = ["router", "app"]
