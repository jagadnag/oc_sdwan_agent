# Daily Operational Workflows for SDWAN_AI

This document defines repeatable playbooks for the three SDWAN_AI personas. Each workflow includes the trigger, MCP tools used, decision tree, sample LLM prompt, and expected output.

---

## 1. Morning Health Check (Scheduled Daily at 8am ET)

**Trigger**: Cron job `0 8 * * MON-FRI` (Eastern time)

**Persona**: sdwan-architect

**Duration**: 3-5 minutes

**Objective**: Assess fabric state at business day start; alert on overnight issues.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_devices(limit=1000)` | Inventory of all fabric devices |
| `get_control_plane_health()` | vSmart/vBond/OMP peer status |
| `get_data_plane_health()` | BFD sessions, tunnel status |
| `get_alarms(severity_min="critical", limit=20)` | Critical/major alarms |
| `get_fabric_overview()` | Reachability statistics |

### Decision Tree

```
START: Health Check
  ├─→ Get fabric overview
  │     ├─→ Reachable devices > 98%? YES → GOOD
  │     └─→ Reachable devices < 98%? NO → Flag unreachable list
  │
  ├─→ Get control plane health
  │     ├─→ All vSmarts up? YES → GOOD
  │     ├─→ Any vSmart down? NO → CRITICAL (escalate)
  │     └─→ Any OMP peers down? YES → Flag, investigate
  │
  ├─→ Get data plane health
  │     ├─→ BFD flapping? YES → Flag device pairs
  │     └─→ BFD stable? NO → GOOD
  │
  ├─→ Get alarms
  │     ├─→ 0 critical? YES → GOOD
  │     └─→ >0 critical? NO → Summarize by category
  │
  └─→ Synthesize & Report
        ├─→ Fabric HEALTHY → Brief summary, standby
        ├─→ Fabric at risk → Detailed findings + recommendations
        └─→ Fabric CRITICAL → Page architect
```

### Sample LLM Prompt

```
Run SDWAN_AI morning health check for fabric "production-us-east".

Steps:
1. Get fabric overview (all devices, reachability count)
2. Get control plane health (vSmarts, OMP peers)
3. Get data plane health (BFD sessions)
4. Get critical/major alarms (limit 20)

Synthesis:
- Compare reachability to baseline (should be >98%)
- Flag any control plane issues (vSmart down, OMP peers down)
- Identify BFD flapping tunnels (>2 state changes in last hour)
- Categorize alarms by root cause (hardware, software, config)
- Provide 1-3 actionable recommendations if issues found

Tone: Executive summary (1 paragraph healthy; 3-5 paragraphs if issues)

Expected output format:
---
**SDWAN Fabric Health Check - 2025-01-15 08:00 ET**

Status: [HEALTHY | AT RISK | CRITICAL]

**Fabric Overview**
- Total Devices: 147
- Reachable: 145 (98.6%)
- Unreachable: 2 (vedge-dc2-2, vedge-backhaul-1)

**Control Plane**
[Summary of vSmarts and OMP peers]

**Data Plane**
[Summary of BFD sessions; any flapping?]

**Alarms**
[Top issues by severity and category]

**Recommendations**
1. [Action 1]
2. [Action 2]
---
```

### Expected Output

```
**SDWAN Fabric Health Check - 2025-01-15 08:00 ET**

Status: HEALTHY

**Fabric Overview**
- Total Devices: 147
- Reachable: 145 (98.6%)
- Unreachable: 2 (vedge-dc2-2, vedge-backhaul-1)
  - Note: vedge-dc2-2 unreachable since 2025-01-14 23:45 ET
  - Note: vedge-backhaul-1 planned maintenance window

**Control Plane**
- vSmarts: 3/3 online (hub-1, hub-2, hub-3)
- OMP Peers: 145/145 established
- Control Connections: All healthy (0 flaps in last 4h)

**Data Plane**
- BFD Sessions: 284 up, 0 down
- Flapping Detection: 0 sessions flapping
- IPsec Tunnels: 568 active, 0 errors

**Alarms**
- Critical: 0
- Major: 2 (vedge-dc2-2 unreachable [known], vedge-backhaul-1 unreachable [maintenance])
- Minor: 5 (routine interface flaps on site-50, site-75)

