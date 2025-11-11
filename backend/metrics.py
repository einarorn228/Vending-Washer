"""Lightweight in-process metrics storage for diagnostics and reporting."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict, Iterable, Tuple

_lock = threading.Lock()
_counters = defaultdict(int)
_gauges = defaultdict(float)
_histo = {}

_WINDOW_SEC = 3600
_STEP = 5
_START_TIME = time.time()


def _key(name: str, labels: Dict[str, object] | None) -> Tuple[str, Tuple[Tuple[str, object], ...]]:
    if not labels:
        return name, tuple()
    return name, tuple(sorted(labels.items()))


def inc(name: str, amt: int = 1, **labels: object) -> None:
    with _lock:
        _counters[_key(name, labels)] += amt


def set_gauge(name: str, value: float, **labels: object) -> None:
    with _lock:
        _gauges[_key(name, labels)] = float(value)


def observe_ms(name: str, ms: int, **labels: object) -> None:
    k = _key(name, labels)
    now = time.time()
    value = int(ms)
    with _lock:
        dq = _histo.setdefault(k, deque())
        dq.append((now, value))
        cutoff = now - _WINDOW_SEC
        while dq and dq[0][0] < cutoff:
            dq.popleft()


def _percentile(values: Iterable[int], percentile: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = max(int(percentile * len(ordered)) - 1, 0)
    return ordered[index]


def snapshot():
    with _lock:
        counters = {(name, labels): value for (name, labels), value in _counters.items()}
        gauges = {(name, labels): value for (name, labels), value in _gauges.items()}
        histo_payload = {}
        for (name, labels), dq in _histo.items():
            values = [ms for _, ms in dq]
            if not values:
                histo_payload[(name, labels)] = {}
                continue
            histo_payload[(name, labels)] = {
                "count": len(values),
                "avg_ms": sum(values) / len(values),
                "p95_ms": _percentile(values, 0.95),
                "p99_ms": _percentile(values, 0.99),
                "max_ms": max(values),
            }

        uptime = time.time() - _START_TIME
        gauges[("uptime_seconds_total", tuple())] = uptime

        total_scans = 0
        rejected_scans = 0
        for (metric, labels), value in counters.items():
            if metric != "scan_total":
                continue
            total_scans += value
            label_dict = dict(labels)
            if label_dict.get("outcome") not in {"accepted", "success"}:
                rejected_scans += value
        if total_scans:
            gauges[("code_fail_rate", tuple())] = rejected_scans / total_scans

        return counters, gauges, histo_payload


__all__ = ["inc", "set_gauge", "observe_ms", "snapshot"]
