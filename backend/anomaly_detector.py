"""
Pure Python Anomaly Detection Layer — Dependency-free statistical scoring for security logs.
"""

import csv
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalous IPs using statistical rule-based scoring on behavioural features."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self._contamination = contamination
        self._random_state = random_state
        self._last_summary: Dict = {"anomalous_count": 0, "anomalous_ips": []}

    def score_file(self, csv_path: str) -> Dict:
        """
        Reads log CSV directly, computes per-IP behavioural features,
        and flags anomalous IPs based on risk scoring thresholds.
        """
        try:
            ip_data: Dict[str, List[Dict]] = {}
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get("ip_address")
                    if ip:
                        if ip not in ip_data:
                            ip_data[ip] = []
                        ip_data[ip].append(row)
        except Exception as e:
            logger.error(f"Error reading CSV file in AnomalyDetector: {e}")
            return self._last_summary

        # Define failure and error statuses
        fail_statuses = {"Failed_Login", "failed_login"}
        error_statuses = {"404_Not_Found", "500_Server_Error", "403_Forbidden"}

        ip_features: Dict[str, Dict] = {}
        for ip, rows in ip_data.items():
            # Parse timestamps to calculate time span
            timestamps = []
            for r in rows:
                ts_str = r.get("timestamp")
                if ts_str:
                    try:
                        # try parsing standard ISO formats
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        timestamps.append(ts)
                    except ValueError:
                        pass
            
            if timestamps:
                ts_min = min(timestamps)
                ts_max = max(timestamps)
                time_span_seconds = (ts_max - ts_min).total_seconds()
            else:
                time_span_seconds = 0.0

            # Calculate 5-minute windows
            n_windows = max(1.0, time_span_seconds / 300.0)

            failed_count = sum(1 for r in rows if r.get("status") in fail_statuses)
            unique_endpoints = len(set(r.get("endpoint") for r in rows if r.get("endpoint")))
            error_count = sum(1 for r in rows if r.get("status") in (error_statuses | fail_statuses))
            total = len(rows)

            error_rate = error_count / total if total > 0 else 0.0
            request_velocity = total / n_windows

            ip_features[ip] = {
                "failed_count": failed_count,
                "unique_endpoints": unique_endpoints,
                "error_rate": error_rate,
                "request_velocity": request_velocity,
                "total": total
            }

        anomalous_ips = []
        for ip, feat in ip_features.items():
            score = 0
            # Condition 1: High failed login attempts (Brute force pattern)
            if feat["failed_count"] > 5:
                score += 2
            
            # Condition 2: Volumetric traffic (DDoS / flooding pattern)
            if feat["request_velocity"] > 15:
                score += 2

            # Condition 3: High error rates (Probing / fuzzing / vulnerability scanning)
            if feat["error_rate"] > 0.4 and feat["total"] > 3:
                score += 2

            # Condition 4: Directory traversal / path scanning
            if feat["unique_endpoints"] > 8 and feat["error_rate"] > 0.2:
                score += 1

            # Flag as anomalous if score threshold is reached
            if score >= 2:
                anomalous_ips.append(ip)

        self._last_summary = {
            "anomalous_count": len(anomalous_ips),
            "anomalous_ips": anomalous_ips,
        }
        return self._last_summary

    def get_summary(self) -> Dict:
        """Return count and list of anomalous IPs from the last scoring run."""
        return self._last_summary
