# RobotBench

**A local workbench for building and debugging reproducible robot experiments.**

Configure a serial robot arm, run a controller experiment, inspect tracking errors and failures, replay the exact result, and compare it with a baseline. RobotBench combines a desktop workspace with a headless CLI and versioned, portable run files.

This is the **0.1.0 initial source release**. Its built-in backend is a simplified joint-servo simulator with 3D kinematics and capsule/sphere collision checks. It is not a full rigid-body physics engine or a hardware control application.

## Install

Python 3.10+ and NumPy are required. From this directory:

```sh
python -m pip install -e .
python -m robotbench init experiments
python -m robotbench gui experiments
```

`init` creates a new workspace with a three-joint URDF and three experiments. Choose a new or empty directory; initialization never overwrites an existing workspace. Desktop mode needs Tkinter and a display; Linux distributions may package Tkinter separately. No ROS installation, account, API key, GPU or network service is required to run the application after installation.

The command `robotbench` is also installed as a console entry point. Using `python -m robotbench` avoids PATH issues on Windows.

## First experiment

1. Open `reach.json` in the sidebar and click **Run experiment**.
2. A completed run appears in history. Use **Play** or the timeline to replay it. Drag the 3D view to orbit and scroll to zoom.
3. Select a joint and signal: position/target, tracking error, or commanded effort.
4. **Pin baseline** to keep the current result for comparison.
5. Select `poor_tuning.json`, then run again. The weak controller misses the final goal. Inspect **Compare runs** and the pink baseline signal overlay.
6. Select `collision.json` and run it. In **Diagnostics**, click the collision event to jump to the failure sample. The intersecting robot is highlighted.

The bundled nominal experiment produces about **0.00989 rad** RMS tracking error; the weak-controller experiment produces about **0.38423 rad**. The bundled obstacle is first detected at **2.16 s** with the default 0.01 s sample interval. These are synthetic model results, not real-robot performance measurements.

## Edit an experiment

The sidebar accepts controller gains as a scalar (all joints) or a JSON array (one per joint). Click **Apply gains to draft**, then run. Other settings are edited in **Experiment JSON**: waypoints, initial positions, noise, seed, dynamics, obstacles, duration and sample interval.

Running uses a frozen, normalized snapshot of the draft. It does not overwrite the experiment file. **Save experiment** preserves the draft. Successful, failed and UI-cancelled runs are automatically saved under the workspace's `runs/` directory. **Save run** offers another destination if automatic saving fails. **Export CSV** exports signals from the selected run.

Changing the selected experiment replaces the draft after a discard prompt. Run history and baseline selection refer to saved or completed runs, so results remain tied to the configuration that actually produced them. Replaying a result does not change the current experiment draft. Saving an experiment into a different directory requires its relative URDF reference to resolve there.

## Headless workflow

```sh
python -m robotbench run experiments/reach.json --output nominal.run.json --csv signals.csv
python -m robotbench run experiments/poor_tuning.json --output weak.run.json
python -m robotbench compare nominal.run.json weak.run.json --output comparison.json
python -m robotbench inspect weak.run.json
```

The weak experiment intentionally returns exit code **1** while still saving its result. Completed runs return **0**; invalid inputs or file errors return **2**. A CLI process interrupted with Ctrl+C returns **130** and does not guarantee a partial artifact. Desktop **Cancel run** is cooperative and saves a cancelled result at the next simulation sample boundary.

`compare` reports data and returns 0 for a valid comparison, even when the current run regresses. CI callers must inspect `status_regressed` or apply their own numerical tolerance. Comparison is restricted to the same robot geometry and limits. Changes in noise, seed, dynamics, trajectory, obstacles or other experiment context are flagged; changing controller gains is permitted. Early-terminated runs cover different intervals, so RMS alone cannot establish improvement.

## What the release includes

- A packaged Python project, CLI and desktop application.
- Restricted serial URDF import, 3D skeleton view and forward kinematics.
- Quintic joint-waypoint interpolation and deterministic seeded sensor noise.
- PID control, conditional-integration anti-windup, effort limits and bounded velocities.
- Exact held-effort integration of decoupled joint dynamics.
- Sampled capsule/sphere clearance checks and structured failure events.
- Versioned run snapshots, automatic history, atomic JSON saving and CSV export.
- Playback, scrubbing, event-to-frame navigation, baseline overlays and contextual run comparison.
- Three bundled experiments, focused numerical/integration tests and a GitHub Actions workflow.

## Supported robot and simulation scope

URDF support is intentionally restricted to one connected serial chain with **1–8 bounded revolute joints** and optional fixed joints, up to 32 total joints. Branched, continuous, prismatic, mimic, floating and planar joints are rejected. Models must provide finite position, effort and velocity limits. URDF paths stay inside the experiment directory; external mesh files are not loaded.

The viewer draws joint-center segments plus a configured tool offset. Collision geometry uses a single configured capsule radius for these segments and spherical obstacles. URDF visuals, collision meshes and inertial data are not used. Collision checks happen at sample boundaries; there is no swept collision, self-collision, gravity, coupled dynamics, contact response or inverse kinematics.

The backend models each joint using scenario-specified inertia and damping. These are surrogate parameters, not a physical dynamics model inferred from the URDF. Velocity and position bounds are simplified limits. The application never sends robot commands and its trajectories are not hardware-ready programs.

## Checks and verification

```sh
python -m unittest discover -s tests -v
```

The local suite has 25 checks covering known FK positions, URDF validation, analytic dynamics, target interpolation, seed reproducibility, nominal/failing controllers, collision/limit stops, cancellation, artifact round trips, CSV, CLI outcomes and comparison contexts.

A Linux desktop smoke check exercised workspace loading, nominal and failing runs, automatic history, replay, baseline pinning/overlays, comparison and collision-event navigation. It also caught and led to a fix for low-contrast controls. This is not a complete automated GUI test suite. The repository workflow targets Ubuntu and Windows on Python 3.10 and 3.12; see the actual workflow runs for results beyond local verification.

## Documentation

- [Architecture and extension points](docs/ARCHITECTURE.md)
- [Experiment and run formats](docs/FORMATS.md)
- [Simulation semantics and metrics](docs/SIMULATION.md)
- [Roadmap and completion gates](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

MIT licensed. This project is independently implemented and is not a compatibility clone of a commercial robotics platform. No paid-tool source code, assets or robot libraries are bundled.
