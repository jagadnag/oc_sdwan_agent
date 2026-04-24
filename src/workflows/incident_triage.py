"""Incident triage workflow for rapid problem diagnosis"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..vmanage_client import VManageClient
from ..collector import SDWANCollector
from ..analyzers.bfd_analyzer import BFDAnalyzer
from ..analyzers.control_analyzer import ControlPlaneAnalyzer
from ..analyzers.alarm_correlator import AlarmCorrelator

logger = logging.getLogger(__name__)


def triage_incident(client: VManageClient,
                    site_id_or_device: str,
                    time_window_min: int = 60) -> Dict[str, Any]:
    """
    Triage an incident affecting a site or device

    Collects targeted data around the incident time window and performs
    rapid correlation analysis to identify root cause

    Args:
        client: Authenticated VManageClient instance
        site_id_or_device: Site ID or device ID affected (e.g., "denver-site-1" or "device-uuid")
        time_window_min: Time window in minutes to analyze (default 60)

    Returns:
        {
          "incident_id": str,
          "timestamp": ISO string,
          "target": str,
          "target_type": "site" | "device",
          "time_window_min": int,
          "device_health": {...},
          "control_plane_snapshot": {...},
          "data_plane_snapshot": {...},
          "events_timeline": [...],
          "alarms_in_window": [...],
          "root_cause_analysis": {
            "most_likely": str,
            "confidence": 0-100,
            "evidence": [...]
          },
          "immediate_actions": [...]
        }
    """
    logger.info(f"Starting incident triage for {site_id_or_device} (window: {time_window_min} min)")

    incident_id = f"incident-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.utcnow().isoformat() + "Z"

    try:
        collector = SDWANCollector(client)

        # Determine if target is site or device
        devices = client.get_devices()
        target_type = "unknown"
        target_devices = []

        # Check if it's a device ID
        for dev in devices:
            dev_id = dev.get("deviceId") or dev.get("uuid")
            if dev_id == site_id_or_device:
                target_type = "device"
                target_devices = [dev]
                break

        # If not found as device, try as site ID
        if target_type == "unknown":
            target_type = "site"
            target_devices = [d for d in devices
                             if d.get("site-id") == site_id_or_device or d.get("siteId") == site_id_or_device]

        if not target_devices:
            return {
                "incident_id": incident_id,
                "timestamp": timestamp,
                "error": f"Target {site_id_or_device} not found",
                "root_cause_analysis": {
                    "most_likely": "Invalid target",
                    "confidence": 100,
                    "evidence": ["Target site/device not found in fabric"]
                }
            }

        # Collect device health snapshot
        logger.debug("Collecting device health...")
        device_health = {}
        for device in target_devices:
            dev_id = device.get("deviceId") or device.get("uuid")
            status = client.get_device_status(dev_id) if dev_id else {}
            device_health[dev_id or "unknown"] = {
                "hostname": device.get("hostName") or device.get("hostname", ""),
                "reachability": status.get("status", "unknown"),
                "software_version": device.get("softwareVersion", ""),
                "device_type": device.get("deviceType", ""),
                "last_updated": status.get("lastUpdated", "")
            }

        # Collect control plane for affected devices
        logger.debug("Collecting control plane snapshot...")
        control_conns = client.get_control_connections()
        device_ids = set(d.get("deviceId") or d.get("uuid") for d in target_devices if d.get("deviceId") or d.get("uuid"))
        control_plane_snapshot = [c for c in control_conns if c.get("device_id") in device_ids]

        # Collect BFD for affected devices
        logger.debug("Collecting data plane snapshot...")
        bfd_sessions = []
        for dev_id in device_ids:
            if dev_id:
                bfd_sessions.extend(client.get_bfd_sessions(device_id=dev_id))
        data_plane_snapshot = bfd_sessions

        # Collect recent events and alarms
        logger.debug("Collecting events and alarms...")
        start_time = datetime.utcnow() - timedelta(minutes=time_window_min)
        all_events = client.get_events()
        # Filter events in time window (simplified - would need proper timestamp parsing in real impl)
        events_timeline = all_events[:20]  # Last 20 events

        # Collect alarms for affected devices/site
        alarms = client.get_alarms()
        if target_type == "site":
            alarms_in_window = [a for a in alarms if a.get("site_id") == site_id_or_device or a.get("siteId") == site_id_or_device]
        else:
            alarms_in_window = [a for a in alarms if a.get("device_id") in device_ids]

        # Perform root cause analysis
        logger.debug("Performing root cause analysis...")
        root_cause = _analyze_root_cause(
            device_health, control_plane_snapshot, data_plane_snapshot,
            events_timeline, alarms_in_window, time_window_min
        )

        # Generate immediate actions
        immediate_actions = _generate_incident_actions(root_cause, device_health)

        return {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "target": site_id_or_device,
            "target_type": target_type,
            "time_window_min": time_window_min,
            "affected_devices": list(device_ids),
            "device_health": device_health,
            "control_plane_snapshot": {
                "total_connections": len(control_plane_snapshot),
                "up_connections": sum(1 for c in control_plane_snapshot if c.get("state", "").lower() == "up"),
                "down_connections": sum(1 for c in control_plane_snapshot if c.get("state", "").lower() != "up"),
                "connections": control_plane_snapshot[:10]
            },
            "data_plane_snapshot": {
                "total_sessions": len(data_plane_snapshot),
                "up_sessions": sum(1 for s in data_plane_snapshot if s.get("state", "").lower() == "up"),
                "down_sessions": sum(1 for s in data_plane_snapshot if s.get("state", "").lower() != "up"),
                "sessions": data_plane_snapshot[:10]
            },
            "events_timeline": events_timeline,
            "alarms_in_window": {
                "total": len(alarms_in_window),
                "critical": sum(1 for a in alarms_in_window if a.get("severity", "").lower() == "critical"),
                "major": sum(1 for a in alarms_in_window if a.get("severity", "").lower() == "major"),
                "alarms": alarms_in_window[:15]
            },
            "root_cause_analysis": root_cause,
            "immediate_actions": immediate_actions
        }

    except Exception as e:
        logger.error(f"Incident triage failed: {e}")
        return {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "target": site_id_or_device,
            "error": str(e),
            "root_cause_analysis": {
                "most_likely": "Analysis failed",
                "confidence": 0,
                "evidence": [str(e)]
            }
        }


def _analyze_root_cause(device_health: Dict, control_plane: List[Dict],
                        data_plane: List[Dict], events: List[Dict],
                        alarms: List[Dict], time_window_min: int) -> Dict[str, Any]:
    """
    Analyze collected data to determine root cause

    Returns most likely cause with confidence and supporting evidence
    """
    candidates = []

    # Check device reachability
    unreachable_devices = [
        dev for dev, health in device_health.items()
        if health.get("reachability", "").lower() != "reachable"
    ]
    if unreachable_devices:
        candidates.append({
            "cause": f"Device unreachability: {', '.join(unreachable_devices[:3])}",
            "confidence": 90,
            "type": "device_connectivity",
            "evidence": [f"{len(unreachable_devices)} devices unreachable from vManage"]
        })

    # Check control plane
    control_up = sum(1 for c in control_plane if c.get("state", "").lower() == "up")
    control_down = len(control_plane) - control_up
    if control_down > len(control_plane) * 0.25:
        candidates.append({
            "cause": "Control plane connectivity degradation",
            "confidence": 80 if control_down > len(control_plane) * 0.5 else 60,
            "type": "control_plane",
            "evidence": [f"{control_down}/{len(control_plane)} control connections down"]
        })

    # Check data plane
    data_up = sum(1 for s in data_plane if s.get("state", "").lower() == "up")
    data_down = len(data_plane) - data_up
    if data_down > len(data_plane) * 0.25:
        candidates.append({
            "cause": "Data plane tunnel instability",
            "confidence": 75 if data_down > len(data_plane) * 0.5 else 55,
            "type": "data_plane",
            "evidence": [f"{data_down}/{len(data_plane)} BFD sessions down"]
        })

    # Check alarm patterns
    critical_count = sum(1 for a in alarms if a.get("severity", "").lower() == "critical")
    if critical_count > 0:
        alarm_types = set(a.get("type") for a in alarms if a.get("type"))
        candidates.append({
            "cause": f"Critical alarms: {', '.join(list(alarm_types)[:3])}",
            "confidence": 70,
            "type": "active_alarms",
            "evidence": [f"{critical_count} critical alarms in {time_window_min}min window"]
        })

    # If no clear candidates, suggest generic investigation
    if not candidates:
        candidates.append({
            "cause": "Unable to determine specific root cause - manual investigation required",
            "confidence": 30,
            "type": "unknown",
            "evidence": ["No clear anomalies detected in collected data"]
        })

    # Sort by confidence and return top candidate
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    top = candidates[0]

    return {
        "most_likely": top["cause"],
        "confidence": top["confidence"],
        "type": top["type"],
        "evidence": top["evidence"],
        "alternative_causes": [
            {"cause": c["cause"], "confidence": c["confidence"]}
            for c in candidates[1:3]
        ]
    }


def _generate_incident_actions(root_cause: Dict, device_health: Dict) -> List[Dict[str, Any]]:
    """Generate immediate troubleshooting actions"""
    actions = []
    cause_type = root_cause.get("type", "")

    if cause_type == "device_connectivity":
        actions.append({
            "action": "Verify device WAN connectivity",
            "priority": "IMMEDIATE",
            "details": "Check underlay links, firewall rules, default routes"
        })
        actions.append({
            "action": "Restart vEdge management plane if needed",
            "priority": "HIGH",
            "details": "SSH to device and verify system status"
        })

    elif cause_type == "control_plane":
        actions.append({
            "action": "Verify vManage and vSmart controllers are reachable",
            "priority": "IMMEDIATE",
            "details": "Check DNS, firewall, and controller service status"
        })
        actions.append({
            "action": "Check control plane dtls-port (12346) connectivity",
            "priority": "HIGH",
            "details": "Verify no firewall blocks on UDP 12346"
        })

    elif cause_type == "data_plane":
        actions.append({
            "action": "Verify tunnel endpoints and TLOC status",
            "priority": "HIGH",
            "details": "Check TLOC advertisements and color definitions"
        })
        actions.append({
            "action": "Check for MTU mismatches and NAT issues",
            "priority": "MEDIUM",
            "details": "Review BFD output for fragmentation or keepalive issues"
        })

    elif cause_type == "active_alarms":
        actions.append({
            "action": "Address active alarms in priority order",
            "priority": "HIGH",
            "details": "Review alarm details and follow resolution steps"
        })

    return actions[:3]
