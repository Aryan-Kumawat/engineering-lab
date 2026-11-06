# Roadmap

## 0.1 — Reproducible servo experiments (implemented)

Serial URDF kinematics, controller/noise configuration, deterministic simulation, structured failures, snapshots, replay and baseline comparison. This establishes one complete experiment workflow with an inspectable built-in backend.

## 0.2 — Experiment authoring and stronger verification

- Add a structured waypoint editor and obstacle placement controls alongside JSON.
- Add automated desktop interaction tests on supported operating systems.
- Collect performance/memory measurements at documented limits.
- Define batch experiment execution and explicit regression thresholds.

Completion gate: a user can create a valid experiment without hand-editing JSON, and an automated test can run, inspect, replay and compare it through the UI.

## 0.3 — Dynamics backend integration

- Specify a versioned backend contract with cancellation and portable diagnostics.
- Integrate one established dynamics simulator after validating its model and licensing requirements.
- Add backend-specific assumptions and capability discovery.

Completion gate: benchmark a set of reference systems against analytical expectations and simulator-native results. Report different backends as distinct experiment contexts.

## 0.4 — Robot task experiments

- Add a ROS 2 adapter with strict simulation/hardware separation.
- Add task execution traces and recorded topic/joint streams.
- Link control/task failures to replay timestamps.

Completion gate: replay a recorded simulation run without requiring the original live ROS graph, and compare repeated runs on a fixed scenario.

## Longer-term

Motion planning, richer collision geometry, sensor visualization, shared experiment bundles and plugins. These are future capabilities, not claims about the current release. A browser frontend can follow after the experiment/backend contract is stable.
