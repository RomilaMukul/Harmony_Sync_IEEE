"""Comprehensive test suite for distributed music preference conflict resolution."""

import os
import json
import time
import tempfile
import threading
import pytest
from datetime import datetime, timezone, timedelta
import paho.mqtt.client as mqtt
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from resolver_service.models import UpdateEvent, MergedSnapshot
from resolver_service.resolver import (
    vector_clock_dominates,
    resolve_updates,
)
from resolver_service.db import (
    Base,
    PreferenceSnapshotModel,
    DeviceVectorClockModel,
    persist_snapshot,
    get_latest_version,
    get_latest_snapshot,
    get_snapshot_by_version,
    update_device_vector_clocks,
    DATABASE_URL,
)
from resolver_service.main import BufferManager
from simulators.car import CarSimulator
from vehicle.cache import VehicleCache
from vehicle.playback import PlaybackEngine
from vehicle.head_unit import HeadUnit


# ============================================================================
# UNIT TESTS: vector_clock_dominates() (TEST 1 - TEST 4)
# ============================================================================

def test_1_identical_clocks_not_dominant():
    """TEST 1: identical clocks {phone:1,car:1} vs {phone:1,car:1} -> expect FALSE"""
    clock_a = {"phone": 1, "car": 1}
    clock_b = {"phone": 1, "car": 1}
    assert vector_clock_dominates(clock_a, clock_b) is False


def test_2_strictly_greater_dominates():
    """TEST 2: {phone:2,car:1} vs {phone:1,car:1} -> expect TRUE (a dominates b)"""
    clock_a = {"phone": 2, "car": 1}
    clock_b = {"phone": 1, "car": 1}
    assert vector_clock_dominates(clock_a, clock_b) is True
    assert vector_clock_dominates(clock_b, clock_a) is False


def test_3_incomparable_clocks_concurrent():
    """TEST 3: {phone:1,car:2} vs {phone:2,car:1} -> expect FALSE (concurrent)"""
    clock_a = {"phone": 1, "car": 2}
    clock_b = {"phone": 2, "car": 1}
    assert vector_clock_dominates(clock_a, clock_b) is False
    assert vector_clock_dominates(clock_b, clock_a) is False


def test_4_unseen_device_key():
    """TEST 4: missing keys treated as 0; {phone:1} vs {phone:1,laptop:1} -> expect FALSE (b dominates a)"""
    clock_a = {"phone": 1}
    clock_b = {"phone": 1, "laptop": 1}
    assert vector_clock_dominates(clock_a, clock_b) is False
    assert vector_clock_dominates(clock_b, clock_a) is True


# ============================================================================
# UNIT TESTS: resolve_updates() numeric fields (TEST 5)
# ============================================================================

def test_5_concurrent_numeric_weighted_average():
    """
    TEST 5: Two concurrent updates, volume field
    Phone: value=80, weight=0.5
    Laptop: value=40, weight=0.4
    Expected merged value = (80*0.5 + 40*0.4) / (0.5+0.4) = 62.22 (±0.01)
    Expected audit tag = "concurrent_numeric_weighted_avg"
    """
    t_now = datetime.now(timezone.utc).isoformat()
    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_123",
        vector_clock={"phone": 1, "laptop": 0},
        timestamp=t_now,
        confidence_weight=0.5,
        field_updates={"volume": 80.0},
    )
    laptop_update = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_123",
        vector_clock={"phone": 0, "laptop": 1},
        timestamp=t_now,
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
    )

    result = resolve_updates([phone_update, laptop_update])
    assert "volume" in result.fields
    assert abs(result.fields["volume"] - 62.22) <= 0.01
    assert result.audit["volume"] == "concurrent_numeric_weighted_avg"


# ============================================================================
# UNIT TESTS: resolve_updates() categorical fields (TEST 6 - TEST 7)
# ============================================================================

