# HarmonySync — Revision Changelog

**Date:** 2026-10-16  
**Document:** HarmonySync_Paper_Fixed.docx → HarmonySync_IEEE_Revised.docx  
**Basis:** Six-phase implementation audit (Phases 2–6); full source-code inspection

> This changelog documents every material change made (or required) during the paper revision. Items marked [IMPLEMENTED IN REVISED DOCX] have been applied. Items marked [AUTHOR ACTION REQUIRED] require the author to supply missing information.

---

## 1. Title

| Change | Rationale |
|---|---|
| Remove or qualify any form of "real-time" | System has a 2-second inactivity window; "real-time" is unsupported |
| Remove "optimal" if present | No comparative optimality analysis exists |
| Suggested revised title: "HarmonySync: A Prototype for Context-Aware Multi-Device Music Preference Synchronization Using Causal Vector Clocks and Confidence-Weighted Conflict Resolution" | Accurate and defensible |

---

## 2. Abstract

| Change | Rationale |
|---|---|
| Replace "EWMA-based on-device pre-aggregation" → "sliding-window arithmetic mean aggregation" | aggregator/engine.py:91 implements sum/n; no EWMA anywhere |
| Replace "delta-only synchronization" → "full-snapshot version reconciliation on vehicle reconnect" | vehicle/head_unit.py:80-106 fetches GET /preferences/latest (full snapshot) |
| Add: "A confirmed defect in the causal-pruning logic causes superseded updates to be included in weighted averaging when concurrent updates co-exist, yielding 47.14 instead of the correct 62.22 in a controlled three-device reproduction." | Phase 4 evidence; factually required |
| Remove any mention of production readiness, security, or scalability | None of these are demonstrated |
| Add: "All evaluations use synthetic preference inputs and controlled in-memory or local-service tests." | Integrity requirement |
| [AUTHOR ACTION REQUIRED] Fill: actual author name(s), affiliation(s), and corresponding author email | Not present in audit evidence |

---

## 3. Index Terms

| Change | Rationale |
|---|---|
| Retain: distributed systems, conflict resolution, vector clocks, MQTT, IoT, connected vehicles, preference synchronization | Accurate |
| Remove: "EWMA", "real-time synchronization", "secure" | Not verified |
| Add: "implementation audit", "causal consistency" | Reflect actual contribution |

---

## 4. Section I — Introduction

| Change | Rationale |
|---|---|
| Separate prototype goals from demonstrated behavior | Required by integrity rules |
| Replace "enforces confidence weights" → "assigns confidence weights by source type in the intended design; current prototype trusts client-supplied values" | C-008; Phase 6 §2 |
| Replace "Python 3.11" → "Python 3.14.2 (actual runtime; requirements.txt specifies no Python version)" | C-009; Phase 2 §1 |
| Contribution list should read: (1) three-layer prototype architecture; (2) causal vector-clock and confidence-weighted resolver; (3) privacy guard at edge layer; (4) reproducible causal-pruning defect characterization; (5) weight-spoofing vulnerability analysis | Accurate scope |

---

## 5. Section II — Related Work

| Change | Rationale |
|---|---|
| Verify all citation details before inclusion | Integrity requirement |
| Do not claim novelty over any work unless a specific property is verified | Integrity requirement |
| Remove invented DOIs or fabricated references | Integrity requirement |
| [AUTHOR ACTION REQUIRED] Verify and provide full bibliographic details for all retained references | Cannot be checked from source code |

---

## 6. Section III — System Architecture

| Change | Rationale |
|---|---|
| Describe three verified layers: Edge Aggregation, Cloud Resolver Service (FastAPI), Vehicle Head Unit | VERIFIED |
| Add: "MQTT broker configured with anonymous access; no TLS or authentication" | Phase 6; mosquitto.conf |
| Add: "Vehicle SQLite cache does not include a user_id column; single-user-per-database-file assumed" | Phase 3; vehicle/cache.py |
| Change: "2-second buffer window" → "2-second inactivity sliding window (timer resets on each arriving update)" | Phase 3; main.py:54 |
| Add Fig. 1 marker: [FIGURE 1 INSERT HERE: Verified HarmonySync three-layer system architecture] | Architecture visualization |
| Add Fig. 2 marker after pipeline description: [FIGURE 2 INSERT HERE: Actual update-processing pipeline] | Pipeline visualization |

---

## 7. Section IV — Implementation and Algorithms

| Change | Rationale |
|---|---|
| **EWMA → Arithmetic Mean:** Replace all EWMA equations with: $\hat{v} = \frac{1}{n}\sum_{i=1}^{n} r_i$ where $ is the number of buffered raw samples in the current cycle | aggregator/engine.py:91; CONTRADICTED by source code |
| **Categorical aggregation:** Accurately describe mode selection with latest-on-tie for same-mode-count | aggregator/engine.py:104-117 |
| **Causal dominance scope:** Add: "This check is effective only when a single candidate strictly dominates all others simultaneously. The implementation does not perform maximal candidate filtering; when concurrent and dominated updates co-exist, dominated updates are erroneously included in resolution." | resolver.py:42-61; Phase 4 |
| **Weighted average:** Retain formula $\frac{\sum w_i v_i}{\sum w_i}$ — correctly implemented | resolver.py:115-118 |
| Add Table I marker: [FIGURE 4 INSERT HERE: Aggregation formula — claimed vs implemented] | Clarifies discrepancy |
| **Recovery subsection:** Replace delta-sync description with: "On reconnect, the vehicle head unit issues a single HTTP GET to /users/{user_id}/preferences/latest. The response contains the full preference snapshot. Vector clock metadata is not embedded in the snapshot payload." | head_unit.py:80-106 |
| Add Fig. 7 marker: [FIGURE 7 INSERT HERE: Vehicle recovery workflow] | Recovery visualization |
| **Confidence weights:** Add: "The CONFIDENCE_WEIGHTS dictionary (car=0.9, phone=0.5, laptop=0.4) is defined in resolver_service/models.py but is not imported or enforced by the resolver at runtime. The cloud resolver reads confidence_weight directly from the client payload." | Phase 6; models.py:8; resolver.py:77 |

