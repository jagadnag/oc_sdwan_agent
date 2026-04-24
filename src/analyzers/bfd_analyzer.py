"""BFD session health analysis for SD-WAN data plane"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BFDAnalyzer:
    """Analyzes BFD (Bidirectional Forwarding Detection) session health"""

    @staticmethod
    def analyze_bfd_sessions(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze BFD sessions for health metrics and anomalies

        Returns comprehensive health analysis with per-color breakdown

        Args:
            sessions: List of BFD session dictionaries from vManage API

        Returns:
            {
              "total": int,
              "up": int,
              "down": int,
              "flapping": int,
              "by_color": {
                "color_name": {"up": int, "down": int, "flapping": int, "health_score": 0-100}
              },
              "recommendations": ["action 1", "action 2"],
              "top_issues": [{"device": str, "color": str, "issue": str}]
            }
        """
        if not sessions:
            return {
                "total": 0,
                "up": 0,
                "down": 0,
                "flapping": 0,
                "by_color": {},
                "recommendations": ["No BFD sessions found - verify device connectivity"],
                "top_issues": []
            }

        total = len(sessions)
        up_count = 0
        down_count = 0
        flapping_count = 0
        by_color = {}
        issues = []

        for session in sessions:
            state = session.get("state", "").lower()
            color = session.get("color", "unknown")
            device_id = session.get("device_id", "unknown")
            src_ip = session.get("src_ip") or session.get("local_ip", "")
            dst_ip = session.get("dst_ip") or session.get("remote_ip", "")

            # Initialize color tracking
            if color not in by_color:
                by_color[color] = {
                    "up": 0,
                    "down": 0,
                    "flapping": 0,
                    "sessions": []
                }

            by_color[color]["sessions"].append(session)

            # Count session states
            if state == "up":
                up_count += 1
                by_color[color]["up"] += 1
            else:
                down_count += 1
                by_color[color]["down"] += 1

            # Detect flapping: state changes > 3 or high variance in uptime
            state_changes = session.get("state_changes", 0)
            if state_changes and state_changes > 3:
                flapping_count += 1
                by_color[color]["flapping"] += 1
                issues.append({
                    "device": device_id,
                    "color": color,
                    "issue": f"Flapping tunnel ({state_changes} state changes) {src_ip} -> {dst_ip}",
                    "severity": "high"
                })

            # High packet loss
            loss_pct = float(session.get("loss_percentage", 0) or 0)
            if loss_pct > 5:
                issues.append({
                    "device": device_id,
                    "color": color,
                    "issue": f"High packet loss ({loss_pct}%) {src_ip} -> {dst_ip}",
                    "severity": "medium"
                })

            # High latency
            latency_ms = float(session.get("latency", 0) or 0)
            if latency_ms > 500:
                issues.append({
                    "device": device_id,
                    "color": color,
                    "issue": f"High latency ({latency_ms}ms) {src_ip} -> {dst_ip}",
                    "severity": "medium"
                })

            # High jitter
            jitter_ms = float(session.get("jitter", 0) or 0)
            if jitter_ms > 100:
                issues.append({
                    "device": device_id,
                    "color": color,
                    "issue": f"High jitter ({jitter_ms}ms) {src_ip} -> {dst_ip}",
                    "severity": "low"
                })

        # Calculate per-color health scores
        for color, data in by_color.items():
            sessions_count = len(data["sessions"])
            if sessions_count > 0:
                health = (data["up"] / sessions_count) * 100
                data["health_score"] = int(health)
            else:
                data["health_score"] = 0
            # Remove sessions list from output
            del data["sessions"]

        # Generate recommendations
        recommendations = []
        if down_count > 0:
            pct = (down_count / total) * 100
            if pct > 50:
                recommendations.append(f"CRITICAL: {pct:.1f}% of BFD sessions are down - check underlay connectivity")
            else:
                recommendations.append(f"Investigate {down_count} down BFD sessions - verify WAN link status")

        if flapping_count > 0:
            recommendations.append(f"Troubleshoot {flapping_count} flapping tunnels - common causes: MTU issues, underlay instability, NAT")

        if len(issues) > 0:
            high_severity = sum(1 for i in issues if i["severity"] == "high")
            if high_severity > 3:
                recommendations.append("Multiple high-severity BFD issues detected - consider escalating to network operations")

        # Check color distribution
        bad_colors = [c for c, d in by_color.items() if d.get("health_score", 0) < 50]
        if bad_colors:
            recommendations.append(f"Colors with poor health: {', '.join(bad_colors)} - verify path engineering")

        if not recommendations:
            recommendations.append("BFD health is nominal")

        # Sort issues by severity
        issues.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))

        return {
            "total": total,
            "up": up_count,
            "down": down_count,
            "flapping": flapping_count,
            "availability_percent": (up_count / total * 100) if total > 0 else 0,
            "by_color": by_color,
            "recommendations": recommendations,
            "top_issues": issues[:10]
        }

    @staticmethod
    def detect_tunnel_degradation(sessions: List[Dict[str, Any]],
                                  loss_threshold: float = 5.0,
                                  latency_threshold: float = 500.0) -> Dict[str, Any]:
        """
        Detect degraded tunnels based on performance metrics

        Args:
            sessions: List of BFD session dictionaries
            loss_threshold: Packet loss percentage threshold (default 5%)
            latency_threshold: Latency threshold in milliseconds (default 500ms)

        Returns:
            {
              "degraded_tunnels": [...],
              "degraded_count": int,
              "by_issue": {"loss": [...], "latency": [...]}
            }
        """
        degraded = []
        by_issue = {"loss": [], "latency": [], "jitter": []}

        for session in sessions:
            issues = []
            device_id = session.get("device_id", "")
            color = session.get("color", "")
            src = session.get("src_ip") or session.get("local_ip", "")
            dst = session.get("dst_ip") or session.get("remote_ip", "")

            loss = float(session.get("loss_percentage", 0) or 0)
            latency = float(session.get("latency", 0) or 0)
            jitter = float(session.get("jitter", 0) or 0)

            if loss > loss_threshold:
                issues.append("packet_loss")
                by_issue["loss"].append({
                    "device": device_id,
                    "color": color,
                    "tunnel": f"{src} -> {dst}",
                    "loss_pct": loss
                })

            if latency > latency_threshold:
                issues.append("high_latency")
                by_issue["latency"].append({
                    "device": device_id,
                    "color": color,
                    "tunnel": f"{src} -> {dst}",
                    "latency_ms": latency
                })

            if jitter > 100:
                issues.append("high_jitter")
                by_issue["jitter"].append({
                    "device": device_id,
                    "color": color,
                    "tunnel": f"{src} -> {dst}",
                    "jitter_ms": jitter
                })

            if issues:
                degraded.append({
                    "device": device_id,
                    "color": color,
                    "tunnel": f"{src} -> {dst}",
                    "issues": issues,
                    "metrics": {
                        "loss_pct": loss,
                        "latency_ms": latency,
                        "jitter_ms": jitter
                    }
                })

        return {
            "degraded_tunnels": degraded,
            "degraded_count": len(degraded),
            "by_issue": by_issue
        }

    @staticmethod
    def color_health_summary(by_color: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Generate summary of health by color

        Args:
            by_color: Color health dictionary from analyze_bfd_sessions

        Returns:
            {
              "healthy_colors": [...],
              "degraded_colors": [...],
              "avg_health": float
            }
        """
        healthy = []
        degraded = []
        total_health = 0
        color_count = 0

        for color, data in by_color.items():
            score = data.get("health_score", 0)
            total_health += score
            color_count += 1

            if score >= 95:
                healthy.append(color)
            elif score < 80:
                degraded.append(color)

        avg = total_health / color_count if color_count > 0 else 0

        return {
            "healthy_colors": healthy,
            "degraded_colors": degraded,
            "average_health_score": int(avg),
            "total_colors": color_count
        }
