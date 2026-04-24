# SDWAN_AI Sample Workflow Examples

This document provides 6 end-to-end workflow examples showing realistic human→agent interactions and expected outputs. Each workflow demonstrates multi-step processes that require careful planning, approval gates, and validation.

---

## Workflow 1: Onboard New Branch Site (2-Week Process)

**Scenario**: A new branch office opening in Sydney needs to be onboarded to the SD-WAN fabric. The architect must design the site topology, create device configs, and stage a controlled rollout.

### Day 1: Design Phase

**Human Query**:
```
We're opening a new branch in Sydney with 50 employees. 
The site will have a primary MPLS connection and Internet backup.
We have 2 Cisco SD-WAN edge routers arriving next week.
What's the design recommendation for integrating into our APAC hub topology?
```

**Agent (Architect) Response**:

```
SYDNEY BRANCH SITE ONBOARDING DESIGN

Current APAC Topology:
Per `/dataservice/device`: 42 existing APAC sites connected to Singapore regional hub
Per `/dataservice/network/topology`: Hub-spoke topology with Singapore as primary hub
Hub capacity: Primary hub has 287 OMP peers, <50 devices; CPU at 45% (headroom available)

New Site Profile:
- Location: Sydney (APAC region, existing coverage zone)
- Users: 50 (medium branch, business-critical)
- WAN links: MPLS (primary) + Internet (backup)
- Device count: 2 edge routers (primary + local backup)
- Traffic profile: Typical branch (office 365, Salesforce, video conferencing)

Recommended Design: Hub-Spoke with Local Device Redundancy

Network Topology:
- Primary hub: Singapore (existing, proven)
- Site-specific hub: Sydney-Edge-01 (primary), Sydney-Edge-02 (failover)
- Color pairs: MPLS primary, Internet secondary (auto-failover via BFD)
- OMP attributes: site-id=143 (next available), region=APAC-SOUTH

Expected Impact:
- New OMP peers to hub: 2 (Sydney edge routes)
- New BFD sessions: 4 (2 colors × 2 edges)
- Hub CPU impact: <1% (negligible)
- Deployment complexity: LOW (standard spoke template)

Design Tradeoffs:

Option A: Hub-Spoke (Recommended)
- Pros: Simplest config, proven template, fast deployment (1 day)
- Cons: All Sydney-to-APAC traffic transits Singapore hub (acceptable for 50 users)

Option B: Partial Mesh (SYD ↔ Top 5 APAC sites)
- Pros: Local east-west traffic bypasses hub
- Cons: More complex policy, higher ops overhead, minimal benefit for 50 users

Option C: Secondary Hub (Sydney becomes regional hub)
- Pros: Best scalability if site grows to 200+ users later
- Cons: Requires 2nd vSmart, multi-hub policies, 2-week deployment

Recommendation: Option A (Hub-Spoke) for now. Plan Option C if site grows to 100+ users in 2026.

Next Steps:
1. Confirm design choice (recommend A)
2. Finalize device inventory: model, serial numbers, firmware versions
3. Create device templates for Sydney-Edge-01 and Sydney-Edge-02
4. Generate config files (CSR, site-specific overrides)
5. Prepare canary deployment plan (start with Edge-01 only, monitor 7 days, then attach Edge-02)

Timeline:
- Day 1: Design approval
- Day 2-3: Template creation and dry-run
- Day 4: Canary deployment (Edge-01 only)
- Day 5-10: Validation period (monitor device health, policies, connectivity)
- Day 11: Edge-02 deployment (if Edge-01 stable)
- Day 12-14: Final validation and sign-off

Ready to proceed with template creation? (Confirm 'yes')
```

**Human**: "Yes, proceed. I'll have the device serial numbers and firmware versions tomorrow."

---

### Day 2-3: Template Preparation

**Human Query**:
```
Device serial numbers:
- Sydney-Edge-01: Serial ABC12345, running v20.8.1
- Sydney-Edge-02: Serial DEF67890, running v20.8.1

Both need MPLS connection to 203.0.113.1/24 and Internet to ISP-provided IP 198.51.100.1/24.
Site-specific overrides: QoS policy for video conference priority.

Ready to generate configs?
```

**Agent (Architect) Response**:

