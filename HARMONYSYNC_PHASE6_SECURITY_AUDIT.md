# HARMONYSYNC — PHASE 6 CONFIDENCE-WEIGHT TRUST AND INPUT-VALIDATION AUDIT REPORT

**Audit Date:** 2026-10-12  
**Project Path:** `D:\projects\HarmonySync-main\HarmonySync-main`  
**Execution Context:** Security, authorization, and input-validation audit. Application code remains unmodified.  
**Supporting Experiment:** `test_security_audit.py` (executed in-memory and against broker config).

---

## 1. Executive Summary

The paper describes HarmonySync as a trusted distributed conflict resolution platform where fixed confidence weights are assigned per device type:
* In-Vehicle Head Unit: `0.9`
* Mobile Phone: `0.5`
* Laptop: `0.4`

**Core Finding:** In the actual prototype implementation, **confidence weights are not derived, validated, or enforced by the server**. Instead, the server resolver blindly trusts whatever `confidence_weight` value is submitted by the client inside the incoming `UpdateEvent` JSON payload.

Through deterministic testing, a simulated mobile phone submitting a spoofed weight (`confidence_weight: 99.0`) successfully hijacked both categorical and numeric conflict resolution over a legitimate in-vehicle head unit (`confidence_weight: 0.9`), completely overturning the core design premise of the system.

Furthermore, the prototype features **zero network authentication, zero topic authorization, and zero numeric boundary validation**.

---

## 2. Experimental Verification: Client Weight Spoofing & Hijacking

### Test Setup:
* **Legitimate In-Vehicle Head Unit:**
  * Source Type: `car`
  * Value: `genre = "jazz"`, `volume = 30.0`
  * Legitimate Paper Weight: `0.9`
* **Rogue Phone Client:**
  * Source Type: `phone`
  * Value: `genre = "hardstyle"`, `volume = 100.0`
  * Spoofed Weight: `99.0` (client-injected in JSON payload)

### Observed Output of Resolver:
* **Genre Output:** `'hardstyle'` (Audit: `concurrent_categorical_highest_weight`)
* **Volume Output:** `99.37` (Audit: `concurrent_numeric_weighted_avg`)
* **Mathematical Calculation:**
  $$\text{Volume} = \frac{(30.0 \times 0.9) + (100.0 \times 99.0)}{0.9 + 99.0} = \frac{27.0 + 9900.0}{99.9} = \mathbf{99.37}$$