**Recommendations**
1. No immediate action required
2. Monitor vedge-dc2-2; expect to come online post-maintenance
3. Site-50 and site-75 interface flaps merit investigation (likely ISP circuit)
```

---

## 2. Alarm Triage (On-Demand, When Paged)

**Trigger**: PagerDuty alert or manual request

**Persona**: sdwan-troubleshooter

**Duration**: 5-15 minutes (depending on complexity)

**Objective**: Rapidly diagnose alarm root cause and provide mitigation steps.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_alarms(severity_min, limit=50)` | Fetch all active alarms |
| `get_events(device_ip, time_window_hours=2)` | Recent events on device |
| `get_device_health(system_ip)` | Device metrics (CPU, memory, certs) |
| `get_control_connections(system_ip)` | Control plane state per device |
| `get_bfd_sessions(system_ip)` | BFD state for tunnels |
| `correlate_alarms(alarm_list)` | AI-driven correlation (root cause) |

### Decision Tree

```
START: Alarm Triage
  ├─→ Fetch alarms (severity >= trigger severity)
  ├─→ Group by event category (e.g., OMP_PEER_DOWN, BFD_FLAP, CONTROL_CONN_DOWN)
  │
  ├─→ FOR EACH alarm category:
  │     ├─→ Get device health (CPU, memory, uptime)
  │     ├─→ Get device events (recent changes)
  │     ├─→ Get control/data plane state
  │     │
  │     ├─→ Diagnosis:
  │     │     ├─→ Hardware issue? (CPU > 90%, memory > 95%, reboot?) → Escalate to hardware TAC
  │     │     ├─→ Config mismatch? (template change in last 1h) → Validate policy
  │     │     ├─→ Transient (ISP flap)? (single BFD flap, recovery in <1m) → Monitor
  │     │     ├─→ Network partition? (multiple devices down same ISP) → Contact ISP
  │     │     └─→ Unknown? → Escalate with context snapshot
  │
  └─→ Report & Recommend (ranked by severity)
```

### Sample LLM Prompt

```
Triage SD-WAN alarms. You have been paged on these issues:

Alarms to investigate:
- OMP Peer Down: hub-1 (10.1.1.1)
- BFD Flap: vedge-site50 <-> hub-2 (public color) [3 flaps in 5 minutes]
- Control Connection Down: vedge-site75 <-> hub-3

Steps:
1. Get full alarm list (severity >= Major)
2. For each alarm:
   a. Get device health (CPU, memory, uptime, cert status)
   b. Get device events from last 2 hours (config changes, reboots)
   c. Get control/data plane state (connections, BFD, OMP)
   d. Diagnose root cause (hardware, config, network, transient)
3. Correlate: Are these symptoms of same root cause? (e.g., hub-1 down → all OMP/control to hub-1 down)
4. Provide ranked recommendations (immediate vs. investigate)

Output format:
---
**Alarm Triage Report - [timestamp]**

**Summary**
- Total Alarms: N
- Root Cause Categories: [hardware, config, network, transient, unknown]
- Immediate Action Required: [YES/NO]

**Diagnosis by Device**
[For each affected device]

**Recommendations (Ranked by Priority)**
1. [Immediate action - do NOW]
2. [Short-term (within 1h)]
3. [Monitor - no action required]
---
```

### Example Output

```
**Alarm Triage Report - 2025-01-15 14:23 ET**

Summary
- Total Alarms: 3
- Root Cause: Single point of failure (hub-1 partial outage)
- Immediate Action: YES

---

**Diagnosis**

**ROOT CAUSE: hub-1 (10.1.1.1) - vSmart/Control Connection Issues**

Evidence:
- hub-1 system IP reachable (ping OK)
- hub-1 CPU: 92% (high)
- hub-1 Memory: 88% (elevated)
- Control connections from spokes to hub-1: DOWN (all 50 spokes)
- Control connections from spokes to hub-2: UP (all 50 spokes)
- OMP peers on hub-1: DOWN (no route propagation)
- Events: vSmartController process restart at 2025-01-15 14:15 ET (coincides with alarms)

Root Cause: Likely vSmartController process crash on hub-1 due to resource exhaustion (CPU/memory spike).
Recovery: Automatic (process restarting); monitor for recurring crashes.

**Secondary Effects (Expected to Resolve)**
- OMP Peer Down: hub-1 → Will establish once vSmart recovers
- Control Connection Down: vedge-site75 → Will establish once hub-1 recovers
- BFD Flap: vedge-site50 <-> hub-2 → Likely caused by control failover traffic spike; will stabilize

---

**Recommendations (Ranked)**

1. [IMMEDIATE] Monitor hub-1 recovery (should take 2-3 minutes). If not recovered in 5 minutes → Reboot hub-1.
   
2. [SHORT-TERM] Investigate why vSmartController crashed:
   - Check hub-1 system logs (/var/log/syslog)
   - Validate hub-1 resource limits (may need upgrade or load redistribution)
   - Check for recent config changes or policy attachments (could cause memory leak)
   
3. [MONITOR] BFD flaps on site-50 should stabilize once hub-1 OMP converges. If flapping persists → investigate site-50 ISP link.

4. [POST-INCIDENT] Schedule fabric resilience review:
   - Are we over-provisioning vSmarts?
   - Consider split-brain or vSmart redundancy improvements
   - Implement hub-1 auto-recovery (or PagerDuty escalation to hardware team)
```