```
PRE-TEMPLATE REVIEW

Device Compatibility Check:
- Firmware: v20.8.1 (current hub is v20.9.2)
- Compatibility matrix (BRKENT-2215): v20.8.1 edge ↔ v20.9.2 vSmart = SUPPORTED ✓
- Recommendation: Plan firmware upgrade to v20.9.2 within 30 days (before policy v3.6 rollout)

Template Creation Plan:

1. Base Device Template (applies to both Edge-01 and Edge-02)
   - Site ID: 143
   - Site name: Sydney-Branch
   - Region: APAC-SOUTH
   - OMP attributes: Advertise site as "Sydney backup for APAC"
   - Default route: Via Singapore hub (primary)

2. WAN Color Configuration
   - MPLS color (primary):
     * IP: 203.0.113.2/24
     * Gateway: 203.0.113.1
     * BFD interval: 300ms, hold multiplier: 3 (standard)
     * Preferred: Yes
   
   - Internet color (secondary):
     * IP: 198.51.100.2/24
     * Gateway: 198.51.100.1
     * BFD interval: 300ms, hold multiplier: 3
     * Preferred: No (failover only)

3. QoS Policy Override (site-specific)
   - Video conference app (Zoom): Priority high (DSCP EF)
   - Voice (SIP): Priority high (DSCP EF)
   - Data apps: Priority medium
   - Best-effort traffic: Priority low

4. Device-Specific Overrides
   - Sydney-Edge-01: Set as primary (primary=true in OMP)
   - Sydney-Edge-02: Set as secondary (primary=false in OMP)

Dry-Run Preview (Sastre):

Template attachment simulation:
Sydney-Edge-01:
- New config lines: 47 (device template + color config + QoS policy)
- Risk: Low (standard template, proven on 42 existing sites)
- Validation: Expected to pass (no conflicts)

Sydney-Edge-02:
- New config lines: 47 (identical to Edge-01, except primary=false)
- Risk: Low
- Validation: Expected to pass

Rollback Plan:
- Sastre snapshot [2026-04-14_14:30] created before attachment
- Rollback time: <5 minutes (restore snapshot)

APPROVAL CHECKPOINT:

Ready to proceed with template attachment?
Canary approach:
1. Attach template to Sydney-Edge-01 only (Day 4)
2. Monitor for 7 days (verify OMP peers established, connectivity OK, policies active)
3. If healthy, attach template to Sydney-Edge-02 (Day 11)
4. Validate Edge-02, then sign-off (Day 14)

Expected outcome:
- Edge-01: Device reports to vManage, OMP neighbors established to Singapore hub, policies active
- Latency baseline: ~40-50ms to hub (MPLS), ~55-65ms (Internet)
- Throughput: Full 1Gbps MPLS, 100Mbps Internet backup (if applicable)

Confirm 'yes, proceed to canary deployment on Day 4' (or adjust timeline).
```

**Human**: "Yes, proceed with canary on Day 4. I'll provision the WAN circuits by then."

---

### Day 4: Canary Deployment

**Human Query**:
```
Circuits are ready. WAN IP configuration is locked in.
Ready to deploy Sydney-Edge-01?
```

**Agent (Architect) Response**:

```
CANARY DEPLOYMENT READINESS

Pre-Deployment Checklist:
✓ Device serial numbers verified: ABC12345
✓ WAN circuits provisioned and tested
✓ Device firmware: v20.8.1 (compatible)
✓ Sastre backup created: [2026-04-14_14:30]
✓ Template tested in dry-run: diffs verified
✓ Monitoring alerts configured for Sydney devices

Phase 1: Canary Deployment (Sydney-Edge-01)

Execution Steps:
1. Ship device Sydney-Edge-01 to site
2. Install at branch office (onsite tech support)
3. Initial power-on and self-test (30 min)
4. SSH to device and verify bootup logs (check for errors)
5. Attach device to vManage (zero-touch provisioning, or manual CSR enrollment)
6. Attach device template via Sastre
7. Verify device config matches template (device → template sync)

Expected Outcome (T+60 min):
- Device appears in vManage device list: CONNECTED ✓
- OMP peer to Singapore hub: ESTABLISHED ✓
- BFD sessions: UP on both MPLS and Internet colors ✓
- Policy templates: ACTIVE ✓
- Device heartbeat: <15 seconds ✓

Validation Monitoring (T+1h to T+7d):
1. Device connectivity: Must stay UP continuously
2. OMP peers: No flapping (watch for BFD instability)
3. Interface errors: Monitor for packet loss, CRC errors on WAN
4. Policy compliance: Video traffic marked correctly (DSCP EF validation)
5. Alarm baseline: Expect 0 critical/major alarms for this device
6. User feedback: 50 employees testing connectivity to apps

Daily Health Checks (Day 4-10):
- Day 4 (deployment day): 4 checks (1h, 3h, 8h, end-of-day)
- Day 5-10 (monitoring period): 1 check per day (morning baseline)
- Any alarm or connectivity issue triggers immediate investigation

Approval Checkpoint:

After 7-day canary validation:
- If all checks PASS: Ready to deploy Sydney-Edge-02 (proceed to canary Day 2)
- If issues detected: Troubleshoot and extend validation period (do NOT proceed to Edge-02)

Escalation Triggers (activate Troubleshooter agent):
- OMP peer flapping >2 times per day
- Device loses connectivity >5 minutes
- Policy validation fails
- Interface packet loss >1%

Ready to deploy Sydney-Edge-01? I will attach template and begin 7-day monitoring.

Confirm 'yes, deploy canary' to proceed.
```

**Human**: "Yes, deploy canary. I'll coordinate with branch IT for physical installation."

---

### Day 5-10: Canary Validation

