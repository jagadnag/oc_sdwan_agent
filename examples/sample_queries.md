# SDWAN_AI Sample Query Examples

This document provides 20 example prompts that a CCIE SD-WAN architect might ask, organized by category. Each includes the user query, which agent should answer it, which MCP tools fire, and a sketch of expected output.

---

## INVENTORY & BASELINE QUERIES

### 1. Device Count and Version Distribution

**User Query**: "What's our current device count by version and region?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_device_inventory` → device list with version, site, status
- Network topology → site-to-region mapping (if region data available)

**Expected Output**:
```
DEVICE INVENTORY SUMMARY

Device Count by Version:
- v20.9.2: 125 devices (88%) ✓ Current
- v20.9.1: 15 devices (11%)
- v20.8.1: 2 devices (1%) ← Lagging

Device Count by Region:
- APAC: 42 devices (all v20.9.2)
- EMEA: 48 devices (45x v20.9.2, 3x v20.9.1)
- Americas: 52 devices (80x v20.9.2, 12x v20.9.1, 2x v20.8.1)

Total: 142 devices
Connectivity: 142 online, 0 offline, 0 degraded
Last heartbeat: All devices <15 min (healthy)
```

---

### 2. Hub Topology and Control Plane Health

**User Query**: "How many hubs do we have and what's the current OMP peer state?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_network_topology` → hub/spoke/mesh structure
- `get_omp_peers` → peer adjacency state, attributes

**Expected Output**:
```
CONTROL PLANE TOPOLOGY

Hub Controllers:
- SiteA-Hub (primary): 145 OMP peers established, 0 failed
- SiteB-Hub (secondary): 143 OMP peers established, 2 failed (spokes offline)

OMP Peer Status:
- Established: 288 (98%)
- Failed: 4 (2%) [devices: branch-02, branch-15, branch-31, branch-88]
- Flapping: 0

Control Plane Redundancy:
- Primary hub: Healthy
- Secondary hub: Healthy (ready for failover)
- WAN connectivity to hubs: Optimal

OMP Attribute Summary:
- Region distribution: 5 regions advertised via OMP
- Site-id coverage: 1-142 assigned
- Preference attributes: Weighted appropriately for failover
```

---

### 3. Link Health and Baseline Metrics

**User Query**: "What's the baseline latency and packet loss across our major color pairs?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_bfd_sessions` → BFD metrics (latency, loss) by color pair
- `get_interface_stats` → interface-level drops, errors, CRC

**Expected Output**:
```
LINK HEALTH BASELINE

Latency by Color Pair (p50/p95/p99):
- Private (MPLS): 35ms / 48ms / 62ms ✓ Excellent
- Public (Internet): 52ms / 78ms / 110ms ✓ Good
- Metro-Ethernet: 28ms / 35ms / 42ms ✓ Excellent

Packet Loss by Color:
- Private (MPLS): 0.1% ✓ Excellent
- Public (Internet): 0.5% ✓ Within SLA
- Metro-Ethernet: <0.05% ✓ Excellent

BFD Session Count: 284 sessions, 100% up
Flapping in last 24h: 0 flaps
```

---

## MONITORING & ALARMS

### 4. Critical Alarms in Last 24 Hours

**User Query**: "Show me all critical alarms from the last 24 hours."

**Agent**: sdwan-operator

**MCP Tools**:
- `list_alarms` (severity=critical, time_range=24h)

**Expected Output**:
```
CRITICAL ALARMS (Last 24h)

Count: 0 critical alarms ✓

Top Major Alarms (informational):
1. OMP-NEIGHBOR-DOWN: SiteA-Hub MPLS tunnel [2 occurrences, last 6h ago]
2. BFD-SESSION-DOWN: SiteB-Hub color-pair flap [resolved 4h ago]
3. Policy-Validation-Error: 3 devices [pending investigation]

Trend: Alarm frequency stable, no escalations
```

---

### 5. Trending Alarm Patterns

**User Query**: "Are there any alarm trends or patterns emerging? Any repeated issues?"

**Agent**: sdwan-troubleshooter (if investigating) or sdwan-operator (if routine)

**MCP Tools**:
- `list_alarms` (time_range=7d, group_by=type)

**Expected Output**:
```
ALARM TREND ANALYSIS (Last 7 days)

Recurring Alarms:
1. OMP-NEIGHBOR-DOWN (SiteA-Hub MPLS): 3 occurrences
   - Pattern: Occurs every 40-50 hours, lasts ~5 minutes
   - Root cause hypothesis: Intermittent WAN jitter causing BFD timeout
   - Recommendation: Investigate link quality with ISP; tune BFD hold multiplier

2. Certificate-Expiring-Warning (multiple devices): 1 new alert per day
   - Pattern: Escalating frequency as expiration dates approach
   - Root cause: No proactive renewal workflow in place
   - Recommendation: Schedule cert sweep and renewal window

3. Disk-Low (vManage secondary): 2 occurrences
   - Pattern: Increasing trend (will reach critical in 10 days)
   - Root cause: Log growth exceeding rotation policy
   - Recommendation: Run cleanup job; review log retention settings

Recommendation: Escalate OMP flapping to troubleshooter for deeper RCA
```

