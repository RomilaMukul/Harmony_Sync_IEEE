"""Database layer for Postgres persistence of preference snapshots and vector clocks."""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from sqlalchemy import (
    create_engine,
    Column,
    String,
    BigInteger,
    DateTime,
    JSON,
    PrimaryKeyConstraint,
    desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from resolver_service.models import UpdateEvent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sync_user:sync_password@localhost:5434/music_sync_db",
)

# Allow SQLite fallback if specified (e.g., in unit testing environments without postgres)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PreferenceSnapshotModel(Base):
    """Stores immutable versions of resolved user preference snapshots."""
    __tablename__ = "preference_snapshots"

    user_id = Column(String(64), nullable=False)
    version = Column(BigInteger, nullable=False)
    snapshot = Column(JSON, nullable=False)
    merged_from = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "version", name="pk_preference_snapshots"),
    )


class DeviceVectorClockModel(Base):
    """Stores the latest vector clock value per device for each user."""
    __tablename__ = "device_vector_clocks"

    user_id = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False)
    clock_value = Column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "device_id", name="pk_device_vector_clocks"),
    )


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_latest_version(db: Session, user_id: str) -> int:
    """Retrieve the latest snapshot version for a user (0 if none exist)."""
    latest = (
        db.query(PreferenceSnapshotModel)
        .filter(PreferenceSnapshotModel.user_id == user_id)
        .order_by(desc(PreferenceSnapshotModel.version))
        .first()
    )
    return latest.version if latest else 0


def persist_snapshot(
    db: Session,
    user_id: str,
    version: int,
    snapshot: Dict[str, Any],
    merged_from: Dict[str, str],
) -> PreferenceSnapshotModel:
    """Persist a new immutable version snapshot to database."""
    record = PreferenceSnapshotModel(
        user_id=user_id,
        version=version,
        snapshot=snapshot,
        merged_from=merged_from,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_snapshot_by_version(
    db: Session, user_id: str, version: int
) -> Optional[PreferenceSnapshotModel]:
    """Retrieve a specific snapshot version for a user."""
    return (
        db.query(PreferenceSnapshotModel)
        .filter(
            PreferenceSnapshotModel.user_id == user_id,
            PreferenceSnapshotModel.version == version,
        )
        .first()
    )


def get_latest_snapshot(
    db: Session, user_id: str
) -> Optional[PreferenceSnapshotModel]:
    """Retrieve the latest snapshot for a user."""
    return (
        db.query(PreferenceSnapshotModel)
        .filter(PreferenceSnapshotModel.user_id == user_id)
        .order_by(desc(PreferenceSnapshotModel.version))
        .first()
    )


def update_device_vector_clocks(
    db: Session, user_id: str, buffered_updates: List[UpdateEvent]
) -> Dict[str, int]:
    """Update stored device vector clocks with maximum seen clock values."""
    clocks: Dict[str, int] = {}
    for update in buffered_updates:
        for dev_id, val in update.vector_clock.items():
            clocks[dev_id] = max(clocks.get(dev_id, 0), val)

    for dev_id, val in clocks.items():
        existing = (
            db.query(DeviceVectorClockModel)
            .filter(
                DeviceVectorClockModel.user_id == user_id,
                DeviceVectorClockModel.device_id == dev_id,
            )
            .first()
        )
        if existing:
            if val > existing.clock_value:
                existing.clock_value = val
        else:
            new_clock = DeviceVectorClockModel(
                user_id=user_id,
                device_id=dev_id,
                clock_value=val,
            )
            db.add(new_clock)

    db.commit()
    return clocks
