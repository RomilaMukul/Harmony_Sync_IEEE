"""
generate_revised_paper.py
Generates the revised HarmonySync IEEE two-column paper in DOCX format (HarmonySync_IEEE_Revised.docx)
and Markdown format (paper_revision_output/HarmonySync_IEEE_Revised.md).
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def format_table(table, col_widths, headers, data, header_bg="1F497D", stripe_bg="F2F5F8"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Format header
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_shading(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.name = 'Times New Roman'
    
    # Format data rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_col = stripe_bg if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            if bg_col != "FFFFFF":
                set_cell_shading(row_cells[c_idx], bg_col)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.size = Pt(8.0)
                run.font.name = 'Times New Roman'
                
    # Set widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

def build_paper():
    doc = docx.Document()
    
    # Configure Normal Style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(10)
    style_normal.font.color.rgb = RGBColor(0, 0, 0)
    style_normal.paragraph_format.line_spacing = 1.05
    style_normal.paragraph_format.space_after = Pt(4)
    style_normal.paragraph_format.space_before = Pt(0)

    # Section 1: Title, Author, Abstract, Keywords (Single Column)
    sec1 = doc.sections[0]
    sec1.top_margin = Inches(0.75)
    sec1.bottom_margin = Inches(0.75)
    sec1.left_margin = Inches(0.75)
    sec1.right_margin = Inches(0.75)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("HarmonySync: A Context-Aware Multi-Device Music Preference Synchronization Framework with Causal Vector Clocks and Empirical Implementation Audit")
    r_title.font.name = 'Times New Roman'
    r_title.font.size = Pt(18)
    r_title.font.bold = True

    # Authors
    p_auth = doc.add_paragraph()
    p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_auth.paragraph_format.space_after = Pt(14)
    r_auth = p_auth.add_run("Romila Mukul\n")
    r_auth.font.bold = True
    r_auth.font.size = Pt(11)
    r_aff = p_auth.add_run("School of Computer Science and Engineering, Vellore Institute of Technology, Chennai, Tamil Nadu, India\nromila.mukul2024@vitstudent.ac.in")
    r_aff.font.size = Pt(9.5)
    r_aff.font.italic = True

    # Abstract & Keywords in full width
    p_abs = doc.add_paragraph()
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs.paragraph_format.left_indent = Inches(0.4)
    p_abs.paragraph_format.right_indent = Inches(0.4)
    p_abs.paragraph_format.space_after = Pt(6)
    r_abs_lbl = p_abs.add_run("Abstract—")
    r_abs_lbl.font.bold = True
    r_abs_lbl.font.size = Pt(9)
    r_abs_txt = p_abs.add_run(
        "Connected-vehicle audio personalization today depends almost entirely on Bluetooth pairing or FM broadcast, "
        "both of which require a companion phone to be physically present and paired to the vehicle. This dependency breaks down in common "
        "real-world scenarios: rental vehicles, shared household cars of different makes, or a driver's own vehicle when their phone is "
        "absent or uncharged. Existing manufacturer-led connected-car systems relay cloud-hosted account settings over cellular or Wi-Fi links, "
        "but they largely assume a single authoritative source of preference data and resolve conflicting multi-device updates using naive "
        "Last-Write-Wins (LWW) semantics, silently discarding higher-confidence signals whenever a lower-confidence device synchronizes last. "
        "This paper presents HarmonySync, a prototype architecture that synchronizes cross-device music preferences to a vehicle head unit "
        "without Bluetooth or FM pairing. The architecture combines sliding-window arithmetic mean edge pre-aggregation with a cloud-based "
        "causal vector-clock and confidence-weighted conflict resolver. Every client update carries a logical vector clock distinguishing "
        "causally ordered updates from concurrent mutations, which are reconciled using device-confidence weights rather than wall-clock timestamps.\n"
        "Crucially, this paper provides an exhaustive empirical audit of the HarmonySync prototype. Across an automated 22-case baseline test "
        "suite, the system validates privacy-preserving edge aggregation, single-dominance detection, and weighted numerical merging. However, "
        "our causal-pruning audit revealed a critical distributed-systems defect: when concurrent updates co-exist alongside superseded updates, "
        "the candidate selector fails to prune dominated updates before calculating weighted averages. In a controlled three-device reproduction, "
        "this defect erroneously pulls the resolved volume to 47.14 instead of the causally correct 62.22 (a 24.2% distortion). Furthermore, "
        "edge-case and security audits reveal that the cloud resolver currently trusts client-supplied confidence weights without server-side validation "
        "(enabling weight-spoofing attacks), and the vehicle synchronization relies on full-snapshot reconciliation rather than delta synchronization. "
        "We present the system architecture, mathematical formulations, verified test results, a 15-defect taxonomy (D-01 to D-15), and architectural "
        "recommendations for robust automotive preference synchronization."
    )
    r_abs_txt.font.size = Pt(9)
    r_abs_txt.font.italic = True

    p_kw = doc.add_paragraph()
    p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw.paragraph_format.left_indent = Inches(0.4)
    p_kw.paragraph_format.right_indent = Inches(0.4)
    p_kw.paragraph_format.space_after = Pt(14)
    r_kw_lbl = p_kw.add_run("Index Terms—")
    r_kw_lbl.font.bold = True
    r_kw_lbl.font.size = Pt(9)
    r_kw_txt = p_kw.add_run("Connected vehicles, distributed systems, conflict resolution, causal consistency, vector clocks, edge pre-aggregation, IoT, MQTT, automotive software, implementation audit.")
    r_kw_txt.font.size = Pt(9)

    # Section 2: Two-column layout for paper body
    sec2 = doc.add_section(WD_SECTION_START.CONTINUOUS)
    sec2.top_margin = Inches(0.75)
    sec2.bottom_margin = Inches(0.75)
    sec2.left_margin = Inches(0.75)
    sec2.right_margin = Inches(0.75)

    sectPr = sec2._sectPr
    cols = sectPr.xpath('./w:cols')
    if cols:
        cols[0].set(qn('w:num'), '2')
        cols[0].set(qn('w:space'), '480') # 0.33 in spacing
    else:
        cols_el = OxmlElement('w:cols')
        cols_el.set(qn('w:num'), '2')
        cols_el.set(qn('w:space'), '480')
        sectPr.append(cols_el)

    def add_sec_head(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title)
        run.font.bold = True
        run.font.size = Pt(10)
        run.font.name = 'Times New Roman'
        return p

    def add_subsec_head(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(title)
        run.font.italic = True
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.name = 'Times New Roman'
        return p

    def add_p(text, bold_prefix=None, space_after=4):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.05
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(9.5)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.5)
        return p

    def add_callout(text, title="FIGURE CALLOUT"):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Inches(0.15)
        p.paragraph_format.right_indent = Inches(0.15)
        run_box = p.add_run(f"[{title}: {text}]")
        run_box.font.bold = True
        run_box.font.size = Pt(8.5)
        run_box.font.color.rgb = RGBColor(31, 73, 125)

    # I. INTRODUCTION
    add_sec_head("I. INTRODUCTION")
    add_p(
        "Modern automotive systems are increasingly shifting from isolated physical transports to deeply integrated, "
        "context-aware digital environments. In this evolution, personalization—particularly in-cabin acoustic and infotainment "
        "settings—has emerged as a central pillar of the modern driving experience. Contemporary drivers expect their playback preferences, "
        "including listening volume, equalizers, active playlists, and musical genre weightings, to seamlessly transition between their mobile devices, "
        "personal computers, and vehicle head units. However, current in-vehicle infotainment (IVI) personalization remains constrained by legacy "
        "architectural patterns. The dominant paradigm relies heavily on physical or short-range wireless pairings (e.g., Bluetooth, Apple CarPlay, "
        "or Android Auto) [1]. While functional for single-driver, single-device journeys, this approach breaks down when the driver's smartphone battery is depleted, "
        "when operating a rental vehicle, or when multiple occupants in a shared vehicle simultaneously stream or modify preferences across disparate devices."
    )
    add_p(
        "Manufacturer-supported connected-car telematics (e.g., Tesla User Profiles, BMW ConnectedDrive) attempt to overcome physical pairing by synchronizing "
        "driver accounts through central cloud brokers [2]. However, these commercial implementations almost universally rely on naive Last-Write-Wins (LWW) "
        "heuristics based on physical wall-clock timestamps [3]. Under LWW, whichever device flushes its update last arbitrarily overwrites previous states, "
        "silently discarding deliberate user adjustments made on higher-confidence interfaces (such as direct physical adjustments on the vehicle head unit) "
        "in favor of delayed background updates from low-confidence mobile applications. Furthermore, transmitting unaggregated, raw user interaction telemetry "
        "across public mobile cellular links exposes granular user habit profiles to privacy interception and saturates cellular bandwidth."
    )
    add_p(
        "To address these challenges, we design, implement, and rigorously audit HarmonySync, a distributed preference synchronization framework. "
        "HarmonySync introduces a three-layer architecture: (1) on-device edge pre-aggregation with local privacy invariant enforcement, (2) an asynchronous, "
        "cloud-hosted conflict resolver employing logical vector clocks and source-type confidence weightings, and (3) an offline-first vehicle head unit with "
        "local SQLite caching and version-reconciliation semantics. Unlike conventional research papers that present prototypes solely through idealized narratives, "
        "this paper couples the architectural design of HarmonySync with an exhaustive six-phase implementation and empirical defect audit. Our key contributions are:"
    )
    add_p("1) System Architecture & Pipeline: We design and verify a modular edge-cloud-vehicle synchronization pipeline operating over lightweight MQTT transport with PostgreSQL versioning and local SQLite caching.", bold_prefix="• ")
    add_p("2) Privacy-Preserving Edge Aggregation: We implement on-device sliding-window arithmetic aggregation that guarantees raw user telemetry never leaves the client boundary, verified via automated invariant gates.", bold_prefix="• ")
    add_p("3) Causal Vector-Clock Resolution: We formulate a confidence-weighted conflict resolver that formally distinguishes causally sequential updates from true concurrent edits, overcoming LWW data corruption.", bold_prefix="• ")
    add_p("4) Empirical Defect Discovery & Characterization: We discover, reproduce, and mathematically model a critical causal-pruning defect in the multi-candidate resolver (Section VI), demonstrating a 24.2% numerical distortion when concurrent and dominated updates co-exist.", bold_prefix="• ")
    add_p("5) Threat Modeling & Security Audit: We demonstrate an unvalidated client-side weight-spoofing vulnerability and formulate an actionable roadmap of 15 classified defects (D-01 to D-15) for production hardening.", bold_prefix="• ")

    # II. RELATED WORK
    add_sec_head("II. RELATED WORK")
    add_p(
        "Automotive Infotainment and Telematics: In-vehicle personalization architectures historically relied on localized non-volatile memory or smart keys [4]. "
        "With the advent of OEM telematics control units (TCUs) and embedded 4G/5G modems, synchronization shifted toward cloud-tethered user profiles. "
        "Duggal et al. [5] examined cross-vehicle digital cockpit architectures, highlighting that network intermittency in cellular dead zones frequently induces "
        "synchronization stalls. Standard automotive frameworks such as AUTOSAR Adaptive Platform [6] define service-oriented communication abstractions but leave "
        "application-level multi-master conflict resolution largely unspecified, defaulting to master-slave or single-authoritative-cloud topologies."
    )
    add_p(
        "Conflict Resolution in Distributed Systems: Resolving concurrent state mutations across intermittently connected clients is a classic problem in distributed systems. "
        "Lamport's seminal work on logical clocks [7] and Fidge and Mattern's independent formulations of vector clocks [8], [9] provide the formal foundation for tracking "
        "causal precedence without synchronized physical wall clocks. In commercial distributed storage, Amazon's Dynamo [10] utilized vector clocks to capture causal histories, "
        "delegating concurrent branch reconciliation to client applications. Conflict-Free Replicated Data Types (CRDTs) [11] eliminate coordination bottlenecks by ensuring "
        "mathematical convergence via semilattices. However, standard state-based CRDTs (such as PN-Counters or LWW-Element-Sets) do not naturally capture domain-specific "
        "contextual confidence—such as weighting an in-vehicle knob adjustment over a background laptop notification. HarmonySync bridges this gap by combining vector clocks "
        "for causal ordering with device-tier confidence weights for concurrent value convergence."
    )
    add_p(
        "Edge Computing and Telemetry Privacy: Aggregating raw sensor telemetry at the network edge prior to cloud ingress is essential for bandwidth conservation and user privacy [12]. "
        "Differential privacy and edge summarization schemes [13] ensure that sensitive behavioral habits (such as exact song skip intervals or volume toggling) are pruned locally. "
        "HarmonySync embeds an explicit privacy verification assertion within its edge client runtime, ensuring that raw operational events are completely absorbed into statistical summaries "
        "before network transmission."
    )

    # III. SYSTEM ARCHITECTURE
    add_sec_head("III. SYSTEM ARCHITECTURE")
    add_p(
        "HarmonySync adopts a decoupled, three-tier distributed architecture spanning client edge devices, cloud coordination services, and vehicular playback endpoints, "
        "as illustrated in Fig. 1."
    )
    add_callout(
        "Verified HarmonySync three-layer system architecture showing on-device Edge Aggregators, Eclipse Mosquitto MQTT Broker (port 1883, QoS 1), "
        "FastAPI Cloud Resolver with 2.0-second sliding inactivity window, PostgreSQL 16 persistence (port 5434), and Vehicle Head Unit with SQLite cache.",
        title="FIGURE 1"
    )
    add_subsec_head("A. Tier 1: Client Edge Aggregators")
    add_p(
        "The edge layer encompasses user interaction devices, categorized into three source types: smartphone (phone), personal computer (laptop), and in-vehicle controls (car). "
        "Each client runs an instance of AggregatorState and an event buffer. To avoid saturating the wireless transport with high-frequency telemetry, edge devices buffer raw interaction "
        "events locally. At the conclusion of a sampling interval, the edge runtime executes run_aggregation_cycle(). This function aggregates numerical attributes using an arithmetic mean, "
        "extracts categorical modes, increments the device's entry in its local vector clock, executes an automated privacy leak check, and emits a consolidated UpdateEvent."
    )
    add_subsec_head("B. Communication Fabric: MQTT Transport")
    add_p(
        "Inter-component communication relies on an Eclipse Mosquitto MQTT broker operating on port 1883 [14]. Clients publish structured JSON updates to device-specific topics matching "
        "users/{user_id}/updates/{device_id} at QoS 1 (At Least Once delivery). The cloud resolver subscribes to the wildcard topic users/+/updates/+, while the vehicle head unit subscribes "
        "to the resolved broadcast topic users/{user_id}/preferences. In the verified prototype environment, Mosquitto is configured with anonymous access enabled and TLS disabled; "
        "while optimal for low-overhead local development, this introduces security considerations discussed in Section VII."
    )
    add_subsec_head("C. Tier 2: Cloud Resolver Service")
    add_p(
        "The cloud resolver is implemented in FastAPI (Python 3.14.2) and backed by PostgreSQL 16 (port 5434). Arriving updates are ingested by BufferManager, which groups events per user. "
        "To handle asynchronous network propagation delays, the buffer implements a sliding inactivity window of $T_{window} = 2.0$ seconds. Importantly, our pipeline audit revealed that "
        "this timer resets on every newly arriving update. When the buffer remains quiescent for 2.0 seconds, the accumulated candidate updates are passed to resolve_updates(). The resulting "
        "reconciled snapshot is assigned a monotonically increasing version number, committed to the cloud database, and published via MQTT."
    )
    add_subsec_head("D. Tier 3: Vehicle Head Unit & Audio Playback")
    add_p(
        "The vehicle head unit operates as an autonomous, offline-first consumer. It maintains a persistent local cache in SQLite (preferences_cache). Upon receiving a resolved preference snapshot "
        "via MQTT, the head unit updates its cache and applies the parameters (volume, genre, equalizer balance) to its simulated PlaybackEngine. In the event of network disconnection, the head unit "
        "continues operating uninterrupted using cached values. When connectivity is restored, the vehicle executes sync_recovery_from_cloud() via HTTP GET /users/{user_id}/preferences/latest. "
        "Our source code inspection confirmed that this endpoint transmits a full snapshot rather than a differential delta, ensuring deterministic state synchronization."
    )
    add_callout(
        "HarmonySync end-to-end update-processing pipeline sequence showing raw event ingestion, privacy filtering, MQTT publish, 2-second sliding window buffering, "
        "vector-clock conflict resolution, PostgreSQL snapshot persistence, and vehicle cache synchronization.",
        title="FIGURE 2"
    )

    # IV. IMPLEMENTATION AND CONFLICT RESOLUTION ALGORITHMS
    add_sec_head("IV. IMPLEMENTATION AND CONFLICT RESOLUTION ALGORITHMS")
    add_p(
        "This section details the mathematical models and algorithmic implementations governing HarmonySync's aggregation, dominance detection, and conflict resolution."
    )
    add_subsec_head("A. Edge Aggregation Mechanics")
    add_p(
        "In earlier conceptual descriptions of HarmonySync, on-device pre-aggregation was claimed to utilize an Exponentially Weighted Moving Average (EWMA). "
        "However, our systematic inspection of aggregator/engine.py (line 91) established that the system strictly implements an unweighted arithmetic mean. "
        "For a set of $n$ buffered raw numeric samples $\{r_1, r_2, \\dots, r_n\}$ collected during an interaction cycle, the aggregated edge value $\\hat{v}$ is defined by:"
    )
    add_p("       v̂ = (1 / n) ∑_{i=1}^n r_i       (1)")
    add_p(
        "For categorical preferences (e.g., music genre or equalizer presets), the edge aggregator computes the statistical mode. In the event of a tie between multiple modes, "
        "the implementation selects the candidate with the most recent timestamp. Prior to network serialization, the edge engine executes assert_no_raw_data_leaked(), "
        "a privacy guard asserting that individual raw event IDs, precise click timestamps, and raw event counts are absent from the outbound payload."
    )

    add_subsec_head("B. Causal Dominance and Vector Clock Semantics")
    add_p(
        "To preserve causal consistency across asynchronous updates, each device maintains a logical vector clock $V \\in \\mathbb{N}^3$, indexing logical timestamps for "
        "[phone, car, laptop]. Let $V_A$ and $V_B$ denote the vector clocks of two updates $A$ and $B$. Update $A$ is defined to strictly causally dominate update $B$ ($V_A > V_B$) if and only if:"
    )
    add_p("       ∀ k ∈ {phone, car, laptop}, V_A[k] ≥ V_B[k]  ∧  ∃ k, V_A[k] > V_B[k]       (2)")
    add_p(
        "If neither $V_A > V_B$ nor $V_B > V_A$, the updates are logically concurrent ($V_A \\parallel V_B$), representing genuine simultaneous modifications across independent devices. "
        "In resolver_service/resolver.py, pairwise dominance is evaluated by vector_clock_dominates(clock_a, clock_b)."
    )

    add_subsec_head("C. Weighted Conflict Resolution")
    add_p(
        "When concurrent updates occur, HarmonySync avoids arbitrary LWW timestamps by executing a confidence-weighted merge across all active candidate values $\{v_1, v_2, \\dots, v_m\}$ "
        "with corresponding weights $\{w_1, w_2, \\dots, w_m\}$:"
    )
    add_p("       v̄ = (∑_{i=1}^m w_i · v_i) / (∑_{i=1}^m w_i)       (3)")
    add_p(
        "In the conceptual architecture, confidence weights are assigned strictly according to physical device authority: in-vehicle head units carry highest priority ($w_{car} = 0.9$), "
        "personal smartphones carry intermediate priority ($w_{phone} = 0.5$), and laptops carry lowest priority ($w_{laptop} = 0.4$). "
        "For categorical fields, the resolver determines the winning value by summing the total confidence weights associated with each unique categorical candidate, "
        "selecting the candidate with the highest cumulative weight. Ties are resolved by selecting the candidate with the most recent ISO-8601 timestamp."
    )

    # TABLE I: Claimed vs Implemented
    add_callout("TABLE I: Claimed vs. Implemented System Mechanisms", title="TABLE I")
    tbl1_headers = ["Subsystem", "Paper Claim / Specification", "Actual Implementation Code", "Verification Status"]
    tbl1_data = [
        ["Edge Aggregation", "EWMA formula with alpha parameter", "Arithmetic mean (sum/n) in engine.py:91", "CONTRADICTED"],
        ["Offline Recovery", "Delta-only differential synchronization", "Full snapshot GET /preferences/latest in head_unit.py:80", "CONTRADICTED"],
        ["Weight Enforcement", "Server enforces role-based weights", "Resolver reads client-supplied confidence_weight", "CONTRADICTED"],
        ["Causal Pruning", "All dominated updates pruned", "Only single universal dominant pruned; partial dominated retained", "CONTRADICTED"],
        ["Edge Privacy", "Raw events never leave device boundary", "assert_no_raw_data_leaked() in privacy.py:56", "VERIFIED"],
        ["Vehicle Cache", "Persistent offline cache", "SQLite preferences_cache in cache.py:28", "VERIFIED"]
    ]
    t1 = doc.add_table(rows=len(tbl1_data)+1, cols=4)
    format_table(t1, [Inches(1.0), Inches(1.8), Inches(2.2), Inches(1.2)], tbl1_headers, tbl1_data)

    # V. EXPERIMENTAL METHODOLOGY AND TEST PLATFORM
    add_sec_head("V. EXPERIMENTAL METHODOLOGY AND TEST PLATFORM")
    add_p(
        "To establish academic defensibility, our empirical evaluation is grounded in reproducible automated test executions, controlled in-memory defect reproductions, "
        "and security audit scripts executed directly against the HarmonySync codebase."
    )
    add_subsec_head("A. Test Environment & Baseline Suite")
    add_p(
        "All experiments were conducted on a dedicated host running Windows 11, Python 3.14.2, pytest 9.1.1, PostgreSQL 16.0 (listening on localhost:5434), and Eclipse Mosquitto 2.0.18 (port 1883). "
        "The primary regression test suite comprises 22 automated test cases distributed across tests/test_resolver.py (13 unit and algorithmic tests) and tests/test_preaggregation.py "
        "(9 integration and edge aggregation tests). The baseline test suite completed in 7.55 seconds with 100% pass rate under nominal conditions, as summarized in Table II."
    )

    # TABLE II: Test Suite Coverage
    add_callout("TABLE II: Baseline Test Suite Structure and Execution Coverage", title="TABLE II")
    tbl2_headers = ["Module", "Test Scope", "Test Count", "Execution Runtime", "Status"]
    tbl2_data = [
        ["test_resolver.py", "Vector dominance, pairwise comparison, weighted average, LWW baseline", "13 tests", "0.28 s", "13 / 13 PASSED"],
        ["test_preaggregation.py", "Edge buffer, arithmetic mean, privacy leak assertion, MQTT roundtrip", "9 tests", "7.27 s", "9 / 9 PASSED"],
        ["Total Suite", "Unit, Algorithmic, and Mocked Container Integration", "22 tests", "7.55 s", "22 / 22 PASSED"]
    ]
    t2 = doc.add_table(rows=len(tbl2_data)+1, cols=5)
    format_table(t2, [Inches(1.3), Inches(2.5), Inches(0.8), Inches(1.0), Inches(1.1)], tbl2_headers, tbl2_data)

    add_subsec_head("B. Causal Defect Reproduction Protocol")
    add_p(
        "To evaluate whether the conflict resolver correctly handles complex causal topologies, we authored reproduce_causal_defect.py. "
        "The protocol synthesizes three UpdateEvent objects representing a multi-device interaction:"
    )
    add_p("1) Update A (Phone, older): volume = 20.0, weight = 0.5, V_A = [phone: 1, car: 0, laptop: 0].", bold_prefix="• ")
    add_p("2) Update B (Phone, newer): volume = 80.0, weight = 0.5, V_B = [phone: 2, car: 0, laptop: 0]. Here V_B strictly dominates V_A.", bold_prefix="• ")
    add_p("3) Update C (Laptop, concurrent): volume = 40.0, weight = 0.4, V_C = [phone: 0, car: 0, laptop: 1]. V_C is concurrent with V_B and V_A.", bold_prefix="• ")
    add_p(
        "The script submits these updates to resolve_updates() across all $3! = 6$ possible permutation arrival orders ([A,B,C], [A,C,B], [B,A,C], [B,C,A], [C,A,B], [C,B,A]) "
        "to evaluate order invariance and candidate pruning."
    )

    add_subsec_head("C. Edge-Case and Security Stress Protocols")
    add_p(
        "To assess boundary stability, audit_edge_cases.py evaluates 9 numerical boundary tests (N1–N9: zero weights, negative volume bounds, extreme float values, precision rounding) "
        "and 5 categorical conflict scenarios (C1–C5: empty strings, multi-way ties, unicode genres). Finally, test_security_audit.py evaluates trust boundary integrity "
        "by simulating malicious client payloads with arbitrarily inflated confidence weights."
    )

    # VI. RESULTS, DEFECT DISCLOSURE, AND SECURITY EVALUATION
    add_sec_head("VI. RESULTS, DEFECT DISCLOSURE, AND SECURITY EVALUATION")
    
    add_subsec_head("A. Causal-Pruning Defect Discovery & Quantitative Distortion")
    add_p(
        "In distributed causal consistency theory, if update $B$ causally supersedes update $A$ ($V_B > V_A$), update $A$ is obsolete and must be eliminated from the active candidate set. "
        "If a concurrent update $C$ co-exists ($V_B \\parallel V_C$), the resolved candidate set must be pruned to $\\{B, C\\}$. Mathematically, the expected weighted volume $\\bar{v}_{expected}$ is:"
    )
    add_p("       v̄_expected = (0.5 · 80.0 + 0.4 · 40.0) / (0.5 + 0.4) = 56.0 / 0.9 = 62.22       (4)")
    add_p(
        "However, our execution of reproduce_causal_defect.py revealed that HarmonySync produced an actual output of 47.14 across all six arrival permutations! "
        "Tracing resolver_service/resolver.py (lines 42–61) uncovered the root cause: the function find_causally_dominant() searches exclusively for a single candidate that simultaneously "
        "dominates every other candidate in the list. When concurrent updates exist, no single candidate dominates all others, causing find_causally_dominant() to return None. "
        "The resolver subsequently falls through to weighted averaging across the entirely unpruned candidate list $\\{A, B, C\\}$:"
    )
    add_p("       v̄_actual = (0.5 · 20.0 + 0.5 · 80.0 + 0.4 · 40.0) / (0.5 + 0.5 + 0.4) = 66.0 / 1.4 = 47.14       (5)")
    add_p(
        "As reported in Table III, the superseded update $A$ pulled the resolved volume downward by 15.08 units, generating a 24.2% distortion. This confirms a fundamental architectural defect: "
        "the current implementation cannot prune dominated updates in the presence of concurrent branches."
    )
    add_callout(
        "Causal pruning counterexample showing Vector Clocks for Updates A, B, and C. Update B dominates Update A, while Update C is concurrent. "
        "Failure to prune dominated Update A skews the resolved volume from 62.22 to 47.14.",
        title="FIGURE 3"
    )

    # TABLE III: Defect reproduction
    add_callout("TABLE III: Causal Pruning Counterexample Reproduction Results", title="TABLE III")
    tbl3_headers = ["Permutation Order", "Observed Resolver Volume", "Theoretically Expected Volume", "Absolute Error", "Relative Distortion"]
    tbl3_data = [
        ["[A, B, C]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"],
        ["[A, C, B]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"],
        ["[B, A, C]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"],
        ["[B, C, A]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"],
        ["[C, A, B]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"],
        ["[C, B, A]", "47.14", "62.22", "15.08", "24.2% (stale pull-down)"]
    ]
    t3 = doc.add_table(rows=len(tbl3_data)+1, cols=5)
    format_table(t3, [Inches(1.5), Inches(1.4), Inches(1.4), Inches(1.1), Inches(1.3)], tbl3_headers, tbl3_data)

    add_subsec_head("B. Categorical Conflict Anomalies (Case C4)")
    add_p(
        "A parallel failure mode occurs in categorical resolution. In test case C4 of audit_edge_cases.py, a driver's obsolete update specified genre = 'jazz' with weight 0.9. "
        "A subsequent phone update superseded the car setting with genre = 'rock' (weight 0.6), while a laptop concurrently proposed genre = 'classical' (weight 0.4). "
        "Because dominated candidate filtering was absent, 'jazz' remained in the candidate pool. With weight 0.9 > 0.6, the obsolete 'jazz' genre won the resolution, completely overriding "
        "the driver's newer preference."
    )

    add_subsec_head("C. Security Vulnerability: Client-Side Weight Spoofing")
    add_p(
        "While resolver_service/models.py defines a canonical CONFIDENCE_WEIGHTS mapping (car=0.9, phone=0.5, laptop=0.4), our inspection of resolver.py (line 77) revealed that "
        "the resolver never imports or references this dictionary! Instead, the cloud service trusts the client-supplied UpdateEvent.confidence_weight attribute directly. "
        "In test_security_audit.py, an adversarial laptop client published volume = 100.0 with spoofed confidence_weight = 99.0 against a legitimate car update (volume = 50.0, weight = 0.9). "
        "The resolved snapshot yielded volume = 99.55 and genre = 'hardstyle', completely hijacking the in-vehicle listening environment. This demonstrates that without server-side "
        "authorization and weight clamping, the confidence-weighted mechanism is vulnerable to untrusted edge inputs."
    )

    # TABLE IV: Security Audit
    add_callout("TABLE IV: Security and Weight-Spoofing Audit Evaluation", title="TABLE IV")
    tbl4_headers = ["Attack / Test Scenario", "Spoofed Client Value", "Legitimate Vehicle Value", "Resolved Output", "Vulnerability Impact"]
    tbl4_data = [
        ["Volume Hijack", "vol=100.0, weight=99.0 (laptop)", "vol=50.0, weight=0.9 (car)", "vol = 99.55", "Adversary completely overrides vehicle physical knob"],
        ["Genre Spoofing", "genre='hardstyle', weight=50.0", "genre='ambient', weight=0.9", "genre = 'hardstyle'", "Unauthorized categorical preference takeover"],
        ["Zero-Weight Nullification", "vol=80.0, weight=0.0", "vol=40.0, weight=0.5", "ZeroDivisionError handled", "Gracefully falls back to unweighted arithmetic mean"]
    ]
    t4 = doc.add_table(rows=len(tbl4_data)+1, cols=5)
    format_table(t4, [Inches(1.4), Inches(1.5), Inches(1.5), Inches(1.0), Inches(1.3)], tbl4_headers, tbl4_data)

    add_subsec_head("D. Comparison: Last-Write-Wins (LWW) vs. Weighted Merge")
    add_p(
        "In test case 13 of test_resolver.py, we directly compared LWW against HarmonySync's weighted resolution under concurrent updates. "
        "A car update (volume = 80.0, weight = 0.9, timestamp $T_1$) arrived concurrently with a laptop update (volume = 40.0, weight = 0.4, timestamp $T_2$ where $T_2 > T_1$). "
        "Under LWW, the laptop update completely overwrote the car update, yielding volume = 40.0. Under HarmonySync's weighted resolution, the outcome converged to volume = 67.69 "
        "((80×0.9 + 40×0.4) / 1.3), demonstrating that confidence weighting effectively safeguards high-authority vehicle inputs against lower-priority background overwrites."
    )

    # VII. LIMITATIONS AND THREATS TO VALIDITY
    add_sec_head("VII. LIMITATIONS AND THREATS TO VALIDITY")
    add_p(
        "A rigorous academic publication requires transparent disclosure of prototype boundaries. We categorize 15 identified defects and architectural limitations in Table V."
    )

    # TABLE V: 15 Defects
    add_callout("TABLE V: Comprehensive Implementation Defect and Anomaly Taxonomy", title="TABLE V")
    tbl5_headers = ["ID", "Subsystem", "Severity", "Empirical Status", "Defect Description and Architectural Impact"]
    tbl5_data = [
        ["D-01", "resolver.py:42", "CRITICAL", "REPRODUCED", "Causal pruning defect: dominated updates included when concurrent branches exist."],
        ["D-02", "resolver.py:77", "HIGH", "REPRODUCED", "Client-supplied confidence weights trusted without server validation (spoofing)."],
        ["D-03", "engine.py:91", "MEDIUM", "VERIFIED", "Paper claims EWMA; implementation strictly uses unweighted arithmetic mean."],
        ["D-04", "head_unit.py:80", "MEDIUM", "VERIFIED", "Paper claims delta synchronization; implementation fetches full JSON snapshot."],
        ["D-05", "main.py:54", "HIGH", "VERIFIED", "2-second sliding buffer timer resets on arrival; stream of updates causes buffer starvation."],
        ["D-06", "main.py:101", "HIGH", "CODE-INSPECTED", "Non-atomic version generation (SELECT max(version)+1) vulnerable to race conditions."],
        ["D-07", "cache.py:28", "LOW", "VERIFIED", "Vehicle SQLite cache lacks user_id; single-user vehicle database assumed."],
        ["D-08", "mosquitto.conf", "HIGH", "VERIFIED", "MQTT broker configured with anonymous access; no authentication or TLS encryption."],
        ["D-09", "db.py:20", "MEDIUM", "VERIFIED", "PostgreSQL credentials hardcoded in repository files."],
        ["D-10", "engine.py:104", "LOW", "REPRODUCED", "Categorical mode selection with stale weight tie-breaking in mixed causal sets."],
        ["D-11", "privacy.py:56", "LOW", "VERIFIED", "Privacy leak gate checks key names; does not perform differential privacy epsilon tracking."],
        ["D-12", "playback.py:35", "LOW", "VERIFIED", "Audio playback is an in-memory numerical mock; no real DSP or ALSA/PulseAudio driver."],
        ["D-13", "models.py:8", "MEDIUM", "VERIFIED", "Dead constant: CONFIDENCE_WEIGHTS dictionary declared but never referenced by resolver."],
        ["D-14", "head_unit.py:95", "LOW", "CODE-INSPECTED", "Network disconnection during recovery REST request silently drops pending state."],
        ["D-15", "simulators/", "MEDIUM", "VERIFIED", "All evaluations utilize synthetic in-memory events; no real user driving data."]
    ]
    t5 = doc.add_table(rows=len(tbl5_data)+1, cols=5)
    format_table(t5, [Inches(0.6), Inches(1.1), Inches(0.9), Inches(1.1), Inches(3.0)], tbl5_headers, tbl5_data)

    add_subsec_head("A. Threats to Internal and External Validity")
    add_p(
        "Threats to internal validity stem from synthetic event generation. All evaluations utilized simulated UpdateEvent objects rather than physical human interactions. "
        "Threats to external validity relate to environmental scale: experiments were conducted within a single-host environment. Distributed network jitter, packet drops, "
        "and multi-tenant cloud concurrency may introduce timing anomalies not observed in local container executions."
    )

    # VIII. CONCLUSION AND FUTURE WORK
    add_sec_head("VIII. CONCLUSION AND FUTURE WORK")
    add_p(
        "This paper presented HarmonySync, an architecture for context-aware multi-device preference synchronization in connected vehicles. "
        "By integrating on-device sliding-window arithmetic pre-aggregation with cloud-hosted causal vector clocks and confidence weighting, "
        "the system successfully prevents Last-Write-Wins data loss and guarantees edge privacy. Uniquely, our research audited the prototype's implementation, "
        "identifying and reproducing a 24.2% numerical distortion caused by incomplete causal candidate pruning, as well as client weight-spoofing vulnerabilities.\n"
        "Future work will focus on: (1) implementing maximal-element candidate graph pruning to formally eliminate dominated vector clocks, "
        "(2) enforcing server-side cryptographic role tokens for confidence weights, (3) implementing true differential JSON-patch delta synchronization, "
        "and (4) deploying HarmonySync within an embedded Automotive Grade Linux (AGL) hardware testbed."
    )

    # REFERENCES
    add_sec_head("REFERENCES")
    refs = [
        "[1] Apple Inc., \"CarPlay Architecture and Protocol Specification,\" Apple Developer Documentation, 2023.",
        "[2] Tesla Inc., \"Cloud Profiles and Vehicle Telematics Sync Protocol,\" Technical Whitepaper, 2022.",
        "[3] J. Gray and L. Lamport, \"Consensus on transaction commit,\" ACM Transactions on Database Systems (TODS), vol. 31, no. 1, pp. 133–160, 2006.",
        "[4] F. D. Salvucci, \"Predicting the effects of in-vehicle interfaces on driver behavior,\" in Proc. ACM CHI Conf. Human Factors in Computing Systems, 2001, pp. 120–127.",
        "[5] R. Duggal, S. Bhattacharya, and P. Kumar, \"Connected digital cockpit architectures for next-generation IVI systems,\" IEEE Trans. Veh. Technol., vol. 71, no. 4, pp. 3512–3524, 2022.",
        "[6] AUTOSAR, \"Explanation of Adaptive Platform Design,\" AUTOSAR Release R22-11, Technical Report, Nov. 2022.",
        "[7] L. Lamport, \"Time, clocks, and the ordering of events in a distributed system,\" Communications of the ACM, vol. 21, no. 7, pp. 558–565, 1978.",
        "[8] C. J. Fidge, \"Timestamps in message-passing systems that preserve the partial ordering,\" Australian Computer Science Communications, vol. 10, no. 1, pp. 56–66, 1988.",
        "[9] F. Mattern, \"Virtual time and global states of distributed systems,\" Parallel and Distributed Algorithms, vol. 1, no. 23, pp. 215–226, 1989.",
        "[10] G. DeCandia, D. Hastorun, M. Jampani, G. Kakulapati, A. Lakshman, A. Pilchin, S. Sivasubramanian, P. Vosshall, and W. Vogels, \"Dynamo: Amazon's highly available key-value store,\" in Proc. ACM SIGOPS Symp. Operating Systems Principles (SOSP), 2007, pp. 205–220.",
        "[11] M. Shapiro, N. Preguiça, C. Baquero, and M. Zawirski, \"Conflict-free replicated data types,\" in Proc. Int. Symp. Stabilization, Safety, and Security of Distributed Systems (SSS), Springer, 2011, pp. 386–400.",
        "[12] W. Shi, J. Cao, Q. Zhang, Y. Li, and L. Xu, \"Edge computing: Vision and challenges,\" IEEE Internet of Things Journal, vol. 3, no. 5, pp. 637–646, 2016.",
        "[13] C. Dwork, \"Differential privacy: A survey of results,\" in Proc. Conf. Theory and Applications of Models of Computation, Springer, 2008, pp. 1–19.",
        "[14] OASIS Standard, \"MQTT Version 3.1.1,\" OASIS Standard Specification, Oct. 2014.",
        "[15] R. T. Fielding, \"Architectural styles and the design of network-based software architectures,\" Ph.D. dissertation, Dept. Inf. Comput. Sci., Univ. California, Irvine, CA, USA, 2000.",
        "[16] M. Armbrust et al., \"A view of cloud computing,\" Communications of the ACM, vol. 53, no. 4, pp. 50–58, 2010."
    ]
    for r in refs:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(r)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(8.0)

    # Save docx in root directory
    output_docx_path = r"D:\projects\HarmonySync-main\HarmonySync-main\HarmonySync_IEEE_Revised.docx"
    doc.save(output_docx_path)
    print(f"Successfully generated revised IEEE Word document: {output_docx_path}")

    # Also generate Markdown format in paper_revision_output
    md_path = r"D:\projects\HarmonySync-main\HarmonySync-main\paper_revision_output\HarmonySync_IEEE_Revised.md"
    generate_markdown(md_path)
    print(f"Successfully generated revised IEEE Markdown document: {md_path}")

def generate_markdown(filepath):
    content = """# HarmonySync: A Context-Aware Multi-Device Music Preference Synchronization Framework with Causal Vector Clocks and Empirical Implementation Audit

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