**Daily Health Check Summary (Day 5 Morning)**:

```
CANARY HEALTH CHECK - DAY 1 (Sydney-Edge-01)

Deployment Status: ✓ SUCCESSFUL

Device Connectivity:
- Device online: YES ✓
- Last heartbeat: 3 minutes ago
- OMP peers to Singapore hub: 2 established (MPLS + Internet colors)
- BFD sessions: UP on both colors

Policy Status:
- Device template: v2.1 (ACTIVE) ✓
- QoS policy: ACTIVE (video apps marked DSCP EF) ✓
- Policy validation: PASSED ✓

Network Performance:
- Latency to hub (MPLS): 42ms (baseline 40-50ms) ✓
- Latency to hub (Internet): 58ms (baseline 55-65ms) ✓
- Packet loss (MPLS): 0.1% ✓
- Packet loss (Internet): 0.3% ✓

Alarms:
- Critical: 0
- Major: 0
- Warning: 0
- Minor: 0 (no false positives) ✓

User Feedback:
- 50 employees tested connectivity: All apps accessible ✓
- Video conferencing (Zoom): Quality GOOD (priority marking working)
- VPN/Data: Throughput normal

Day 2-10 Validation Plan:
- Continue daily health checks through Day 10
- Monitor for any degradation or intermittent issues
- On Day 11, if all checks pass: Deploy Sydney-Edge-02

Status: HEALTHY — Continue validation monitoring
```

**Day 11: Edge-02 Deployment** (after 7-day validation)

```
EDGE-02 CANARY APPROVAL & DEPLOYMENT

Edge-01 Validation Summary (Days 4-10):
✓ 7 days of continuous operation
✓ 0 device disconnects
✓ 0 policy validation errors
✓ 0 alarms
✓ User feedback: 100% positive
✓ Performance: Stable, baseline metrics maintained

Ready to deploy Sydney-Edge-02.

Dry-Run Edge-02 Template:
- Config changes: Identical to Edge-01, except primary=false (secondary failover)
- Expected impact: Create second OMP peer to hub, add 2nd BFD session pair
- Rollback: Sastre snapshot [2026-04-21_14:30] available

Deployment:
- Ship Edge-02 to Sydney site
- Install as secondary/failover device
- Attach device template via Sastre
- Expected outcome: 2 OMP peers + 4 BFD sessions (2 per edge router)

Canary Phase 2 Validation (Days 11-14):
- Monitor both Edge-01 and Edge-02 together
- Verify failover behavior (manually trigger Edge-01 reboot, watch Edge-02 take over)
- Confirm user connectivity during failover
- Verify both devices in sync with vManage

Sign-Off Criteria:
✓ Edge-01: Stable 7 days
✓ Edge-02: Stable 3 days
✓ Failover tested: Works as designed
✓ All policies active on both edges
✓ User acceptance: Confirmed

Confirm 'yes, deploy Edge-02 canary' to proceed.
```

**Human**: "Yes, deploy Edge-02. Expecting device onsite by Day 10."

---

### Day 14: Final Validation & Sign-Off

```
SYDNEY BRANCH ONBOARDING - SIGN-OFF

Deployment Complete ✓

Summary:
- Sydney-Edge-01: STABLE (10 days online, 0 incidents)
- Sydney-Edge-02: STABLE (3 days online, 0 incidents)
- Site-to-hub connectivity: Redundant (MPLS + Internet, Edge-01 + Edge-02)
- User experience: Excellent (50 employees, 0 escalations)

Final Metrics:
- Device count: 2 (both reporting to vManage)
- OMP peers: 4 (2 edges × 2 colors)
- BFD sessions: 8 (2 edges × 2 colors × 2 directions)
- Alarms (site-specific): 0
- Policy compliance: 100%

Failover Test Results:
- Manual Edge-01 reboot: Users experienced <2 second failover to Internet + Edge-02
- Recovery: Edge-01 rejoined topology within 30 seconds ✓

Documentation:
- Change ticket closed with deployment photos and metrics
- Runbook updated: Sydney site topology, failover procedures, escalation contacts
- Sastre backup: Final snapshot [2026-04-24_EOD] stored as "Sydney-Branch-v1-Deployed"

Future Maintenance:
1. Quarterly health check (monitoring trend)
2. Firmware upgrade to v20.9.2 (plan for Q2 2026)
3. Monitor for capacity growth (if site exceeds 100 users, plan secondary hub)
4. Policy updates: Include Sydney in future policy rollouts (standard spoke templates)

Onboarding Complete. Site ready for production.

Next site to onboard: [List upcoming branches or standby for requests]
```

---

## Workflow 2: Incident Investigation & Recovery (2-Hour Process)

**Scenario**: An SD-WAN troubleshooter receives an alert that 5 devices in the APAC region lost connectivity. The troubleshooter must rapidly diagnose the root cause and recommend remediation.

### T+0 min: Initial Alert