---

## TOPOLOGY & DESIGN

### 6. New Site Onboarding Design

**User Query**: "We're adding 30 new branch sites to APAC. What topology design should I use?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_device_inventory` → current hub/spoke structure
- `get_network_topology` → existing APAC layout
- `get_bfd_sessions` → hub CPU/BFD session load

**Expected Output**:
```
APAC SITE ONBOARDING DESIGN

Current APAC Topology:
- 42 existing sites
- 1 regional hub (Singapore)
- 30 spoke sites connected via MPLS + Internet colors

Recommended Design for 30 New Sites:
1. Single Regional Hub (Singapore) [simplest config]
   - All 30 new sites → Singapore hub (spoke-only)
   - Hub CPU load: Will reach 65% (headroom remaining)
   - BFD sessions: +60 new sessions (285 total, <50% of typical max)
   - New color pairs per site: 2 (MPLS + Internet)

Alternative Design A: Metro Mesh [best latency]
   - Hub: Singapore
   - Metro mesh (10 high-traffic sites): partial mesh topology
   - Remaining 20: spoke-only
   - Benefit: Local failover; reduced hub transit
   - Cost: More complex policy, higher ops overhead

Alternative Design B: Multi-Hub [highest scale]
   - Regional hubs: Singapore (primary) + Sydney (secondary)
   - Distribute 30 new sites: 15 to Singapore, 15 to Sydney
   - Benefit: Load-balanced, best scalability
   - Cost: 2x vSmart controller, multi-hub OMP policies

Recommendation: Design A (Metro Mesh) balances complexity and performance.
- Provides local failover for high-traffic sites
- Keeps hub CPU within comfortable range
- Manageable policy complexity

Next Steps:
1. Confirm topology choice and budget constraints
2. List 30 sites with traffic profiles (to identify metro mesh candidates)
3. Create device templates for spoke-only and mesh-capable devices
4. Prepare Sastre dry-run for canary sites (3-5 pilot locations)
```

---

### 7. Site Redundancy Analysis

**User Query**: "Which sites have single-link WAN connections? Are they at risk?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_network_topology` → TLOC availability per site
- `get_interface_stats` → WAN interface count per device

**Expected Output**:
```
SITE REDUNDANCY ANALYSIS

Single-Link Sites (at risk):
- SiteC (branch): 1x MPLS only
  Risk: If MPLS link fails, site goes offline
  Recommendation: Add Internet color pair for backup failover

- SiteE (branch): 1x Internet only
  Risk: If Internet link fails, site goes offline
  Recommendation: Add MPLS color pair for backup failover

- SiteM (branch): 1x Metro-Ethernet only
  Risk: Single carrier, no backup
  Recommendation: Add Internet secondary for resilience

Total Sites with Single Link: 12/142 (8%)
Recommended Action: Plan 3-month rollout to add secondary color to all 12 sites

Multi-Link Sites (healthy):
- 130 sites with 2+ colors (91%) ✓
```

---

## POLICY & SECURITY

### 8. Current Policy Status and Coverage

**User Query**: "What policies are currently active? How many devices are covered?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_policy_status` → active policies, version, device bindings
- `get_template_status` → policy template attachment

**Expected Output**:
```
POLICY STATUS SUMMARY

Active Policies:

1. Centralized Control Policy (v1.2)
   - Status: Active on 142 devices (100%)
   - Last updated: 2 weeks ago
   - Rules: 18 (traffic engineering, tunnel steering, load balancing)
   - Validation: ✓ All devices passing validation

2. Centralized Data Policy (v3.5)
   - Status: Active on 142 devices (100%)
   - Last updated: 4 days ago
   - Rules: 85 (app classification, flow-based routing, encryption enforcement)
   - Validation: ✓ All devices passing validation

3. App-Aware Routing (v2.1)
   - Status: Active on 110 devices (77% coverage)
   - Last updated: 1 month ago
   - SaaS apps: 45 rules (Office 365, Salesforce, Slack, etc.)
   - Video apps: 12 rules (Zoom, Teams, WebEx)
   - Data apps: 28 rules (DB replication, backup, sync)
   - Coverage gaps: 32 devices pending upgrade to v20.9.2

Policy Validation Health:
- All validation passed: 142 devices
- Partial validation: 0 devices
- Failed: 0 devices

Recommendation: Plan upgrade for 32 devices to enable AAR coverage on remaining sites
```

---

