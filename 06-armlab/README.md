# ArmLab

An independent educational robot arm planner inspired by offline programming workflows. Define link lengths, click a target, choose an elbow configuration, preview motion and export the joint path. Python 3.10+, standard library only.

## Run

```sh
python armlab.py
```

Requires Tkinter and a desktop display. On Linux your OS may package Tkinter separately. No account, server or paid API is required.

Headless sample export:

```sh
python armlab.py --export trajectory.csv
python -m unittest -v
```

## Plan implemented

1. Model a two-link planar arm with forward kinematics.
2. Solve target position analytically with two inverse-kinematics branches.
3. Reject targets beyond the outer reach circle or inside the inner circle.
4. Generate 151 samples using quintic joint interpolation, with zero endpoint velocity and acceleration in the continuous interpolation.
5. Animate the arm and trace the tool path.
6. Export time, joint angles in radians and Cartesian tip coordinates as CSV.

The model assumes continuous revolute joints, zero-thickness links and free space. The shortest equivalent angular motion is used. Link lengths and target coordinates share arbitrary units. Target clicks update the target; use Plan to regenerate the path. Export always writes the last successfully planned path, even if entry fields were subsequently changed.

## Mathematical model

`x = L1*cos(q1) + L2*cos(q1+q2)`

`y = L1*sin(q1) + L2*sin(q1+q2)`

The inverse solution uses the cosine law. At full extension, full folding, or a zero-position target with equal links, the arm is singular; a valid position solution does not imply stable velocity control. Joint interpolation produces a curved Cartesian path and does not enforce a straight line.

## Scope and next work

This initial release provides a complete planar planning workflow. It has no collision checking, joint limits, velocity/torque constraints, dynamics, 3D scene, hardware drivers or industrial controller export. CSV is simulation data, not a hardware-ready program. Next milestones are joint limits and collision rejection, followed by a separate 3D URDF workflow. No proprietary code, models or branding are included.

Core tests validate FK/IK agreement across both branches, unreachable targets and trajectory endpoints. The GUI has not been visually verified in the headless build environment.
