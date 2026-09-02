"""Read-only diagnostics used by the dev/admin panel.

These helpers exist so the dev/admin blueprint and the inline `/admin/*` routes in
`flask_server.py` share one implementation of "recent scan logs" and "metrics
snapshot" instead of each growing their own copy.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.metrics import snapshot
from backend.models.scan_log_model import ScanLog

MAX_SCAN_LOGS = 200


def normalise_labels(labels_tuple) -> Dict[str, Any]:
    """Metric label tuples are stored as pairs; render them as a plain mapping."""

    if not labels_tuple:
        return {}
    return {key: value for key, value in labels_tuple}


def recent_scan_logs(db, limit: int = 50) -> List[dict]:
    limit = max(1, min(int(limit or 50), MAX_SCAN_LOGS))
    logs = db.query(ScanLog).order_by(ScanLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "code": log.code,
            "order_id": log.order_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "result": log.result,
            "details": log.details,
        }
        for log in logs
    ]


def metrics_snapshot() -> dict:
    counters, gauges, histograms = snapshot()

    def _prepare(mapping):
        return [
            {"name": name, "labels": normalise_labels(labels), "value": value}
            for (name, labels), value in mapping.items()
        ]

    histogram_payload = []
    for (name, labels), values in histograms.items():
        entry = {"name": name, "labels": normalise_labels(labels)}
        entry.update(values)
        histogram_payload.append(entry)

    return {
        "counters": _prepare(counters),
        "gauges": _prepare(gauges),
        "histograms": histogram_payload,
    }
