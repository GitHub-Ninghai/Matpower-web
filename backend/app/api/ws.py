"""
WebSocket Endpoints
Real-time communication for simulation progress updates
"""
import json
import logging
from typing import Dict, Any, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from app.models.schemas import SimulationProgress

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
_active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manager for WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to {client_id}: {e}")
                    disconnected.add(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, client_id)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        for client_id, connections in self.active_connections.items():
            disconnected = set()
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to {client_id}: {e}")
                    disconnected.add(connection)

            for conn in disconnected:
                self.disconnect(conn, client_id)

    async def send_progress_update(
        self,
        task_id: str,
        client_id: str,
        status: str,
        progress: float,
        message: str = ""
    ):
        """Send a simulation progress update"""
        progress_update = SimulationProgress(
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            timestamp=datetime.now().isoformat()
        )
        await self.send_personal_message(progress_update.model_dump(), client_id)


manager = ConnectionManager()


@router.websocket("/ws/simulation/{client_id}")
async def simulation_websocket(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for simulation progress updates

    Clients can connect to receive real-time updates about:
    - Simulation start/progress/completion
    - Task status changes
    - Error notifications

    Message format:
    {
        "task_id": "uuid",
        "status": "running|completed|failed",
        "progress": 0-100,
        "message": "status message",
        "timestamp": "ISO timestamp"
    }
    """
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Receive messages from client (for heartbeat, commands, etc.)
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get('type') == 'ping':
                await websocket.send_json({'type': 'pong', 'timestamp': datetime.now().isoformat()})
            elif message.get('type') == 'subscribe':
                # Subscribe to specific task updates
                task_id = message.get('task_id')
                if task_id:
                    await websocket.send_json({
                        'type': 'subscribed',
                        'task_id': task_id,
                        'timestamp': datetime.now().isoformat()
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket, client_id)


@router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket):
    """
    Public WebSocket endpoint for system-wide events

    Broadcasts events like:
    - New simulations started
    - System errors
    - Case updates
    """
    await websocket.accept()
    client_id = f"anonymous_{id(websocket)}"

    try:
        # Send welcome message
        await websocket.send_json({
            'type': 'connected',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        })

        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})

    except WebSocketDisconnect:
        logger.info(f"Events client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Events WebSocket error: {e}")


@router.websocket("/ws/monitor/{client_id}")
async def monitor_websocket(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for system monitoring

    Clients can connect to receive real-time updates about:
    - System health status
    - Active simulations
    - Alarm notifications
    - Resource usage

    Message format:
    {
        "type": "alarm|status|resource",
        "data": {...},
        "timestamp": "ISO timestamp"
    }
    """
    await manager.connect(websocket, f"monitor_{client_id}")

    try:
        # Send initial status
        await websocket.send_json({
            'type': 'connected',
            'client_id': client_id,
            'mode': 'monitor',
            'timestamp': datetime.now().isoformat()
        })

        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get('type') == 'ping':
                await websocket.send_json({
                    'type': 'pong',
                    'mode': 'monitor',
                    'timestamp': datetime.now().isoformat()
                })
            elif message.get('type') == 'subscribe_alarms':
                # Subscribe to alarm notifications
                await websocket.send_json({
                    'type': 'subscribed',
                    'channel': 'alarms',
                    'timestamp': datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, f"monitor_{client_id}")
    except Exception as e:
        logger.error(f"Monitor WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket, f"monitor_{client_id}")


# Helper functions for sending updates from other modules
async def notify_simulation_start(client_id: str, task_id: str):
    """Notify clients that a simulation has started"""
    await manager.send_progress_update(task_id, client_id, "running", 0, "Simulation started")


async def notify_simulation_progress(client_id: str, task_id: str, progress: float, message: str):
    """Send simulation progress update"""
    await manager.send_progress_update(task_id, client_id, "running", progress, message)


async def notify_simulation_complete(client_id: str, task_id: str, success: bool):
    """Notify clients that simulation is complete"""
    status = "completed" if success else "failed"
    progress = 100
    message = "Simulation completed successfully" if success else "Simulation failed"
    await manager.send_progress_update(task_id, client_id, status, progress, message)


async def broadcast_system_event(event_type: str, data: Dict[str, Any]):
    """Broadcast a system-wide event"""
    message = {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    await manager.broadcast(message)
