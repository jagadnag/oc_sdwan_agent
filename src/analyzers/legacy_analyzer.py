"""SD-WAN analysis functions (pure Python, no API calls)"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class SDWANAnalyzer:
    """Pure Python analysis functions for SD-WAN health assessment"""

    @staticmethod
    def analyze_bfd_health(bfd_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze BFD session health

        Args:
            bfd_data: List of BFD session dictionaries from collector

        Returns:
            {
              "up_sessions": int,
              "down_sessions": int,
              "flapping_sessions": int,
              "total_sessions": int,
              "availability_percent": float,
              "issues": [...]
            }
        """
        if not bfd_data:
            return {
                "up_sessions": 0,
                "down_sessions": 0,
                "flapping_sessions": 0,
                "total_sessions": 0,
                "availability_percent": 0,
                "issues": ["No BFD sessions found"]
            }

        up = sum(1 for s in bfd_data if s.get("state", "").lower() == "up")
        down = sum(1 for s in bfd_data if s.get("state", "").lower() != "up")
        total = len(bfd_data)

        # Detect flapping: sessions with high loss or state changes
        flapping = 0
        high_loss = 0
        high_latency = 0

        issues = []
        for session in bfd_data:
            state = session.get("state", "").lower()
            loss = float(session.get("loss_percentage", 0) or 0)
            latency = float(session.get("latency", 0) or 0)
            jitter = float(session.get("jitter", 0) or 0)

            if state != "up":
                flapping += 1
                issues.append(f"Session DOWN: {session.get('local_ip')} -> {session.get('remote_ip')}")

            if loss > 5:
                high_loss += 1
                issues.append(f"High loss ({loss}%): {session.get('local_ip')} -> {session.get('remote_ip')}")

            if latency > 500:
                high_latency += 1
                issues.append(f"High latency ({latency}ms): {session.get('local_ip')} -> {session.get('remote_ip')}")

        availability = (up / total * 100) if total > 0 else 0

        return {
            "up_sessions": up,
            "down_sessions": down,
            "flapping_sessions": flapping,
            "total_sessions": total,
            "high_loss_sessions": high_loss,
            "high_latency_sessions": high_latency,
            "availability_percent": availability,
            "issues": issues
        }

    @staticmethod
    def analyze_control_health(control_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze control plane connections health

        Args:
            control_data: List of control connection dictionaries

        Returns:
            {
              "up_connections": int,
              "down_connections": int,
              "total_connections": int,
              "isolated_devices": [...],
              "partial_isolation": [...]
            }
        """
        if not control_data:
            return {
                "up_connections": 0,
                "down_connections": 0,
                "total_connections": 0,
                "isolated_devices": [],
                "partial_isolation": []
            }

        up = sum(1 for c in control_data if c.get("state", "").lower() == "up")
        down = sum(1 for c in control_data if c.get("state", "").lower() != "up")
        total = len(control_data)

        # Find completely isolated devices (no connections up)
        device_connections = {}
        for conn in control_data:
            device = conn.get("device_id") or conn.get("deviceId")
            if device not in device_connections:
                device_connections[device] = {"up": 0, "down": 0}
            if conn.get("state", "").lower() == "up":
                device_connections[device]["up"] += 1
            else:
                device_connections[device]["down"] += 1

        isolated = []
        partial = []
        for device, counts in device_connections.items():
            if counts["up"] == 0:
                isolated.append(device)
            elif counts["down"] > 0:
                partial.append(device)

        return {
            "up_connections": up,
            "down_connections": down,
            "total_connections": total,
            "isolated_devices": isolated,
            "partial_isolation": partial
        }

    @staticmethod
    def analyze_alarm_severity(alarm_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze alarm severity distribution

        Args:
            alarm_data: List of alarm dictionaries

        Returns:
            {
              "critical_count": int,
              "major_count": int,
              "minor_count": int,
              "total_count": int,
              "critical_alarms": [...],
              "top_issues": [...]
            }
        """
        if not alarm_data:
            return {
                "critical_count": 0,
                "major_count": 0,
                "minor_count": 0,
                "total_count": 0,
                "critical_alarms": [],
                "top_issues": []
            }

        critical = [a for a in alarm_data if a.get("severity", "").lower() == "critical"]
        major = [a for a in alarm_data if a.get("severity", "").lower() == "major"]
        minor = [a for a in alarm_data if a.get("severity", "").lower() == "minor"]

        # Count by type
        alarm_types = {}
        for alarm in alarm_data:
            alarm_type = alarm.get("type", "unknown")
            alarm_types[alarm_type] = alarm_types.get(alarm_type, 0) + 1

        top_issues = sorted(alarm_types.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "critical_count": len(critical),
            "major_count": len(major),
            "minor_count": len(minor),
            "total_count": len(alarm_data),
            "critical_alarms": critical[:10],  # Top 10 critical
            "top_issues": [{"type": t, "count": c} for t, c in top_issues]
        }

    @staticmethod
    def calculate_site_risk_score(site_data: Dict[str, Any]) -> int:
        """
        Calculate numeric risk score for a site (0-100)

        Factors:
        - Control plane isolation (40 pts)
        - Data plane health (15 pts)
        - BFD flapping (10 pts)
        - Alarms (15 pts)
        - Certificates (10 pts)

        Args:
            site_data: Site health data dictionary

        Returns:
            Risk score 0-100 (0=healthy, 100=critical)
        """
        risk = 0

        # Control plane: no connections = 40 pts, partial = 20 pts
        control = site_data.get("control_plane", {})
        if control.get("down_connections", 0) > 0:
            if control.get("healthy_connections", 0) == 0:
                risk += 40
            else:
                risk += 20

        # Data plane: down sessions and flapping
        data = site_data.get("data_plane", {})
        down_sessions = data.get("down_sessions", 0)
        total_sessions = data.get("total_sessions", 1)
        if total_sessions > 0:
            down_percent = (down_sessions / total_sessions) * 100
            risk += min(15, down_percent // 10)  # Max 15 pts

        flapping = data.get("flapping_sessions", 0)
        if flapping > 0:
            risk += min(10, flapping * 2)  # Max 10 pts

        # Alarms
        alarms = site_data.get("alarms", {})
        critical_count = alarms.get("critical_count", 0)
        major_count = alarms.get("major_count", 0)
        risk += min(15, critical_count * 5 + major_count * 2)  # Max 15 pts

        # Certificates: expiring soon
        certs = site_data.get("certificates", {})
        expiring_7 = certs.get("expiring_7days", 0)
        expiring_30 = certs.get("expiring_30days", 0)
        if expiring_7 > 0:
            risk += 10
        elif expiring_30 > 0:
            risk += 3

        return min(100, risk)

    @staticmethod
    def detect_flapping(event_data: List[Dict], threshold: int = 3) -> Dict[str, Any]:
        """
        Detect flapping interfaces/tunnels from event timeline

        Flapping = state changes more than threshold in short period

        Args:
            event_data: List of events from timeline
            threshold: Number of state changes to trigger flap detection

        Returns:
            {
              "flapping_interfaces": [...],
              "flapping_tunnels": [...],
              "flap_events": [...]
            }
        """
        flapping_items = {}
        flap_events = []

        # Group events by item (interface, tunnel)
        for event in event_data:
            item_id = f"{event.get('device_id')}/{event.get('interface_name') or event.get('tunnel_id')}"
            if item_id not in flapping_items:
                flapping_items[item_id] = []
            flapping_items[item_id].append(event)

        # Detect flapping
        flapping_interfaces = []
        flapping_tunnels = []

        for item_id, events in flapping_items.items():
            if len(events) > threshold:
                # Count state changes
                state_changes = sum(1 for e in events if "state" in e.get("description", "").lower())
                if state_changes > threshold:
                    if "interface" in item_id.lower():
                        flapping_interfaces.append(item_id)
                    else:
                        flapping_tunnels.append(item_id)
                    flap_events.extend(events[:5])  # Keep first 5 events

        return {
            "flapping_interfaces": flapping_interfaces,
            "flapping_tunnels": flapping_tunnels,
            "flap_count": len(flapping_interfaces) + len(flapping_tunnels),
            "flap_events": flap_events
        }

    @staticmethod
    def check_certificate_expiry(cert_data: List[Dict], days_warning: int = 30) -> Dict[str, Any]:
        """
        Check certificate expiry and flag expiring certificates

        Args:
            cert_data: List of certificate dictionaries
            days_warning: Days before expiry to warn (default 30)

        Returns:
            {
              "total_certificates": int,
              "expiring_soon": [...],
              "expired": [...],
              "days_to_expiry": {...}
            }
        """
        if not cert_data:
            return {
                "total_certificates": 0,
                "expiring_soon": [],
                "expired": [],
                "days_to_expiry": {}
            }

        now = datetime.utcnow()
        expiring_soon = []
        expired = []
        days_to_expiry = {}

        for cert in cert_data:
            try:
                cn = cert.get("common_name") or cert.get("cn")
                expiry_str = cert.get("expiry_date") or cert.get("not_after")

                if not expiry_str:
                    continue

                # Parse expiry (format varies)
                try:
                    expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                except:
                    expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")

                delta = (expiry - now).days
                days_to_expiry[cn] = delta

                if delta < 0:
                    expired.append({"cn": cn, "expiry_date": expiry_str, "days_overdue": abs(delta)})
                elif delta < days_warning:
                    expiring_soon.append({"cn": cn, "expiry_date": expiry_str, "days_to_expiry": delta})
            except Exception as e:
                logger.debug(f"Error parsing certificate: {e}")

        return {
            "total_certificates": len(cert_data),
            "expiring_soon": expiring_soon,
            "expired": expired,
            "days_to_expiry": days_to_expiry
        }

    @staticmethod
    def compare_software_versions(device_list: List[Dict], target_version: str) -> Dict[str, Any]:
        """
        Compare device software versions against target

        Args:
            device_list: List of device dictionaries
            target_version: Target software version (e.g., "20.12.4")

        Returns:
            {
              "total_devices": int,
              "compliant": int,
              "non_compliant": int,
              "non_compliant_devices": [...],
              "compliance_percent": float
            }
        """
        if not device_list:
            return {
                "total_devices": 0,
                "compliant": 0,
                "non_compliant": 0,
                "non_compliant_devices": [],
                "compliance_percent": 0
            }

        compliant = 0
        non_compliant_devices = []

        for device in device_list:
            version = device.get("softwareVersion") or device.get("version")
            device_id = device.get("deviceId") or device.get("uuid")
            device_name = device.get("hostName") or device.get("hostname") or device_id

            if version == target_version:
                compliant += 1
            else:
                non_compliant_devices.append({
                    "device_id": device_id,
                    "device_name": device_name,
                    "current_version": version,
                    "target_version": target_version
                })

        non_compliant = len(device_list) - compliant
        compliance_percent = (compliant / len(device_list) * 100) if device_list else 0

        return {
            "total_devices": len(device_list),
            "compliant": compliant,
            "non_compliant": non_compliant,
            "non_compliant_devices": non_compliant_devices,
            "compliance_percent": compliance_percent
        }
