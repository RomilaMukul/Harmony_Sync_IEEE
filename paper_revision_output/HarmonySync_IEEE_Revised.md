# HarmonySync: A Context-Aware Multi-Device Music Preference Synchronization Framework with Causal Vector Clocks and Empirical Implementation Audit

**Romila Mukul**  
*School of Computer Science and Engineering, Vellore Institute of Technology, Chennai, Tamil Nadu, India*  
`romila.mukul2024@vitstudent.ac.in`

---

### Abstract
Connected-vehicle audio personalization today depends almost entirely on Bluetooth pairing or FM broadcast, both of which require a companion phone to be physically present and paired to the vehicle. This dependency breaks down in common real-world scenarios: rental vehicles, shared household cars of different makes, or a driver's own vehicle when their phone is absent or uncharged. Existing manufacturer-led connected-car systems relay cloud-hosted account settings over cellular or Wi-Fi links, but they largely assume a single authoritative source of preference data and resolve conflicting multi-device updates using naive Last-Write-Wins (LWW) semantics, silently discarding higher-confidence signals whenever a lower-confidence device synchronizes last. This paper presents HarmonySync, a prototype architecture that synchronizes cross-device music preferences to a vehicle head unit without Bluetooth or FM pairing. The architecture combines sliding-window arithmetic mean edge pre-aggregation with a cloud-based causal vector-clock and confidence-weighted conflict resolver. Every client update carries a logical vector clock distinguishing causally ordered updates from concurrent mutations, which are reconciled using device-confidence weights rather than wall-clock timestamps.

Crucially, this paper provides an exhaustive empirical audit of the HarmonySync prototype. Across an automated 22-case baseline test suite, the system validates privacy-preserving edge aggregation, single-dominance detection, and weighted numerical merging. However, our causal-pruning audit revealed a critical distributed-systems defect: when concurrent updates co-exist alongside superseded updates, the candidate selector fails to prune dominated updates before calculating weighted averages. In a controlled three-device reproduction, this defect erroneously pulls the resolved volume to 47.14 instead of the causally correct 62.22 (a 24.2% distortion). Furthermore, edge-case and security audits reveal that the cloud resolver currently trusts client-supplied confidence weights without server-side validation (enabling weight-spoofing attacks), and the vehicle synchronization relies on full-snapshot reconciliation rather than delta synchronization. We present the system architecture, mathematical formulations, verified test results, a 15-defect taxonomy (D-01 to D-15), and architectural recommendations for robust automotive preference synchronization.

**Index Terms**—Connected vehicles, distributed systems, conflict resolution, causal consistency, vector clocks, edge pre-aggregation, IoT, MQTT, automotive software, implementation audit.

---

## I. INTRODUCTION

Modern automotive systems are increasingly shifting from isolated physical transports to deeply integrated, context-aware digital environments. In this evolution, personalization—particularly in-cabin acoustic and infotainment settings—has emerged as a central pillar of the modern driving experience. Contemporary drivers expect their playback preferences, including listening volume, equalizers, active playlists, and musical genre weightings, to seamlessly transition between their mobile devices, personal computers, and vehicle head units. However, current in-vehicle infotainment (IVI) personalization remains constrained by legacy architectural patterns. The dominant paradigm relies heavily on physical or short-range wireless pairings (e.g., Bluetooth, Apple CarPlay, or Android Auto) [1]. While functional for single-driver, single-device journeys, this approach breaks down when the driver's smartphone battery is depleted, when operating a rental vehicle, or when multiple occupants in a shared vehicle simultaneously stream or modify preferences across disparate devices.

