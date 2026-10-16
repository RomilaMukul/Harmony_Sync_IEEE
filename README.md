<p align="center">
  <h1 align="center">HarmonySync</h1>
  <p align="center">
    <strong>Distributed Music Preference Sync with Weighted Conflict Resolution</strong>
  </p>
  <p align="center">
    <a href="#the-algorithm">Algorithm</a> &nbsp;&bull;&nbsp;
    <a href="#architecture">Architecture</a> &nbsp;&bull;&nbsp;
    <a href="#running-the-demo">Demo</a> &nbsp;&bull;&nbsp;
    <a href="#running-tests">Tests</a> &nbsp;&bull;&nbsp;
    <a href="#setup-instructions">Setup</a>
  </p>
</p>

---

## The Problem

When drivers adjust volume, favorite genres, or playlists across multiple devices — smartphones, in-vehicle head units, laptops — traditional cloud sync relies on **Last-Write-Wins (LWW)**.

In real vehicular environments, LWW consistently fails:

| Scenario | What Happens with LWW | What Should Happen |
|---|---|---|
| Driver sets volume to **80** on the car dial. Laptop at home auto-syncs volume **40** with a 1-second network delay. | LWW picks **40** (later timestamp). Driver's preference is lost. | Weighted merge produces **62.22**, preserving the higher-confidence car signal. |
| Driver selects **jazz** in the car. Phone background process picks **rock**. | LWW picks **rock** (later timestamp). Intentional selection overwritten. | Confidence weighting picks **jazz** (car weight 0.9 > phone weight 0.5). |

**HarmonySync** solves this with a cloud-mediated architecture featuring a **causally-aware, confidence-weighted conflict resolution engine** — not just "cloud sync instead of Bluetooth."

---

## Architecture

```
 LAYER 1: CLIENT DEVICES
 ┌─────────────────────────────────────────────────────────────────────┐
 │                                                                     │
 │   ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
 │   │  Phone (w=0.5)  │  │  Car HU (w=0.9)  │  │ Laptop (w=0.4)  │   │
 │   └────────┬────────┘  └────────┬─────────┘  └────────┬────────┘   │
 │            │  Privacy Guard      │  Privacy Guard       │           │
 │            │  (edge aggregate)   │  (edge aggregate)    │           │
 └────────────┼─────────────────────┼──────────────────────┼───────────┘
              │                     │                      │
              └──────────┬──────────┴──────────────────────┘
                         │
                         │  MQTT: users/{user_id}/updates/{device_id}
                         ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  LAYER 2: RESOLVER SERVICE (FastAPI + PostgreSQL)                   │
 │                                                                     │
 │   ┌─────────────────────────────────────────────────────────────┐   │
 │   │  2-Second Sliding Window Buffer (per user)                  │   │
 │   │  ─────────────────────────────────────────────────────────  │   │
 │   │  1. Check vector clock causal dominance                     │   │
 │   │  2. Confidence-weighted numeric merge (continuous fields)   │   │
 │   │  3. Highest-weight categorical selection (discrete fields)  │   │
 │   │  4. Persist immutable versioned snapshot + audit trail       │   │
 │   └─────────────────────────────────────────────────────────────┘   │
 │                                                                     │
 └───────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 │  MQTT: users/{user_id}/preferences
                                 ▼
 ┌─────────────────────────────────────────────────────────────────────┐
 │  LAYER 3: VEHICLE HEAD UNIT                                         │
 │                                                                     │
 │   MQTT Subscriber ──► Local SQLite Cache ──► Playback Engine        │
 │                        (offline-first)        (non-blocking reads)   │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

---

## Why This Is Different

Generic connected-car cloud sync platforms substitute Bluetooth pairing with cloud HTTP polling or WebSocket messaging. **Cloud sync instead of Bluetooth alone is not novel.**

The actual contribution is the **conflict resolution mechanism**:

- **Vector Clock Causality** — Detects "happened-before" relationships across devices, ensuring stale updates never override causally newer ones.
- **Confidence Weighting** — Assigns fixed trust weights per device context (`car = 0.9`, `phone = 0.5`, `laptop = 0.4`), so adjustments made in the driving context dominate over background device drift.
- **Privacy-Preserving Pre-Aggregation** — Raw interaction telemetry (slider drags, skip bursts, timestamps) is aggregated on-device before leaving the edge, with a hard privacy guard blocking any raw data leakage.
- **Offline-First Vehicle Playback** — The playback engine reads exclusively from a local SQLite cache, completely decoupled from network availability.

---

## The Algorithm

The conflict resolution engine runs in three phases for each 2-second user update buffer:

### Phase 1: Causal Dominance (Vector Clocks)

Every event carries a vector clock. If candidate A's clock strictly dominates B's (every element ≥, at least one >), A wins outright.

```
Laptop clock: {phone: 0, car: 0, laptop: 1}  →  value: "acoustic"
Car clock:    {phone: 0, car: 1, laptop: 1}  →  value: "edm"