---

## 3. BFD Flap Investigation

**Trigger**: On-demand (triggered by flap alarms or manual request)

**Persona**: sdwan-troubleshooter

**Duration**: 5-10 minutes

**Objective**: Diagnose BFD tunnel instability and recommend stabilization.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_bfd_sessions(system_ip)` | Current BFD state and flap count |
| `get_device_status(system_ip)` | Device CPU, memory, uptime |
| `get_interface_stats(system_ip)` | Interface errors, drops |
| `get_control_connections(system_ip)` | Control plane latency |
| `diagnose_bfd_flap(system_ip, remote_ip, color)` | AI-driven BFD diagnosis |

### Sample LLM Prompt

```
Investigate BFD flapping tunnel.

Input: vedge-site5 (10.0.50.1) <-> hub-1 (10.1.1.1) on "public" color
Observations: 5 state changes in 10 minutes; currently UP

Steps:
1. Get BFD session details (latency, loss, jitter, flap count, intervals)
2. Get device health (CPU, memory, interface stats)
3. Get control plane metrics (control connection latency)
4. Diagnose root cause:
   - Is this ISP circuit issue? (high loss, jitter, latency spike)
   - Is this vSD-WAN config issue? (low BFD multiplier, aggressive detect timer)
   - Is this device resource exhaustion? (CPU > 85%, memory > 90%)
   - Is this intermittent ISP congestion? (loss/latency periodic)
5. Provide remediations ranked by confidence

Output:
---
**BFD Flap Diagnosis**

Tunnel: vedge-site5 (10.0.50.1) <-> hub-1 (10.1.1.1) / public

Current State: [UP/DOWN]
Flaps in Last Hour: N
Last Flap: [timestamp]

BFD Configuration:
- Detect Time: X ms
- TX Interval: Y ms
- Multiplier: Z
- Assessment: [Aggressive/Moderate/Conservative]

Circuit Metrics:
- Latency: X ms (baseline: Y ms)
- Loss: X% (baseline: Y%)
- Jitter: X ms

Root Cause (Confidence %)
1. [Cause 1] - X%
2. [Cause 2] - Y%

Recommendations:
1. [Immediate action if critical]
2. [Tune BFD parameters]
3. [Monitor for recurrence]
---
```

### Example Output

```
**BFD Flap Diagnosis**

Tunnel: vedge-site5 (10.0.50.1) <-> hub-1 (10.1.1.1) / public

Current State: UP
Flaps in Last Hour: 5
Last Flap: 2025-01-15 14:05 ET (18 minutes ago)
Time Between Flaps: 2-3 minutes (unstable)

BFD Configuration:
- Detect Time: 3000 ms (3 sec)
- TX Interval: 1000 ms (1 sec)
- Multiplier: 3
- Assessment: CONSERVATIVE (good settings)

Circuit Metrics (vedge-site5 eth0 <-> ISP):
- Latency: 85 ms (baseline: 50 ms) ⚠️ +70% vs baseline
- Loss: 2.5% (baseline: 0.1%) ⚠️ HIGH
- Jitter: 45 ms (baseline: 5 ms) ⚠️ UNSTABLE

Device Metrics (vedge-site5):
- CPU: 35% (normal)
- Memory: 62% (normal)
- Interface Errors: 0
- Interface Drops: 15 (on public interface)

Control Plane (vedge-site5 -> hub-1):
- Latency: 90 ms (stable)
- Status: UP

