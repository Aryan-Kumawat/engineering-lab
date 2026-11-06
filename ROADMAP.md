# Engineering Lab roadmap

## Flagship: RobotBench

The [RobotBench](robotbench/) 0.1.0 workflow is implemented: restricted serial URDF models, reproducible servo experiments, structured failures, portable results, replay and baseline comparison. It includes desktop and headless entry points.

The [dedicated roadmap](robotbench/docs/ROADMAP.md) defines subsequent authoring, backend-integration and ROS milestones. Broader dynamics, motion planning and hardware support remain future work.

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

## Newly implemented initial workflows

| Project | Delivered | Next useful milestone |
|---|---|---|
| CloudLabel | ASCII PLY/PCD viewing, editable axis-aligned boxes, undo/redo, autosave and cloud-matched JSON labels | Depth-aware selection, GPU rendering and semantic labels |
| CellSketch | Editable process layouts, FIFO discrete-event simulation, travel times, baseline comparison and reports | Finite buffers, resource sharing and reach overlays |

Both tools include example files, focused automated checks and selected Linux desktop smoke checks. Their READMEs record supported formats, simulation assumptions and verification limits.

## Release expectations

Every release should have setup instructions, representative examples, meaningful checks, documented input/output contracts and explicit verification limits. Validate desktop/browser interactions and gather real data before making broader reliability or accuracy claims.
