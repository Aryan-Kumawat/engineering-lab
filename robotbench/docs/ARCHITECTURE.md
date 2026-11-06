# Architecture

RobotBench treats an experiment as a versioned input and a run as an immutable result snapshot. Replay does not rerun physics or require the original URDF file.

| Module | Responsibility |
|---|---|
| `robot.py` | Restricted URDF parsing, robot snapshots, transforms, FK and geometric clearance |
| `experiment.py` | Input normalization, bounds, relative URDF resolution and smooth targets |
| `engine.py` | Seeded controller/sensor loop, surrogate dynamics, diagnostics and metrics |
| `results.py` | Atomic JSON, run validation, CSV signals and contextual comparisons |
| `workspace.py` | Bundled project initialization and saved-run discovery |
| `cli.py` | Headless workflows and explicit exit semantics |
| `gui.py` | Draft editor, background execution, replay, diagnostics and comparison |

## Execution lifecycle

1. Load the experiment and its local URDF; validate and normalize parameters.
2. Freeze the draft and robot model for the run.
3. Run deterministic simulation on a worker thread in desktop mode.
4. Record every sample and diagnostic event, including the terminal sample.
5. Save an independent run snapshot; failed and cancelled runs remain inspectable.
6. Replay the snapshot or compare its metrics and context with another run.

Tk widgets are touched only by the UI thread. The simulation worker reports progress/results through a queue and observes a threading Event for cancellation. The app allows replay of an old result while an experiment uses its frozen snapshot. Changing workspaces and starting another simulation are disabled during a run.

## Why a small built-in backend

The first release establishes experiment identity, reproducibility, failures, persistence and debugging against an inspectable model. The joint-servo backend is deliberately documented and analytically testable. Replacing it with a richer simulator should not change what a run means or silently mix incomparable results.

A future backend must return the same versioned sample/event contract, identify its implementation/version, support cancellation and expose its modeling assumptions. The current code does not include a stable backend plugin API or a ROS/Gazebo adapter. These must be designed and tested before claiming integration support.

## Storage

Workspace experiment JSON and URDF files remain editable. Each run is saved as `runs/<UTC timestamp>-<random prefix>.run.json`. A run has a full random ID, a configuration SHA-256, robot/experiment snapshots, samples, events and metrics. Timestamps and IDs differ between otherwise identical runs; seeded numerical samples, events and metrics should reproduce within the documented environment.

No database, daemon or cloud service is required. History displays up to 200 most recent run filenames. JSON is replaced atomically, but not fsynced; atomic replacement is not a guarantee against power-loss data loss. Runs can be large, and history has no automatic retention policy.