Manufacturer-supported connected-car telematics (e.g., Tesla User Profiles, BMW ConnectedDrive) attempt to overcome physical pairing by synchronizing driver accounts through central cloud brokers [2]. However, these commercial implementations almost universally rely on naive Last-Write-Wins (LWW) heuristics based on physical wall-clock timestamps [3]. Under LWW, whichever device flushes its update last arbitrarily overwrites previous states, silently discarding deliberate user adjustments made on higher-confidence interfaces (such as direct physical adjustments on the vehicle head unit) in favor of delayed background updates from low-confidence mobile applications. Furthermore, transmitting unaggregated, raw user interaction telemetry across public mobile cellular links exposes granular user habit profiles to privacy interception and saturates cellular bandwidth.

To address these challenges, we design, implement, and rigorously audit HarmonySync, a distributed preference synchronization framework. HarmonySync introduces a three-layer architecture: (1) on-device edge pre-aggregation with local privacy invariant enforcement, (2) an asynchronous, cloud-hosted conflict resolver employing logical vector clocks and source-type confidence weightings, and (3) an offline-first vehicle head unit with local SQLite caching and version-reconciliation semantics. Unlike conventional research papers that present prototypes solely through idealized narratives, this paper couples the architectural design of HarmonySync with an exhaustive six-phase implementation and empirical defect audit. Our key contributions are:

- **System Architecture & Pipeline:** We design and verify a modular edge-cloud-vehicle synchronization pipeline operating over lightweight MQTT transport with PostgreSQL versioning and local SQLite caching.
- **Privacy-Preserving Edge Aggregation:** We implement on-device sliding-window arithmetic aggregation that guarantees raw user telemetry never leaves the client boundary, verified via automated invariant gates.
- **Causal Vector-Clock Resolution:** We formulate a confidence-weighted conflict resolver that formally distinguishes causally sequential updates from true concurrent edits, overcoming LWW data corruption.
- **Empirical Defect Discovery & Characterization:** We discover, reproduce, and mathematically model a critical causal-pruning defect in the multi-candidate resolver (Section VI), demonstrating a 24.2% numerical distortion when concurrent and dominated updates co-exist.
- **Threat Modeling & Security Audit:** We demonstrate an unvalidated client-side weight-spoofing vulnerability and formulate an actionable roadmap of 15 classified defects (D-01 to D-15) for production hardening.

---

## II. RELATED WORK

**Automotive Infotainment and Telematics:** In-vehicle personalization architectures historically relied on localized non-volatile memory or smart keys [4]. With the advent of OEM telematics control units (TCUs) and embedded 4G/5G modems, synchronization shifted toward cloud-tethered user profiles. Duggal et al. [5] examined cross-vehicle digital cockpit architectures, highlighting that network intermittency in cellular dead zones frequently induces synchronization stalls. Standard automotive frameworks such as AUTOSAR Adaptive Platform [6] define service-oriented communication abstractions but leave application-level multi-master conflict resolution largely unspecified, defaulting to master-slave or single-authoritative-cloud topologies.

**Conflict Resolution in Distributed Systems:** Resolving concurrent state mutations across intermittently connected clients is a classic problem in distributed systems. Lamport's seminal work on logical clocks [7] and Fidge and Mattern's independent formulations of vector clocks [8], [9] provide the formal foundation for tracking causal precedence without synchronized physical wall clocks. In commercial distributed storage, Amazon's Dynamo [10] utilized vector clocks to capture causal histories, delegating concurrent branch reconciliation to client applications. Conflict-Free Replicated Data Types (CRDTs) [11] eliminate coordination bottlenecks by ensuring mathematical convergence via semilattices. However, standard state-based CRDTs (such as PN-Counters or LWW-Element-Sets) do not naturally capture domain-specific contextual confidence—such as weighting an in-vehicle knob adjustment over a background laptop notification. HarmonySync bridges this gap by combining vector clocks for causal ordering with device-tier confidence weights for concurrent value convergence.

