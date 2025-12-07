"""Telemetry polling and in-memory machine state tracking."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import requests
from sqlalchemy.orm import joinedload

from backend.metrics import set_gauge
from backend.models import Session
from backend.models.device_model import Device
from backend.models.machine_model import Machine
from backend.utils.logger import get_error_logger, get_event_logger

logger = logging.getLogger(__name__)
events_logger = get_event_logger()
error_logger = get_error_logger()


RUNSTATE_AVAILABLE = "available"
RUNSTATE_IN_USE = "in_use"
RUNSTATE_OFFLINE = "offline"


@dataclass
class DeviceInfo:
    id: int
    name: str
    role: str
    model: Optional[str]
    ip: str
    relay_channel: Optional[int]
    input_channel: Optional[int]
    metric_source: Optional[str]


@dataclass
class MachineConfigInfo:
    on_threshold: int
    off_threshold: int
    on_confirm_ms: int
    off_confirm_ms: int
    poll_interval_ms: int


@dataclass
class MachineRuntime:
    db_id: int
    slug: str
    ui_name: str
    uni_device: DeviceInfo
    config: MachineConfigInfo
    i4_device_id: Optional[int]
    i4_button_index: Optional[int]
    is_enabled: bool
    run_state: str = RUNSTATE_AVAILABLE
    available: bool = True
    pending_start: bool = False
    last_value: Optional[float] = None
    last_read_ts: Optional[float] = None
    above_since: Optional[float] = None
    below_since: Optional[float] = None
    next_poll_ts: float = field(default_factory=lambda: 0.0)


@dataclass
class MachinePollContext:
    slug: str
    uni_device: DeviceInfo
    config: MachineConfigInfo


class MachineStateStore:
    """Singleton managing the in-memory state for machines."""

    _instance: Optional["MachineStateStore"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._machines: Dict[str, MachineRuntime] = {}
        self._devices_by_role: Dict[str, DeviceInfo] = {}
        self._button_to_machine: Dict[int, str] = {}
        self._lock = threading.Lock()
        self._listeners: Dict[str, List[Callable[[str], None]]] = {
            "runstate_started": [],
            "runstate_stopped": [],
            "device_offline": [],
        }

    @classmethod
    def instance(cls) -> "MachineStateStore":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # ----- Definition management -----
    def update_definitions(
        self,
        machines: Dict[str, MachineRuntime],
        devices_by_role: Dict[str, DeviceInfo],
    ) -> None:
        now = time.monotonic()
        with self._lock:
            to_remove = set(self._machines.keys()) - set(machines.keys())
            for slug in to_remove:
                self._machines.pop(slug, None)

            for slug, runtime in machines.items():
                existing = self._machines.get(slug)
                if existing:
                    runtime.run_state = existing.run_state
                    runtime.available = existing.available
                    runtime.pending_start = existing.pending_start
                    runtime.last_value = existing.last_value
                    runtime.last_read_ts = existing.last_read_ts
                    runtime.above_since = existing.above_since
                    runtime.below_since = existing.below_since
                    runtime.next_poll_ts = max(existing.next_poll_ts, now)
                else:
                    runtime.available = runtime.run_state == RUNSTATE_AVAILABLE
                    runtime.next_poll_ts = now
                self._machines[slug] = runtime

            self._devices_by_role = devices_by_role
            self._button_to_machine = {
                runtime.i4_button_index: slug
                for slug, runtime in self._machines.items()
                if runtime.i4_button_index is not None
            }

    # ----- Listener management -----
    def add_listener(self, event: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            callbacks = self._listeners.get(event)
            if callbacks is None:
                raise ValueError(f"Unsupported event '{event}'")
            callbacks.append(callback)

    def _emit(self, event: str, slug: str) -> None:
        callbacks = []
        with self._lock:
            callbacks = list(self._listeners.get(event, []))
        for cb in callbacks:
            try:
                cb(slug)
            except Exception:  # pragma: no cover - listener errors shouldn't crash
                error_logger.exception(
                    "Listener error", extra={"event": event, "machine": slug}
                )

    # ----- Query helpers -----
    def get_snapshot(self) -> List[Dict[str, object]]:
        with self._lock:
            return [
                {
                    "id": runtime.slug,
                    "name": runtime.ui_name,
                    "available": runtime.available,
                }
                for runtime in self._machines.values()
                if runtime.is_enabled
            ]

    def get_machine(self, slug: str) -> Optional[MachineRuntime]:
        with self._lock:
            runtime = self._machines.get(slug)
            if runtime is None:
                return None
            return MachineRuntime(**runtime.__dict__)

    def mark_pending_start(self, slug: str) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            runtime.pending_start = True
            runtime.available = False

    def clear_pending_start(self, slug: str) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            runtime.pending_start = False
            runtime.available = runtime.run_state == RUNSTATE_AVAILABLE

    def set_run_state(self, slug: str, new_state: str) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            runtime.run_state = new_state
            runtime.available = new_state == RUNSTATE_AVAILABLE and not runtime.pending_start
            set_gauge("machine_available", 1 if runtime.available else 0, machine=slug)

    def update_measurement(
        self,
        slug: str,
        value: Optional[float],
        success: bool,
        timestamp: float,
    ) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            runtime.last_value = value if success else None
            runtime.last_read_ts = timestamp
            if not success:
                runtime.above_since = None
                runtime.below_since = None

    def get_poll_contexts(self, now: float) -> List[MachinePollContext]:
        contexts: List[MachinePollContext] = []
        with self._lock:
            for runtime in self._machines.values():
                if not runtime.is_enabled:
                    continue
                if runtime.uni_device.metric_source in (None, "none"):
                    continue
                if runtime.next_poll_ts > now:
                    continue
                runtime.next_poll_ts = now + max(runtime.config.poll_interval_ms, 500) / 1000.0
                contexts.append(
                    MachinePollContext(
                        slug=runtime.slug,
                        uni_device=runtime.uni_device,
                        config=runtime.config,
                    )
                )
        return contexts

    def get_device_by_role(self, role: str) -> Optional[DeviceInfo]:
        with self._lock:
            return self._devices_by_role.get(role)

    def resolve_button(self, button_index: int) -> Optional[str]:
        with self._lock:
            return self._button_to_machine.get(button_index)

    def list_slugs(self) -> List[str]:
        with self._lock:
            return list(self._machines.keys())

    def set_transition_markers(
        self, slug: str, above_since: Optional[float], below_since: Optional[float]
    ) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            runtime.above_since = above_since
            runtime.below_since = below_since

    def mark_offline(self, slug: str) -> None:
        with self._lock:
            runtime = self._machines.get(slug)
            if not runtime:
                return
            was_offline = runtime.run_state == RUNSTATE_OFFLINE
            runtime.run_state = RUNSTATE_OFFLINE
            runtime.available = False
            runtime.pending_start = False
        if not was_offline:
            events_logger.warning("DEVICE_OFFLINE", extra={"machine": slug})
            self._emit("device_offline", slug)
            set_gauge("machine_available", 0, machine=slug)

    def transition_to_in_use(self, slug: str) -> None:
        self.set_run_state(slug, RUNSTATE_IN_USE)
        events_logger.info("RUNSTATE_STARTED", extra={"machine": slug})
        self._emit("runstate_started", slug)

    def transition_to_available(self, slug: str) -> None:
        previous_state = None
        with self._lock:
            runtime = self._machines.get(slug)
            if runtime:
                previous_state = runtime.run_state
        self.set_run_state(slug, RUNSTATE_AVAILABLE)
        if previous_state == RUNSTATE_IN_USE:
            events_logger.info("RUNSTATE_STOPPED", extra={"machine": slug})
            self._emit("runstate_stopped", slug)


def _load_definitions() -> Dict[str, MachineRuntime]:
    session = Session()
    try:
        machines = (
            session.query(Machine)
            .options(joinedload(Machine.uni_device), joinedload(Machine.i4_device), joinedload(Machine.config))
            .all()
        )
        runtimes: Dict[str, MachineRuntime] = {}
        for machine in machines:
            if not machine.uni_device or not machine.config:
                continue
            uni_info = DeviceInfo(
                id=machine.uni_device.id,
                name=machine.uni_device.name,
                role=machine.uni_device.role,
                model=machine.uni_device.model,
                ip=machine.uni_device.ip,
                relay_channel=machine.uni_device.relay_channel,
                input_channel=machine.uni_device.input_channel,
                metric_source=machine.uni_device.metric_source,
            )
            config_info = MachineConfigInfo(
                on_threshold=machine.config.on_threshold,
                off_threshold=machine.config.off_threshold,
                on_confirm_ms=machine.config.on_confirm_ms,
                off_confirm_ms=machine.config.off_confirm_ms,
                poll_interval_ms=machine.config.poll_interval_ms,
            )
            runtimes[machine.name] = MachineRuntime(
                db_id=machine.id,
                slug=machine.name,
                ui_name=machine.ui_name,
                uni_device=uni_info,
                config=config_info,
                i4_device_id=machine.i4_device.id if machine.i4_device else None,
                i4_button_index=machine.i4_button_index,
                is_enabled=bool(machine.is_enabled),
            )
        return runtimes
    finally:
        session.close()


def _load_devices_by_role() -> Dict[str, DeviceInfo]:
    session = Session()
    try:
        devices = session.query(Device).all()
        mapping: Dict[str, DeviceInfo] = {}
        for device in devices:
            mapping[device.role] = DeviceInfo(
                id=device.id,
                name=device.name,
                role=device.role,
                model=device.model,
                ip=device.ip,
                relay_channel=device.relay_channel,
                input_channel=device.input_channel,
                metric_source=device.metric_source,
            )
        return mapping
    finally:
        session.close()


def _read_metric(device: DeviceInfo) -> Optional[float]:
    channel = device.relay_channel or 0
    metric = (device.metric_source or "").lower()

    try:
        if metric == "power":
            url = f"http://{device.ip}/rpc/Switch.GetStatus?id={channel}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                value = data.get("apower")
                if value is not None:
                    return float(value)
            status_resp = requests.get(f"http://{device.ip}/status", timeout=3)
            if status_resp.status_code == 200:
                data = status_resp.json()
                meters = data.get("meters")
                if isinstance(meters, list) and len(meters) > channel:
                    value = meters[channel].get("power")
                    if value is not None:
                        return float(value)
                # Shelly UNI Gen2 devices expose voltage via Shelly.GetStatus; use it as a
                # last-resort fallback for "power" sources when no apower readings exist.
                voltmeter = data.get("voltmeter:100")
                if isinstance(voltmeter, dict) and "voltage" in voltmeter:
                    return float(voltmeter["voltage"])

        elif metric == "adc":
            url = f"http://{device.ip}/rpc/Adc.GetStatus?id={channel}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if "voltage" in data:
                    return float(data["voltage"])
                if "adc" in data:
                    return float(data["adc"])

        elif metric == "digital":
            input_channel = device.input_channel or 0
            url = f"http://{device.ip}/rpc/Input.GetStatus?id={input_channel}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state")
                if state is not None:
                    return float(1 if state else 0)

        elif metric in {"voltage", "voltmeter"}:
            # Shelly UNI Gen2 exposes its built-in voltmeter via this RPC endpoint. The ID
            # "100" is reserved for the internal voltmeter on UNI devices and returns a
            # floating-point voltage value. If the request fails or the field is missing,
            # treat the device as offline so telemetry can recover gracefully.
            url = f"http://{device.ip}/rpc/Voltmeter.GetStatus?id=100"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if "voltage" in data:
                    return float(data["voltage"])

    except Exception:  # pragma: no cover - network interactions
        error_logger.exception("Telemetry read failed", extra={"device": device.ip})
        return None

    return None


def _handle_poll(store: MachineStateStore, ctx: MachinePollContext) -> None:
    started = time.monotonic()
    value = _read_metric(ctx.uni_device)
    success = value is not None
    if success:
        logger.debug(
            "TELEMETRY_READ",
            extra={"machine": ctx.slug, "status": "ok", "value": value},
        )
    else:
        events_logger.warning(
            "TELEMETRY_READ",
            extra={"machine": ctx.slug, "status": "error", "value": value},
        )
    store.update_measurement(ctx.slug, value, success, started)
    if not success:
        store.mark_offline(ctx.slug)
        return

    runtime = store.get_machine(ctx.slug)
    if runtime is None:
        return

    if runtime.run_state == RUNSTATE_OFFLINE:
        store.set_run_state(ctx.slug, RUNSTATE_AVAILABLE)

    threshold_on = ctx.config.on_threshold
    threshold_off = ctx.config.off_threshold
    now = time.monotonic()

    above_confirm = ctx.config.on_confirm_ms / 1000.0
    below_confirm = ctx.config.off_confirm_ms / 1000.0

    if value >= threshold_on:
        runtime.above_since = runtime.above_since or now
        runtime.below_since = None
        if runtime.run_state != RUNSTATE_IN_USE and now - runtime.above_since >= above_confirm:
            store.transition_to_in_use(ctx.slug)
            store.clear_pending_start(ctx.slug)
            runtime.above_since = None
    elif value <= threshold_off:
        runtime.below_since = runtime.below_since or now
        runtime.above_since = None
        if runtime.run_state == RUNSTATE_IN_USE and now - runtime.below_since >= below_confirm:
            store.transition_to_available(ctx.slug)
            runtime.below_since = None
        if runtime.run_state != RUNSTATE_IN_USE:
            store.set_run_state(ctx.slug, RUNSTATE_AVAILABLE)
    else:
        runtime.above_since = None
        runtime.below_since = None

    store.set_transition_markers(ctx.slug, runtime.above_since, runtime.below_since)
    store.update_measurement(ctx.slug, value, True, now)


def start_telemetry_poll() -> None:
    """Launch telemetry polling thread if not already running."""

    store = MachineStateStore.instance()

    def _poll_loop():
        logger.info("Telemetry loop starting")
        while True:
            try:
                machines = _load_definitions()
                devices = _load_devices_by_role()
                store.update_definitions(machines, devices)
                now = time.monotonic()
                contexts = store.get_poll_contexts(now)
                for ctx in contexts:
                    _handle_poll(store, ctx)
            except Exception:  # pragma: no cover - loop resilience
                error_logger.exception("Telemetry polling failure")
            time.sleep(0.2)

    threading.Thread(target=_poll_loop, daemon=True, name="telemetry-poll").start()