Root Cause (Confidence %)
1. ISP Circuit Issue (Latency/Loss/Jitter spike) - 95%
2. Packet Loss on vedge-site5 Public Interface - 75%
3. BFD Detect Timeout (just barely recovering each time) - 40%

Assessment: This is a clear ISP circuit degradation. The BFD session is oscillating because loss/latency is borderline for the BFD timers. vedge-site5 is dropping 15 packets on public interface (possible ISP congestion).

Recommendations:
1. [IMMEDIATE] Contact ISP - Report increased latency (+70%), loss (+2500%), jitter (+900%) on site-5 circuit. Request status check and possible alternative routing.
2. [SHORT-TERM] Increase BFD Detect Time from 3000ms to 5000ms (site-5 only) to reduce false positives. Use centralized policy to override.
3. [MONITOR] Activate circuit health monitoring via ThousandEyes (if available). Escalate to ISP if issue persists >30 minutes.
4. [CONTINGENCY] Enable dual-carrier failover on site-5 (if backup ISP available) to shift public color traffic to backup.

Estimated ISP RCA Timeline: 15-30 minutes
Estimated Fix Timeline: Depends on ISP response (1-4 hours typical)
```

---

## 4. Control Plane Outage Troubleshooting

**Trigger**: Critical alert (all OMP peers down) or manual request

**Persona**: sdwan-troubleshooter

**Duration**: 10-20 minutes

**Objective**: Restore control plane connectivity; ensure fabric stability.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_devices()` | Device inventory, reachability |
| `get_control_plane_health()` | vSmart status, OMP state |
| `get_alarms()` | Correlation of related alarms |
| `get_events()` | Config changes, reboots |
| `get_device_health(system_ip)` | vSmart resource metrics |
| `analyze_control_plane()` | Root cause analysis |

### Decision Tree

```
START: Control Plane Down
  ├─→ Get all vSmarts (should be 3)
  │     ├─→ vSmarts UP > 0? YES → Partial outage (some control alive)
  │     └─→ vSmarts UP = 0? NO → TOTAL CONTROL PLANE DOWN (CRITICAL)
  │
  ├─→ Check vSmart reachability (ping, SSH)
  │     ├─→ Reachable? YES → vSmartController process crashed (restart)
  │     └─→ Unreachable? NO → Network connectivity issue (check vBond/mgmt path)
  │
  ├─→ Check vBond orchestrator
  │     ├─→ vBond reachable? YES → vBond OK
  │     └─→ vBond unreachable? NO → MAJOR issue (contact TAC)
  │
  ├─→ Check management connectivity
  │     ├─→ vManage reachable? YES → Mgmt OK
  │     └─→ vManage unreachable? NO → Network partition (firewall/routing issue)
  │
  └─→ Remediation:
        ├─→ Restart vSmartController process
        ├─→ Check vSmartController logs (memory leak? crash dumps?)
        ├─→ Verify OMP peer adjacency recovery (takes 30-60 sec)
        └─→ Monitor for stability (any recurrence?)
```

### Sample LLM Prompt

```
CRITICAL: Control Plane Outage Troubleshooting

Alert: All OMP peers down; 145 edge devices isolated
Severity: CRITICAL - Fabric data plane at risk

Steps:
1. Get control plane health (vSmart status, OMP peer count)
2. Get all devices (are vSmarts reachable?)
3. Get vSmart health (CPU, memory, uptime, recent reboots)
4. Get device events (any config changes? orchestration changes?)
5. Get alarms (what else is down?)
6. Diagnose: Is this vSmart process crash? Network partition? vBond issue?
7. Provide immediate remediation steps (restart, network check, etc.)

Output format:
---
**CRITICAL: Control Plane Outage Diagnosis**

Severity: [CRITICAL/MAJOR]
Affected Devices: [N edge devices isolated]
Expected Service Impact: No data traffic routing (overlay down)
Time to Resolution: [minutes estimate]

**Current State**
[vSmart status, OMP peer count, reachability]

**Root Cause (Confidence %)**
1. [Most likely]
2. [Alternative]

**Immediate Actions (Do NOW)**
1. [Action 1]
2. [Action 2]

**Monitoring**
- OMP peer recovery expected in: X-Y seconds
- Monitor for recurring crashes

---
```

### Example Output

