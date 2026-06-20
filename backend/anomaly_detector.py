"""
ML Anomaly Detection Layer — IsolationForest-based anomaly scoring for security logs.
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detect anomalous IPs using IsolationForest on per-IP behavioural features."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self._contamination = contamination
        self._random_state = random_state
        self._model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
        )
        self._last_summary: Dict = {"anomalous_count": 0, "anomalous_ips": []}

    def score_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute per-IP features over a rolling 5-minute window, fit IsolationForest,
        and return the dataframe augmented with anomaly_score and anomaly_label columns.
        """
        if df.empty:
            df["anomaly_score"] = pd.Series(dtype=int)
            df["anomaly_label"] = pd.Series(dtype=str)
            return df

        df = df.copy()

        # Ensure timestamp is datetime
        if "timestamp" in df.columns:
            df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
        else:
            df["_ts"] = pd.Timestamp.now()

        # Define failure and error statuses
        fail_statuses = {"Failed_Login", "failed_login"}
        error_statuses = {"404_Not_Found", "500_Server_Error", "403_Forbidden"}

        # Compute per-IP features using a 5-minute rolling window
        # Group by IP first, then compute window-based features
        ip_features: Dict[str, Dict] = {}

        for ip, group in df.groupby("ip_address"):
            group = group.sort_values("_ts")
            ts_min = group["_ts"].min()
            ts_max = group["_ts"].max()

            # Use 5-minute windows; if total span < 5 min, treat as one window
            window = pd.Timedelta(minutes=5)
            total_span = ts_max - ts_min
            n_windows = max(1, int(np.ceil(total_span / window))) if pd.notna(total_span) else 1

            failed_count = group["status"].isin(fail_statuses).sum()
            unique_endpoints = group["endpoint"].nunique()
            error_count = group["status"].isin(error_statuses | fail_statuses).sum()
            total = len(group)
            error_rate = error_count / total if total > 0 else 0.0
            request_velocity = total / n_windows

            ip_features[ip] = {
                "failed_count": failed_count,
                "unique_endpoints": unique_endpoints,
                "error_rate": error_rate,
                "request_velocity": request_velocity,
            }

        features_df = pd.DataFrame.from_dict(ip_features, orient="index")

        if len(features_df) < 2:
            # Not enough data for IsolationForest — mark everything normal
            df["anomaly_score"] = 1
            df["anomaly_label"] = "NORMAL"
            df.drop(columns=["_ts"], inplace=True)
            self._last_summary = {"anomalous_count": 0, "anomalous_ips": []}
            return df

        # Fit and predict
        feature_cols = ["failed_count", "unique_endpoints", "error_rate", "request_velocity"]
        X = features_df[feature_cols].values
        predictions = self._model.fit_predict(X)

        features_df["anomaly_score"] = predictions
        features_df["anomaly_label"] = [
            "ANOMALOUS" if p == -1 else "NORMAL" for p in predictions
        ]

        # Map back to original df rows
        score_map = features_df["anomaly_score"].to_dict()
        label_map = features_df["anomaly_label"].to_dict()

        df["anomaly_score"] = df["ip_address"].map(score_map).fillna(1).astype(int)
        df["anomaly_label"] = df["ip_address"].map(label_map).fillna("NORMAL")

        # Update summary
        anomalous_ips = features_df[features_df["anomaly_label"] == "ANOMALOUS"].index.tolist()
        self._last_summary = {
            "anomalous_count": len(anomalous_ips),
            "anomalous_ips": anomalous_ips,
        }

        df.drop(columns=["_ts"], inplace=True)
        return df

    def get_summary(self) -> Dict:
        """Return count and list of anomalous IPs from the last scoring run."""
        return self._last_summary