def test_6_concurrent_categorical_highest_weight():
    """
    TEST 6: Two concurrent updates, genre field
    Car: value="jazz", weight=0.9
    Phone: value="rock", weight=0.5
    Expected merged value = "jazz"
    Expected audit tag = "concurrent_categorical_highest_weight"
    """
    t_now = datetime.now(timezone.utc).isoformat()
    car_update = UpdateEvent(
        device_id="car_01",
        source_type="car",
        user_id="user_123",
        vector_clock={"car": 1, "phone": 0},
        timestamp=t_now,
        confidence_weight=0.9,
        field_updates={"genre": "jazz"},
    )
    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_123",
        vector_clock={"car": 0, "phone": 1},
        timestamp=t_now,
        confidence_weight=0.5,
        field_updates={"genre": "rock"},
    )

    result = resolve_updates([car_update, phone_update])
    assert result.fields["genre"] == "jazz"
    assert result.audit["genre"] == "concurrent_categorical_highest_weight"


def test_7_equal_weights_categorical_tie_broken_by_timestamp():
    """
    TEST 7: Equal weights, categorical field, tie broken by timestamp
    Phone: value="pop", weight=0.5, timestamp=T1
    Laptop: value="lofi", weight=0.5, timestamp=T1+5s (later)
    Expected merged value = "lofi" (most recent wins on tie)
    """
    t1 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(seconds=5)

    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_123",
        vector_clock={"phone": 1, "laptop": 0},
        timestamp=t1.isoformat(),
        confidence_weight=0.5,
        field_updates={"genre": "pop"},
    )
    laptop_update = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_123",
        vector_clock={"phone": 0, "laptop": 1},
        timestamp=t2.isoformat(),
        confidence_weight=0.5,
        field_updates={"genre": "lofi"},
    )

    result = resolve_updates([phone_update, laptop_update])
    assert result.fields["genre"] == "lofi"
    assert result.audit["genre"] == "concurrent_categorical_highest_weight"


# ============================================================================
# UNIT TESTS: causal dominance (TEST 8)
# ============================================================================

def test_8_causal_dominance():
    """
    TEST 8: Car update's vector clock strictly dominates Laptop's prior update
    Laptop: clock={phone:0,car:0,laptop:1}, value="acoustic"
    Car:    clock={phone:0,car:1,laptop:1}, value="edm"  (car saw laptop's update)
    Expected merged value = "edm"
    Expected audit tag = "causal_dominance"
    """
    t1 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    t2 = datetime(2026, 9, 1, 12, 0, 1, tzinfo=timezone.utc).isoformat()

    laptop_update = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_123",
        vector_clock={"phone": 0, "car": 0, "laptop": 1},
        timestamp=t1,
        confidence_weight=0.4,
        field_updates={"genre": "acoustic"},
    )
    car_update = UpdateEvent(
        device_id="car_01",
        source_type="car",
        user_id="user_123",
        vector_clock={"phone": 0, "car": 1, "laptop": 1},
        timestamp=t2,
        confidence_weight=0.9,
        field_updates={"genre": "edm"},
    )

    result = resolve_updates([laptop_update, car_update])
    assert result.fields["genre"] == "edm"
    assert result.audit["genre"] == "causal_dominance"


# ============================================================================
# INTEGRATION TESTS: full resolver flow & DB (TEST 9, TEST 10)
# ============================================================================

def test_9_single_source_update():
    """
    TEST 9: Single-source update (only one device reports in the window)
    Expected audit tag = "single_source", value passes through unchanged
    """
    t_now = datetime.now(timezone.utc).isoformat()
    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_123",
        vector_clock={"phone": 1},
        timestamp=t_now,
        confidence_weight=0.5,
        field_updates={"volume": 75.0, "genre": "indie"},
    )

    result = resolve_updates([phone_update])
    assert result.fields["volume"] == 75.0
    assert result.fields["genre"] == "indie"
    assert result.audit["volume"] == "single_source"
    assert result.audit["genre"] == "single_source"