**Human Query**:
```
ALERT: 5 devices in Singapore region went offline.
OMP neighbors down on SiteA, SiteB, SiteC, SiteE, SiteG.
Last heartbeat was 10 minutes ago.
Are we in a regional outage situation?
```

**Agent (Troubleshooter) Response**:

```
INCIDENT TRIAGE - SINGAPORE REGIONAL OUTAGE

Severity: CRITICAL (5 sites offline, ~250 users affected, business impact HIGH)

Triage Results (0-5 min):

Device Connectivity Status:
Per `/dataservice/device`:
- SiteA: offline, last heartbeat 10 min ago
- SiteB: offline, last heartbeat 10 min ago
- SiteC: offline, last heartbeat 10 min ago
- SiteE: offline, last heartbeat 10 min ago
- SiteG: offline, last heartbeat 10 min ago
- All 5 devices: Last online at 14:32 UTC, now 14:42 UTC (10-minute gap)

Regional Scope:
- APAC total: 42 sites
- Singapore offline: 5/42 (12%)
- Melbourne/Sydney: 10 devices online ✓
- Other APAC: 27 devices online ✓
- EMEA: 48 devices online ✓
- Americas: 52 devices online ✓

Regional Outage Confirmed: YES (Singapore only)

Alarm Summary (last 15 min):
Per `/dataservice/alarms`:
- OMP-NEIGHBOR-DOWN: 5 devices (triggered at 14:33 UTC)
- vManage-DEVICE-UNREACHABLE: 5 devices (triggered at 14:34 UTC)
- No hub alarms detected (Singapore hub appears to be up)

Root Cause Hypothesis (ranked by likelihood):

Hypothesis A (likelihood: HIGH) — WAN Link to Singapore Hub Down or Congested
- Evidence: All 5 Singapore devices lost OMP at same timestamp (14:33 UTC)
- Evidence: All other regional devices still online (not a vManage outage)
- Evidence: Hub controller not reporting alarms (hub itself up)
- Test: Ping Singapore hub WAN interface from external location; check carrier status
- Fix: Coordinate with ISP; verify hub WAN links up; force failover to secondary hub if available

Hypothesis B (likelihood: MEDIUM) — Hub Controller Failure (Primary vSmart)
- Evidence: Hub appears up (no critical alarms), but all SG-to-hub OMP connections failed
- Evidence: Timing suggests simultaneous failure (not gradual)
- Test: Verify primary vSmart process status; check hub CPU/memory
- Fix: Failover to secondary vSmart (if redundancy available); restart primary if hung

Hypothesis C (likelihood: MEDIUM) — BGP Routing Loss (Carrier-Level)
- Evidence: Multiple devices failed simultaneously (unlikely to be device-level issue)
- Evidence: All SG site loss (could be region-specific routing issue at ISP)
- Test: Traceroute from hub to SG devices; check BGP neighbor status on hub
- Fix: Investigate ISP routing; request BGP session failover; check alternate path availability

Hypothesis D (likelihood: LOW) — DNS/Hub Hostname Resolution Failure
- Evidence: Devices can't resolve hub hostname
- Test: SSH to one offline device (if accessible) and nslookup hub hostname
- Fix: Update device DNS servers; switch to IP-based hub addresses

Recommended Immediate Actions:

1. (NOW) Verify Singapore hub health:
   - SSH to primary vSmart and check process status: systemctl status vsmartd
   - Check hub CPU/memory: top | grep vsmartd
   - Check hub WAN connectivity: ping ISP gateway
   
2. (NOW) Check ISP status:
   - Call ISP NOC: "5 devices in Singapore region offline, started 14:32 UTC"
   - Ask: Is there a regional outage or routing issue?
   - Ask: Are BGP sessions to hub up?
   
3. (If primary vSmart is hung) Failover to secondary vSmart:
   - Redirect device registration to secondary hub IP (manual DNS override or device config)
   - Expected recovery: <5 min (devices re-establish OMP to secondary)
   
4. (If ISP confirms outage) Implement workaround:
   - If secondary WAN color available (Internet backup): Force traffic failover
   - Expected recovery: <10 min (devices use backup color)
   
5. (Ongoing) Monitor recovery:
   - Watch for device heartbeat re-establishment
   - Monitor for new alarms after recovery
   - Collect device syslog for RCA documentation

ETA to Resolution: 15-30 minutes (depending on root cause)

Status: INVESTIGATING — Need you to confirm hub status and call ISP NOC. Keep me updated.
```

**Human**: "Checking hub now. Pinging hub and it's responding. ISP NOC says no regional outage. Hub CPU is normal. Looks like hub connectivity to Singapore devices might be asymmetric (hub can't reach devices). Standing by."

---

### T+15 min: Investigation Deepening

**Agent (Troubleshooter) Response**:

