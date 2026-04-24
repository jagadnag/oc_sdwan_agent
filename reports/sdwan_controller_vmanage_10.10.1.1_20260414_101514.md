# SD-WAN Health Summary Report - vmanage_10.10.1.1

**Generated:** 2026-04-14 15:15:14 UTC  
**Data Source:** Sastre exports (`devices.json`, `state.json`, `alarms.json`, `certificates.json`)  
**Report Method:** `report_generator` template + LLM-authored AI assessment

## AI Assessment Summary

### Executive Summary
Fabric is risk-elevated: controllers are reachable, but 1 device(s) are unreachable and alarm pressure is high (Critical=43, High=49). Primary risk is branch resource saturation, not control-plane collapse.

### CCIE Technical Summary
Sastre state snapshot shows BFD 36/36 up, control 26/26 up, and OMP 7/7 up. Inventory/state skew should be validated for unreachable nodes with realtime checks. Alarm concentration is highest on site2-cedge01, my-10-f33116-mc01 (memory/cpu dominant).

### Key Findings
- Controllers reachable: 3/3
- Unreachable devices: 1
- Alarm distribution: Critical 43, High 49, Medium 4, Low 4
- Top alarm types: memory-usage (67), cpu-usage (33)
- Certificates valid: 40/40

### Recommendations
1) Validate unreachable devices with Sastre realtime checks and controller telemetry correlation.
2) Prioritize CPU/memory remediation on top alarming edges; review services, logging, and process utilization.
3) Apply phased remediation (canary -> regional -> global) with rollback checkpoints.
4) Tune alarm baselines and dampening to reduce noise while preserving critical safety alerts.

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
| Active Alarms | 11 |
| BFD Sessions | 36 |
| Control Connections | 26 |
| OMP Peers | 7 |
| Certificates | 40 |

## Alert Categorization

| Category | Count | Source Severity Mapping |
|---|---|---|
| Critical | 43 | Critical |
| High | 49 | Major |
| Medium | 4 | Medium |
| Low | 4 | Minor |

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
| site2-cedge01 | 46 |
| my-10-f33116-mc01 | 40 |
| vmanage | 14 |

### Top Alarm Types
| Alarm Type | Count |
|---|---|
| memory-usage | 67 |
| cpu-usage | 33 |

### Active Alarms (Current)
| Time | Device | Severity | Type | Message |
|---|---|---|---|---|
| 2026-04-14 06:15:53 UTC | site2-cedge01 | Critical | memory-usage | System memory usage is above 93% |
| 2026-04-14 06:15:15 UTC | my-10-f33116-mc01 | Critical | memory-usage | System memory usage is above 93% |
| 2026-04-14 06:15:06 UTC | my-10-f33116-mc01 | Major | memory-usage | System memory usage is above 88% |
| 2026-04-14 06:15:03 UTC | site2-cedge01 | Major | memory-usage | System memory usage is above 88% |
| 2026-04-14 06:14:39 UTC | site2-cedge01 | Critical | cpu-usage | System CPU load is 1min-15, 5min-12, 15min-12 |
| 2026-04-14 06:09:52 UTC | site2-cedge01 | Major | cpu-usage | System CPU load is 1min-9, 5min-11, 15min-12 |
| 2026-04-14 05:53:33 UTC | vmanage | Critical | cpu-usage | System CPU usage is above 90% (critically high) |
| 2026-04-14 05:39:32 UTC | vmanage | Major | cpu-usage | System CPU usage is above 75% |
| 2026-04-14 05:30:00 UTC | my-10-f33116-mc01 | Critical | cpu-usage | System CPU load is 1min-19, 5min-12, 15min-11 |
| 2026-04-14 05:29:34 UTC | vmanage | Medium | cpu-usage | System CPU usage is above 60% |
| 2026-04-14 05:27:56 UTC | my-10-f33116-mc01 | Major | cpu-usage | System CPU load is 1min-10, 5min-8, 15min-10 |

## Certificate Posture

| Status | Count |
|---|---|
| valid | 40 |

## Risk Notes
- One branch (`dc-cedge01`) is unreachable in inventory while control/BFD rows are present in state export. This is an inconsistency that should be validated against real-time status.
- Alarm pressure is concentrated on `site2-cedge01` and `my-10-f33116-mc01` (memory/cpu), indicating sustained resource saturation risk.
- Control, BFD, and OMP are fully up in exported state data, suggesting no fabric-wide control-plane outage at capture time.