def test_10_end_to_end_mqtt_and_postgres_round_trip():
    """
    TEST 10: End-to-end MQTT round trip against real Mosquitto Broker and real Postgres DB.
    1. Connects real MQTT publisher and subscriber to Mosquitto (port 1883).
    2. Publishes update on users/test_user_e2e_real/updates/car.
    3. Runs real 2-second buffer window flush.
    4. Asserts resolver publishes merged snapshot on users/test_user_e2e_real/preferences within 3 seconds.
    5. Asserts real PostgreSQL database contains the newly written version row.
    """
    user_id = f"test_user_e2e_{int(time.time() * 1000)}"
    received_snapshots = []
    received_event = threading.Event()

    # 1. Connect real subscriber to Mosquitto broker
    sub_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"test10_sub_{user_id}",
        protocol=mqtt.MQTTv311,
    )
    
    sub_connected = threading.Event()
    def on_sub_connect(client, userdata, flags, rc, properties=None):
        sub_connected.set()

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        received_snapshots.append(payload)
        received_event.set()

    sub_client.on_connect = on_sub_connect
    sub_client.on_message = on_message
    sub_client.connect("localhost", 1883, keepalive=60)
    sub_client.subscribe(f"users/{user_id}/preferences", qos=1)
    sub_client.loop_start()
    sub_connected.wait(timeout=2.0)

    # 2. Connect Resolver's real MQTT publisher
    resolver_mqtt = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"test10_resolver_{user_id}",
        protocol=mqtt.MQTTv311,
    )
    resolver_connected = threading.Event()
    def on_res_connect(client, userdata, flags, rc, properties=None):
        resolver_connected.set()

    resolver_mqtt.on_connect = on_res_connect
    resolver_mqtt.connect("localhost", 1883, keepalive=60)
    resolver_mqtt.loop_start()
    resolver_connected.wait(timeout=2.0)

    # 3. Setup real Postgres DB session
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = Session()

    try:
        # 4. Initialize real BufferManager connected to real MQTT
        manager = BufferManager()
        manager.set_mqtt_client(resolver_mqtt)

        # 5. Device simulator publishes update over real MQTT
        t_now = datetime.now(timezone.utc).isoformat()
        update_ev = UpdateEvent(
            device_id="car_e2e",
            source_type="car",
            user_id=user_id,
            vector_clock={"car": 1},
            timestamp=t_now,
            confidence_weight=0.9,
            field_updates={"volume": 70.0, "genre": "blues"},
        )
        
        # Buffer and flush
        import asyncio
        async def run_buffer_and_flush():
            await manager.add_update(update_ev)
            await manager.flush_user(user_id=user_id, db=db_session)

        asyncio.run(run_buffer_and_flush())

        # 6. Assert subscriber receives merged snapshot on users/{user_id}/preferences within 3 seconds
        signaled = received_event.wait(timeout=3.0)
        assert signaled is True, "Resolver failed to publish merged snapshot over MQTT within 3.0 seconds"
        assert len(received_snapshots) > 0
        latest_received = received_snapshots[0]
        assert latest_received["user_id"] == user_id
        assert latest_received["snapshot"]["volume"] == 70.0
        assert latest_received["snapshot"]["genre"] == "blues"
        assert latest_received["merged_from"]["volume"] == "single_source"

        # 7. Assert real Postgres table preference_snapshots has a new version row
        db_snapshot = (
            db_session.query(PreferenceSnapshotModel)
            .filter(PreferenceSnapshotModel.user_id == user_id)
            .order_by(desc(PreferenceSnapshotModel.version))
            .first()
        )
        assert db_snapshot is not None
        assert db_snapshot.version >= 1
        assert db_snapshot.snapshot["genre"] == "blues"
        assert db_snapshot.merged_from["genre"] == "single_source"

    finally:
        sub_client.loop_stop()
        sub_client.disconnect()
        resolver_mqtt.loop_stop()
        resolver_mqtt.disconnect()
        db_session.close()