```
**CRITICAL: Control Plane Outage Diagnosis**

Severity: CRITICAL
Affected Devices: 145 edge devices (all OMP peers down)
Expected Service Impact: Complete overlay down; data plane isolated
Time to Resolution: 2-5 minutes (if process crash)

---

**Current State**

vSmarts:
- hub-1 (10.1.1.1): REACHABLE (via mgmt), vSmartController process: DOWN ✗
- hub-2 (10.1.1.2): REACHABLE (via mgmt), vSmartController process: UP ✓
- hub-3 (10.1.1.3): REACHABLE (via mgmt), vSmartController process: UP ✓

OMP Peers: 0/145 established (all down)

vBond: REACHABLE, online

vManage: REACHABLE, online

Edge Devices:
- All 145 edges: Control connections DOWN
- Data plane: Partially intact (local VPN 0 still up; overlays down)

---

**Root Cause Analysis**

Primary (Confidence 98%): hub-1 vSmartController process crash
- hub-1 reachable (mgmt network OK)
- vSmartController process DOWN (confirmed via SSH)
- hub-2 and hub-3 vSmarts UP and online
- NO recent config changes or reboots (unlikely caused by operator)

Evidence:
- All OMP peers expected to hub-1: DOWN
- All OMP peers expected to hub-2: DOWN (because hub-1 out, mesh not healing)
- hub-1 system resources: CPU 15% (not overloaded), Memory 72% (normal)
- hub-1 logs show clean shutdown of vSmartController at 2025-01-15 14:02 ET

Secondary (Confidence 5%): vBond orchestration connectivity issue
- vBond status: Reachable
- vBond-to-vSmart connectivity: Confirmed
- (Low likelihood; vSmartController process is clearly crashed)

---

**IMMEDIATE ACTIONS (DO NOW)**

1. **RESTART vSmartController on hub-1** (Estimated impact: 2-3 minutes downtime)
   ```
   ssh admin@10.1.1.1
   request system reboot process vsmartctrl
   # Wait 30-60 seconds for process restart
   # Monitor OMP peer recovery
   ```

2. **Monitor OMP Convergence** (Next 60 seconds)
   - Expected: OMP peers will re-establish as hub-1 comes back
   - Recovery time: ~30 seconds per 50 devices
   - Success indicator: All OMP peer counts return to baseline

3. **Check for Recurring Crash** (Next 5 minutes)
   - If vSmartController crashes again after restart → escalate to TAC
   - Possible causes: Memory leak, config issue causing OOM, bug
   - Collect crash logs: `request system dump vsmartctrl`

---

**Post-Incident Investigation**

Once fabric is stable (within 10 minutes):

1. **Review hub-1 vSmartController Logs**
   - Check for OOM (Out of Memory) errors
   - Check for core dump files
   - Validate system resources (available memory, disk space)

2. **Validate Control Policy** (on hub-1)
   - Ensure no massive control policy changes in last 24h
   - Verify template/policy counts (control policy can be memory-intensive)

3. **Check Capacity**
   - 145 OMP peers: Is hub-1 at capacity?
   - Consider vSmart cluster rebalancing or upgrade

4. **Enable Monitoring**
   - Alert on vSmartController process down/restart
   - Alert on hub-1 CPU/memory anomalies
   - Set up automatic restart (if TAC approves)

---

**Expected Timeline**

- T+0min: Restart command issued
- T+1min: vSmartController comes online
- T+2min: OMP convergence (peers re-establish)
- T+3min: Fabric back to normal
- T+5-10min: Post-incident investigation

**If recovery does NOT occur by T+5min:**
- Escalate to Cisco TAC
- Provide: hub-1 config snapshot, logs, system dump
- Consider emergency failover (shift traffic to backup vSmarts)
```

---

## 5. AAR (App-Aware Routing) Policy Validation

**Trigger**: On-demand (before policy deployment or during app steering issues)

**Persona**: sdwan-architect

**Duration**: 5-10 minutes

**Objective**: Validate AAR policies are matching flows correctly and steering traffic appropriately.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_policies()` | List all AAR policies |
| `validate_policy_attachment()` | Check policy syntax and device compat |
| `get_approute_stats(time_window)` | Real traffic steering telemetry |
| `analyze_policy_effectiveness()` | Are policies achieving intent? |

### Sample Workflow

```
Workflow: Validate "Office365-AAR" Policy

