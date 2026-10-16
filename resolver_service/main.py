"""FastAPI Resolver Service with 2-second buffer window and MQTT pub/sub."""

import os
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from resolver_service.models import UpdateEvent, MergedSnapshot
from resolver_service.resolver import resolve_updates
from resolver_service.db import (
    init_db,
    get_db,
    SessionLocal,
    get_latest_version,
    persist_snapshot,
    get_latest_snapshot,
    get_snapshot_by_version,
    update_device_vector_clocks,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("resolver_service")

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
BUFFER_WINDOW_SECONDS = float(os.getenv("BUFFER_WINDOW_SECONDS", "2.0"))


class BufferManager:
    """Manages buffered updates per user with a 2-second sliding window flush."""

    def __init__(self):
        self.buffers: Dict[str, List[UpdateEvent]] = {}
        self.last_update_time: Dict[str, float] = {}
        self.lock = asyncio.Lock()
        self.mqtt_client: Optional[mqtt.Client] = None

    def set_mqtt_client(self, client: mqtt.Client):
        self.mqtt_client = client

    async def add_update(self, update: UpdateEvent):
        async with self.lock:
            user_id = update.user_id
            if user_id not in self.buffers:
                self.buffers[user_id] = []
            self.buffers[user_id].append(update)
            self.last_update_time[user_id] = time.time()
            logger.info(
                f"Buffered update for user {user_id} from {update.device_id} ({update.source_type}). Total in window: {len(self.buffers[user_id])}"
            )

    async def flush_user(self, user_id: str, db: Optional[Session] = None) -> Optional[MergedSnapshot]:
        async with self.lock:
            updates = self.buffers.pop(user_id, [])
            self.last_update_time.pop(user_id, None)

        if not updates:
            return None

        owns_session = False
        if db is None:
            db = SessionLocal()
            owns_session = True

        try:
            # 1. Resolve conflicts
            result = resolve_updates(updates)

            # 2. Increment version & persist
            new_version = get_latest_version(db, user_id) + 1
            result.user_id = user_id
            result.version = new_version
            result.created_at = datetime.now(timezone.utc).isoformat()

            persist_snapshot(
                db=db,
                user_id=user_id,
                version=new_version,
                snapshot=result.fields,
                merged_from=result.audit,
            )

            # 3. Update vector clocks
            update_device_vector_clocks(db, user_id, updates)

            logger.info(
                f"Flushed user {user_id} -> version {new_version} | fields: {result.fields} | audit: {result.audit}"
            )

            # 4. Publish merged snapshot over MQTT
            if self.mqtt_client and self.mqtt_client.is_connected():
                topic = f"users/{user_id}/preferences"
                payload = {
                    "user_id": user_id,
                    "version": new_version,
                    "snapshot": result.fields,
                    "merged_from": result.audit,
                    "created_at": result.created_at,
                }
                self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
                logger.info(f"Published merged snapshot to MQTT topic: {topic}")

            return result
        finally:
            if owns_session:
                db.close()

    async def check_and_flush_expired(self):
        """Check all users and flush those whose 2-second window has expired."""
        now = time.time()
        users_to_flush = []
        async with self.lock:
            for user_id, last_time in list(self.last_update_time.items()):
                if now - last_time >= BUFFER_WINDOW_SECONDS:
                    users_to_flush.append(user_id)

        for user_id in users_to_flush:
            await self.flush_user(user_id)


buffer_manager = BufferManager()
loop_task: Optional[asyncio.Task] = None
mqtt_client_instance: Optional[mqtt.Client] = None


async def buffer_flusher_loop():
    """Background loop checking expired buffer windows."""
    while True:
        try:
            await buffer_manager.check_and_flush_expired()
        except Exception as e:
            logger.error(f"Error in buffer flusher loop: {e}")
        await asyncio.sleep(0.2)


def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    logger.info(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to preference updates from all devices across all users
    client.subscribe("users/+/updates/+", qos=1)
    logger.info("Subscribed to MQTT topic: users/+/updates/+")


def on_mqtt_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)
        update_event = UpdateEvent(**data)
        
        # Schedule adding to async buffer
        asyncio.run_coroutine_threadsafe(
            buffer_manager.add_update(update_event),
            userdata["event_loop"],
        )
    except Exception as e:
        logger.error(f"Failed to process MQTT message on {msg.topic}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop_task, mqtt_client_instance
    init_db()
    event_loop = asyncio.get_running_loop()

    # Setup MQTT
    client = mqtt.Client(
        client_id="resolver_service",
        userdata={"event_loop": event_loop},
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        client.loop_start()
        buffer_manager.set_mqtt_client(client)
        mqtt_client_instance = client
        logger.info(f"MQTT client connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    except Exception as e:
        logger.warning(f"Could not connect to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}: {e}")

    loop_task = asyncio.create_task(buffer_flusher_loop())
    yield
    if loop_task:
        loop_task.cancel()
    if mqtt_client_instance:
        mqtt_client_instance.loop_stop()
        mqtt_client_instance.disconnect()


app = FastAPI(
    title="Music Preference Conflict Resolver Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    mqtt_status = (
        mqtt_client_instance.is_connected()
        if mqtt_client_instance
        else False
    )
    return {"status": "ok", "mqtt_connected": mqtt_status}


@app.post("/users/{user_id}/updates")
async def post_update(user_id: str, update: UpdateEvent):
    """HTTP endpoint to submit an update event."""
    if update.user_id != user_id:
        raise HTTPException(status_code=400, detail="Mismatched user_id in URL and payload")
    await buffer_manager.add_update(update)
    return {"status": "buffered", "device_id": update.device_id}


@app.post("/users/{user_id}/flush")
async def manual_flush(user_id: str, db: Session = Depends(get_db)):
    """Manually flush the buffer for a user immediately."""
    result = await buffer_manager.flush_user(user_id, db=db)
    if not result:
        return {"status": "empty_buffer"}
    return {
        "status": "flushed",
        "version": result.version,
        "snapshot": result.fields,
        "merged_from": result.audit,
    }


@app.get("/users/{user_id}/preferences/latest")
def get_latest_user_preferences(user_id: str, db: Session = Depends(get_db)):
    """Get the latest snapshot version for a user."""
    rec = get_latest_snapshot(db, user_id)
    if not rec:
        raise HTTPException(status_code=404, detail="No preference snapshots found for user")
    return {
        "user_id": rec.user_id,
        "version": rec.version,
        "snapshot": rec.snapshot,
        "merged_from": rec.merged_from,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


@app.get("/users/{user_id}/preferences/version/{version}")
def get_user_preference_version(user_id: str, version: int, db: Session = Depends(get_db)):
    """Get a specific snapshot version for a user."""
    rec = get_snapshot_by_version(db, user_id, version)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Version {version} not found for user")
    return {
        "user_id": rec.user_id,
        "version": rec.version,
        "snapshot": rec.snapshot,
        "merged_from": rec.merged_from,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }
