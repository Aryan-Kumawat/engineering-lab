# Engineering Lab roadmap

## Implemented initial releases

| Project | Delivered | Next useful milestone |
|---|---|---|
| Sensor Log | CSV checks and streaming statistics | Multi-channel schema and machine-readable summaries |
| PID Playground | First-order plant, tuning GUI and CSV mode | Noise/delay experiments and GUI verification |
| Compact Anomaly Detector | Quantized statistical parameters and held-out synthetic evaluation | Real sensor recordings and embedded implementation |
| Robot Telemetry | Bounded queue, local TCP and acknowledged replay | Message IDs, deduplication and measured throughput |
| Codebase Explorer | Local FTS search and source citations | Retrieval benchmark and incremental indexing |
| ArmLab | Planar inverse kinematics, interpolation, animation and export | Joint limits, collisions and GUI verification |
| ControlCanvas | Graph editing, simulation, plots and model persistence | Undo/redo, parameter sweeps and browser interaction checks |
| TaskTree Studio | JSON editor, execution trace, retries and cancellation | Graphical node authoring and asynchronous action semantics |
| CalibLab | TCP fit, rigid registration, residual plots and held-out reports | Robust fitting, uncertainty and independent hardware measurements |

## Planned

### CloudLabel

Begin with point-cloud import, orbit controls and editable 3D boxes. Add portable annotation export, undo/redo and autosave before sequence labeling. Completion requires exact annotation round trips and a measured viewer performance limit.

### CellSketch

Begin with a top-down equipment layout and deterministic discrete-event process simulation. Show throughput, queues and bottlenecks. Compare against hand-calculated examples before adding reach overlays or a 3D viewer.

## Release expectations

Every release should have setup instructions, representative examples, meaningful checks, documented input/output contracts and explicit verification limits. Validate desktop/browser interactions and gather real data before making broader reliability or accuracy claims.