```
ASYMMETRIC CONNECTIVITY ISSUE IDENTIFIED

Updated Root Cause Hypothesis:

The hub can ping Singapore devices, but devices can't reach hub.
This suggests: Firewall rule change, ACL misconfiguration, or device-side routing issue.

Updated Hypothesis Ranking:

Hypothesis A (UPDATED — likelihood now HIGH) — Device Firewall Rule Change
- Evidence: Hub ↔ devices asymmetric connectivity (one direction works, other blocked)
- Evidence: Timing at 14:32 UTC: Was a security policy or firewall rule pushed?
- Test: Check vManage audit log for template/policy changes since 14:00 UTC
- Fix: Rollback firewall rule if recent change confirmed

Hypothesis B (UPDATED — likelihood now MEDIUM) — Device-Side BGP Route Loss
- Evidence: Devices have WAN connectivity (since hub can ping them), but lost IP route to hub
- Evidence: All 5 devices affected (suggests common config or failure)
- Test: SSH to one offline device and check routing table: show ip route
- Fix: Restart routing process or reload device

Hypothesis C — Device WAN Interface Down (despite ping response)
- Evidence: Asymmetric suggests device interface issue
- Test: SSH to device and check WAN interface status: show interfaces wide
- Fix: Bounce WAN interface or restart device

Immediate Actions:

1. Check audit log for recent policy/firewall changes:
   Per `/dataservice/audits` (last 30 min):
   - Are there any template attachments or policy activations since 14:00?
   - If YES and recent: This is likely the root cause

2. SSH to offline device (pick SiteA) and run:
   - show ip route 0.0.0.0/0 (check if default route to hub exists)
   - show interfaces wide (check WAN interface status, protocol up/down)
   - ping <hub-ip> (test if device can reach hub from its perspective)

3. If routing issue confirmed:
   - Restart routing process: service reset protocol bgp
   - Check if device re-establishes OMP to hub

Status: Narrowing root cause. Awaiting audit log review and device SSH results.
```

**Human**: "Audit log shows a security policy was pushed at 14:30 UTC (Security-Policy-v3.6 activated). Timestamp matches the outage. Comparing v3.5 vs v3.6... found it: v3.6 added a new firewall rule that blocks OMP traffic from non-hub sites. Rule is overly broad and caught the hub connectivity."

---

### T+20 min: Root Cause Confirmed & Remediation

**Agent (Troubleshooter) Response**:

```
ROOT CAUSE CONFIRMED: Firewall Rule Regression in Security-Policy v3.6

Issue:
Security-Policy v3.6 introduced a new firewall rule that inadvertently blocks OMP traffic
from devices to hubs. Rule logic:
  
  "Deny OMP traffic between non-hub sites (prevent spoke-to-spoke OMP)"
  
But the rule was too broad and also blocked hub-to-spoke OMP.

Evidence:
- Policy v3.5 (before 14:30 UTC): OMP allowed in both directions
- Policy v3.6 (after 14:30 UTC): OMP blocked in device-to-hub direction
- 5 Singapore devices affected: All tried to reach hub, traffic dropped by new rule

Impact:
- 5 devices lost OMP connectivity to hub
- Users at 5 sites lost access to enterprise network
- 250+ users affected
- Duration: 10+ minutes (until fix applied)

Recommended Remediation:

Option A: Rollback Security-Policy v3.6 (FASTEST, 5 min)
- Revert to v3.5 (known-good state)
- Expected recovery: <2 min (devices re-establish OMP)
- Pros: Fast, low-risk
- Cons: Lose security improvements in v3.6 (8 new URL filter rules)

Option B: Fix Security-Policy v3.6 and Re-deploy (15-20 min)
- Modify rule to correctly exclude hub devices from "deny non-hub OMP" logic
- Dry-run fix on canary device (3 min)
- Re-deploy fixed v3.6 to all devices (10 min)
- Pros: Keep security improvements
- Cons: Longer recovery time, requires testing

Option C: Deploy Hotfix Rule (7-10 min)
- Add a "permit OMP hub-to-spoke" rule (higher priority) above the problematic rule
- Re-deploy updated v3.6 to all devices
- Pros: Medium recovery time, keeps security improvements
- Cons: Requires quick rule edit and dry-run

Recommendation: Option A (Rollback v3.6 to v3.5)
- Fastest recovery (2 min)
- Safest choice (v3.5 is known-good)
- Schedule v3.6 fix for tomorrow with thorough testing

Rollback Plan:

1. Activate previous policy version (v3.5)
   - Command: [Activate Security-Policy v3.5 via vManage]
   - Target: All 142 devices
   - Dry-run: [Already verified — v3.5 is safe baseline]
   
2. Expected outcome:
   - Device policy update: <1 min
   - OMP re-establishment: <1 min
   - User connectivity: Restored within 2 min

3. Validation (post-rollback):
   - All 5 Singapore devices: OMP peers UP ✓
   - All 5 devices: Device heartbeat UP ✓
   - No new alarms ✓
   - Users report access restored ✓

POST-INCIDENT ACTIONS:

1. Immediate (next 30 min):
   - Execute rollback to v3.6
   - Validate all 142 devices
   - Notify stakeholders: incident resolved

2. Short-term (tomorrow):
   - RCA meeting: Review policy v3.6 change, identify root cause in rule design
   - Fix policy v3.6: Rewrite rule to be more specific (add hub-exclude condition)
   - Test v3.6 fix on canary devices (3 test devices) for 24 hours

3. Long-term (this week):
   - Deploy fixed v3.6 once validated
   - Add monitoring rule: Alert on OMP flap patterns (catch similar issues faster)
   - Review policy change process: Require dry-run testing before deployment

APPROVAL CHECKPOINT:

Ready to rollback Security-Policy v3.6 to v3.5?
This will:
- Restore OMP connectivity to 5 offline devices
- Re-enable connectivity for ~250 users
- Temporarily lose URL filter improvements in v3.6 (defer until fix is ready)

Expected recovery time: 2 minutes
Risk: LOW (reverting to known-good baseline)

Confirm 'yes, execute rollback immediately' to proceed.
```