---

## 8. Section V — Experimental Methodology

| Change | Rationale |
|---|---|
| Report test suite as: 22 tests; Python 3.14.2; pytest 9.1.1; 7.55 s; command: python -m pytest tests/test_resolver.py tests/test_preaggregation.py -v | Phase 2 verbatim |
| Add Table II marker: [FIGURE 5 INSERT HERE: Test suite coverage table] | Phase 2 data |
| Describe causal defect reproduction: inputs, command (python reproduce_causal_defect.py), in-memory execution, 6 permutations | Phase 4 |
| Describe edge-case audit: command (python audit_edge_cases.py), N1–N9 and C1–C5, in-memory execution | Phase 5 |
| Describe weight-spoofing test: command (python test_security_audit.py), setup, in-memory execution | Phase 6 |
| Explicitly state: "All experiments use synthetic UpdateEvent objects. No real user interaction data, real music player integration, or production telemetry was used." | Integrity requirement |

---

## 9. Section VI — Results and Discussion

| Change | Rationale |
|---|---|
| Include confirmed causal defect values: actual=47.14, expected=62.22, error=15.08 (24.2%), all 6 permutations defective | Phase 4 VERIFIED |
| Add Fig. 3 marker: [FIGURE 3 INSERT HERE: Reproducible causal-pruning counterexample] | Visualization |
| Include C4 categorical defect: obsolete 'jazz' (w=0.9) wins over newer 'rock' (w=0.6) | Phase 5 VERIFIED |
| Include weight-spoofing: volume=99.37 (formula verified); genre='hardstyle' | Phase 6 VERIFIED |
| Remove any invented latency/throughput/scalability numbers | No evidence exists |
| [AUTHOR ACTION REQUIRED: RUN LATENCY EXPERIMENT AND INSERT VERIFIED RESULT] | No measurement exists |
| Discuss LWW vs weighted merge using Test 13 verified values: LWW=40.0, Weighted=62.22 | test_resolver.py:test_13 VERIFIED |

---

## 10. Section VII — Limitations and Threats to Validity

| Change | Rationale |
|---|---|
| Add all 15 defects from Defect Summary Table (D-01 through D-15) | Required by integrity rules |
| Distinguish: D-01 (confirmed + reproduced), D-03 (confirmed + reproduced), D-05 (confirmed from code), D-06 (code-level risk only), D-08–D-15 (code-level analysis) | Avoid overstating reproduction depth |
| Internal validity: no A/B comparison across algorithm variants; all comparisons synthetic | Required |
| External validity: synthetic inputs only; no real users, no real music player, no field deployment | Required |
| Measurement validity: test suite exercises only 2-device scenarios; 3-device defect is in untested path | Required |
| Reproducibility: all in-memory tests fully reproducible without network; 3 integration tests require live containers | Phase 2 |

---

## 11. Section VIII — Conclusion and Future Work

| Change | Rationale |
|---|---|
| Summarize actual contribution: privacy-preserving edge aggregation prototype + reproducible defect characterization | Factual |
| Do NOT introduce new performance claims in conclusion | Integrity rule |
| Future work: (1) maximal-candidate pruning fix in resolver.py; (2) server-side weight enforcement; (3) atomic buffer persistence; (4) delta synchronization implementation; (5) MQTT authentication and TLS; (6) latency and scalability evaluation; (7) real user evaluation | Based on confirmed defects |

---

## 12. References

| Change | Rationale |
|---|---|
| [AUTHOR ACTION REQUIRED] Verify all existing references against original publications | Cannot verify from source code |
| Remove any references that cannot be verified (no fabricated authors, titles, DOIs, or URLs) | Integrity requirement |
| Add standard references: Lamport (1978) vector clocks; MQTT v3.1.1 specification (OASIS); Paxos/CRDTs if directly compared | Only if cited claims are verified |
| Use IEEE numbered format: [1], [2], … | IEEE formatting |

---

## 13. IEEE Formatting Changes

| Change | Rationale |
|---|---|
| IEEE two-column layout with standard margins | Required |
| IEEE title + author block | Required |
| Abstract + Index Terms block | Required |
| Roman numeral section headings | Required |
| IEEE numbered citations [1]–[N] | Required |
| Sequential figure and table numbering (Fig. 1, Fig. 2, ..., Table I, Table II) | Required |
| Equation numbering for all displayed equations | Required |
| [AUTHOR ACTION REQUIRED] Insert real author names, affiliations, and email | Not available from code |
| [AUTHOR ACTION REQUIRED] Insert copyright/conference footer if venue is known | Not determinable from code |

---

## Author Decisions Required

| Decision ID | Decision Required |
|---|---|
| AD-01 | Provide author name(s), affiliation(s), email address |
| AD-02 | Confirm target venue (IEEE conference or journal) and its page limit |
| AD-03 | Verify or replace all references in the reference list |
| AD-04 | Decide whether to fix causal pruning defect before submission (and if so, add regression tests) |
| AD-05 | Run end-to-end latency experiment if any latency claim is to be made |
| AD-06 | Capture demo terminal screenshot for Fig. 4 (optional) |
| AD-07 | Decide whether to disclose weight-spoofing vulnerability in full detail or summarize |
| AD-08 | Confirm whether the paper targets a security/privacy venue or a systems/IoT venue |