### 9. Security Policy Stack Review

**User Query**: "What's our current security posture? Do we have ZBFW, URL filtering, and Snort enabled?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_policy_status` → security-related rules (ZBFW, URL filter)
- `get_device_inventory` → Snort module deployment

**Expected Output**:
```
SECURITY STACK ASSESSMENT

Zone-Based Firewall (ZBFW):
- Status: Enabled on 142 devices (100%)
- Zones configured: 6 (Internet, MPLS, Metro, LTE, Management, OOB)
- Default deny rules: Active (deny-all, then whitelist)
- Threat prevention: ✓ Active

URL Filtering:
- Status: Enabled on 142 devices (100%)
- Categories enforced: 15 (malware, phishing, adult, gambling, etc.)
- Block policy: Redirect to security gateway
- Block rate: 0.3% of traffic (within normal range)

Snort IPS/IDS (Intrusion Prevention):
- Status: Enabled on 78 devices (55%) [hubs + high-risk sites]
- CPU impact: <2% on hub devices
- Coverage gap: 64 branch devices (opt-in model)
- Recommendation: Consider enabling on 20 additional high-traffic branches

Encryption Enforcement:
- Status: IPsec tunnel encryption required on all overlay routes ✓
- AES-256: Used on 90% of tunnels ✓
- Legacy AES-128: Used on 10% (older devices pending upgrade)

Overall Security Posture: GOOD (85/100)
Gaps to Address:
1. Expand Snort IPS/IDS coverage to 20 additional branch sites
2. Complete AES-256 encryption migration on legacy devices
3. Add URL category logging for compliance reporting

Timeline: Q2 2026 (2-month plan)
```

---

## CERTIFICATE MANAGEMENT

### 10. Certificate Expiration Timeline

**User Query**: "What's our certificate expiration forecast? Do any expire in the next 30 days?"

**Agent**: sdwan-operator

**MCP Tools**:
- `get_expiring_certificates` (window=30d, 60d, 90d)

**Expected Output**:
```
CERTIFICATE EXPIRATION FORECAST

CRITICAL (< 7 days):
- None ✓

WARNING (7-14 days):
- SiteA-Hub-01: Expires 2026-04-19 | Action: Start renewal within 24 hours

ALERT (14-30 days):
- SiteB-Hub-01: Expires 2026-04-25 | Action: Schedule renewal for week of Apr 15
- SiteC-Branch-02: Expires 2026-05-02 | Action: Schedule renewal for week of Apr 20

UPCOMING (30-60 days):
- [12 additional devices with renewal dates]

Root CA Certificate:
- Status: Valid
- Expires: 2027-12-31 (18 months away) ✓
- Renewal plan: Begin planning for 2027 renewal in Q4 2026

Renewal Workflow Timeline:
1. SiteA-Hub-01: CSR (2h) + Signing (1h) + Install (1h) = 4h total
   Maintenance window: Tuesday 2am-6am UTC
   
2. SiteB-Hub-01: Same day, rolling window (sequential to avoid device disconnects)

3. SiteC-Branch-02: Following week (less critical)

Recommendation: Implement automated renewal workflow to reduce manual effort
```

---

## TROUBLESHOOTING & INCIDENTS

### 11. BFD Flapping Investigation

**User Query**: "BFD is flapping every 90 seconds between SiteA and SiteB. What's happening?"

**Agent**: sdwan-troubleshooter

**MCP Tools**:
- `get_bfd_sessions` → BFD metrics, flap count, state transitions
- `list_alarms` → correlated BFD and OMP alarms
- `get_interface_stats` → packet loss, latency, CRC errors on WAN link

**Expected Output**:
```
BFD FLAP INVESTIGATION

Issue Summary:
- Symptom: BFD session between SiteA-Hub (MPLS color) flapping every 90 seconds
- Duration: Started 2 hours ago
- Scope: 1 site pair (SiteA ↔ Hub)
- Severity: High (video users impacted)

Telemetry:
- BFD hold multiplier: 3 (typical)
- BFD probe interval: 300ms
- Flap pattern: Up ~30 sec → Down ~5 sec → Up ~30 sec (repeats)
- SiteA MPLS WAN interface: Packet loss 2.3%, latency +10ms from baseline

Root Cause Analysis:

Hypothesis A (likelihood: High)
- Cause: Physical WAN link degradation causing packet loss
- Evidence: 2.3% loss detected on SiteA MPLS interface; 10ms latency increase
- Test: Correlate flaps with carrier-level issues; request ISP line quality check
- Fix: Coordinate with ISP for line quality improvement; increase BFD hold multiplier to tolerate jitter

Hypothesis B (likelihood: Medium)
- Cause: BFD timer mismatch between SiteA and Hub devices
- Evidence: Regular 90-second cycle suggests timeout-related (hold=3 × interval 300ms = 900ms)
- Test: Compare BFD config on both devices
- Fix: Align hold multiplier or interval on both sides

Hypothesis C (likelihood: Low)
- Cause: Recent policy/template change introduced BFD config mismatch
- Evidence: Check audit log for template pushes in last 2 hours
- Test: Compare pre/post template BFD config
- Fix: Rollback template or push corrected config

Recommended Actions:
Immediate: Increase BFD hold multiplier from 3 to 5 (reduce sensitivity to jitter)
Near-term: Investigate WAN link quality with ISP; collect 24-hour carrier stats
Follow-up: Add monitoring alert for BFD version skew across topology

Rollback: Previous template config available; recovery time <5 minutes
```

