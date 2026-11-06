# Formats

## Experiment JSON v1

Start with the bundled `reach.json`. Unknown top-level fields are rejected to catch misspellings. All positions/rotations use SI units: metres and radians. Times use seconds and commanded efforts use Nm.

| Field | Contract |
|---|---|
| `schema_version` | Integer 1 |
| `name` | 1–100 characters |
| `robot` | Relative URDF path inside the experiment's directory |
| `dt_s` | 0.001–0.1 s |
| `duration_s` | Up to 120 s, integer multiple of dt, at most 20,000 intervals |
| `seed` | Integer in [0, 2^32) |
| `initial_rad` | One initial angle per active joint, within URDF limits |
| `waypoints` | 2–100 objects with `time_s` and `positions_rad`; strictly increasing from zero |
| `controller` | `kp`, `ki`, `kd`; scalar or per-joint arrays, nonnegative, at most 1000 |
| `dynamics` | `inertia`, `damping`; scalar or arrays; inertia positive, damping nonnegative |
| `position_noise_std_rad` | Gaussian measurement standard deviation, 0–0.5 rad |
| `velocity_noise_std_rad_s` | Gaussian velocity measurement standard deviation, 0–5 rad/s |
| `tool_offset_m` | XYZ translation in the final link frame |
| `link_radius_m` | Capsule radius, 0.001–1 m |
| `obstacles` | Up to 20 spheres: unique `id`, XYZ `center_m`, positive `radius_m` |
| `goal_tolerance_rad` | Final goal tolerance applied per joint, 1e-6–1 rad |

Active joint order follows the serial chain from base to tool. Axes are normalized on URDF import; origin rotations use `Rz(yaw) @ Ry(pitch) @ Rx(roll)`. The origin transform is applied before joint-axis motion. URDF `<inertial>`, `<visual>` and `<collision>` data are not interpreted by this backend.

Inertia is a scenario-specified scalar joint inertia, not URDF link mass/inertia. For each joint `I*qdd + damping*qd = effort`; gains and damping should be selected consistently with this surrogate model.

## Run JSON v1

Runs contain:

- `schema_version`, `engine_version`, `backend`, `run_id`, `created_at`, `config_sha256`.
- `joint_names`, a portable `robot` snapshot and the normalized `experiment` snapshot.
- `status`: completed, failed or cancelled; `failure_reason` when applicable.
- `metrics`, timestamped `events` and an ordered `samples` array.

Each sample stores time, true positions/velocities, measured positions, target positions/velocities, commanded effort, tool-tip XYZ and minimum obstacle clearance (null when there are no obstacles). The terminal sample includes a computed controller command even though no later physics interval is executed.

The configuration hash covers normalized experiment and robot snapshots. It is not a signature or authenticity proof. Run import validates key shapes/ranges, but does not recompute every stored metric; load results produced by a trusted RobotBench process when numerical provenance matters.

Events use time, level, code and message. Current codes include `run_started`, `effort_saturated`, `effort_recovered`, `velocity_clipped`, `collision`, `joint_limit`, `goal_missed`, `user_cancelled`, `numeric_failure` and `run_finished`.

Run import is capped at 100 MB and 20,001 samples. URDF is capped at 1 MB; experiment JSON at 200 KB. Saved run files need no original source files for replay, but reproducing their experiment requires an appropriate URDF plus the experiment snapshot. There is no cross-version run migration in this release.

## CSV

CSV contains time, true/target joint positions, true velocities, commanded efforts, tool-tip XYZ and clearance. Joint names prefix column keys. CSV does not contain the complete robot/configuration, diagnostics or measured positions; use run JSON for full-fidelity replay.
