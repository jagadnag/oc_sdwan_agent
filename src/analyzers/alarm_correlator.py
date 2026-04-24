"""Alarm correlation and root-cause analysis"""

import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlarmCorrelator:
    """Correlates alarms to detect patterns and root causes"""

    def __init__(self):
        """Initialize alarm correlator"""
        pass

    def correlate(self, alarms: List[Dict[str, Any]], time_window_min: int = 30) -> Dict[str, Any]:
        """
        Correlate alarms within a time window to detect patterns and root causes

        Args:
            alarms: List of alarm dictionaries from vManage
            time_window_min: Time window in minutes for correlation (default 30)

        Returns:
            {
              "total_alarms": int,
              "by_device": {device: [alarms]},
              "by_type": {alarm_type: [alarms]},
              "by_site": {site_id: [alarms]},
              "thundering_herd": bool,
              "herd_alarms": [...],
              "root_cause_candidates": [
                {"cause": str, "confidence": 0-100, "affected_count": int, "reasoning": str}
              ],
              "severity_distribution": {"critical": int, "major": int, "minor": int}
            }
        """
        if not alarms:
            return {
                "total_alarms": 0,
                "by_device": {},
                "by_type": {},
                "by_site": {},
                "thundering_herd": False,
                "herd_alarms": [],
                "root_cause_candidates": [],
                "severity_distribution": {"critical": 0, "major": 0, "minor": 0}
            }

        # Group alarms by various dimensions
        by_device = defaultdict(list)
        by_type = defaultdict(list)
        by_site = defaultdict(list)
        by_severity = defaultdict(list)

        for alarm in alarms:
            device = alarm.get("device_id") or alarm.get("uuid", "unknown")
            alarm_type = alarm.get("type", "unknown")
            site = alarm.get("site_id") or alarm.get("siteId", "unknown")
            severity = alarm.get("severity", "").lower()

            by_device[device].append(alarm)
            by_type[alarm_type].append(alarm)
            by_site[site].append(alarm)
            by_severity[severity].append(alarm)

        # Detect thundering herd pattern
        # Thundering herd = >10 alarms of same severity in same time window
        thundering_herd = False
        herd_alarms = []
        herd_severity = None

        critical_count = len(by_severity.get("critical", []))
        if critical_count > 10:
            thundering_herd = True
            herd_severity = "critical"
            herd_alarms = by_severity["critical"]
        else:
            major_count = len(by_severity.get("major", []))
            if major_count > 15:
                thundering_herd = True
                herd_severity = "major"
                herd_alarms = by_severity["major"]

        # Detect root cause candidates
        root_causes = self._detect_root_causes(
            alarms, by_device, by_type, by_site, thundering_herd
        )

        severity_dist = {
            "critical": len(by_severity.get("critical", [])),
            "major": len(by_severity.get("major", [])),
            "minor": len(by_severity.get("minor", []))
        }

        return {
            "total_alarms": len(alarms),
            "by_device": {k: len(v) for k, v in by_device.items()},
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_site": {k: len(v) for k, v in by_site.items()},
            "thundering_herd": thundering_herd,
            "herd_severity": herd_severity,
            "herd_alarm_count": len(herd_alarms),
            "root_cause_candidates": root_causes,
            "severity_distribution": severity_dist
        }

    def _detect_root_causes(self, alarms: List[Dict],
                            by_device: dict,
                            by_type: dict,
                            by_site: dict,
                            thundering_herd: bool) -> List[Dict[str, Any]]:
        """
        Detect potential root causes for alarms

        Returns top 5 root cause candidates with confidence scores
        """
        candidates = []

        # Pattern 1: Site-wide outage
        for site, site_alarms in by_site.items():
            if len(site_alarms) > 5:
                # Multiple devices at same site with issues
                affected_devices = set(a.get("device_id") for a in site_alarms if a.get("device_id"))
                if len(affected_devices) > 2:
                    confidence = min(100, 40 + len(affected_devices) * 10)
                    candidates.append({
                        "cause": f"Site-wide connectivity issue at {site}",
                        "confidence": confidence,
                        "affected_count": len(affected_devices),
                        "reasoning": f"{len(affected_devices)} devices at site {site} reporting simultaneous issues",
                        "type": "site_outage"
                    })

        # Pattern 2: Device hardware/software issue
        for device, device_alarms in by_device.items():
            alarm_types = set(a.get("type") for a in device_alarms if a.get("type"))
            if len(device_alarms) > 3:
                confidence = min(100, 30 + len(device_alarms) * 5)
                candidates.append({
                    "cause": f"Device {device} experiencing multiple failures",
                    "confidence": confidence,
                    "affected_count": 1,
                    "reasoning": f"Device reporting {len(device_alarms)} different alarm types",
                    "type": "device_failure"
                })

        # Pattern 3: Specific alarm type affecting many devices
        for alarm_type, type_alarms in by_type.items():
            if len(type_alarms) > 4:
                affected_devices = set(a.get("device_id") for a in type_alarms if a.get("device_id"))
                if len(affected_devices) > 2:
                    confidence = min(100, 50 + len(affected_devices) * 3)
                    candidates.append({
                        "cause": f"Systematic issue: {alarm_type}",
                        "confidence": confidence,
                        "affected_count": len(affected_devices),
                        "reasoning": f"{alarm_type} alarm reported by {len(affected_devices)} devices",
                        "type": "systematic_issue"
                    })

        # Pattern 4: Thundering herd
        if thundering_herd:
            candidates.append({
                "cause": "Thundering herd pattern detected - cascading failures",
                "confidence": 85,
                "affected_count": len(alarms),
                "reasoning": "Large number of alarms in short time window - likely cascading from single root cause",
                "type": "cascading_failure"
            })

        # Pattern 5: Control plane issues
        control_alarms = [a for a in alarms if "control" in a.get("type", "").lower() or
                          "omp" in a.get("type", "").lower()]
        if len(control_alarms) > 3:
            candidates.append({
                "cause": "Control plane connectivity degradation",
                "confidence": 70,
                "affected_count": len(set(a.get("device_id") for a in control_alarms)),
                "reasoning": f"Multiple control/OMP related alarms ({len(control_alarms)} total)",
                "type": "control_plane"
            })

        # Sort by confidence and return top 5
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates[:5]

    @staticmethod
    def group_by_severity(alarms: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group alarms by severity level

        Args:
            alarms: List of alarm dictionaries

        Returns:
            {
              "critical": [...],
              "major": [...],
              "minor": [...],
              "info": [...]
            }
        """
        grouped = {
            "critical": [],
            "major": [],
            "minor": [],
            "info": []
        }

        for alarm in alarms:
            severity = alarm.get("severity", "info").lower()
            if severity in grouped:
                grouped[severity].append(alarm)
            else:
                grouped["info"].append(alarm)

        return grouped

    @staticmethod
    def top_alarm_types(alarms: List[Dict], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top alarm types by frequency

        Args:
            alarms: List of alarm dictionaries
            limit: Number of top types to return

        Returns:
            [{"type": str, "count": int, "percent": float}]
        """
        type_counts = defaultdict(int)

        for alarm in alarms:
            alarm_type = alarm.get("type", "unknown")
            type_counts[alarm_type] += 1

        total = len(alarms)
        top_types = sorted(
            [{"type": t, "count": c, "percent": round(c / total * 100, 1)}
             for t, c in type_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        return top_types[:limit]

    @staticmethod
    def timeline_analysis(alarms: List[Dict], bucket_minutes: int = 5) -> Dict[str, Any]:
        """
        Analyze alarm timeline to detect sudden spikes

        Args:
            alarms: List of alarm dictionaries with timestamps
            bucket_minutes: Time bucket size in minutes

        Returns:
            {
              "timeline": [{"bucket": str, "alarm_count": int, "spike": bool}],
              "spike_detected": bool,
              "peak_time": str
            }
        """
        if not alarms:
            return {
                "timeline": [],
                "spike_detected": False,
                "peak_time": None
            }

        # Group alarms by time bucket
        timeline = defaultdict(int)
        peak_count = 0
        peak_time = None

        for alarm in alarms:
            # Parse timestamp (format varies)
            ts_str = alarm.get("timestamp") or alarm.get("entry_time", "")
            if not ts_str:
                continue

            try:
                # Try parsing ISO format
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                # Round down to bucket
                bucket_dt = ts.replace(minute=(ts.minute // bucket_minutes) * bucket_minutes, second=0, microsecond=0)
                bucket_str = bucket_dt.isoformat()
                timeline[bucket_str] += 1

                if timeline[bucket_str] > peak_count:
                    peak_count = timeline[bucket_str]
                    peak_time = bucket_str
            except:
                pass

        # Detect spikes (bucket with >2x average)
        avg_count = len(alarms) / len(timeline) if timeline else 0
        spike_threshold = avg_count * 2

        timeline_list = [
            {
                "bucket": bucket,
                "alarm_count": count,
                "spike": count > spike_threshold
            }
            for bucket, count in sorted(timeline.items())
        ]

        spike_detected = any(item["spike"] for item in timeline_list)

        return {
            "timeline": timeline_list[-20:],  # Last 20 buckets
            "spike_detected": spike_detected,
            "peak_time": peak_time,
            "peak_alarm_count": peak_count,
            "average_per_bucket": round(avg_count, 1)
        }
