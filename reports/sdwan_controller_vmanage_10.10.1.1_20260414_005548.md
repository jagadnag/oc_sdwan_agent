# SD-WAN Health Summary Report - vmanage_10.10.1.1

**Generated:** 2026-04-14 05:55:48 UTC  
**Data Source:** Sastre exports (`devices.json`, `state.json`, `alarms.json`, `certificates.json`)  
**Report Method:** `report_generator` template + LLM-authored AI assessment

## AI Assessment Summary

### Executive Summary
The fabric is operational but risk-elevated: all controllers are reachable and control/data-plane adjacencies are up in the exported state, yet one branch edge (dc-cedge01) is flagged unreachable and alarm load is high (100 total in 24h, including 30 Critical and 50 High). Current risk is primarily service degradation due to sustained edge resource pressure (memory/CPU) rather than a control-plane collapse.

### CCIE Technical Summary
From a control-plane perspective, exported Sastre state indicates stable OMP (7/7 up), control connections (26/26 up), and BFD sessions (36/36 up) across dual-color transport combinations (mpls/public-internet). However, observability conflict exists: inventory reachability marks dc-cedge01 unreachable while state tables still show active control/BFD entries, which can occur from polling skew, stale cache, or transient management reachability issues. Alarm concentration on site2-cedge01 and my-10-f33116-mc01 (memory-usage dominant) suggests branch compute exhaustion risk that can cascade to control and app-route instability if not mitigated.

### Key Findings
- Controllers (vManage/vSmart/vBond) are healthy and reachable at site 101.
- Fabric control/data indicators are green in state exports (BFD/control/OMP all up).
- 1/7 device unreachable in inventory: dc-cedge01 (site 100).
- Alarm profile is severe and bursty: Critical+High = 80/100 alarms; top types are memory-usage (78) and cpu-usage (22).
- Alarm hotspots are concentrated on site2-cedge01 (51) and my-10-f33116-mc01 (38).
- Certificate posture is clean in this snapshot (40/40 valid).

### Recommendations
1) Validate dc-cedge01 with real-time checks (Sastre realtime/state + controller telemetry) and confirm if this is true reachability loss or inventory lag.
2) Execute immediate capacity triage on site2-cedge01 and my-10-f33116-mc01: inspect control-plane CPU, memory consumers, app hosting/services, and logging overhead; adjust thresholds if noisy but keep critical guards intact.
3) Run phased remediation: canary tuning on one affected edge, then roll to similar branches with 30-minute hold points and rollback checkpoints.
4) Add an architectural guardrail: resource baseline policy per edge class (CPU/memory headroom targets, alarm dampening windows, and escalation on sustained >15 min breaches).
5) Schedule software/lifecycle review for affected edge models to align with controller train and reduce operational drift.

## Snapshot KPIs

| Metric | Value |
|---|---|
| Overall Health | CRITICAL |
| Composite Health Score (/100) | 94.3 |
| Total Devices | 7 |
| Controllers | 3 |
| Edges | 4 |
| Reachable | 6 |
| Unreachable | 1 |
| Total Alarms | 100 |
| Active Alarms | 7 |
| BFD Sessions | 36 |
| Control Connections | 26 |
| OMP Peers | 7 |
| Certificates | 40 |

## Alert Categorization

| Category | Count | Source Severity Mapping |
|---|---|---|
| Critical | 30 | Critical |
| High | 50 | Major |
| Medium | 4 | Medium |
| Low | 16 | Minor |

## Controller Status

| Name | System IP | Site | Reachability | Type | Model |
|---|---|---|---|---|---|
| vbond | 10.10.1.3 | 101 | reachable | vbond | vedge-cloud |
| vmanage | 10.10.1.1 | 101 | reachable | vmanage | vmanage |
| vsmart | 10.10.1.5 | 101 | reachable | vsmart | vsmart |

## Device Inventory

| Name | System IP | Site | Reachability | Type | Model |
|---|---|---|---|---|---|
| dc-cedge01 | 10.10.1.11 | 100 | unreachable | cedge | vedge-C8000V |
| my-10-f33116-mc01 | 10.10.1.13 | 1001 | reachable | cedge | vedge-C8000V |
| site2-cedge01 | 10.10.1.15 | 1002 | reachable | cedge | vedge-C8000V |
| site3-vedge01 | 10.10.1.17 | 1003 | reachable | vedge | vedge-cloud |
| vbond | 10.10.1.3 | 101 | reachable | vbond | vedge-cloud |
| vmanage | 10.10.1.1 | 101 | reachable | vmanage | vmanage |
| vsmart | 10.10.1.5 | 101 | reachable | vsmart | vsmart |

## VPN / Tunnel Snapshot

### VPN (VRF) Interface Distribution
| VPN (VRF) | Interface Count |
|---|---|
| 0 | 53 |
| 65530 | 8 |
| 512 | 7 |
| 65528 | 7 |
| 1 | 5 |
| 65529 | 3 |

### BFD Tunnel Color-Pair Distribution
| Tunnel Pair | Count |
|---|---|
| mpls -> mpls | 9 |
| mpls -> public-internet | 9 |
| public-internet -> mpls | 9 |
| public-internet -> public-internet | 9 |

## BFD / Control / OMP Health

| Plane | Total | Up | Down/Other |
|---|---|---|---|
| BFD | 36 | 36 | 0 |
| Control Connections | 26 | 26 | 0 |
| OMP | 7 | 7 | 0 |

## Alarm Hotspots

### Top Devices by Alarm Volume
| Device | Alarm Count |
|---|---|
| site2-cedge01 | 51 |
| my-10-f33116-mc01 | 38 |
| vmanage | 11 |

### Top Alarm Types
| Alarm Type | Count |
|---|---|
| memory-usage | 78 |
| cpu-usage | 22 |

### Active Alarms (Current)
| Time | Device | Severity | Type | Message |
|---|---|---|---|---|
| 2026-04-13 21:41:24 UTC | vmanage | Medium | cpu-usage | System CPU usage is above 60% |
| 2026-04-13 21:40:28 UTC | my-10-f33116-mc01 | Major | cpu-usage | System CPU load is 1min-3, 5min-11, 15min-15 |
| 2026-04-13 21:37:09 UTC | my-10-f33116-mc01 | Major | memory-usage | System memory usage is above 88% |
| 2026-04-13 21:36:41 UTC | site2-cedge01 | Critical | memory-usage | System memory usage is above 93% |
| 2026-04-13 21:36:21 UTC | site2-cedge01 | Critical | cpu-usage | System CPU load is 1min-18, 5min-12, 15min-11 |
| 2026-04-13 21:32:20 UTC | site2-cedge01 | Major | memory-usage | System memory usage is above 88% |
| 2026-04-13 21:26:38 UTC | site2-cedge01 | Major | cpu-usage | System CPU load is 1min-6, 5min-8, 15min-11 |

## Certificate Posture

| Status | Count |
|---|---|
| valid | 40 |

## Risk Notes
- One branch (`dc-cedge01`) is unreachable in inventory while control/BFD rows are present in state export. This is an inconsistency that should be validated against real-time status.
- Alarm pressure is concentrated on `site2-cedge01` and `my-10-f33116-mc01` (memory/cpu), indicating sustained resource saturation risk.
- Control, BFD, and OMP are fully up in exported state data, suggesting no fabric-wide control-plane outage at capture time.