---

### 12. Control Connection Down — Multiple Sites

**User Query**: "5 devices in APAC went offline. OMP neighbors are down. Is this a regional outage?"

**Agent**: sdwan-troubleshooter

**MCP Tools**:
- `get_omp_peers` → OMP peer state for affected devices
- `list_alarms` → regional alarm correlation
- `get_device_inventory` → connectivity status by region

**Expected Output**:
```
REGIONAL OUTAGE INVESTIGATION

Issue Summary:
- Symptom: 5 devices in APAC lost OMP connectivity (neighbors down)
- Devices: SiteA, SiteB, SiteC, SiteE, SiteG (all in Singapore region)
- Duration: 15 minutes
- Severity: Critical (5 sites offline, ~200 users impacted)

Scope Analysis:
- APAC affected: 5/42 devices (12%)
- EMEA affected: 0/48 devices ✓
- Americas affected: 0/52 devices ✓
- Regional issue: YES (Singapore region only)

Telemetry:
- OMP neighbors on affected devices: All failed (no adjacency to hubs)
- Hub status: Primary hub (SiteA-Hub) and secondary hub (SiteB-Hub) both up
- WAN connectivity: Devices last heartbeat 15 minutes ago
- Alarms: OMP-NEIGHBOR-DOWN (5 devices), vManage-UNREACHABLE (0 devices)

Root Cause Analysis:

Hypothesis A (likelihood: High)
- Cause: WAN link to Singapore hub region down or severely congested
- Evidence: All 5 devices in Singapore lost OMP at same time (regional correlation)
- Test: Check if Singapore hub WAN interfaces are up; ping devices from hub
- Fix: Investigate ISP for regional outage; failover to secondary hub if available

Hypothesis B (likelihood: Medium)
- Cause: Hub controller failure or maintenance window
- Evidence: Hub heartbeat status check (if available)
- Test: Verify hub availability and process status
- Fix: Failover to secondary hub (automatic if redundancy configured)

Hypothesis C (likelihood: Low)
- Cause: DNS resolution failure for hub hostname across region
- Evidence: Devices can't reach hub hostname
- Test: SSH to affected device and check DNS/IP resolution
- Fix: Update device DNS servers or switch to IP-based hub addresses

Recommended Actions:
Immediate: 
1. Verify Singapore hub is up and healthy
2. Check WAN carrier status (call ISP NOC if needed)
3. If failover available, verify devices failover to secondary hub
4. Escalate to war room if outage persists >30 minutes

Near-term:
1. Investigate hub WAN connectivity
2. Check for recent config changes (audit log)
3. Collect device logs from affected sites

Rollback: N/A (investigate first; no config change needed unless hub recovery required)

ETA to recovery: Depends on ISP response (if link down) or hub failover (if controller issue)
```

---

### 13. App Performance Degradation

**User Query**: "Users at SiteA report video calls are choppy. Where's the bottleneck?"

**Agent**: sdwan-troubleshooter

**MCP Tools**:
- `get_app_aware_routing_stats` → AAR policy matching, flow steering
- `get_interface_stats` → WAN link utilization, packet loss, latency
- `get_bfd_sessions` → overlay tunnel health

