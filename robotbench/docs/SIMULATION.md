# Simulation contract

The built-in backend is `decoupled_joint_servo_v1`. It evaluates 3D kinematics while integrating independent joint dynamics. It is useful for experiment workflow development and simple servo studies, not contact physics or validating hardware safety.

## Per-sample order

1. Evaluate the quintic-interpolated target and target velocity.
2. Sample position and velocity noise from a seeded NumPy generator.
3. Compute PID effort with conditional integration; clamp effort to URDF limits.
4. Record the current true state, target, measurements, command and tip position.
5. Check cancellation, a pending hard limit and geometric collision.
6. Unless terminal, integrate held effort over the next dt, bound velocities, and detect position-limit crossings.

The dynamics `I*qdd + b*qd = effort` are integrated analytically with stable small-damping limits. No gravity, Coriolis terms, actuator delay or cross-joint coupling is modeled. Velocity clipping occurs at sample boundaries; displacement was integrated from the unclipped held-effort solution, so clipping is an approximation rather than exact constrained dynamics. Hard joint limits clamp the next position and terminate at that sample.

Quintic interpolation has zero velocity/acceleration at waypoint endpoints. There is no planner: the user supplies joint waypoints, and the interpolation does not optimize for obstacles or velocity limits. Target waypoints are position-limit checked; dynamically overshooting a limit is still possible. A smaller dt can change sampled controller/collision outcomes even though the held-input joint integration is exact.

## Collision

Consecutive joint-origin/tool points define capsule centerline segments. Each segment uses the same configured radius. Clearance against a sphere is point-to-segment distance minus sphere and link radii. Clearance <= 0 is a collision and stops execution. Fixed and coincident joint origins can create zero-length segments; these are treated as spheres.

Checks occur at sample boundaries, so fast movement or thin obstacles can be missed between samples. There is no self-collision, swept-volume check, ground collision, mesh collision or contact response. The rendered ground grid is only a visual reference.

## Outcomes

A completed run must reach its configured horizon and finish within tolerance of the final waypoint. Failure reasons distinguish missed goal, geometric collision, hard joint limit and numerical failure. Desktop cancellation is a separate outcome. A failed/cancelled run can happen to end near the final goal, so `goal_reached` never overrides the run status.

## Metrics

- `rms_error_rad`: square root of the time-weighted mean squared tracking error, averaged over joints. Trapezoidal integration uses the observed interval. With only one sample, instantaneous squared error is used.
- `rms_per_joint_rad`: the corresponding RMS for each joint.
- `final_error_rad`: error against the interpolated target at the last observed sample.
- `final_goal_error_rad`: error against the experiment's final waypoint, even when terminated early.
- `peak_abs_error_rad`: sampled peak tracking error per joint.
- `effort_saturation_fraction`: fraction of executed intervals with effort beyond the command limit before clipping; the unexecuted terminal command is excluded.
- `minimum_clearance_m`: sampled minimum geometric clearance; null without obstacles.
- `observed_duration_s`: actual simulated duration before termination.
- `goal_reached`: all final-waypoint errors are within the configured per-joint tolerance.

A small tracking RMS on a short collision run is not evidence of a good experiment. Inspect status, failure events, observed duration and final-goal error together. Baseline overlays also identify differences in experiment context, including random seed, instead of attributing every metric change to controller tuning.