1. Get policy definition (rules, match criteria, actions)
   - Does policy match Office365 traffic correctly?
   - Are match criteria sufficient (IP, port, DSCP)?
   
2. Check policy attachment (which devices?)
   - Are all sites attached?
   - Are there excluded sites (intentional)?
   
3. Get real AAR statistics (last 1 hour)
   - How many flows matched?
   - Traffic volume per application?
   - Which sites are steering to primary vs backup?
   
4. Validate outcomes
   - Expected: Office365 traffic on primary carrier (MPLS)
   - Actual: Does telemetry match?
   - If mismatch: Policy not matching? OR flows to uncovered addresses?
   
5. Recommendations
   - Policy is effective → No changes
   - Policy not matching → Update match criteria
   - Traffic not steering correctly → Check tunnel availability
```

---

## 6. Site Onboarding Checklist

**Trigger**: On-demand (new site deployment)

**Persona**: sdwan-operator

**Duration**: 30-45 minutes (depends on complexity)

**Objective**: Safely onboard new edge device to fabric with full validation.

### Checklist

```
SDWAN_AI Site Onboarding Checklist - [Site Name]

Phase 1: Pre-Staging (Before Device Deployment)
---
[ ] Zone allowlist: Is site-id in vBond allowlist? (request vBond update if not)
[ ] Certificate: Is site CSR signed? Root CA + device cert ready? (request from CA if not)
[ ] Device template: Is site-specific device template created? (create if not)
[ ] IP planning: LAN, management, overlay IPs conflict-free?
[ ] Connectivity: ISP order confirmed? Circuit bandwidth >= SLA?
[ ] Pre-flight snapshot: Capture current fabric state (baseline)

Phase 2: Device Provisioning
---
[ ] Device serial number: Verify HW serial (prevent duplicate enrollments)
[ ] Image version: Install correct OS version (match hub version)
[ ] Bootstrap: Load initial config (system IP, vBond IP, credentials)
[ ] Console verification: Device boots, reaches vBond, gets cert signed

Phase 3: Device Enrollment
---
[ ] Device appears in vManage? (may take 30-60 sec)
[ ] Certificate status: Valid or Pending CSR Signature?
[ ] Control connections: Any to hubs? (should be 1-3)
[ ] OMP peer state: Any OMP sessions? (should be 1-3)
[ ] System IP reachable: Ping device system-ip (from hub)

Phase 4: Template Attachment
---
[ ] Device template attachment: Dryrun first (view diff)
[ ] Diff review: All config changes as intended?
[ ] Device sync: Has device received config? (check last-sync timestamp)
[ ] Interface status: All interfaces up?
[ ] vManage connectivity: vManage data plane flowing?

Phase 5: Policy Attachment
---
[ ] Feature templates: All attached? (AAA, NTP, etc.)
[ ] Device-level policy: Attached? (QoS, NAT, firewall)
[ ] Centralized policy: Site included in policy scope?
[ ] AAR policy: Site in AAR policy? (if applicable)

Phase 6: Validation & Testing
---
[ ] Control plane health: All OMP peers up?
[ ] Data plane health: BFD sessions up?
[ ] Fabric connectivity: Can reach hub/other spokes? (traceroute)
[ ] Throughput test: Run iperf (basic validation)
[ ] AAR verification: Are app policies matching correctly?
[ ] Alarms: Any critical/major alarms from new site?

Phase 7: Post-Deployment
---
[ ] Capture post-deploy snapshot (compare to pre-deploy)
[ ] Monitor for 1 hour (watch for crashes/issues)
[ ] Document deployment (runbook update, change log)
[ ] Notify NOC (site now in production)

---

Issues Found During Onboarding:
[Document any deviations or concerns]

Approved by: _______________
Date: _______________
```

---

## 7. Pre-Change Validation Snapshot

**Trigger**: Before any configuration change (template attach, policy modification)

**Persona**: sdwan-operator / sdwan-architect

**Duration**: 5 minutes

**Objective**: Capture baseline state for comparison post-change (to validate change impact).

### Procedure

```
Pre-Change Validation Snapshot

Command: `create_change_snapshot(change_description)`

Captured Metrics:
- Device inventory (count, version dist, reachability)
- Control plane (OMP peers, control connections, vSmart status)
- Data plane (BFD sessions, tunnel counts, TLOC preferences)
- Policy attachment graph (which devices have which templates)
- Alarms (current baseline)
- Interface stats (bandwidth, errors, drops)