**Expected Output**:
```
APP PERFORMANCE INVESTIGATION

Issue Summary:
- Symptom: Users at SiteA report Zoom video calls are choppy/laggy
- Duration: Last 30 minutes
- Scope: SiteA branch (25 users affected)
- Severity: High (business impact, customer-facing)

Telemetry:
- SiteA WAN links: MPLS 85% utilized, Internet 35% utilized
- Latency: MPLS 65ms (baseline 35ms), Internet 52ms (baseline 52ms) ✓
- Packet loss: MPLS 1.2% (SLA 0.5%), Internet 0.3% ✓
- BFD state: Both colors up, but MPLS showing increased jitter

App Traffic Routing:
- Zoom traffic (video): AAR policy steering to MPLS color
- Flow count on MPLS: 45 flows (high)
- Flow count on Internet: 5 flows (backup underutilized)

Root Cause Analysis:

Hypothesis A (likelihood: High)
- Cause: MPLS link congestion + loss causing video quality degradation
- Evidence: MPLS at 85% utilization, 1.2% loss (above SLA)
- Test: Check if other high-priority traffic shares MPLS link
- Fix: Shift video traffic to Internet color pair via AAR policy adjustment

Hypothesis B (likelihood: Medium)
- Cause: AAR policy not prioritizing Zoom correctly
- Evidence: QoS policy may be deprioritizing video traffic
- Test: Verify DSCP markings and QoS rules for Zoom (port 443)
- Fix: Update QoS policy to prioritize RTP streams

Hypothesis C (likelihood: Low)
- Cause: Hub processing delay (hub CPU overloaded)
- Evidence: Check hub CPU during SiteA video calls
- Test: SSH to hub and check CPU/memory during peak usage
- Fix: If CPU high, review hub policies; consider load balancing

Recommended Actions:
Immediate:
1. Enable traffic steering from MPLS to Internet for video traffic (temporary fix)
2. Monitor loss rate and latency — should improve within 5 minutes
3. Verify users report improvement

Near-term:
1. Investigate MPLS link congestion (what app is consuming bandwidth?)
2. Adjust AAR policy to balance video traffic across both colors
3. Review QoS policy to ensure video has priority

Follow-up:
1. Check if MPLS link capacity is undersized for site growth
2. Consider adding secondary Internet link if sustained high utilization

Rollback: Revert AAR policy change (restore original Zoom routing)
Expected recovery: 5-10 minutes after fix applied
```

---

## UPGRADE & CHANGE MANAGEMENT

### 14. Pre-Upgrade Health Check

**User Query**: "We want to upgrade to v20.10.1. What should we check before starting?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_software_versions` → current version distribution
- `get_device_inventory` → capacity headroom (CPU, memory, disk)
- `get_expiring_certificates` → certificate validity
- `list_backups` → recent backup availability

**Expected Output**:
```
PRE-UPGRADE HEALTH CHECK FOR v20.10.1

Compatibility Assessment:

1. Device Version Readiness
   - Current: v20.9.2 (125 devices), v20.9.1 (15 devices), v20.8.1 (2 devices)
   - Target path: v20.9.2 → v20.10.1 (single hop) ✓ Recommended
   - Peer compatibility: v20.10.1 devices ↔ v20.9.2 vSmart ✓ Supported
   - Migration path: Devices first, then vSmart, then vManage (recommended sequence)

2. Capacity Headroom
   - CPU p95: 45% (headroom 55%) ✓ Excellent
   - Memory p95: 62% (headroom 38%) ✓ Good
   - Disk usage: 71% avg (headroom 29%) ✓ Acceptable
   - Recommendation: No hardware upgrades needed before upgrade

3. Certificate Validity
   - All device certs valid >90 days ✓
   - Root CA valid >365 days ✓
   - Pre-condition met: Proceed with upgrade

4. Backup Status
   - Last backup: 2 hours ago ✓
   - Backup size: 125MB (templates + policies + device configs)
   - Restore tested: 3 weeks ago ✓
   - Pre-condition met: Rollback available

5. Alarm Baseline
   - Critical alarms: 0 ✓
   - Major alarms: 2 (non-blocking, historical)
   - Pre-condition met: Network stable for upgrade

6. Recent Config Changes
   - Last template change: 4 days ago ✓
   - Last policy change: 2 days ago ✓
   - Recommendation: Wait 3-5 days post-change to verify stability (to isolate upgrade issues from config issues)

ASSESSMENT: ✓ Ready to proceed with upgrade

Recommended Next Steps:
1. Plan upgrade timeline: 4-8 weeks (phased approach)
2. Design phased rollout: test group → canary → production
3. Create pre-upgrade snapshot for rollback
4. Schedule Phase 1 execution for [date]
5. Notify stakeholders of upgrade window and expected impact
```

---

### 15. Staged Template Deployment

**User Query**: "We have a new security policy template. What's the safest way to roll it out to all 142 devices?"

**Agent**: sdwan-operator

**MCP Tools**:
- `get_template_status` → current template versions, device bindings
- `create_backup` → Sastre snapshot before change
- `attach_template` (with --dry-run) → preview diffs