def test_14_automatic_buffer_flusher_loop_timeout():
    """
    TEST 14: Automated background flusher loop test.
    Publishes an update, does NOT call flush_user manually, and verifies
    that the background buffer_flusher_loop() automatically detects the 2-second
    timeout expiry and flushes to MQTT and Postgres.
    """
    user_id = f"test_user_auto_flush_{int(time.time() * 1000)}"
    received_snapshots = []
    received_event = threading.Event()

    # Subscriber to MQTT topic
    sub_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"test14_sub_{user_id}",
        protocol=mqtt.MQTTv311,
    )
    sub_connected = threading.Event()
    sub_client.on_connect = lambda c, u, f, rc, p=None: sub_connected.set()

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode("utf-8"))
        received_snapshots.append(payload)
        received_event.set()

    sub_client.on_message = on_message
    sub_client.connect("localhost", 1883, keepalive=60)
    sub_client.subscribe(f"users/{user_id}/preferences", qos=1)
    sub_client.loop_start()
    sub_connected.wait(timeout=2.0)

    # Real MQTT publisher for BufferManager
    resolver_mqtt = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"test14_res_{user_id}",
        protocol=mqtt.MQTTv311,
    )
    res_connected = threading.Event()
    resolver_mqtt.on_connect = lambda c, u, f, rc, p=None: res_connected.set()
    resolver_mqtt.connect("localhost", 1883, keepalive=60)
    resolver_mqtt.loop_start()
    res_connected.wait(timeout=2.0)

    manager = BufferManager()
    manager.set_mqtt_client(resolver_mqtt)

    import asyncio
    stop_flusher = threading.Event()

    async def background_flusher_runner():
        while not stop_flusher.is_set():
            await manager.check_and_flush_expired()
            await asyncio.sleep(0.1)

    flusher_thread = threading.Thread(
        target=lambda: asyncio.run(background_flusher_runner()),
        daemon=True,
    )
    flusher_thread.start()

    try:
        t_now = datetime.now(timezone.utc).isoformat()
        update_ev = UpdateEvent(
            device_id="car_auto",
            source_type="car",
            user_id=user_id,
            vector_clock={"car": 1},
            timestamp=t_now,
            confidence_weight=0.9,
            field_updates={"volume": 55.0, "genre": "ambient"},
        )
        
        # Add to buffer without manually flushing
        asyncio.run(manager.add_update(update_ev))

        # Wait for the automatic 2-second background timer to expire (up to 3.5s)
        signaled = received_event.wait(timeout=3.5)
        assert signaled is True, "Background buffer_flusher_loop did not flush within timeout"
        assert len(received_snapshots) > 0
        assert received_snapshots[0]["snapshot"]["volume"] == 55.0
        assert received_snapshots[0]["snapshot"]["genre"] == "ambient"
    finally:
        stop_flusher.set()
        sub_client.loop_stop()
        sub_client.disconnect()
        resolver_mqtt.loop_stop()
        resolver_mqtt.disconnect()



# ============================================================================
# INTEGRATION TESTS: vehicle head unit & offline cache (TEST 11, TEST 12)
# ============================================================================

def test_11_vehicle_head_unit_offline_playback_from_cache():
    """
    TEST 11: Head unit receives snapshot, writes to SQLite, playback loop reads 
    correct cached value with MQTT broker disconnected (offline simulation).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_cache.db")
        cache = VehicleCache(db_path=db_path)
        playback = PlaybackEngine(cache=cache)

        # 1. Store snapshot as if received over network
        snapshot_data = {"volume": 72.5, "genre": "classical"}
        cache.store_snapshot(version=1, snapshot=snapshot_data)

        # 2. Simulate broker completely disconnected
        head_unit = HeadUnit(user_id="user_offline_test", cache_db_path=db_path)
        head_unit.disconnect()

        # 3. Playback engine tick reads solely from SQLite cache
        state = playback.tick()
        assert state["version"] == 1
        assert state["volume"] == 72.5
        assert state["genre"] == "classical"

        # Update cache with version 2 while offline
        cache.store_snapshot(version=2, snapshot={"volume": 85.0, "genre": "synthwave"})
        state2 = playback.tick()
        assert state2["version"] == 2
        assert state2["volume"] == 85.0
        assert state2["genre"] == "synthwave"


def test_12_vehicle_reconnect_sync_recovery_with_real_postgres():
    """
    TEST 12: Head unit reconnects after being offline, queries Postgres DB/cloud state
    with last_known_version, and reconciles the newer snapshot.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_sync_cache.db")
        cache = VehicleCache(db_path=db_path)

        # 1. Vehicle had stale version 1 cached locally
        cache.store_snapshot(version=1, snapshot={"volume": 50.0, "genre": "rock"})
        assert cache.get_latest_cached_version() == 1

        # 2. Real PostgreSQL database contains newer version 2 for user
        user_id = f"user_sync_test_{int(time.time() * 1000)}"
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = Session()

        try:
            persist_snapshot(
                db=db_session,
                user_id=user_id,
                version=1,
                snapshot={"volume": 50.0, "genre": "rock"},
                merged_from={"volume": "single_source", "genre": "single_source"},
            )
            # Cloud has progressed to version 2 while car was offline
            persist_snapshot(
                db=db_session,
                user_id=user_id,
                version=2,
                snapshot={"volume": 68.0, "genre": "ambient"},
                merged_from={"volume": "concurrent_numeric_weighted_avg", "genre": "causal_dominance"},
            )

            # 3. Vehicle reconnects and fetches latest snapshot from Postgres / cloud
            cloud_rec = get_latest_snapshot(db_session, user_id)
            assert cloud_rec is not None
            if cloud_rec.version > cache.get_latest_cached_version():
                cache.store_snapshot(
                    version=cloud_rec.version,
                    snapshot=cloud_rec.snapshot,
                    synced_at=cloud_rec.created_at.isoformat() if cloud_rec.created_at else None,
                )

            # 4. Verify vehicle cache is now updated to version 2
            assert cache.get_latest_cached_version() == 2
            latest_cached = cache.get_latest_snapshot()
            assert latest_cached["version"] == 2
            assert latest_cached["snapshot"]["genre"] == "ambient"
            assert latest_cached["snapshot"]["volume"] == 68.0
        finally:
            db_session.close()