### Code Evidence:
In [resolver_service/resolver.py:73-86](file:///D:/projects/HarmonySync-main/HarmonySync-main/resolver_service/resolver.py#L73-L86):
```python
def group_updates_by_field(updates: List[UpdateEvent]) -> Dict[str, List[FieldCandidate]]:
    grouped: Dict[str, List[FieldCandidate]] = {}
    for update in updates:
        for field_name, value in update.field_updates.items():
            candidate = FieldCandidate(
                field_name=field_name,
                value=value,
                confidence_weight=update.confidence_weight,  # <--- DIRECTLY TRUSTS CLIENT VALUE
                timestamp=update.timestamp,
                vector_clock=update.vector_clock,
                device_id=update.device_id,
                source_type=update.source_type,
                raw_event=update,
            )
```
The dictionary `CONFIDENCE_WEIGHTS` defined in `resolver_service/models.py:8` is **never imported or referenced** in `resolver_service/resolver.py` or `resolver_service/main.py`.

---

## 3. Detailed Security Findings

| Vulnerability / Flaw | Inspected File & Location | Mechanism & Behavior | Exploitability | Severity | Status |
|---|---|---|---|---|---|
| **Client-Supplied Confidence Weights** | `resolver_service/resolver.py:77`<br>`resolver_service/models.py:22` | Server reads `update.confidence_weight` directly from untrusted client payload without server-side validation. | Trivial: Any client sets `confidence_weight: 99.0` in MQTT JSON. | **CRITICAL** | **CONFIRMED DEFECT** |
| **Negative & Non-Positive Weights Accepted** | `resolver_service/models.py:22` | Pydantic model defines `confidence_weight: float = 0.5` without `gt=0` constraint. `confidence_weight: -1.5` accepted. | High: Negative weights can invert weighted averaging or bypass checks. | **HIGH** | **CONFIRMED DEFECT** |
| **Anonymous Unauthenticated MQTT Access** | `mosquitto.conf:1-2`<br>`docker-compose.yml:2-9` | Configuration specifies `listener 1883` and `allow_anonymous true`. Zero TLS, zero username/password. | Trivial: Anyone with network access can connect and publish. | **HIGH** | **CONFIRMED LIMITATION** |
| **Zero Topic Access Control (ACL)** | `resolver_service/main.py:146` | Resolver subscribes to `users/+/updates/+`. No check that client ID matches device ID or user ID. | Trivial: Phone simulator can publish directly to `users/target/updates/car_01`. | **HIGH** | **CONFIRMED DEFECT** |
| **Unbounded Numeric Field Values** | `resolver_service/models.py:23`<br>`resolver_service/resolver.py:118` | `field_updates` values typed as `Union[float, str]`. No bounds on `volume` (e.g. `999999.0` or `-500.0` accepted). | High: Injection of volume `1e9` destroys listening context. | **MEDIUM** | **CONFIRMED DEFECT** |
| **Unbounded & Unvalidated Timestamps** | `resolver_service/models.py:21`<br>`resolver_service/resolver.py:124` | `timestamp` typed as `str`. Accepts arbitrary strings (e.g. `"2099-01-01T00:00:00Z"`). Categorical tie-breaker uses string comparison. | High: Injected future timestamp permanently wins tie-breakers. | **MEDIUM** | **CONFIRMED DEFECT** |
| **Silent Ingestion of Extraneous Payload Keys** | `resolver_service/models.py:15` | Default Pydantic model configuration silently allows extra payload keys without rejection (`extra="ignore"`). | Low: Undetected field injection. | **LOW** | **CONFIRMED RISK** |
| **Buffer Draining Before Persistence (Data Loss)** | `resolver_service/main.py:61, 82` | `flush_user()` pops updates from memory *before* `persist_snapshot()` commits to PostgreSQL. | High: DB connection blip causes silent, permanent update loss. | **CRITICAL** | **CONFIRMED DEFECT** |

---

## 4. Input-Validation Comparison: Client Edge vs Cloud Resolver

| Security Layer | Edge Pre-Aggregation (`aggregator/`) | Cloud Resolver Service (`resolver_service/`) |
|---|---|---|
| **Privacy Check** | **STRICT:** Recursive check (`assert_no_raw_data_leaked`) blocks raw event objects and forbidden substrings (`raw`, `trace`, etc.). | **NONE:** Relies entirely on client-side check. Resolver has no privacy verification. |
| **Confidence Weights** | Assigns `CONFIDENCE_WEIGHTS.get(source_type, 0.5)` on-device. | **BLIND TRUST:** Takes weight from payload, allowing spoofing by untrusted clients. |
| **Payload Scalars** | Enforces scalar types (`int, float, str`) in `field_updates`. | Accepts `Union[float, str]` without range or length bounds. |
| **Device Source Type** | Sets `source_type` from internal state. | Trusts `source_type` string without device certificate authentication. |

---

## 5. Baseline Test Suite Verification

The baseline test suite was re-executed:
```powershell
python -m pytest tests/test_resolver.py tests/test_preaggregation.py -v
```
* **Result:** **22 passed in 6.85 seconds**.
* **Integrity:** Zero modifications to existing application files.

---

## 6. Required Remediations for Phase 12

1. **Authoritative Server-Side Confidence Weights:**
   * Modify `resolver_service/resolver.py`: Override `update.confidence_weight` using authoritative lookup:
     `weight = CONFIDENCE_WEIGHTS.get(update.source_type, 0.5)`
   * Completely ignore any client-supplied `confidence_weight` field.
2. **Strict Field Validation in `UpdateEvent`:**
   * Add validator to ensure `confidence_weight > 0`.
   * Add field-specific boundary validation (e.g. `0.0 <= volume <= 100.0`).
   * Validate that `timestamp` is a valid ISO 8601 string within a reasonable clock-skew tolerance ($\le \pm 60\text{ seconds}$).
3. **Atomic Buffer Persistence:**
   * Do not drain `self.buffers[user_id]` until `persist_snapshot()` has successfully committed the transaction to PostgreSQL.