**Expected Output**:
```
STAGED TEMPLATE DEPLOYMENT PLAN

Current State:
- Active security template: v3.5 (deployed to 142 devices)
- New template: v3.6 (8 new URL filter rules, 2 removed)
- Expected CPU impact: <1% (low risk)

Deployment Strategy: Phased Rollout with Approval Gates

Phase 0 (Preparation)
✓ Sastre backup created: 2026-04-13_10:15 (snapshot v3.5)
✓ Dry-run diffs shown: v3.5 → v3.6
✓ Device count affected: 142 (all sites)
✓ Approval checkpoint: Ready for Phase 1? (Confirm 'yes')

Phase 1 (Canary - 3 test devices)
Devices: SiteA (APAC), SiteB (EMEA), SiteC (Americas)
Expected timeline: 10 minutes
Actions: Attach v3.6 to canary group; monitor for 10 min
Validation: Device sync ✓, new alarms ✓, policy rules active ✓
Approval checkpoint: Phase 1 success. Ready for Phase 2? (Confirm 'yes' to proceed to APAC)

Phase 2A (APAC Regional - 42 devices)
Devices: All APAC branch sites (minus canary)
Expected timeline: 30 minutes (3 sites at a time, 10-min wait between batches)
Actions: Attach v3.6 to APAC region in batches
Validation: 15-min monitoring after batch, check for errors
Approval checkpoint: APAC complete. Ready for EMEA? (Confirm 'yes')

Phase 2B (EMEA Regional - 48 devices)
Expected timeline: 30 minutes
Approval checkpoint: EMEA complete. Ready for Americas? (Confirm 'yes')

Phase 2C (Americas Regional - 52 devices)
Expected timeline: 30 minutes
Approval checkpoint: Deployment complete

Phase 3 (Post-Deployment Validation)
✓ All devices synced: 142/142 (100%)
✓ New alarms: None
✓ Policy validation: Passed on all devices
✓ Before/after metrics: No performance degradation
✓ Change ticket updated with audit trail and Sastre backup reference

Total deployment time: 2-3 hours (with monitoring/validation)
Rollback available: Sastre snapshot v3.5 [2026-04-13_10:15]
Rollback time: 15 minutes (restore snapshot)
```

---

## CAPACITY PLANNING

### 16. CPU and Capacity Trending

**User Query**: "What's our hub CPU trending? When will we hit limits?"

**Agent**: sdwan-operator or sdwan-architect

**MCP Tools**:
- `get_device_inventory` (include stats) → CPU utilization p95 by device
- Query stats over 30 days → trend calculation

**Expected Output**:
```
CAPACITY TREND ANALYSIS

Hub CPU Utilization (Last 30 Days):

Primary Hub (SiteA-Hub):
- Baseline (30 days ago): 35%
- Current (today): 45%
- Trend: +0.33% per day (increasing)
- p95 peak: 52%
- Max capacity: 90% (conservative limit)

Forecast (at current growth):
- 30 days: 55% (still healthy)
- 60 days: 65% (approaching concern threshold)
- 90 days: 75% (plan upgrade window now)

Root cause of growth:
- Device count increase: 142 devices (stable, no new sites)
- OMP peer scaling: 288 peers (increasing slightly as sites stabilize)
- Policy complexity: Rules increasing (3 new policy rules per month trend)

Secondary Hub (SiteB-Hub):
- Baseline: 30%
- Current: 40%
- Trend: +0.33% per day
- Forecast: Tracks primary hub

Capacity Planning Recommendation:
1. Short-term (0-60 days): No action needed, continue monitoring
2. Medium-term (60-90 days): Plan hardware upgrade or hub expansion
3. Long-term (90+ days): Implement multi-hub architecture or hub replacement

Upgrade options:
A) Increase primary hub capacity (vSmart appliance upgrade) — 2-week procurement, 4-hour upgrade window
B) Add secondary hub (new vSmart appliance) — 4-week procurement, 2-hour deployment, requires policy redesign
C) Reduce device scale to primary hub (redistribute to new regional hub) — 6-week planning, 8-week rollout

Recommended choice: Option B (secondary hub) for best long-term scalability
Timeline: Begin procurement in 60 days; deploy in 90 days; redirect new sites to secondary hub in 120 days

Next steps: Budget approval, procurement initiation
```

---

## MONITORING & ANALYTICS

### 17. Device Link Redundancy Check

**User Query**: "How many devices have single-link WAN? Which are critical?"

**Agent**: sdwan-architect

**MCP Tools**:
- `get_network_topology` → TLOC availability per device
- `get_device_inventory` → device criticality (if available via custom data)