Car has seen Laptop's update (laptop: 1) and made its own (car: 1).
Result: "edm" wins via causal_dominance.
```

### Phase 2: Confidence-Weighted Numeric Merge

For concurrent continuous fields (e.g., volume), values are merged using device weights:

```
                    Σ(value × weight)       (80 × 0.5) + (40 × 0.4)
Merged Value  =  ────────────────────  =  ──────────────────────────  =  62.22
                      Σ(weight)                  0.5 + 0.4
```

### Phase 3: Categorical Highest Weight

For discrete fields (e.g., genre), the candidate with the highest confidence weight wins. Equal weights are tie-broken by the latest timestamp.

```
Car:   genre = "jazz"   weight = 0.9   ← WINNER (highest confidence)
Phone: genre = "rock"   weight = 0.5
```

---

## Privacy-Preserving Pre-Aggregation Layer

High-frequency raw interactions never leave the device. The edge aggregator consolidates them locally before publishing:

```
 Raw Events (on-device only)              Published Payload (over MQTT)
 ───────────────────────────              ──────────────────────────────
 slider_drag: 78.0                        field_updates: {
 slider_drag: 80.0                            "volume": 80.0     ← mean
 slider_drag: 82.0                        }
 genre_tap:   "lofi"                      aggregation_metadata: {
 genre_tap:   "lofi"                          "sample_counts": {"volume": 3, "genre": 2}
 genre_tap:   "pop"                       }
```

**Hard Privacy Guard** — `assert_no_raw_data_leaked()` recursively scans the entire payload (including inside `aggregation_metadata`) for forbidden keys (`raw_*`, `traces`, `events`, `interaction_*`). If any raw data is detected, `PrivacyViolationError` is raised and MQTT publishing is blocked.

The pre-aggregation layer is **purely additive** — the cloud `resolver_service/` remains 100% unmodified.

---

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### 1. Launch Infrastructure

```bash
docker compose up -d
docker compose ps      # verify both containers are healthy
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Resolver Service

```bash
python -m uvicorn resolver_service.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Running the Demo

### Comparison Mode — LWW vs Weighted Merge

```bash
python demo/run_demo.py
```

**Output:**
```
================================================================================
 DISTRIBUTED MUSIC PREFERENCE SYNC: LWW VS WEIGHTED CONFLICT RESOLUTION
================================================================================

[SCENARIO 1] Concurrent Volume Adjustments from Multiple Devices
--------------------------------------------------------------------------------
Device 1: Phone  | Volume: 80.0 | Weight: 0.5
Device 2: Laptop | Volume: 40.0 | Weight: 0.4 (Later timestamp)

  -> Naive Last-Write-Wins (LWW): 40.00
     Discards high-confidence phone signal due to 1s clock drift

  -> Causally-Aware Weighted Merge: 62.22
     Audit: concurrent_numeric_weighted_avg

[SCENARIO 2] Categorical Conflict: Car vs Phone
--------------------------------------------------------------------------------
Device 1: Car   | Genre: 'jazz' | Weight: 0.9
Device 2: Phone | Genre: 'rock' | Weight: 0.5

  -> Naive Last-Write-Wins (LWW): 'rock'
     Background phone overrides intentional driver selection

  -> Causally-Aware Weighted Merge: 'jazz'
     Audit: concurrent_categorical_highest_weight
================================================================================
```

### Live End-to-End Simulation

```bash
python demo/run_demo.py --live
```

Runs a full pipeline: three devices publish concurrent updates → resolver merges → vehicle head unit caches to SQLite → playback engine reads offline-first.

---

## Running Tests

```bash
# Base system test suite (14 tests)
python -m pytest tests/test_resolver.py -v

# Pre-aggregation layer test suite (8 tests)
python -m pytest tests/test_preaggregation.py -v