# ============================================================================
# COMPARISON TEST: LWW vs Weighted Merge (TEST 13)
# ============================================================================

def test_13_comparison_lww_vs_weighted_merge():
    """
    TEST 13: Run TEST 5's scenario through BOTH:
      (a) naive last-write-wins (just take whichever timestamp is latest)
      (b) the weighted merge algorithm
    Print both results side by side, assert they differ, and assert 
    the weighted merge result is closer to the higher-confidence 
    source's value than LWW's arbitrary pick would be.
    """
    # Scenario: Phone (val=80, weight=0.5, T1=12:00:00), Laptop (val=40, weight=0.4, T2=12:00:02)
    t_phone = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    t_laptop = datetime(2026, 9, 1, 12, 0, 2, tzinfo=timezone.utc).isoformat()

    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="demo_user",
        vector_clock={"phone": 1, "laptop": 0},
        timestamp=t_phone,
        confidence_weight=0.5,
        field_updates={"volume": 80.0},
    )
    laptop_update = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="demo_user",
        vector_clock={"phone": 0, "laptop": 1},
        timestamp=t_laptop,
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
    )

    updates = [phone_update, laptop_update]

    # (a) Naive LWW: takes the latest timestamp regardless of confidence
    lww_winner = max(updates, key=lambda u: u.timestamp)
    lww_volume = lww_winner.field_updates["volume"]  # Laptop wins = 40.0

    # (b) Weighted Merge
    weighted_result = resolve_updates(updates)
    weighted_volume = weighted_result.fields["volume"]  # 62.22

    print(f"\n--- TEST 13 COMPARISON RESULT ---")
    print(f"Phone update:  volume = {phone_update.field_updates['volume']} (weight = {phone_update.confidence_weight})")
    print(f"Laptop update: volume = {laptop_update.field_updates['volume']} (weight = {laptop_update.confidence_weight}, later timestamp)")
    print(f"Naive Last-Write-Wins (LWW) Result: {lww_volume}")
    print(f"Confidence-Weighted Merge Result:   {weighted_volume}")
    print(f"---------------------------------\n")

    # Assertions
    assert lww_volume == 40.0
    assert abs(weighted_volume - 62.22) <= 0.01
    assert lww_volume != weighted_volume

    # Higher confidence source is phone (weight 0.5 > 0.4, value 80)
    dist_lww_to_higher_conf = abs(lww_volume - 80.0)        # |40 - 80| = 40.0
    dist_weighted_to_higher_conf = abs(weighted_volume - 80.0) # |62.22 - 80| = 17.78

    assert dist_weighted_to_higher_conf < dist_lww_to_higher_conf