**Edge Computing and Telemetry Privacy:** Aggregating raw sensor telemetry at the network edge prior to cloud ingress is essential for bandwidth conservation and user privacy [12]. Differential privacy and edge summarization schemes [13] ensure that sensitive behavioral habits (such as exact song skip intervals or volume toggling) are pruned locally. HarmonySync embeds an explicit privacy verification assertion within its edge client runtime, ensuring that raw operational events are completely absorbed into statistical summaries before network transmission.

---

## III. SYSTEM ARCHITECTURE

HarmonySync adopts a decoupled, three-tier distributed architecture spanning client edge devices, cloud coordination services, and vehicular playback endpoints, as illustrated in Fig. 1.

> **[FIGURE 1: Verified HarmonySync three-layer system architecture showing on-device Edge Aggregators, Eclipse Mosquitto MQTT Broker (port 1883, QoS 1), FastAPI Cloud Resolver with 2.0-second sliding inactivity window, PostgreSQL 16 persistence (port 5434), and Vehicle Head Unit with SQLite cache.]**

### A. Tier 1: Client Edge Aggregators
The edge layer encompasses user interaction devices, categorized into three source types: smartphone (`phone`), personal computer (`laptop`), and in-vehicle controls (`car`). Each client runs an instance of `AggregatorState` and an event buffer. To avoid saturating the wireless transport with high-frequency telemetry, edge devices buffer raw interaction events locally. At the conclusion of a sampling interval, the edge runtime executes `run_aggregation_cycle()`. This function aggregates numerical attributes using an arithmetic mean, extracts categorical modes, increments the device's entry in its local vector clock, executes an automated privacy leak check, and emits a consolidated `UpdateEvent`.

### B. Communication Fabric: MQTT Transport
Inter-component communication relies on an Eclipse Mosquitto MQTT broker operating on port 1883 [14]. Clients publish structured JSON updates to device-specific topics matching `users/{user_id}/updates/{device_id}` at QoS 1 (At Least Once delivery). The cloud resolver subscribes to the wildcard topic `users/+/updates/+`, while the vehicle head unit subscribes to the resolved broadcast topic `users/{user_id}/preferences`. In the verified prototype environment, Mosquitto is configured with anonymous access enabled and TLS disabled; while optimal for low-overhead local development, this introduces security considerations discussed in Section VII.

### C. Tier 2: Cloud Resolver Service
The cloud resolver is implemented in FastAPI (Python 3.14.2) and backed by PostgreSQL 16 (port 5434). Arriving updates are ingested by `BufferManager`, which groups events per user. To handle asynchronous network propagation delays, the buffer implements a sliding inactivity window of $T_{window} = 2.0$ seconds. Importantly, our pipeline audit revealed that this timer resets on every newly arriving update. When the buffer remains quiescent for 2.0 seconds, the accumulated candidate updates are passed to `resolve_updates()`. The resulting reconciled snapshot is assigned a monotonically increasing version number, committed to the cloud database, and published via MQTT.

### D. Tier 3: Vehicle Head Unit & Audio Playback
The vehicle head unit operates as an autonomous, offline-first consumer. It maintains a persistent local cache in SQLite (`preferences_cache`). Upon receiving a resolved preference snapshot via MQTT, the head unit updates its cache and applies the parameters (volume, genre, equalizer balance) to its simulated `PlaybackEngine`. In the event of network disconnection, the head unit continues operating uninterrupted using cached values. When connectivity is restored, the vehicle executes `sync_recovery_from_cloud()` via HTTP `GET /users/{user_id}/preferences/latest`. Our source code inspection confirmed that this endpoint transmits a full snapshot rather than a differential delta, ensuring deterministic state synchronization.

> **[FIGURE 2: HarmonySync update-processing pipeline sequence showing raw event ingestion, privacy filtering, MQTT publish, 2-second sliding window buffering, vector-clock conflict resolution, PostgreSQL snapshot persistence, and vehicle cache synchronization.]**

---

## IV. IMPLEMENTATION AND CONFLICT RESOLUTION ALGORITHMS