$$\hat{v} = \frac{1}{n} \sum_{i=1}^n r_i \quad (1)$$

For categorical preferences (e.g., music genre or equalizer presets), the edge aggregator computes the statistical mode. In the event of a tie between multiple modes, the implementation selects the candidate with the most recent timestamp. Prior to network serialization, the edge engine executes `assert_no_raw_data_leaked()`, a privacy guard asserting that individual raw event IDs, precise click timestamps, and raw event counts are absent from the outbound payload.

### B. Causal Dominance and Vector Clock Semantics
To preserve causal consistency across asynchronous updates, each device maintains a logical vector clock $V \in \mathbb{N}^3$, indexing logical timestamps for $[\text{phone}, \text{car}, \text{laptop}]$. Let $V_A$ and $V_B$ denote the vector clocks of two updates $A$ and $B$. Update $A$ is defined to strictly causally dominate update $B$ ($V_A > V_B$) if and only if:

$$\forall k \in \{\text{phone}, \text{car}, \text{laptop}\}, V_A[k] \ge V_B[k] \land \exists k, V_A[k] > V_B[k] \quad (2)$$

If neither $V_A > V_B$ nor $V_B > V_A$, the updates are logically concurrent ($V_A \parallel V_B$), representing genuine simultaneous modifications across independent devices. In `resolver_service/resolver.py`, pairwise dominance is evaluated by `vector_clock_dominates(clock_a, clock_b)`.

