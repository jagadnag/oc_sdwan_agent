"""Network risk scoring for SD-WAN fabric"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculates network risk score (0-100) based on multiple factors"""

    # Weight distribution for risk scoring
    WEIGHT_CONTROL_PLANE = 0.25  # 25%
    WEIGHT_DATA_PLANE = 0.30     # 30%
    WEIGHT_ALARMS = 0.30         # 30%
    WEIGHT_CERTIFICATES = 0.15   # 15%

    @staticmethod
    def score_network(devices: List[Dict],
                      bfd_sessions: List[Dict],
                      control_connections: List[Dict],
                      omp_peers: List[Dict],
                      alarms: List[Dict],
                      certificates: List[Dict]) -> Dict[str, Any]:
        """
        Calculate overall network risk score (0-100) with component breakdown

        Higher score = higher risk

        Args:
            devices: List of device dictionaries
            bfd_sessions: List of BFD session dictionaries
            control_connections: List of control connection dictionaries
            omp_peers: List of OMP peer dictionaries
            alarms: List of alarm dictionaries
            certificates: List of certificate dictionaries

        Returns:
            {
              "overall_score": 0-100,
              "risk_level": "HEALTHY" | "NOMINAL" | "ELEVATED" | "CRITICAL",
              "components": {
                "control_plane": {"score": 0-100, "details": str},
                "data_plane": {"score": 0-100, "details": str},
                "alarms": {"score": 0-100, "details": str},
                "certificates": {"score": 0-100, "details": str}
              },
              "top_risks": [{"risk": str, "score_impact": int, "severity": str}],
              "recommendation": str
            }
        """
        # Calculate component scores
        control_score = RiskScorer._score_control_plane(control_connections, omp_peers)
        data_score = RiskScorer._score_data_plane(bfd_sessions, devices)
        alarm_score = RiskScorer._score_alarms(alarms)
        cert_score = RiskScorer._score_certificates(certificates)

        # Calculate weighted overall score
        overall_score = int(
            (control_score * RiskScorer.WEIGHT_CONTROL_PLANE) +
            (data_score * RiskScorer.WEIGHT_DATA_PLANE) +
            (alarm_score * RiskScorer.WEIGHT_ALARMS) +
            (cert_score * RiskScorer.WEIGHT_CERTIFICATES)
        )

        # Determine risk level
        if overall_score <= 20:
            risk_level = "HEALTHY"
        elif overall_score <= 50:
            risk_level = "NOMINAL"
        elif overall_score <= 80:
            risk_level = "ELEVATED"
        else:
            risk_level = "CRITICAL"

        # Identify top risks
        top_risks = RiskScorer._identify_top_risks(
            control_score, data_score, alarm_score, cert_score,
            control_connections, bfd_sessions, alarms, certificates
        )

        # Generate recommendation
        recommendation = RiskScorer._generate_recommendation(risk_level, top_risks)

        return {
            "overall_score": min(100, overall_score),
            "risk_level": risk_level,
            "components": {
                "control_plane": {
                    "score": control_score,
                    "weight": int(RiskScorer.WEIGHT_CONTROL_PLANE * 100),
                    "details": f"Control connections and OMP peer health"
                },
                "data_plane": {
                    "score": data_score,
                    "weight": int(RiskScorer.WEIGHT_DATA_PLANE * 100),
                    "details": f"BFD session health and tunnel stability"
                },
                "alarms": {
                    "score": alarm_score,
                    "weight": int(RiskScorer.WEIGHT_ALARMS * 100),
                    "details": f"Active alarm severity and distribution"
                },
                "certificates": {
                    "score": cert_score,
                    "weight": int(RiskScorer.WEIGHT_CERTIFICATES * 100),
                    "details": f"Certificate expiry and validity"
                }
            },
            "top_risks": top_risks[:5],
            "recommendation": recommendation
        }

    @staticmethod
    def _score_control_plane(connections: List[Dict], peers: List[Dict]) -> int:
        """Score control plane (0-100, higher = more risk)"""
        if not connections and not peers:
            return 50  # Unknown = moderate risk

        score = 0

        # Analyze connections
        if connections:
            total = len(connections)
            up = sum(1 for c in connections if c.get("state", "").lower() == "up")
            availability = (up / total * 100) if total > 0 else 0

            if availability < 50:
                score += 80
            elif availability < 75:
                score += 50
            elif availability < 90:
                score += 20
            else:
                score += 5

            # Check for asymmetry
            devices = {}
            for conn in connections:
                dev = conn.get("device_id")
                if dev not in devices:
                    devices[dev] = 0
                if conn.get("state", "").lower() == "up":
                    devices[dev] += 1

            if devices:
                max_conn = max(devices.values())
                min_conn = min(devices.values())
                if max_conn - min_conn > 1:
                    score += 15

        # Analyze OMP peers
        if peers:
            total = len(peers)
            established = sum(1 for p in peers if p.get("state", "").lower() in ["established", "up"])
            peer_health = (established / total * 100) if total > 0 else 0

            if peer_health < 50:
                score += 80
            elif peer_health < 75:
                score += 40
            elif peer_health < 90:
                score += 15
            else:
                score += 5

        return min(100, score)

    @staticmethod
    def _score_data_plane(bfd_sessions: List[Dict], devices: List[Dict]) -> int:
        """Score data plane (0-100, higher = more risk)"""
        score = 0

        if not bfd_sessions:
            # No BFD data = moderate risk if devices exist
            return 40 if devices else 0

        total = len(bfd_sessions)
        up = sum(1 for s in bfd_sessions if s.get("state", "").lower() == "up")
        down = total - up

        # BFD availability
        availability = (up / total * 100) if total > 0 else 0
        if availability < 50:
            score += 80
        elif availability < 75:
            score += 50
        elif availability < 90:
            score += 20
        else:
            score += 5

        # Flapping sessions
        flapping_count = sum(1 for s in bfd_sessions if (s.get("state_changes", 0) or 0) > 3)
        if flapping_count > 0:
            flap_pct = (flapping_count / total) * 100
            score += min(25, flap_pct * 2)

        # Performance metrics
        high_loss = sum(1 for s in bfd_sessions if float(s.get("loss_percentage", 0) or 0) > 5)
        if high_loss > 0:
            score += min(15, high_loss * 3)

        high_latency = sum(1 for s in bfd_sessions if float(s.get("latency", 0) or 0) > 500)
        if high_latency > 0:
            score += min(10, high_latency * 2)

        return min(100, score)

    @staticmethod
    def _score_alarms(alarms: List[Dict]) -> int:
        """Score alarms (0-100, higher = more risk)"""
        if not alarms:
            return 0

        score = 0

        critical = sum(1 for a in alarms if a.get("severity", "").lower() == "critical")
        major = sum(1 for a in alarms if a.get("severity", "").lower() == "major")
        minor = sum(1 for a in alarms if a.get("severity", "").lower() == "minor")

        # Critical alarms: 5 points each, max 50
        score += min(50, critical * 5)

        # Major alarms: 2 points each, max 30
        score += min(30, major * 2)

        # Minor alarms: 0.5 points each, max 15
        score += min(15, minor * 0.5)

        # Alarm trend
        total_alarms = len(alarms)
        if total_alarms > 50:
            score += 10
        elif total_alarms > 100:
            score += 20

        return min(100, int(score))

    @staticmethod
    def _score_certificates(certificates: List[Dict]) -> int:
        """Score certificates (0-100, higher = more risk)"""
        from datetime import datetime

        if not certificates:
            return 50  # No cert data = moderate risk

        score = 0
        now = datetime.utcnow()

        for cert in certificates:
            try:
                expiry_str = cert.get("expiry_date") or cert.get("not_after", "")
                if not expiry_str:
                    continue

                expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                days_to_expiry = (expiry - now).days

                if days_to_expiry < 0:
                    score += 100  # Certificate already expired
                elif days_to_expiry < 7:
                    score += 80
                elif days_to_expiry < 30:
                    score += 50
                elif days_to_expiry < 90:
                    score += 20
            except:
                pass

        # Average score across certificates
        if certificates:
            score = score // len(certificates)

        return min(100, score)

    @staticmethod
    def _identify_top_risks(control_score: int, data_score: int, alarm_score: int, cert_score: int,
                            connections: List[Dict], bfd_sessions: List[Dict],
                            alarms: List[Dict], certificates: List[Dict]) -> List[Dict[str, Any]]:
        """Identify top contributing risks"""
        risks = []

        # Control plane risk
        if control_score > 50:
            down_count = sum(1 for c in connections if c.get("state", "").lower() != "up")
            risks.append({
                "risk": f"Control plane connectivity at {100-control_score}% health ({down_count} connections down)",
                "score_impact": control_score,
                "severity": "CRITICAL" if control_score > 80 else "HIGH"
            })

        # Data plane risk
        if data_score > 50:
            down_bfd = sum(1 for b in bfd_sessions if b.get("state", "").lower() != "up")
            risks.append({
                "risk": f"Data plane tunnel health at {100-data_score}% ({down_bfd} BFD sessions down)",
                "score_impact": data_score,
                "severity": "CRITICAL" if data_score > 80 else "HIGH"
            })

        # Alarm risk
        if alarm_score > 40:
            critical_alarms = sum(1 for a in alarms if a.get("severity", "").lower() == "critical")
            risks.append({
                "risk": f"{critical_alarms} critical alarms active",
                "score_impact": alarm_score,
                "severity": "CRITICAL" if critical_alarms > 3 else "HIGH"
            })

        # Certificate risk
        if cert_score > 40:
            from datetime import datetime
            now = datetime.utcnow()
            expiring = 0
            for cert in certificates:
                try:
                    expiry_str = cert.get("expiry_date") or cert.get("not_after", "")
                    if expiry_str:
                        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                        if (expiry - now).days < 30:
                            expiring += 1
                except:
                    pass
            if expiring > 0:
                risks.append({
                    "risk": f"{expiring} certificates expiring within 30 days",
                    "score_impact": cert_score,
                    "severity": "MEDIUM"
                })

        return sorted(risks, key=lambda x: x["score_impact"], reverse=True)

    @staticmethod
    def _generate_recommendation(risk_level: str, top_risks: List[Dict]) -> str:
        """Generate recommendation based on risk level"""
        if risk_level == "HEALTHY":
            return "Network is operating normally. Continue regular monitoring."
        elif risk_level == "NOMINAL":
            return "Network health is stable. Monitor for any trend changes."
        elif risk_level == "ELEVATED":
            msg = "Network requires attention. "
            if top_risks:
                msg += f"Primary concern: {top_risks[0]['risk']}"
            return msg
        else:  # CRITICAL
            msg = "CRITICAL: Immediate action required. "
            if top_risks:
                msg += f"Top priority: {top_risks[0]['risk']}"
            return msg