**Expected Output**:
```
SITE REDUNDANCY ANALYSIS

Single-Link WAN Sites (No Color Redundancy):
- 12 devices out of 142 (8%)

Critical Sites with Single Link (require immediate attention):
1. SiteC (Branch headquarters, 200 users)
   - Current: MPLS only
   - Risk: Site goes offline if MPLS link fails
   - Recommended fix: Add Internet color pair for failover
   - Priority: HIGH

2. SiteE (Data center, mission-critical app)
   - Current: Internet only
   - Risk: Data center connectivity single point of failure
   - Recommended fix: Add MPLS + Metro-Ethernet for dual redundancy
   - Priority: HIGH

3. SiteM (Regional hub, 50 branch spoke connections)
   - Current: Metro-Ethernet only
   - Risk: All spoke sites lose hub connectivity if link fails
   - Recommended fix: Add MPLS + Internet for triple redundancy
   - Priority: CRITICAL

Non-critical Sites with Single Link (lower priority):
- SiteF, SiteG, SiteH, SiteJ, SiteK, SiteL, SiteN, SiteO (low-usage branch)
  - Risk: Branch users experience outage if link fails
  - Recommended fix: Add secondary color (phased over 6 months)
  - Priority: MEDIUM

Multi-Link Sites (Healthy):
- 130 devices with 2+ colors (91%) ✓

Remediation Plan:
Phase 1 (Urgent, 2-week window): Add redundancy to critical sites (SiteC, SiteE, SiteM)
- SiteC: +Internet color = 4h deployment
- SiteE: +MPLS, +Metro-Ethernet = 6h deployment
- SiteM: +MPLS, +Internet = 6h deployment
- Total effort: 16 hours (1 work week)

Phase 2 (Standard, 6-month rollout): Add redundancy to non-critical sites (9 devices)
- 2-3 devices per month
- Stagger with other change windows

Cost estimate: Hardware (new WAN circuits), labor, testing
Timeline: Complete critical in Q2 2026; non-critical by Q4 2026
```

---

## POLICY COMPLIANCE

### 18. Policy Rule Compliance Audit

**User Query**: "Which devices don't have the latest security policy applied?"

**Agent**: sdwan-operator or sdwan-architect

**MCP Tools**:
- `get_policy_status` → policy version per device, validation status

**Expected Output**:
```
POLICY COMPLIANCE AUDIT

Security Policy Compliance (v3.6):

Compliant (100%):
- 142 devices running policy v3.6 ✓

Non-compliant (0%):
- None

Policy Validation Status:
- Passed: 142 devices (100%) ✓
- Partial: 0 devices
- Failed: 0 devices

Rule Enforcement Status:
- All 85 security rules active on 142 devices ✓
- No rule conflicts detected ✓
- No policy drops or errors ✓

Compliance Score: 100% ✓

Related Policies:

Data Policy (v3.5):
- Compliant: 142/142 (100%) ✓

App-Aware Routing (v2.1):
- Compliant: 110/142 (77%) [32 devices pending v20.9.2 upgrade]
- Gap: SaaS apps not optimized on legacy v20.8.x devices
- Plan: Upgrade 32 devices to enable AAR coverage
- Timeline: 4-week phased upgrade

Localized Policy (per-device QoS):
- Compliant: 128/142 (90%)
- Non-compliant (old policy): 14 devices (older branch devices)
- Plan: Push localized policy v2.0 to 14 non-compliant devices
- Timeline: 1-week deployment (low risk)

Overall Compliance: 96% (accounting for AAR gaps on legacy devices)
Recommendation: Complete AAR upgrade by end of Q2 2026 for 100% compliance
```

---

## BACKUP & DISASTER RECOVERY

### 19. Backup Health & Recovery Capability

**User Query**: "Are our Sastre backups healthy? Can we recover if we need to?"

**Agent**: sdwan-operator

**MCP Tools**:
- `list_backups` → backup metadata (timestamp, size, components)
- Verify backup restore capability (test restore on lab device, if possible)

**Expected Output**:
```
BACKUP HEALTH & RECOVERY ASSESSMENT

Backup Inventory:

Daily Backups (keep 14 most recent):
- 2026-04-13 10:15 UTC: 125MB (templates + policies + devices) ✓
- 2026-04-12 10:15 UTC: 124MB ✓
- 2026-04-11 10:15 UTC: 124MB ✓
- [11 more daily backups]
- Total backup storage: 1.7GB

Weekly Backups (keep 4 most recent):
- 2026-04-12 (Saturday): 124MB ✓
- 2026-04-05 (Saturday): 123MB ✓
- 2026-03-29 (Saturday): 122MB ✓
- 2026-03-22 (Saturday): 121MB ✓
- Total: 490MB

Monthly Backups (keep 1 most recent):
- 2026-04-01: 123MB ✓

Total backup space: 2.2GB
Backup growth rate: +1MB per month (stable)
Backup retention: 6 weeks of daily + 4 weeks of weekly + 1 month

Backup Components Verified:
✓ Templates: 18 versions, latest v3.6
✓ Policies: 3 active policies (control, data, AAR)
✓ Device configs: 142 devices, all versions represented
✓ System settings: vManage configurations

Backup Recovery Capability:

Last restore test: 3 weeks ago [date]
Result: ✓ Successful restore of v3.4 snapshot to test lab (validation time: 15 min)
Recovery time estimate: 15 minutes (to restore snapshot to production)

Disaster Recovery Readiness:
- Full network restore available from today's backup (2026-04-13 10:15)
- RTO (Recovery Time Objective): 30 minutes (backup restore + device sync)
- RPO (Recovery Point Objective): 24 hours (daily backup)
- Recommendation: Consider hourly backups if RPO is unacceptable

Backup Automation Status:
- Daily backup: Scheduled 10:15 UTC ✓ Running
- Backup rotation: Automated (keep 14 daily, 4 weekly, 1 monthly) ✓
- Backup validation: Manual test every 3 weeks (ongoing)

Recommendations:
1. Schedule next restore test for 2026-04-27 (validate latest backup)
2. Consider increasing backup frequency to 12h if RPO needs improvement
3. Archive monthly backup to offsite storage (for long-term disaster recovery)

Conclusion: Backup health is GOOD. Recovery capability verified and ready.
```