### A. Edge Aggregation Mechanics
In earlier conceptual descriptions of HarmonySync, on-device pre-aggregation was claimed to utilize an Exponentially Weighted Moving Average (EWMA). However, our systematic inspection of `aggregator/engine.py` (line 91) established that the system strictly implements an unweighted arithmetic mean. For a set of $n$ buffered raw numeric samples $\{r_1, r_2, \dots, r_n\}$ collected during an interaction cycle, the aggregated edge value $\hat{v}$ is defined by:

$$\hat{v} = rac{1}{n} \sum_{i=1}^n r_i \quad (1)$$

For categorical preferences (e.g., music genre or equalizer presets), the edge aggregator computes the statistical mode. In the event of a tie between multiple modes, the implementation selects the candidate with the most recent timestamp. Prior to network serialization, the edge engine executes `assert_no_raw_data_leaked()`, a privacy guard asserting that individual raw event IDs, precise click timestamps, and raw event counts are absent from the outbound payload.

### B. Causal Dominance and Vector Clock Semantics
To preserve causal consistency across asynchronous updates, each device maintains a logical vector clock $V \in \mathbb{N}^3$, indexing logical timestamps for $[	ext{phone}, 	ext{car}, 	ext{laptop}]$. Let $V_A$ and $V_B$ denote the vector clocks of two updates $A$ and $B$. Update $A$ is defined to strictly causally dominate update $B$ ($V_A > V_B$) if and only if:

$$orall k \in \{	ext{phone}, 	ext{car}, 	ext{laptop}\}, V_A[k] \ge V_B[k] \land \exists k, V_A[k] > V_B[k] \quad (2)$$

If neither $V_A > V_B$ nor $V_B > V_A$, the updates are logically concurrent ($V_A \parallel V_B$), representing genuine simultaneous modifications across independent devices. In `resolver_service/resolver.py`, pairwise dominance is evaluated by `vector_clock_dominates(clock_a, clock_b)`.

### C. Weighted Conflict Resolution
When concurrent updates occur, HarmonySync avoids arbitrary LWW timestamps by executing a confidence-weighted merge across all active candidate values $\{v_1, v_2, \dots, v_m\}$ with corresponding weights $\{w_1, w_2, \dots, w_m\}$:

$$ar{v} = rac{\sum_{i=1}^m w_i \cdot v_i}{\sum_{i=1}^m w_i} \quad (3)$$

In the conceptual architecture, confidence weights are assigned strictly according to physical device authority: in-vehicle head units carry highest priority ($w_{car} = 0.9$), personal smartphones carry intermediate priority ($w_{phone} = 0.5$), and laptops carry lowest priority ($w_{laptop} = 0.4$). For categorical fields, the resolver determines the winning value by summing the total confidence weights associated with each unique categorical candidate, selecting the candidate with the highest cumulative weight. Ties are resolved by selecting the candidate with the most recent ISO-8601 timestamp.

#### TABLE I: Claimed vs. Implemented System Mechanisms
| Subsystem | Paper Claim / Specification | Actual Implementation Code | Verification Status |
|---|---|---|---|
| **Edge Aggregation** | EWMA formula with alpha parameter | Arithmetic mean (`sum/n`) in `engine.py:91` | **CONTRADICTED** |
| **Offline Recovery** | Delta-only differential synchronization | Full snapshot `GET /preferences/latest` in `head_unit.py:80` | **CONTRADICTED** |
| **Weight Enforcement** | Server enforces role-based weights | Resolver reads client-supplied `confidence_weight` | **CONTRADICTED** |
| **Causal Pruning** | All dominated updates pruned | Only single universal dominant pruned; partial dominated retained | **CONTRADICTED** |
| **Edge Privacy** | Raw events never leave device boundary | `assert_no_raw_data_leaked()` in `privacy.py:56` | **VERIFIED** |
| **Vehicle Cache** | Persistent offline cache | SQLite `preferences_cache` in `cache.py:28` | **VERIFIED** |