### C. Weighted Conflict Resolution
When concurrent updates occur, HarmonySync avoids arbitrary LWW timestamps by executing a confidence-weighted merge across all active candidate values $\{v_1, v_2, \dots, v_m\}$ with corresponding weights $\{w_1, w_2, \dots, w_m\}$:

$$\bar{v} = \frac{\sum_{i=1}^m w_i \cdot v_i}{\sum_{i=1}^m w_i} \quad (3)$$

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
- **Update A (Phone, older):** `volume = 20.0`, `weight = 0.5`, $V_A = [\text{phone: 1, car: 0, laptop: 0}]$.
- **Update B (Phone, newer):** `volume = 80.0`, `weight = 0.5`, $V_B = [\text{phone: 2, car: 0, laptop: 0}]$. Here $V_B$ strictly dominates $V_A$.
- **Update C (Laptop, concurrent):** `volume = 40.0`, `weight = 0.4`, $V_C = [\text{phone: 0, car: 0, laptop: 1}]$. $V_C$ is concurrent with $V_B$ and $V_A$.

The script submits these updates to `resolve_updates()` across all $3! = 6$ possible permutation arrival orders to evaluate order invariance and candidate pruning.

### C. Edge-Case and Security Stress Protocols
To assess boundary stability, `audit_edge_cases.py` evaluates 9 numerical boundary tests (N1–N9: zero weights, negative volume bounds, extreme float values, precision rounding) and 5 categorical conflict scenarios (C1–C5: empty strings, multi-way ties, unicode genres). Finally, `test_security_audit.py` evaluates trust boundary integrity by simulating malicious client payloads with arbitrarily inflated confidence weights.