**Human**: "Yes, execute rollback immediately."

---

### T+25 min: Recovery Validation

```
SECURITY-POLICY ROLLBACK - EXECUTION

Status: IN PROGRESS

Step 1: Activate v3.5 on all 142 devices
- Command sent: Activate-Policy Security-Policy v3.5
- Devices receiving update: 142
- Expected completion: 1 minute

Device Status (T+1 min):
- SiteA: OMP peers UP ✓ | Device heartbeat UP ✓
- SiteB: OMP peers UP ✓ | Device heartbeat UP ✓
- SiteC: OMP peers UP ✓ | Device heartbeat UP ✓
- SiteE: OMP peers UP ✓ | Device heartbeat UP ✓
- SiteG: OMP peers UP ✓ | Device heartbeat UP ✓
- Other 137 devices: Status normal, no new alarms ✓

Alarms Trend:
- OMP-NEIGHBOR-DOWN (Singapore sites): Cleared ✓
- vManage-DEVICE-UNREACHABLE: Cleared ✓
- New alarms: None ✓

User Impact:
- Users at 5 sites: Reported access restored ✓
- No secondary failures detected ✓
- No complaints about rollback (URL filter rules disabled, but other policies working)

RECOVERY COMPLETE ✓

Summary:
- Incident duration: 25 minutes (detection to full recovery)
- Root cause: Firewall rule regression in Security-Policy v3.6
- Fix applied: Rollback to v3.5
- Recovery time: 2 minutes (policy deployment + OMP re-establishment)
- User impact: 25-minute outage, ~250 users affected
- Rollback success: 100%

Post-Incident Follow-Up:

1. Schedule RCA meeting for tomorrow morning (team review)
2. Create action items:
   - Fix Security-Policy v3.6 (rule logic correction)
   - Test fixed v3.6 on canary (3 sites, 24 hours)
   - Re-deploy v3.6 once fix validated
3. Update change process:
   - Require dry-run testing for all policy changes >10 rules
   - Add policy validation step before vManage push
4. Add monitoring alert:
   - Alert on OMP flap pattern: >5 flaps in 1 hour from same site

Change Ticket:
- Incident: Singapore regional outage (Security-Policy v3.6 regression)
- Root cause: Firewall rule too broad, blocked hub-to-spoke OMP
- Resolution: Rolled back to v3.5
- Impact: 25-min outage, 250 users affected, <1% of revenue impact
- Status: CLOSED (pending RCA and fix)

Incident complete. Awaiting RCA meeting tomorrow.
```

---

## Workflow 3: Quarterly Certificate Renewal (1-Week Process)

**Scenario**: The operator performs the quarterly certificate audit and discovers 8 devices with certificates expiring in <30 days. The operator must coordinate renewal with change management and coordinate device reboots.

### Day 1: Certificate Sweep

**Human Query (Operator initiated, no user request)**:
```
Running /cert-sweep 30
```

**Agent (Operator) Response**:

```
CERTIFICATE SWEEP REPORT - Q2 2026

Window: 30 days (today 2026-04-13 to 2026-05-13)

CRITICAL (Expiring < 7 days):
- None ✓

WARNING (Expiring 7-14 days):
1. SiteA-Hub-01: Expires 2026-04-19 (6 days) | Action: START RENEWAL TODAY
   - Current cert: Issued 2023-04-19 (3-year validity, 3 years old)
   - Root CA: Internal CA, still valid until 2027-12-31 ✓

ALERT (Expiring 14-30 days):
1. SiteB-Hub-01: Expires 2026-04-25 (12 days) | Action: Schedule renewal for week of Apr 15
2. SiteC-Branch-02: Expires 2026-05-02 (19 days) | Action: Schedule renewal for week of Apr 20
3. SiteD-Branch-03: Expires 2026-05-05 (22 days) | Action: Schedule renewal for week of Apr 27
4. SiteE-Hub-02 (secondary hub): Expires 2026-05-07 (24 days) | Action: Schedule renewal for week of May 1
5. SiteF-Branch-04: Expires 2026-05-08 (25 days) | Action: Schedule renewal for week of May 1
6. SiteG-Branch-05: Expires 2026-05-10 (27 days) | Action: Schedule renewal for week of May 8
7. SiteH-Branch-06: Expires 2026-05-11 (28 days) | Action: Schedule renewal for week of May 8

Root CA Certificate:
- Status: Valid
- Expires: 2027-12-31 (20 months away) ✓
- No renewal needed for 18+ months

Total Devices Requiring Renewal: 8 (5.6% of 142 devices)

Renewal Workflow Summary:

Each certificate renewal requires:
1. Generate CSR on device (10 min)
2. Submit CSR to internal CA (30 min: manual approval workflow)
3. Receive signed certificate (15 min)
4. Install signed certificate on device (15 min)
5. Verify device accepts cert and auth succeeds (10 min)
Total per device: ~80 minutes (1.3 hours)

Maintenance Window Planning:

Critical certificates (SiteA-Hub-01 — expires in 6 days):
- Must be renewed by 2026-04-19 (no margin)
- Recommend: Renewal window Tuesday 2026-04-14, 2am-6am UTC (4-hour window)
- Devices: SiteA-Hub-01 (primary hub — critical, cannot be down during business hours)

High-priority certificates (SiteB-Hub-01, SiteE-Hub-02 — expires in 12-24 days):
- Recommend: Renewal windows weeks of Apr 15 and May 1
- Devices: 2 hub servers + 1 branch = 3 devices, ~4 hours each
- Note: SiteB-Hub-01 is primary hub backup; SiteE-Hub-02 is secondary hub

Standard certificates (SiteC-SiteH branches — expires in 19-28 days):
- Recommend: Renewal windows weeks of Apr 20, Apr 27, May 8
- Devices: 5 branch devices, low-risk (branch outages acceptable if brief)
- Coordinate with branch IT for maintenance window (usually evenings local time)

Renewal Timeline (Recommended):

Week 1 (Apr 14):
- Tuesday 2am-6am UTC: Renew SiteA-Hub-01 (critical hub device)

Week 2 (Apr 21):
- Tuesday 2am-6am UTC: Renew SiteB-Hub-01 (primary hub backup)
- Wednesday 2am-6am UTC: Renew SiteC-Branch-02

Week 3 (Apr 28):
- Tuesday 2am-6am UTC: Renew SiteD-Branch-03

Week 4 (May 5):
- Tuesday 2am-6am UTC: Renew SiteE-Hub-02 (secondary hub)
- Wednesday 2am-6am UTC: Renew SiteF-Branch-04

Week 5 (May 12):
- Tuesday 2am-6am UTC: Renew SiteG-Branch-05
- Wednesday 2am-6am UTC: Renew SiteH-Branch-06

Risk Assessment:
- Hub renewals (SiteA, SiteB, SiteE): Medium risk (hub temporary unavailability)
  Mitigation: Secondary hub provides failover; devices auto-failover if primary down
  
- Branch renewals (SiteC-H): Low risk (branch-only outage, 5-10 min duration acceptable)

Approval Checkpoint:

Recommendation: Proceed with renewal plan as scheduled above.
1. Confirm maintenance windows with branch IT managers
2. Prepare CSR templates for engineering team
3. Schedule 1st renewal (SiteA-Hub-01) for Tuesday 2026-04-14

Ready to schedule renewals? (Confirm 'yes' to proceed with Week 1 renewal)
```

---

### Day 3: First Renewal Execution

**Human Query**:
```
Scheduled SiteA-Hub-01 renewal for Tuesday 2-6am UTC (tomorrow). 
Engineering team is ready to generate CSR and install cert.
Ready to execute Week 1 renewal?
```

**Agent (Operator) Response**:

