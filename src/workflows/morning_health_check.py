"""Morning health check workflow for SD-WAN daily reports"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..vmanage_client import VManageClient
from ..collector import SDWANCollector
from ..sastre_runner import SastreRunner
from ..analyzers.bfd_analyzer import BFDAnalyzer
from ..analyzers.control_analyzer import ControlPlaneAnalyzer
from ..analyzers.alarm_correlator import AlarmCorrelator
from ..analyzers.risk_scorer import RiskScorer

logger = logging.getLogger(__name__)


def run_morning_health_check(client: VManageClient, sastre: SastreRunner = None) -> Dict[str, Any]:
    """
    Run comprehensive morning health check across entire fabric

    Designed to be called once per day (typically 7-9 AM) to provide
    a daily status report for network operations

    Args:
        client: Authenticated VManageClient instance
        sastre: Optional SastreRunner for configuration management checks

    Returns:
        {
          "timestamp": ISO string,
          "status_summary": {
            "overall": "HEALTHY" | "WARNING" | "CRITICAL",
            "fabric_reachability": int (percent),
            "control_plane_health": int (percent),
            "data_plane_health": int (percent)
          },
          "controllers": {
            "total": int,
            "reachable": int,
            "vmanage_status": "UP" | "DEGRADED",
            "vsmart_count": int
          },
          "edges": {
            "total": int,
            "reachable": int,
            "unreachable": int,
            "reachability_percent": float
          },
          "bfd_health": {...},
          "control_plane": {...},
          "alarms_24h": {
            "total": int,
            "critical": int,
            "major": int,
            "minor": int,
            "top_alarms": [...]
          },
          "certificates": {
            "total": int,
            "expiring_30d": int,
            "expiring_7d": int,
            "expired": int,
            "critical_certs": [...]
          },
          "risk_score": {
            "overall": 0-100,
            "level": str,
            "top_risks": [...]
          },
          "top_actions": [
            {"action": str, "priority": "HIGH" | "MEDIUM" | "LOW", "details": str}
          ],
          "sastre_status": {...}
        }
    """
    logger.info("Starting morning health check workflow...")
    timestamp = datetime.utcnow().isoformat() + "Z"

    try:
        # Initialize collector
        collector = SDWANCollector(client)

        # Collect fabric overview
        logger.debug("Collecting fabric overview...")
        fabric = collector.collect_fabric_overview()
        devices = fabric.get("devices", [])
        reachable_count = fabric.get("reachable_count", 0)
        device_count = fabric.get("device_count", 0)

        # Collect control plane
        logger.debug("Collecting control plane health...")
        control_plane = collector.collect_control_plane_health()
        control_conns = control_plane.get("control_connections", [])
        omp_peers = control_plane.get("omp_peers", [])

        # Collect data plane
        logger.debug("Collecting data plane health...")
        data_plane = collector.collect_data_plane_health()
        bfd_sessions = data_plane.get("bfd_sessions", [])

        # Collect alarms (24 hours)
        logger.debug("Collecting alarms...")
        alarms_24h = collector.collect_alarm_summary(hours=24)
        alarms = alarms_24h.get("alarms", [])

        # Collect certificates
        logger.debug("Collecting certificate status...")
        cert_status = collector.collect_certificate_status()
        certificates = cert_status.get("certificates", [])

        # Analyze BFD
        logger.debug("Analyzing BFD sessions...")
        bfd_analysis = BFDAnalyzer.analyze_bfd_sessions(bfd_sessions)

        # Analyze control plane
        logger.debug("Analyzing control plane...")
        control_analysis = ControlPlaneAnalyzer.analyze_control_connections(control_conns)

        # Analyze alarms
        logger.debug("Correlating alarms...")
        correlator = AlarmCorrelator()
        alarm_correlation = correlator.correlate(alarms, time_window_min=1440)  # 24 hours

        # Calculate risk score
        logger.debug("Calculating risk score...")
        risk_assessment = RiskScorer.score_network(
            devices=devices,
            bfd_sessions=bfd_sessions,
            control_connections=control_conns,
            omp_peers=omp_peers,
            alarms=alarms,
            certificates=certificates
        )

        # Generate top actions
        top_actions = _generate_actions(
            control_analysis, bfd_analysis, alarm_correlation,
            cert_status, risk_assessment
        )

        # Sastre status
        sastre_status = {}
        if sastre:
            logger.debug("Checking Sastre status...")
            try:
                devices_list = sastre.list_devices()
                sastre_status = {
                    "available": devices_list.get("success", False),
                    "device_count": devices_list.get("device_count", 0),
                    "last_backup": "unknown"  # Would need to check filesystem
                }
            except Exception as e:
                logger.warning(f"Sastre check failed: {e}")
                sastre_status = {"available": False, "error": str(e)}

        # Determine overall status
        overall_status = "HEALTHY"
        if risk_assessment.get("risk_level") == "CRITICAL":
            overall_status = "CRITICAL"
        elif risk_assessment.get("risk_level") == "ELEVATED":
            overall_status = "WARNING"

        return {
            "timestamp": timestamp,
            "status_summary": {
                "overall": overall_status,
                "fabric_reachability": round((reachable_count / device_count * 100) if device_count > 0 else 0, 1),
                "control_plane_health": 100 - control_analysis.get("total_down", 0),
                "data_plane_health": bfd_analysis.get("availability_percent", 0)
            },
            "controllers": {
                "total": control_analysis.get("vsmart_count", 0) + control_analysis.get("vmanage_count", 0),
                "reachable": control_analysis.get("total_up", 0),
                "vmanage_status": "UP" if control_analysis.get("vmanage_count", 0) > 0 else "DOWN",
                "vsmart_count": control_analysis.get("vsmart_count", 0)
            },
            "edges": {
                "total": device_count,
                "reachable": reachable_count,
                "unreachable": device_count - reachable_count,
                "reachability_percent": round((reachable_count / device_count * 100) if device_count > 0 else 0, 1)
            },
            "bfd_health": {
                "total_sessions": bfd_analysis.get("total", 0),
                "up_sessions": bfd_analysis.get("up", 0),
                "down_sessions": bfd_analysis.get("down", 0),
                "flapping_sessions": bfd_analysis.get("flapping", 0),
                "availability_percent": round(bfd_analysis.get("availability_percent", 0), 1),
                "by_color": bfd_analysis.get("by_color", {}),
                "top_issues": bfd_analysis.get("top_issues", [])[:5]
            },
            "control_plane": {
                "vsmart_peers": control_analysis.get("vsmart_count", 0),
                "vmanage_connections": control_analysis.get("vmanage_count", 0),
                "dtls_connections_up": control_analysis.get("dtls_up", 0),
                "tls_connections_up": control_analysis.get("tls_up", 0),
                "total_down": control_analysis.get("total_down", 0),
                "isolated_devices": len(control_analysis.get("isolated_devices", [])),
                "partially_isolated": len(control_analysis.get("partially_isolated", []))
            },
            "alarms_24h": {
                "total": alarms_24h.get("total_count", 0),
                "critical": alarms_24h.get("critical_count", 0),
                "major": alarms_24h.get("major_count", 0),
                "minor": alarms_24h.get("minor_count", 0),
                "top_alarm_types": AlarmCorrelator.top_alarm_types(alarms, limit=5)
            },
            "certificates": {
                "total": cert_status.get("total_count", 0),
                "expiring_30d": cert_status.get("expiring_30days", 0),
                "expiring_7d": cert_status.get("expiring_7days", 0),
                "expired": cert_status.get("expired", 0),
                "critical_certs": [
                    {"cn": c.get("cn"), "days_to_expiry": c.get("days_to_expiry")}
                    for c in cert_status.get("expiring_soon", [])[:3]
                ]
            },
            "risk_score": {
                "overall": risk_assessment.get("overall_score", 0),
                "level": risk_assessment.get("risk_level", "UNKNOWN"),
                "components": risk_assessment.get("components", {}),
                "top_risks": risk_assessment.get("top_risks", [])[:3]
            },
            "top_actions": top_actions,
            "sastre_status": sastre_status
        }

    except Exception as e:
        logger.error(f"Morning health check failed: {e}")
        return {
            "timestamp": timestamp,
            "error": str(e),
            "status_summary": {
                "overall": "UNKNOWN",
                "fabric_reachability": 0,
                "control_plane_health": 0,
                "data_plane_health": 0
            }
        }


def _generate_actions(control_analysis: Dict, bfd_analysis: Dict,
                      alarm_correlation: Dict, cert_status: Dict,
                      risk_assessment: Dict) -> List[Dict[str, Any]]:
    """Generate prioritized action items from analysis"""
    actions = []

    # Control plane actions
    if control_analysis.get("isolated_devices"):
        actions.append({
            "action": f"Investigate {len(control_analysis['isolated_devices'])} isolated devices",
            "priority": "HIGH",
            "details": f"Devices: {', '.join(control_analysis['isolated_devices'][:3])}"
        })

    # BFD actions
    if bfd_analysis.get("flapping", 0) > 0:
        actions.append({
            "action": f"Troubleshoot {bfd_analysis['flapping']} flapping tunnels",
            "priority": "HIGH",
            "details": "Check MTU, NAT, and underlay link stability"
        })

    if bfd_analysis.get("down", 0) > 0:
        actions.append({
            "action": f"Restore {bfd_analysis['down']} down BFD sessions",
            "priority": "MEDIUM",
            "details": "Verify WAN link connectivity and tunnel configuration"
        })

    # Alarm actions
    critical_count = alarm_correlation.get("severity_distribution", {}).get("critical", 0)
    if critical_count > 3:
        actions.append({
            "action": f"Address {critical_count} critical alarms",
            "priority": "HIGH",
            "details": "Review alarm details and escalate if needed"
        })

    # Certificate actions
    if cert_status.get("expiring_7days", 0) > 0:
        actions.append({
            "action": f"URGENT: {cert_status['expiring_7days']} certificates expiring within 7 days",
            "priority": "HIGH",
            "details": "Plan certificate renewal immediately"
        })

    if cert_status.get("expiring_30days", 0) > 0:
        actions.append({
            "action": f"Schedule renewal of {cert_status['expiring_30days']} certificates",
            "priority": "MEDIUM",
            "details": "Certificates expiring within 30 days"
        })

    # Risk-based actions
    if risk_assessment.get("risk_level") == "CRITICAL":
        actions.append({
            "action": "Escalate to network operations center",
            "priority": "HIGH",
            "details": f"Network risk score: {risk_assessment.get('overall_score')}/100"
        })

    # If no high priority actions, add monitoring reminder
    if not any(a["priority"] == "HIGH" for a in actions):
        actions.append({
            "action": "Continue regular monitoring",
            "priority": "LOW",
            "details": "Network is operating normally"
        })

    return actions[:5]  # Top 5 actions