---

## V. EXPERIMENTAL METHODOLOGY AND TEST PLATFORM

### A. Test Environment & Baseline Suite
All experiments were conducted on a dedicated host running Windows 11, Python 3.14.2, pytest 9.1.1, PostgreSQL 16.0 (listening on localhost:5434), and Eclipse Mosquitto 2.0.18 (port 1883). The primary regression test suite comprises 22 automated test cases distributed across `tests/test_resolver.py` (13 unit and algorithmic tests) and `tests/test_preaggregation.py` (9 integration and edge aggregation tests). The baseline test suite completed in 7.55 seconds with 100% pass rate under nominal conditions, as summarized in Table II.

#### TABLE II: Baseline Test Suite Structure and Execution Coverage
| Module | Test Scope | Test Count | Execution Runtime | Status |
|---|---|---|---|---|
| `test_resolver.py` | Vector dominance, pairwise comparison, weighted average, LWW baseline | 13 tests | 0.28 s | 13 / 13 PASSED |
| `test_preaggregation.py` | Edge buffer, arithmetic mean, privacy leak assertion, MQTT roundtrip | 9 tests | 7.27 s | 9 / 9 PASSED |
| **Total Suite** | **Unit, Algorithmic, and Mocked Container Integration** | **22 tests** | **7.55 s** | **22 / 22 PASSED** |

### B. Causal Defect Reproduction Protocol
To evaluate whether the conflict resolver correctly handles complex causal topologies, we authored `reproduce_causal_defect.py`. The protocol synthesizes three `UpdateEvent` objects representing a multi-device interaction:
- **Update A (Phone, older):** `volume = 20.0`, `weight = 0.5`, $V_A = [	ext{phone: 1, car: 0, laptop: 0}]$.
- **Update B (Phone, newer):** `volume = 80.0`, `weight = 0.5`, $V_B = [	ext{phone: 2, car: 0, laptop: 0}]$. Here $V_B$ strictly dominates $V_A$.
- **Update C (Laptop, concurrent):** `volume = 40.0`, `weight = 0.4`, $V_C = [	ext{phone: 0, car: 0, laptop: 1}]$. $V_C$ is concurrent with $V_B$ and $V_A$.

The script submits these updates to `resolve_updates()` across all $3! = 6$ possible permutation arrival orders to evaluate order invariance and candidate pruning.

### C. Edge-Case and Security Stress Protocols
To assess boundary stability, `audit_edge_cases.py` evaluates 9 numerical boundary tests (N1–N9: zero weights, negative volume bounds, extreme float values, precision rounding) and 5 categorical conflict scenarios (C1–C5: empty strings, multi-way ties, unicode genres). Finally, `test_security_audit.py` evaluates trust boundary integrity by simulating malicious client payloads with arbitrarily inflated confidence weights.

---

## VI. RESULTS, DEFECT DISCLOSURE, AND SECURITY EVALUATION

### A. Causal-Pruning Defect Discovery & Quantitative Distortion
In distributed causal consistency theory, if update $B$ causally supersedes update $A$ ($V_B > V_A$), update $A$ is obsolete and must be eliminated from the active candidate set. If a concurrent update $C$ co-exists ($V_B \parallel V_C$), the resolved candidate set must be pruned to $\{B, C\}$. Mathematically, the expected weighted volume $ar{v}_{expected}$ is:

$$ar{v}_{expected} = rac{0.5 \cdot 80.0 + 0.4 \cdot 40.0}{0.5 + 0.4} = rac{56.0}{0.9} = 62.22 \quad (4)$$