```
SiteA-HUB-01 CERTIFICATE RENEWAL - EXECUTION PLAN

Pre-Renewal Checklist:
✓ Certificate expires: 2026-04-19 (6 days, margin adequate for renewal)
✓ Device: SiteA-Hub-01 (primary hub vSmart controller)
✓ Maintenance window: Tuesday 2026-04-14, 02:00-06:00 UTC
✓ Expected business impact: Low (secondary hub provides failover)
✓ Device access: SSH access confirmed
✓ Internal CA: Ready to sign CSR (engineering confirmed)
✓ Backup: Sastre snapshot [2026-04-13_14:30] created pre-renewal ✓

Renewal Execution Steps:

Step 1: Pre-renewal validation (T-10 min)
- Verify device connectivity and OMP peer count (should see 287 peers)
- Verify secondary hub healthy (SiteB-Hub-01 should have ~285 peers)
- Take baseline metrics: device CPU, memory, connectivity

Step 2: Generate CSR on SiteA-Hub-01 (T+0)
- SSH to device
- Command: openssl req -new -key /etc/ssl/private/site-key.pem -out /tmp/sitea-hub-01.csr
- CSR parameters: CN=SiteA-Hub-01, O=Company, C=US (pre-configured)
- Expected duration: 5 minutes

Step 3: Submit CSR to internal CA (T+5)
- Send CSR file to CA team (internal process, typically <30 min approval)
- Request: Sign with company CA root certificate, 1-year validity
- Expected turnaround: 30 minutes

Step 4: Receive signed certificate (T+35)
- CA team returns signed cert (cert.pem)
- Verify cert details: CN=SiteA-Hub-01, not yet expired, root chain OK
- Expected duration: 5 minutes

Step 5: Install certificate on device (T+40)
- SSH to device
- Backup current certificate: cp /etc/ssl/certs/sitea-hub-01.crt /etc/ssl/certs/sitea-hub-01.crt.bak
- Install new cert: cp cert.pem /etc/ssl/certs/sitea-hub-01.crt
- Restart OMP daemon: systemctl restart vsmartd
- Expected duration: 10 minutes

Step 6: Verify device and certificate (T+50)
- Check device connectivity: OMP peers should re-establish within 30 sec
- Verify certificate: openssl x509 -in /etc/ssl/certs/sitea-hub-01.crt -text -noout (check expiration date)
- Verify device heartbeat: Should report to vManage as UP
- Check alarms: No device-authentication or certificate-related alarms
- Expected duration: 5 minutes

Step 7: Validate OMP and hub health (T+55)
- Verify secondary hub (SiteB-Hub-01) received OMP updates from SiteA (peer count should stabilize)
- Monitor device CPU/memory (should return to baseline)
- Verify no new alarms on any device
- Expected duration: 5 minutes

Total expected duration: 60 minutes (1 hour, within 4-hour window)

Expected Outcome:
- Device SiteA-Hub-01: Certificate renewed, 1 year of validity
- Expiration: 2027-04-19 (new date, successfully rolled forward)
- Device status: Operational, OMP peers healthy, no service interruption
- Users: No impact (seamless failover to secondary hub during renewal)

Rollback Plan (if issues):
- If certificate installation fails: Restore backup cert
- If device connectivity lost: Restore Sastre backup [2026-04-13_14:30] (15-min recovery)
- If secondary hub unhealthy: Abort renewal and escalate to Troubleshooter

Approval Checkpoint:

Ready to execute SiteA-Hub-01 renewal on Tuesday 2am UTC?
Confirm 'yes, execute renewal' to proceed.
(This will start CSR generation at T+0)
```

**Human**: "Yes, execute renewal. CA team standing by for CSR approval."

---

### Day 4: Renewal Completion & Next Steps

```
WEEK 1 RENEWAL COMPLETE - SiteA-Hub-01 ✓

Execution Summary:

Renewal Timeline (Actual):
- T+0 (02:00 UTC): CSR generated successfully
- T+10 (02:10 UTC): CSR submitted to CA team
- T+25 (02:25 UTC): CA team approved and returned signed cert
- T+35 (02:35 UTC): Certificate installed on device, OMP daemon restarted
- T+40 (02:40 UTC): Device reconnected, OMP peers re-established (287 peers UP)
- T+45 (02:45 UTC): Certificate verified, device status UP, no alarms

Total Duration: 45 minutes (within 4-hour window) ✓

Post-Renewal Validation:

Certificate Details:
- CN: SiteA-Hub-01
- Issuer: Company Internal CA
- Valid from: 2026-04-14
- Valid to: 2027-04-14 (1 year validity)
- Status: ACTIVE ✓

Device Health:
- Connectivity: OMP peers established (287 peers) ✓
- Device heartbeat: UP, reporting to vManage ✓
- CPU usage: Baseline (45%, normal) ✓
- Memory usage: Baseline (62%, normal) ✓
- Alarms: 0 new alarms, no certificate-related alerts ✓

User Impact:
- Business disruption: NONE (secondary hub handled failover transparently)
- Service continuity: 100% (no user escalations)

Documentation:
- Change ticket updated: SiteA-Hub-01 cert renewed
- Certificate expiration tracking: Updated to 2027-04-14
- Renewal notes: Completed successfully, no issues

Next Scheduled Renewal:
- Week 2 (Apr 21): SiteB-Hub-01 + SiteC-Branch-02

Ready to proceed with Week 2 renewals? Confirm to schedule both devices for next Tuesday.
```

---

## Summary

These workflow examples demonstrate:

1. **Site Onboarding**: 2-week phased approach with canary validation, approval gates, and sign-off
2. **Incident Response**: 25-minute RCA, root cause confirmation, remediation, and post-incident actions
3. **Certificate Renewal**: Quarterly audit, scheduling coordination, phased renewals over 4 weeks, risk mitigation

Each workflow shows:
- **Planning phase**: Design, preparation, approval
- **Execution phase**: Step-by-step instructions, real-time validation
- **Closure phase**: Validation, documentation, next steps
- **Approval gates**: Explicit human confirmation before proceeding
- **Evidence-based decisions**: Data from vManage guides every decision
- **Rollback strategy**: Every change has a revert plan ready
- **Communication**: Clear status updates and escalation criteria