Output: Snapshot ID saved for post-change diff

Example:
  change_id = "snapshot-2025-01-15-14-30-template-attach-dc2"
  Snapshot saved with:
    - 147 devices, 145 reachable
    - 145 OMP peers up
    - 284 BFD sessions up
    - 2 critical alarms (pre-existing)
  
  [After change is deployed]
  
  Diff Report:
    - Devices reachability: 145 → 145 (no change)
    - OMP peers: 145 → 145 (converged in 45 sec)
    - BFD sessions: 284 → 284 (no loss)
    - Critical alarms: 2 → 2 (no new alarms)
    - CONCLUSION: Change successful, no negative impact
```

---

## 8. Post-Change Validation Diff

**Trigger**: 2-5 minutes after change deployment

**Persona**: sdwan-operator

**Duration**: 5 minutes

**Objective**: Compare post-change state to pre-change snapshot; validate no unintended impacts.

### Procedure

```
Post-Change Validation Diff

Command: `compare_snapshots(change_id, before_snapshot_id, after_snapshot_id)`

Comparison:
1. Device reachability: Any new unreachable devices?
2. Control plane convergence: Did OMP peers re-establish? (time to convergence)
3. Data plane stability: BFD flaps? New tunnel down?
4. Alarms: Any NEW critical/major alarms?
5. Traffic impact: Any significant dataplane errors/drops?

Decision Tree:
  ├─→ All metrics match? YES → ✓ CHANGE SUCCESSFUL
  ├─→ Minor changes (1-2 devices flapped, recovered)? YES → ✓ CHANGE SUCCESSFUL (with note)
  └─→ Significant impact? NO → ROLLBACK! Escalate to architect
  
Example Success Output:
  Pre:  145 devices reachable, 145 OMP peers, 0 critical alarms
  Post: 145 devices reachable, 145 OMP peers, 0 critical alarms
  Convergence time: 47 seconds
  Impact: NONE
  Status: ✓ CHANGE SUCCESSFUL
  
Example Failure Output:
  Pre:  145 devices reachable, 145 OMP peers, 0 critical alarms
  Post: 142 devices reachable, 142 OMP peers, 5 critical alarms
  New unreachable: vedge-site5, vedge-site8, vedge-site12
  New critical alarms: Control Conn Down (3 devices)
  Convergence: NOT CONVERGED (T+5min)
  Impact: SIGNIFICANT
  Status: ✗ CHANGE FAILED - RECOMMEND ROLLBACK
```

---

## 9. Quarterly Upgrade Planning

**Trigger**: Scheduled quarterly (e.g., first Monday of Q)

**Persona**: sdwan-architect

**Duration**: 1-2 hours

**Objective**: Plan safe OS upgrade strategy across fabric.

### Checklist

```
Quarterly SD-WAN Upgrade Planning

1. Current State Assessment
   [ ] Collect current OS versions across all devices (distribution)
   [ ] Identify EOL versions (must upgrade)
   [ ] Identify LTS vs feature releases (stability vs features)
   
2. Target Version Selection
   [ ] New release available? Review release notes (bug fixes, security)
   [ ] TAC recommendation? (latest stable for your scale)
   [ ] Compatibility check: Will upgrade break any policies or integrations?
   
3. Upgrade Path Planning
   [ ] Can we skip versions? (e.g., 19.x → 20.x acceptable?)
   [ ] Rolling upgrade vs. staged? (prefer rolling for uptime)
   [ ] Hub-first or edge-first? (upgrade hubs before edges for compatibility)
   
4. Risk Assessment
   [ ] Any known bugs in target version? (check TAC notes)
   [ ] Rollback plan: Can we downgrade if issues arise?
   [ ] Maintenance window: Schedule during low-traffic window
   
5. Staging & Testing
   [ ] Test upgrade in lab first (if possible)
   [ ] Document pre-upgrade snapshot (for rollback)
   [ ] Schedule SLA notification (brief maintenance window)
   
6. Execution Plan
   [ ] Phase 1: Upgrade hubs (monitor for 24h)
   [ ] Phase 2: Upgrade critical spokes (DC sites, data centers)
   [ ] Phase 3: Upgrade remaining spokes (staged, 20-30 devices per batch)
   