---

## NETWORK CHANGES

### 20. Recent Change Audit Trail

**User Query**: "What configuration changes were made in the last 7 days? Who made them?"

**Agent**: sdwan-architect or sdwan-operator

**MCP Tools**:
- Query vManage audit log (timestamp, user, action, object, before/after)

**Expected Output**:
```
CONFIGURATION CHANGE AUDIT (Last 7 Days)

Summary:
- Total changes: 6
- Policy activations: 1
- Template attachments: 2
- Manual config edits: 1
- System setting changes: 2

Detailed Change Log:

1. Template Attachment: Security Policy v3.5 → v3.6
   - Timestamp: 2026-04-13 10:15 UTC
   - User: admin@company.com
   - Object: 142 devices (all branch sites)
   - Action: Attach new policy template
   - Impact: 8 new URL filter rules, 2 removed
   - Status: ✓ Successfully applied

2. Policy Activation: Data Policy v3.5 (refresh rules)
   - Timestamp: 2026-04-12 14:30 UTC
   - User: operations@company.com
   - Object: 142 devices
   - Action: Reactivate existing policy (rule order change)
   - Impact: No rule changes, reordering for efficiency
   - Status: ✓ Applied

3. Manual Config Edit: vManage DNS settings
   - Timestamp: 2026-04-11 09:45 UTC
   - User: admin@company.com
   - Object: vManage primary server
   - Action: Update secondary DNS from 8.8.4.4 to 9.9.9.9
   - Impact: DNS resolution failover improved
   - Status: ✓ Applied

4. Template Attachment: Device Config v2.1 (NTP update)
   - Timestamp: 2026-04-10 16:20 UTC
   - User: network-eng@company.com
   - Object: SiteA-Hub, SiteB-Hub (controllers only)
   - Action: Attach NTP server config update
   - Impact: Time sync improved (critical for certificate operations)
   - Status: ✓ Applied

5. System Setting Change: Backup rotation policy
   - Timestamp: 2026-04-08 11:00 UTC
   - User: admin@company.com
   - Object: vManage backup settings
   - Action: Increase daily backup retention from 7 days to 14 days
   - Impact: Longer rollback window available
   - Status: ✓ Applied

6. System Setting Change: Alarm threshold (Certificate Expiry)
   - Timestamp: 2026-04-08 11:05 UTC
   - User: admin@company.com
   - Object: Alarm rules
   - Action: Lower expiration alert threshold from 30d to 14d
   - Impact: Earlier warning for cert renewals
   - Status: ✓ Applied

Summary of Changes:
- Configuration additions: 2 (new templates, rules)
- Configuration removals: 1 (removed 2 policy rules)
- Configuration updates: 2 (NTP, DNS)
- System tuning: 1 (backup, alarm thresholds)

Risk Assessment:
- All changes verified to pass policy validation ✓
- No alarms correlated with changes ✓
- Rollback capability confirmed for all changes ✓
- No out-of-band changes detected (unauthorized edits) ✓

Compliance:
- All changes documented in change tickets ✓
- All changes approved per change control process ✓
- Audit trail complete and verifiable ✓

Recommendations:
1. Continue audit trail monitoring (weekly or post-change)
2. Archive audit logs monthly for compliance/legal retention
3. Review unauthorized change detection policy (consider alerting on manual edits)
```

---

## Summary

These 20 example queries cover the major categories a CCIE SD-WAN architect would ask:

- **Inventory** (1-3): Baseline state, topology, health
- **Monitoring** (4-5): Alarms, trends, anomalies
- **Design** (6-7): Site onboarding, redundancy
- **Policy** (8-9): Policy status, security stack
- **Certificates** (10): Expiration timeline
- **Incidents** (11-13): BFD flapping, outages, performance
- **Upgrades** (14-15): Pre-check, deployment
- **Capacity** (16-17): CPU trending, redundancy
- **Compliance** (18-19): Policy audit, backup health
- **Audit** (20): Change trail

Each demonstrates the agent's capability to:
- Query vManage data systematically
- Cite evidence and data points
- Provide actionable recommendations
- Highlight risks and mitigation
- Propose next steps and approval gates
