"""
generate_paper_figures.py
Generates publication-quality, 300 DPI figures for the revised HarmonySync paper.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configure high quality font rendering
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

output_dir = r"D:\projects\HarmonySync-main\HarmonySync-main\paper_figures"
os.makedirs(output_dir, exist_ok=True)

# -------------------------------------------------------------
# FIG 1: System Architecture Diagram
# -------------------------------------------------------------
def make_fig1():
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Color palette
    c_edge = '#E6F0FA'
    c_net = '#FFF2CC'
    c_cloud = '#E2EFDA'
    c_veh = '#FCE4D6'
    border = '#2E4053'

    # Tier 1: Edge Box
    ax.add_patch(patches.FancyBboxPatch((0.4, 0.5), 2.4, 5.0, boxstyle="round,pad=0.1", fc=c_edge, ec=border, lw=1.5))
    ax.text(1.6, 5.2, "TIER 1: CLIENT EDGE", ha='center', va='center', weight='bold', fontsize=9.5, color='#1B4F72')
    
    devices = [("Smartphone (phone)", 4.2), ("In-Vehicle (car)", 3.2), ("Laptop (laptop)", 2.2)]
    for name, y in devices:
        ax.add_patch(patches.FancyBboxPatch((0.6, y-0.35), 2.0, 0.65, boxstyle="round,pad=0.05", fc='#FFFFFF', ec='#5D6D7E', lw=1.0))
        ax.text(1.6, y, name, ha='center', va='center', fontsize=8.0)
    
    ax.add_patch(patches.Rectangle((0.6, 0.8), 2.0, 0.8, fc='#D4E6F1', ec='#2980B9', lw=1.0))
    ax.text(1.6, 1.3, "Edge Aggregator\n(Arithmetic Mean)", ha='center', va='center', fontsize=7.5, weight='bold')
    ax.text(1.6, 0.95, "assert_no_raw_data_leaked()", ha='center', va='center', fontsize=6.5, style='italic', color='#78281F')

    # Network: MQTT Broker
    ax.add_patch(patches.FancyBboxPatch((3.3, 2.0), 1.5, 2.0, boxstyle="round,pad=0.1", fc=c_net, ec='#D68910', lw=1.5))
    ax.text(4.05, 3.5, "MQTT BROKER\n(Mosquitto)", ha='center', va='center', weight='bold', fontsize=8.5, color='#7D6608')
    ax.text(4.05, 2.7, "Port 1883\nQoS 1\n(Anonymous)", ha='center', va='center', fontsize=7.5)

    # Tier 2: Cloud Resolver Box
    ax.add_patch(patches.FancyBboxPatch((5.3, 0.5), 2.1, 5.0, boxstyle="round,pad=0.1", fc=c_cloud, ec='#1E8449', lw=1.5))
    ax.text(6.35, 5.2, "TIER 2: CLOUD SERVICE", ha='center', va='center', weight='bold', fontsize=9.5, color='#145A32')
    
    ax.add_patch(patches.Rectangle((5.5, 3.8), 1.7, 0.9, fc='#FFFFFF', ec='#27AE60', lw=1.0))
    ax.text(6.35, 4.35, "BufferManager", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(6.35, 4.0, "2.0s Inactivity Window", ha='center', va='center', fontsize=7.0, color='#922B21')

    ax.add_patch(patches.Rectangle((5.5, 2.5), 1.7, 0.9, fc='#FFFFFF', ec='#27AE60', lw=1.0))
    ax.text(6.35, 3.05, "Conflict Resolver", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(6.35, 2.7, "Vector Clock + Weights", ha='center', va='center', fontsize=7.0)

    ax.add_patch(patches.Rectangle((5.5, 0.9), 1.7, 1.2, fc='#D5F5E3', ec='#229954', lw=1.0))
    ax.text(6.35, 1.7, "PostgreSQL 16", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(6.35, 1.3, "Port 5434\nSnapshot Versioning", ha='center', va='center', fontsize=7.0)

    # Tier 3: Vehicle Head Unit Box
    ax.add_patch(patches.FancyBboxPatch((7.9, 0.5), 1.7, 5.0, boxstyle="round,pad=0.1", fc=c_veh, ec='#BA4A00', lw=1.5))
    ax.text(8.75, 5.2, "TIER 3: VEHICLE", ha='center', va='center', weight='bold', fontsize=9.5, color='#6E2C00')
    
    ax.add_patch(patches.Rectangle((8.1, 3.6), 1.3, 0.9, fc='#FFFFFF', ec='#D35400', lw=1.0))
    ax.text(8.75, 4.15, "Head Unit", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(8.75, 3.8, "MQTT Subscriber", ha='center', va='center', fontsize=7.0)

    ax.add_patch(patches.Rectangle((8.1, 2.3), 1.3, 0.9, fc='#FFFFFF', ec='#D35400', lw=1.0))
    ax.text(8.75, 2.85, "VehicleCache", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(8.75, 2.5, "SQLite (Offline)", ha='center', va='center', fontsize=7.0)

    ax.add_patch(patches.Rectangle((8.1, 1.0), 1.3, 0.9, fc='#FFFFFF', ec='#D35400', lw=1.0))
    ax.text(8.75, 1.55, "PlaybackEngine", ha='center', va='center', fontsize=8.0, weight='bold')
    ax.text(8.75, 1.2, "Volume / Genre", ha='center', va='center', fontsize=7.0)

    # Connecting Arrows
    arrow_style = dict(arrowstyle="->", lw=1.3, color='#2C3E50')
    ax.annotate("", xy=(3.3, 3.0), xytext=(2.6, 1.3), arrowprops=arrow_style)
    ax.text(2.8, 2.3, "Pub: updates\n(QoS 1)", fontsize=6.8, ha='center', backgroundcolor='#FFFFFF')

    ax.annotate("", xy=(5.5, 4.2), xytext=(4.8, 3.2), arrowprops=arrow_style)
    ax.text(5.1, 3.8, "Sub: updates", fontsize=6.8, ha='center', backgroundcolor='#FFFFFF')

    ax.annotate("", xy=(4.8, 2.6), xytext=(5.5, 2.8), arrowprops=arrow_style)
    ax.annotate("", xy=(8.1, 4.0), xytext=(4.8, 2.4), arrowprops=arrow_style)
    ax.text(4.2, 1.6, "Pub: preferences\n(QoS 1)", fontsize=6.8, ha='center', backgroundcolor='#FFFFFF')

    # Recovery Arrow
    arrow_rec = dict(arrowstyle="->", lw=1.2, color='#A93226', ls='--')
    ax.annotate("", xy=(7.2, 1.5), xytext=(8.1, 2.7), arrowprops=arrow_rec)
    ax.text(7.6, 2.3, "Recovery: GET snapshot", fontsize=6.5, ha='center', color='#922B21', backgroundcolor='#FFFFFF')

    plt.tight_layout()
    fig1_path = os.path.join(output_dir, "fig1_system_architecture.png")
    plt.savefig(fig1_path, bbox_inches='tight')
    plt.close()
    print(f"Generated {fig1_path}")

# -------------------------------------------------------------
# FIG 3: Causal Pruning Counterexample
# -------------------------------------------------------------
def make_fig3():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 4.2), dpi=300)

    # Panel A: Correct Causal Pruning
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.set_title("Panel A: Correct Causal Semantics (Expected)", fontsize=10, weight='bold', color='#196F3D', pad=10)

    ax1.add_patch(patches.FancyBboxPatch((0.5, 7.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#EAECEE', ec='#7F8C8D', lw=1.2))
    ax1.text(2.4, 8.3, "Update A (Phone, Old)\nVol: 20.0, w: 0.5\nVC: [P:1, C:0, L:0]", ha='center', va='center', fontsize=7.5)

    ax1.add_patch(patches.FancyBboxPatch((0.5, 4.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#D4EFDF', ec='#27AE60', lw=1.5))
    ax1.text(2.4, 5.3, "Update B (Phone, New)\nVol: 80.0, w: 0.5\nVC: [P:2, C:0, L:0]", ha='center', va='center', fontsize=7.5, weight='bold')

    ax1.add_patch(patches.FancyBboxPatch((5.7, 4.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#D4EFDF', ec='#27AE60', lw=1.5))
    ax1.text(7.6, 5.3, "Update C (Laptop, Conc)\nVol: 40.0, w: 0.4\nVC: [P:0, C:0, L:1]", ha='center', va='center', fontsize=7.5, weight='bold')

    ax1.annotate("B strictly dominates A (B > A)\n→ Prune A (Obsolete)", xy=(2.4, 6.9), xytext=(2.4, 6.1),
                 arrowprops=dict(arrowstyle="<-", lw=1.5, color='#C0392B'), ha='center', fontsize=7.0, color='#C0392B', weight='bold')

    ax1.add_patch(patches.Rectangle((0.5, 0.5), 9.0, 2.5, fc='#F2F4F4', ec='#27AE60', lw=1.5))
    ax1.text(5.0, 2.4, "Active Candidate Set: {B, C}", ha='center', va='center', fontsize=8.5, weight='bold', color='#145A32')
    ax1.text(5.0, 1.7, "Weighted Average: (0.5×80.0 + 0.4×40.0) / (0.5 + 0.4)", ha='center', va='center', fontsize=7.8)
    ax1.text(5.0, 1.0, "Resolved Volume: 62.22 (Mathematically Correct)", ha='center', va='center', fontsize=9.0, weight='bold', color='#1E8449')

    # Panel B: Actual Implemented Defect
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    ax2.set_title("Panel B: Current Prototype Defect (Actual)", fontsize=10, weight='bold', color='#922B21', pad=10)

    ax2.add_patch(patches.FancyBboxPatch((0.5, 7.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#FADBD8', ec='#E74C3C', lw=1.5))
    ax2.text(2.4, 8.3, "Update A (Phone, Old)\nVol: 20.0, w: 0.5\nVC: [P:1, C:0, L:0]", ha='center', va='center', fontsize=7.5, color='#78281F')

    ax2.add_patch(patches.FancyBboxPatch((0.5, 4.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#FADBD8', ec='#E74C3C', lw=1.5))
    ax2.text(2.4, 5.3, "Update B (Phone, New)\nVol: 80.0, w: 0.5\nVC: [P:2, C:0, L:0]", ha='center', va='center', fontsize=7.5, color='#78281F')

    ax2.add_patch(patches.FancyBboxPatch((5.7, 4.0), 3.8, 2.0, boxstyle="round,pad=0.1", fc='#FADBD8', ec='#E74C3C', lw=1.5))
    ax2.text(7.6, 5.3, "Update C (Laptop, Conc)\nVol: 40.0, w: 0.4\nVC: [P:0, C:0, L:1]", ha='center', va='center', fontsize=7.5, color='#78281F')

    ax2.text(5.0, 6.4, "find_causally_dominant() returns None!\n(No single update dominates all others)\n→ Falls through without pruning A",
             ha='center', va='center', fontsize=7.0, color='#922B21', weight='bold')

    ax2.add_patch(patches.Rectangle((0.5, 0.5), 9.0, 2.5, fc='#FDEDEC', ec='#E74C3C', lw=1.5))
    ax2.text(5.0, 2.4, "Unpruned Pool: {A, B, C} (Includes obsolete A)", ha='center', va='center', fontsize=8.5, weight='bold', color='#78281F')
    ax2.text(5.0, 1.7, "Weighted Average: (0.5×20 + 0.5×80 + 0.4×40) / (0.5+0.5+0.4)", ha='center', va='center', fontsize=7.8)
    ax2.text(5.0, 1.0, "Resolved Volume: 47.14 (Error: -15.08 / 24.2% skew)", ha='center', va='center', fontsize=9.0, weight='bold', color='#922B21')

    plt.tight_layout()
    fig3_path = os.path.join(output_dir, "fig3_causal_defect_counterexample.png")
    plt.savefig(fig3_path, bbox_inches='tight')
    plt.close()
    print(f"Generated {fig3_path}")

# -------------------------------------------------------------
# FIG 5: Vehicle Recovery Workflow Diagram
# -------------------------------------------------------------
def make_fig5():
    fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    # Lifeline Headers
    ax.add_patch(patches.Rectangle((0.8, 5.0), 2.2, 0.7, fc='#D4E6F1', ec='#2980B9', lw=1.2))
    ax.text(1.9, 5.35, "Vehicle Head Unit", ha='center', va='center', weight='bold', fontsize=8.5)

    ax.add_patch(patches.Rectangle((4.0, 5.0), 2.0, 0.7, fc='#D5F5E3', ec='#27AE60', lw=1.2))
    ax.text(5.0, 5.35, "Cloud REST API", ha='center', va='center', weight='bold', fontsize=8.5)

    ax.add_patch(patches.Rectangle((7.0, 5.0), 2.2, 0.7, fc='#FCF3CF', ec='#F39C12', lw=1.2))
    ax.text(8.1, 5.35, "PostgreSQL 16", ha='center', va='center', weight='bold', fontsize=8.5)

    # Lifelines
    ax.plot([1.9, 1.9], [1.0, 5.0], color='#85929E', ls='--', lw=1.0)
    ax.plot([5.0, 5.0], [1.0, 5.0], color='#85929E', ls='--', lw=1.0)
    ax.plot([8.1, 8.1], [1.0, 5.0], color='#85929E', ls='--', lw=1.0)

    # Sequence Messages
    # 1. Detection
    ax.text(1.9, 4.4, "1. Network Reconnected", ha='center', fontsize=7.5, style='italic', backgroundcolor='#FFFFFF')

    # 2. GET Request
    ax.annotate("", xy=(5.0, 3.8), xytext=(1.9, 3.8), arrowprops=dict(arrowstyle="->", lw=1.2, color='#2C3E50'))
    ax.text(3.45, 4.0, "2. GET /preferences/latest", ha='center', fontsize=7.5, weight='bold')

    # 3. DB Query
    ax.annotate("", xy=(8.1, 3.2), xytext=(5.0, 3.2), arrowprops=dict(arrowstyle="->", lw=1.2, color='#2C3E50'))
    ax.text(6.55, 3.4, "3. Query max(version)", ha='center', fontsize=7.5)

    # 4. DB Return
    ax.annotate("", xy=(5.0, 2.6), xytext=(8.1, 2.6), arrowprops=dict(arrowstyle="->", lw=1.0, color='#7F8C8D', ls=':'))
    ax.text(6.55, 2.8, "4. Return Row", ha='center', fontsize=7.2)

    # 5. Full Snapshot response
    ax.annotate("", xy=(1.9, 2.0), xytext=(5.0, 2.0), arrowprops=dict(arrowstyle="->", lw=1.2, color='#C0392B'))
    ax.text(3.45, 2.2, "5. 200 OK: Full JSON Snapshot", ha='center', fontsize=7.5, weight='bold', color='#922B21')

    # 6. Cache store
    ax.text(1.9, 1.4, "6. VehicleCache.store_snapshot()\n(Full overwrite; NO delta)", ha='center', fontsize=7.2,
            style='italic', color='#922B21', backgroundcolor='#FDEDEC')

    plt.tight_layout()
    fig5_path = os.path.join(output_dir, "fig5_recovery_workflow.png")
    plt.savefig(fig5_path, bbox_inches='tight')
    plt.close()
    print(f"Generated {fig5_path}")

if __name__ == '__main__':
    make_fig1()
    make_fig3()
    make_fig5()
    print("All paper figures generated successfully!")
