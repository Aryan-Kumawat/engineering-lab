# CalibLab

A calibration workbench for tool-center-point (TCP) estimation and rigid coordinate-frame registration. Import measured poses or point correspondences, fit the model, inspect per-observation errors and export a report. Includes a desktop report viewer and a headless CLI.

## Install and try

Python 3.10+ and NumPy are required. Tested with NumPy 2.3.5.

```sh
python -m pip install -r requirements.txt
python caliblab.py
```

Desktop mode requires Tkinter and a display. Use **TCP demo** to load the included synthetic observations, or choose a mode and load your own CSV. The residual chart displays up to 100 observations; the table and exports contain all observations. Change a mode or threshold, then load the CSV again to recompute the report.

Headless commands, from this folder:

```sh
python caliblab.py tcp examples/tcp.csv --output tcp-results
python caliblab.py registration examples/registration.csv --output frame-results
python caliblab.py tcp examples/tcp.csv --warning-mm 0.2 --output strict-results
python caliblab.py demo demo-results
python -m unittest -v
```

`demo` generates both synthetic datasets, a known-truth file and two fitted reports. Each output directory receives `report.json` and `residuals.csv`. Existing files with these names are replaced. Data and computation remain local; no accounts or APIs are used.

## TCP input: repeated contact with a stationary pivot

Every observation contains a flange pose in the robot base frame while the same tool tip touches the same stationary physical point. Rotations map **flange coordinates to base coordinates**, using column vectors. Translation is the flange origin in base coordinates. All lengths are millimetres. The estimated tool vector is expressed in flange coordinates; the pivot is expressed in base coordinates.

Exact CSV header:

```text
id,r11,r12,r13,r21,r22,r23,r31,r32,r33,tx,ty,tz
```

The rotation entries are row-major. Provide at least eight observations with unique IDs. Collect diverse orientations around multiple axes. Repeating one orientation or rotating only around one axis cannot identify all TCP coordinates. Rotations must be proper orthonormal matrices; malformed matrices are rejected without repair.

For observation i, solve `R_i * tool + t_i = pivot`. Stacking `[R_i | -I]` gives an ordinary least-squares problem with six unknowns. A rank-deficient system is rejected. A design condition number above 100 generates a sensitivity warning; above 1e8 is rejected. These are numerical heuristics, not hardware accuracy certifications.

## Registration input: corresponding 3D points

Exact CSV header:

```text
id,source_x,source_y,source_z,target_x,target_y,target_z
```

Each row identifies the same physical point in two frames, using millimetres. The Kabsch fit returns a right-handed rigid transform satisfying `target = R * source + translation`. The exported rotation is a nested row-major matrix. There is no scale estimation. Three or more noncollinear fitted point pairs are required; the complete CSV still needs at least eight observations for the validation split. Planar point sets are valid; collinear or nearly collinear sets are rejected.

## Validation and reporting

Zero-based observations 0, 5, 10, ... are reserved before fitting. These held-out observations never influence the model. Rows retain their input order; interleave diverse poses rather than collecting one orientation cluster at the start. A dataset with 30 rows therefore produces 24 fit rows and 6 held-out rows.

The report contains the model, input SHA-256 hash, split rule, condition diagnostic for TCP, per-row error vectors, RMS/median/maximum residuals for each split and warning flags. RMS here means `sqrt(mean(norm(error_xyz)^2))`, not per-axis RMS. The default 0.5 mm warning is a user-configurable display threshold; it is not an acceptance tolerance or an outlier-removal rule. All fitting observations remain in the least-squares fit.

For TCP, the residual is the transformed tool tip minus the fitted pivot. For registration, it is the transformed source point minus the observed target point. Low fitting error alone does not establish real accuracy; inspect the held-out residuals too. A held-out set from the same synthetic generator does not model distribution shift.

## Verification and limitations

Ten automated checks cover known transforms, noiseless TCP recovery, noisy held-out error, split independence, degenerate geometry, invalid rotations, nonfinite values, duplicate IDs and report round trips. The CLI demo was executed successfully. Desktop rendering has not been visually verified in this environment.

The included examples have known synthetic truth and 0.05 mm per-axis translation noise. They do not model orientation uncertainty, robot flex, backlash or a moving pivot. No measurements from physical robots have been validated. The solver uses ordinary least squares without robust fitting or confidence intervals. There is no hand-eye calibration, automatic robot motion or hardware driver. At most 10,000 observations are accepted. Review coordinate conventions and measurement quality before using results outside simulation.

Future work: robust fitting with explicit exclusions, uncertainty estimates, independently collected robot measurements, and a hand-eye calibration module. The project is independently implemented and is not a RoboDK file-format or API clone.

Licensed under MIT; see LICENSE.
