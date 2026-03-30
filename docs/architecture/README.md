# Architecture Documentation

System-wide architecture references and behavior contracts.

## Current references
- Runtime lifecycle: [`runtime-lifecycle.md`](./runtime-lifecycle.md)
- Hardware and telemetry: [`hardware-topology-and-telemetry.md`](./hardware-topology-and-telemetry.md)
- UI state contract: [`ui-state-contract.md`](./ui-state-contract.md)
- Repository overview: [`../../README.md`](../../README.md)

## Notes
- Runtime ownership currently overlaps between `backend/app.py` and `backend/flask_server.py`; treat this as a known design constraint.