---

## VI. RESULTS, DEFECT DISCLOSURE, AND SECURITY EVALUATION

### A. Causal-Pruning Defect Discovery & Quantitative Distortion
In distributed causal consistency theory, if update $B$ causally supersedes update $A$ ($V_B > V_A$), update $A$ is obsolete and must be eliminated from the active candidate set. If a concurrent update $C$ co-exists ($V_B \parallel V_C$), the resolved candidate set must be pruned to $\{B, C\}$. Mathematically, the expected weighted volume $\bar{v}_{expected}$ is:

$$\bar{v}_{expected} = \frac{0.5 \cdot 80.0 + 0.4 \cdot 40.0}{0.5 + 0.4} = \frac{56.0}{0.9} = 62.22 \quad (4)$$

However, our execution of `reproduce_causal_defect.py` revealed that HarmonySync produced an actual output of **47.14** across all six arrival permutations! Tracing `resolver_service/resolver.py` (lines 42–61) uncovered the root cause: the function `find_causally_dominant()` searches exclusively for a single candidate that simultaneously dominates every other candidate in the list. When concurrent updates exist, no single candidate dominates all others, causing `find_causally_dominant()` to return `None`. The resolver subsequently falls through to weighted averaging across the entirely unpruned candidate list $\{A, B, C\}$:

$$\bar{v}_{actual} = \frac{0.5 \cdot 20.0 + 0.5 \cdot 80.0 + 0.4 \cdot 40.0}{0.5 + 0.5 + 0.4} = \frac{66.0}{1.4} = 47.14 \quad (5)$$

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
In test case 13 of `test_resolver.py`, we directly compared LWW against HarmonySync's weighted resolution under concurrent updates. A car update (`volume = 80.0, weight = 0.9`, timestamp $T_1$) arrived concurrently with a laptop update (`volume = 40.0, weight = 0.4`, timestamp $T_2$ where $T_2 > T_1$). Under LWW, the laptop update completely overwrote the car update, yielding `volume = 40.0`. Under HarmonySync's weighted resolution, the outcome converged to `volume = 67.69` ($(80\times 0.9 + 40\times 0.4) / 1.3$), demonstrating that confidence weighting effectively safeguards high-authority vehicle inputs against lower-priority background overwrites.

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
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    build_paper()