# Full suite
python -m pytest tests/ -v
```

**Expected:** `22 passed`

| Test | Description | Type |
|---|---|---|
| TEST 1–4 | Vector clock dominance (identical, dominant, concurrent, unseen keys) | Unit |
| TEST 5 | Numeric weighted average: `(80×0.5 + 40×0.4) / 0.9 = 62.22` | Unit |
| TEST 6 | Categorical highest weight: jazz (0.9) beats rock (0.5) | Unit |
| TEST 7 | Equal weight tie-break by timestamp | Unit |
| TEST 8 | Causal dominance: car saw laptop's update, then overrode | Unit |
| TEST 9 | Single-source passthrough | Unit |
| TEST 10 | End-to-end MQTT + Postgres round trip (real containers) | Integration |
| TEST 11 | Vehicle offline playback from SQLite cache | Integration |
| TEST 12 | Vehicle reconnect sync recovery from Postgres | Integration |
| TEST 13 | LWW vs weighted merge side-by-side divergence proof | Comparison |
| TEST 14 | Automatic 2-second buffer flusher loop (unattended) | Integration |
| Pre-Agg 1–3 | Delta computation, multi-event aggregation, buffer clearing | Unit |
| Pre-Agg 4–5 | Privacy guard: valid pass / raw data leakage detection | Unit |
| Pre-Agg 6 | Backward compatibility: DeltaPayload into unmodified resolver | Integration |
| Pre-Agg 7–8 | Numeric averaging, categorical mode selection | Unit |

---

## Project Structure

```
HarmonySync/
├── docker-compose.yml              # Mosquitto MQTT + PostgreSQL containers
├── mosquitto.conf                  # Broker config (anonymous access)
├── requirements.txt                # Python dependencies
│
├── resolver_service/               # Cloud conflict resolution engine
│   ├── models.py                   #   UpdateEvent, MergedSnapshot, confidence weights
│   ├── resolver.py                 #   Vector clocks, causal dominance, weighted merge
│   ├── db.py                       #   PostgreSQL persistence (snapshots + vector clocks)
│   └── main.py                     #   FastAPI app, 2s buffer window, MQTT pub/sub
│
├── aggregator/                     # Privacy-preserving edge pre-aggregation
│   ├── models.py                   #   RawEvent, AggregatorState, DeltaPayload
│   ├── engine.py                   #   Signal extraction, delta computation, aggregation
│   ├── privacy.py                  #   Hard privacy guard (assert_no_raw_data_leaked)
│   └── publisher.py                #   Privacy-gated MQTT publisher
│
├── simulators/                     # Synthetic device clients
│   ├── base_client.py              #   Base MQTT publisher with vector clock management
│   ├── phone.py                    #   Phone simulator (weight = 0.5)
│   ├── car.py                      #   In-vehicle simulator (weight = 0.9)
│   └── laptop.py                   #   Laptop simulator (weight = 0.4)
│
├── vehicle/                        # Vehicle head unit + offline playback
│   ├── cache.py                    #   Local SQLite preference cache
│   ├── head_unit.py                #   MQTT subscriber + cloud sync recovery
│   └── playback.py                 #   Non-blocking playback engine (reads from cache)
│
├── demo/
│   └── run_demo.py                 #   LWW vs Weighted Merge comparison + --live mode
│
└── tests/
    ├── test_resolver.py            #   14 tests: vector clocks, merge, MQTT, DB, offline
    └── test_preaggregation.py      #   8 tests: aggregation, privacy guard, compatibility
```

---

## Limitations & Future Work

This is a **simulated architectural prototype** demonstrating causally-aware weighted conflict resolution and offline-first vehicle caching. Honest limitations:

- **No real vehicle hardware** — Not integrated with CAN-bus, Automotive Grade Linux, or Android Automotive OS.
- **No real music streaming API** — Does not connect to Spotify Connect, Apple Music, or any real audio source.
- **Static confidence weights** — Production systems would dynamically adjust weights based on occupant sensing, driving state, and interaction recency.
- **No authentication** — MQTT topics and API endpoints are unauthenticated. Production would use mTLS and per-user topic ACLs.
- **Local broker only** — Uses a local Mosquitto container, not a managed cloud MQTT service.

**Future directions:** Dynamic weight adaptation via occupant detection, differential privacy noise injection, OTA weight policy updates, integration with real vehicle middleware (COVESA/VSS), and A/B testing frameworks for resolution strategy comparison.

---

<p align="center">
  Built with FastAPI &bull; PostgreSQL &bull; Mosquitto MQTT &bull; SQLite &bull; Python 3.11+
</p>