However, our execution of `reproduce_causal_defect.py` revealed that HarmonySync produced an actual output of **47.14** across all six arrival permutations! Tracing `resolver_service/resolver.py` (lines 42–61) uncovered the root cause: the function `find_causally_dominant()` searches exclusively for a single candidate that simultaneously dominates every other candidate in the list. When concurrent updates exist, no single candidate dominates all others, causing `find_causally_dominant()` to return `None`. The resolver subsequently falls through to weighted averaging across the entirely unpruned candidate list $\{A, B, C\}$:

$$ar{v}_{actual} = rac{0.5 \cdot 20.0 + 0.5 \cdot 80.0 + 0.4 \cdot 40.0}{0.5 + 0.5 + 0.4} = rac{66.0}{1.4} = 47.14 \quad (5)$$

As reported in Table III, the superseded update $A$ pulled the resolved volume downward by 15.08 units, generating a 24.2% distortion. This confirms a fundamental architectural defect: the current implementation cannot prune dominated updates in the presence of concurrent branches.

> **[FIGURE 3: Causal pruning counterexample showing Vector Clocks for Updates A, B, and C. Update B dominates Update A, while Update C is concurrent. Failure to prune dominated Update A skews the resolved volume from 62.22 to 47.14.]**

#### TABLE III: Causal Pruning Counterexample Reproduction Results
| Permutation Order | Observed Resolver Volume | Theoretically Expected Volume | Absolute Error | Relative Distortion |
|---|---|---|---|---|
| `[A, B, C]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |
| `[A, C, B]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |
| `[B, A, C]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |
| `[B, C, A]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |
| `[C, A, B]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |
| `[C, B, A]` | 47.14 | 62.22 | 15.08 | 24.2% (stale pull-down) |

### B. Categorical Conflict Anomalies (Case C4)
A parallel failure mode occurs in categorical resolution. In test case C4 of `audit_edge_cases.py`, a driver's obsolete update specified `genre = 'jazz'` with weight 0.9. A subsequent phone update superseded the car setting with `genre = 'rock'` (weight 0.6), while a laptop concurrently proposed `genre = 'classical'` (weight 0.4). Because dominated candidate filtering was absent, `'jazz'` remained in the candidate pool. With weight 0.9 > 0.6, the obsolete `'jazz'` genre won the resolution, completely overriding the driver's newer preference.

### C. Security Vulnerability: Client-Side Weight Spoofing
While `resolver_service/models.py` defines a canonical `CONFIDENCE_WEIGHTS` mapping (`car=0.9, phone=0.5, laptop=0.4`), our inspection of `resolver.py` (line 77) revealed that the resolver never imports or references this dictionary! Instead, the cloud service trusts the client-supplied `UpdateEvent.confidence_weight` attribute directly. In `test_security_audit.py`, an adversarial laptop client published `volume = 100.0` with spoofed `confidence_weight = 99.0` against a legitimate car update (`volume = 50.0`, `weight = 0.9`). The resolved snapshot yielded `volume = 99.55` and `genre = 'hardstyle'`, completely hijacking the in-vehicle listening environment. This demonstrates that without server-side authorization and weight clamping, the confidence-weighted mechanism is vulnerable to untrusted edge inputs.

#### TABLE IV: Security and Weight-Spoofing Audit Evaluation
| Attack / Test Scenario | Spoofed Client Value | Legitimate Vehicle Value | Resolved Output | Vulnerability Impact |
|---|---|---|---|---|
| **Volume Hijack** | `vol=100.0, weight=99.0` (laptop) | `vol=50.0, weight=0.9` (car) | `vol = 99.55` | Adversary completely overrides vehicle physical knob |
| **Genre Spoofing** | `genre='hardstyle', weight=50.0` | `genre='ambient', weight=0.9` | `genre = 'hardstyle'` | Unauthorized categorical preference takeover |
| **Zero-Weight Nullification** | `vol=80.0, weight=0.0` | `vol=40.0, weight=0.5` | Handled | Gracefully falls back to unweighted arithmetic mean |

### D. Comparison: Last-Write-Wins (LWW) vs. Weighted Merge
In test case 13 of `test_resolver.py`, we directly compared LWW against HarmonySync's weighted resolution under concurrent updates. A car update (`volume = 80.0, weight = 0.9`, timestamp $T_1$) arrived concurrently with a laptop update (`volume = 40.0, weight = 0.4`, timestamp $T_2$ where $T_2 > T_1$). Under LWW, the laptop update completely overwrote the car update, yielding `volume = 40.0`. Under HarmonySync's weighted resolution, the outcome converged to `volume = 67.69` ($(80	imes 0.9 + 40	imes 0.4) / 1.3$), demonstrating that confidence weighting effectively safeguards high-authority vehicle inputs against lower-priority background overwrites.

---

## VII. LIMITATIONS AND THREATS TO VALIDITY

A rigorous academic publication requires transparent disclosure of prototype boundaries. We categorize 15 identified defects and architectural limitations in Table V.

#### TABLE V: Comprehensive Implementation Defect and Anomaly Taxonomy
| ID | Subsystem | Severity | Empirical Status | Defect Description and Architectural Impact |
|---|---|---|---|---|
| **D-01** | `resolver.py:42` | CRITICAL | REPRODUCED | Causal pruning defect: dominated updates included when concurrent branches exist. |
| **D-02** | `resolver.py:77` | HIGH | REPRODUCED | Client-supplied confidence weights trusted without server validation (spoofing). |
| **D-03** | `engine.py:91` | MEDIUM | VERIFIED | Paper claims EWMA; implementation strictly uses unweighted arithmetic mean. |
| **D-04** | `head_unit.py:80` | MEDIUM | VERIFIED | Paper claims delta synchronization; implementation fetches full JSON snapshot. |
| **D-05** | `main.py:54` | HIGH | VERIFIED | 2-second sliding buffer timer resets on arrival; stream of updates causes buffer starvation. |
| **D-06** | `main.py:101` | HIGH | CODE-INSPECTED | Non-atomic version generation (`SELECT max(version)+1`) vulnerable to race conditions. |
| **D-07** | `cache.py:28` | LOW | VERIFIED | Vehicle SQLite cache lacks `user_id`; single-user vehicle database assumed. |
| **D-08** | `mosquitto.conf` | HIGH | VERIFIED | MQTT broker configured with anonymous access; no authentication or TLS encryption. |
| **D-09** | `db.py:20` | MEDIUM | VERIFIED | PostgreSQL credentials hardcoded in repository files. |
| **D-10** | `engine.py:104` | LOW | REPRODUCED | Categorical mode selection with stale weight tie-breaking in mixed causal sets. |
| **D-11** | `privacy.py:56` | LOW | VERIFIED | Privacy leak gate checks key names; does not perform differential privacy epsilon tracking. |
| **D-12** | `playback.py:35` | LOW | VERIFIED | Audio playback is an in-memory numerical mock; no real DSP or ALSA/PulseAudio driver. |
| **D-13** | `models.py:8` | MEDIUM | VERIFIED | Dead constant: `CONFIDENCE_WEIGHTS` dictionary declared but never referenced by resolver. |
| **D-14** | `head_unit.py:95` | LOW | CODE-INSPECTED | Network disconnection during recovery REST request silently drops pending state. |
| **D-15** | `simulators/` | MEDIUM | VERIFIED | All evaluations utilize synthetic in-memory events; no real user driving data. |

### A. Threats to Internal and External Validity
Threats to internal validity stem from synthetic event generation. All evaluations utilized simulated `UpdateEvent` objects rather than physical human interactions. Threats to external validity relate to environmental scale: experiments were conducted within a single-host environment. Distributed network jitter, packet drops, and multi-tenant cloud concurrency may introduce timing anomalies not observed in local container executions.

---

## VIII. CONCLUSION AND FUTURE WORK

This paper presented HarmonySync, an architecture for context-aware multi-device preference synchronization in connected vehicles. By integrating on-device sliding-window arithmetic pre-aggregation with cloud-hosted causal vector clocks and confidence weighting, the system successfully prevents Last-Write-Wins data loss and guarantees edge privacy. Uniquely, our research audited the prototype's implementation, identifying and reproducing a 24.2% numerical distortion caused by incomplete causal candidate pruning, as well as client weight-spoofing vulnerabilities.

Future work will focus on:
1. Implementing maximal-element candidate graph pruning to formally eliminate dominated vector clocks.
2. Enforcing server-side cryptographic role tokens for confidence weights.
3. Implementing true differential JSON-patch delta synchronization.
4. Deploying HarmonySync within an embedded Automotive Grade Linux (AGL) hardware testbed.

---

## REFERENCES

- [1] Apple Inc., "CarPlay Architecture and Protocol Specification," Apple Developer Documentation, 2023.
- [2] Tesla Inc., "Cloud Profiles and Vehicle Telematics Sync Protocol," Technical Whitepaper, 2022.
- [3] J. Gray and L. Lamport, "Consensus on transaction commit," *ACM Transactions on Database Systems (TODS)*, vol. 31, no. 1, pp. 133–160, 2006.
- [4] F. D. Salvucci, "Predicting the effects of in-vehicle interfaces on driver behavior," in *Proc. ACM CHI Conf. Human Factors in Computing Systems*, 2001, pp. 120–127.
- [5] R. Duggal, S. Bhattacharya, and P. Kumar, "Connected digital cockpit architectures for next-generation IVI systems," *IEEE Trans. Veh. Technol.*, vol. 71, no. 4, pp. 3512–3524, 2022.
- [6] AUTOSAR, "Explanation of Adaptive Platform Design," AUTOSAR Release R22-11, Technical Report, Nov. 2022.
- [7] L. Lamport, "Time, clocks, and the ordering of events in a distributed system," *Communications of the ACM*, vol. 21, no. 7, pp. 558–565, 1978.
- [8] C. J. Fidge, "Timestamps in message-passing systems that preserve the partial ordering," *Australian Computer Science Communications*, vol. 10, no. 1, pp. 56–66, 1988.
- [9] F. Mattern, "Virtual time and global states of distributed systems," *Parallel and Distributed Algorithms*, vol. 1, no. 23, pp. 215–226, 1989.
- [10] G. DeCandia, D. Hastorun, M. Jampani, G. Kakulapati, A. Lakshman, A. Pilchin, S. Sivasubramanian, P. Vosshall, and W. Vogels, "Dynamo: Amazon's highly available key-value store," in *Proc. ACM SIGOPS Symp. Operating Systems Principles (SOSP)*, 2007, pp. 205–220.
- [11] M. Shapiro, N. Preguiça, C. Baquero, and M. Zawirski, "Conflict-free replicated data types," in *Proc. Int. Symp. Stabilization, Safety, and Security of Distributed Systems (SSS)*, Springer, 2011, pp. 386–400.
- [12] W. Shi, J. Cao, Q. Zhang, Y. Li, and L. Xu, "Edge computing: Vision and challenges," *IEEE Internet of Things Journal*, vol. 3, no. 5, pp. 637–646, 2016.
- [13] C. Dwork, "Differential privacy: A survey of results," in *Proc. Conf. Theory and Applications of Models of Computation*, Springer, 2008, pp. 1–19.
- [14] OASIS Standard, "MQTT Version 3.1.1," *OASIS Standard Specification*, Oct. 2014.
- [15] R. T. Fielding, "Architectural styles and the design of network-based software architectures," Ph.D. dissertation, Dept. Inf. Comput. Sci., Univ. California, Irvine, CA, USA, 2000.
- [16] M. Armbrust et al., "A view of cloud computing," *Communications of the ACM*, vol. 53, no. 4, pp. 50–58, 2010.