7. Post-Upgrade Validation
   [ ] All devices on new version?
   [ ] OMP convergence successful?
   [ ] Any new alarms?
   [ ] Performance degradation? (compare pre/post metrics)
```

---

## 10. Certificate Expiry Sweep (Monthly)

**Trigger**: Scheduled monthly (1st of month)

**Persona**: sdwan-architect / sdwan-operator

**Duration**: 10 minutes

**Objective**: Identify expiring certificates; plan renewals before outages.

### Tools Used

| Tool | Purpose |
|------|---------|
| `get_certificate_list()` | All installed certs |
| `get_device_certificates()` | Edge device certs |
| `get_cert_expiry_timeline()` | Days remaining per cert |

### Procedure

```
Certificate Expiry Sweep

Command: `audit_certificates(alert_days=[60, 30, 7, 1])`

Output:
---
**Certificate Expiry Audit - 2025-01-15**

Root CA Certificate:
- Name: SDWAN-Root-CA
- Expiry: 2032-06-10 (7.4 years remaining)
- Status: ✓ OK

vManage Certificate:
- Expiry: 2026-06-15 (16 months remaining)
- Status: ⚠️ ALERT 30-60 days out (plan renewal in Q2)

Device Certificates (Edge Count):
- Valid: 145/145 ✓
- Expiring in 60+ days: 0
- Expiring in 30-60 days: 0
- Expiring in 7-30 days: 2
  - vedge-site50: Expiry 2025-02-10 (26 days) ⚠️
  - vedge-site75: Expiry 2025-02-12 (28 days) ⚠️
- Expiring in <7 days: 0
- Expired: 0

---

Recommendations:
1. Renew vManage cert in next 30 days (schedule for Q2 maintenance)
2. Renew device certs (site-50, site-75) in next 2 weeks
   - Request CSR, submit to CA, deploy via vManage
   - Estimated deploy time: 10 minutes per device (zero downtime)
3. Add calendar reminders for recurring certs (annually for devices)
```

---

## 11. Capacity Planning Review (Monthly)

**Trigger**: Scheduled monthly (mid-month)

**Persona**: sdwan-architect

**Duration**: 30-45 minutes

**Objective**: Track growth trends; plan for upgrades before capacity exhaustion.

### Metrics to Review

```
Capacity Planning Review

1. Device Count Trend
   - Current: 147 devices
   - 3-month trend: +5 devices/month
   - Forecast (next 12 months): 207 devices
   - vSmart capacity: Rated for 500 devices → headroom: 58%
   - Assessment: ✓ OK (but monitor for Q3 expansion)

2. OMP Peer Count
   - Current: 145 OMP peers (+ 3 vSmarts = 148 total)
   - vSmart OMP scalability: ~500 per vSmart
   - Assessment: ✓ OK

3. Bandwidth Utilization (Per Site)
   - 95th percentile median: 45% of SLA
   - Sites approaching 80%: site-5 (78%), site-50 (76%)
   - Assessment: ⚠️ Monitor; plan bandwidth upgrade for sites 5, 50 in Q2

4. Control Plane Load
   - Policy count: 42 policies
   - Template count: 89 templates
   - Device groups: 15 groups
   - vSmartController memory: 78% of available
   - Assessment: ✓ OK, but be cautious with policy proliferation

5. vManage Database
   - Event count (last 30 days): 450K events
   - Alarm count (active): 12 alarms
   - Storage: 65% utilized
   - Backup frequency: Daily (7-day retention)
   - Assessment: ✓ OK (database not at risk)

6. Hub Redundancy
   - Current: 3 vSmarts (mesh topology)
   - Edge distribution: 50 edges per vSmart (avg)
   - Assessment: ✓ OK (balanced)

---

Recommendations:
1. Plan bandwidth upgrade for site-5, site-50 (Q2 ISP ticket)
2. Monitor vSmartController memory growth (if reaches 90% → plan vSmart cluster expansion)
3. Archive old events (older than 90 days) to free vManage storage
4. Q3 projection: Plan for 20-30 additional devices (may need vSmart scaling)
```

---

## References

- Cisco Live BRKENT-2215: AI Troubleshooting Agent
- Cisco Live BRKENT-3797: Policy Troubleshooting
- Cisco Live BRKSEC-2708: Security in SD-WAN
- [Cisco SD-WAN API Docs](https://developer.cisco.com/docs/sdwan/)
