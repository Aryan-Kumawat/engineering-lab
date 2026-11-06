# CellSketch

A top-down workcell layout editor with a deterministic discrete-event process simulator. Place robot, workbench and conveyor process stations, reorder the route, compare layouts and export reports with full event traces. Python 3.10+, standard library only.

## Run

```sh
python cellsketch.py
```

Desktop mode needs Tkinter and a display. The initial example contains loading, robot assembly and an exit conveyor.

1. Select a station in the route list or click it on the floor. Drag it to move it.
2. Edit its name, kind, X/Y position, cycle time and parallel capacity, then **Apply station and run settings**.
3. **Earlier/Later** changes process order. Arrows follow this order.
4. Set jobs, arrival interval, observation horizon and travel speed; click **Run simulation**.
5. Inspect throughput, completed-job lead time, WIP and station utilization.
6. **Pin baseline**, change the layout or settings, then run again. The baseline retains its original settings for comparison.
7. Save/load the layout as JSON. Export the last completed simulation as JSON, including its model snapshot, fingerprint, metrics and event trace.

Station edits in the inspector require Apply; Run and Save read the run settings but do not apply unconfirmed station edits. Results are invalidated by committed layout edits and run-setting changes. The baseline is session-only and does not persist in layout files.

## Headless simulation

```sh
python cellsketch.py --demo --report report.json --events events.csv
python cellsketch.py --run examples/demo.json --report report.json
python -m unittest -v
```

The included example completes 30 of 40 arrived jobs in a 180-second observation horizon: 600 jobs/hour, 10 jobs in progress and approximately 59.662 seconds mean lead time among completed jobs. These are outputs of this simplified model, not measured factory results.

## Model and execution contract

Each station is a processing step, even when its kind is `conveyor` or `workbench`. Kind affects its description only. Cycle time and capacity define its service behavior. The model supports one serial route; every job visits every station in list order.

- Jobs arrive at the first station at times `job_index * arrival_interval_s`. Zero interval releases a batch.
- Queues are FIFO and unbounded. Capacity is the number of identical parallel servers at a station.
- Service duration is fixed. No stochastic distributions are used.
- Travel between stations takes Euclidean distance divided by transport speed. Station coordinates use metres, time uses seconds, and the layout is 40 × 25 m.
- Travel has unlimited concurrent capacity, no traffic conflicts, and no initial source/final sink movement. No service resource is occupied while a job travels.
- Completions precede arrivals at the exact same timestamp. Equal-priority events follow deterministic insertion order.
- Events at the horizon are included; arrivals after it are excluded. Reports count arrivals actually admitted within the horizon.
- Work-in-progress includes queued, processing and travelling jobs. Partially completed jobs are censored from completed-job lead-time averages.

The floor drawing does not model physical footprints: overlapping stations are allowed. Travel does not navigate around equipment. A layout with shorter travel can still have the same throughput if another constraint dominates.

## Metrics

`throughput_jobs_per_hour = completed_jobs / horizon_seconds * 3600`. This uses the configured observation horizon, including startup and idle time, rather than just the time until the last completion.

Per-station utilization is the time integral of occupied servers divided by capacity × horizon. Average queue length is its time integral divided by horizon. Mean waiting time includes only jobs whose service started before or at the horizon; jobs still queued are excluded. `highest_utilization_station` is an observed diagnostic, not proof of the causal bottleneck. Ties choose the first station in route order.

Report JSON includes all model settings, a SHA-256 of canonical model JSON, summary metrics, station metrics and events. CSV event export is available in CLI mode. GUI exports contain events within JSON. Output files with existing names are overwritten. Baseline comparison can include different settings, so inspect the saved model snapshots before attributing a change to layout alone.

## Bounds and verification

Limits: 1–20 stations, 1–2,000 jobs, 1–20 parallel servers per station. Layout imports are limited to 200 KB. Cycle times must be positive; other numerical ranges are checked explicitly. A maximum-size simulation produces a large event report; this is a small-workcell tool rather than a production-scale simulator.

Nine automated checks cover hand-calculated queues, two-stage pipelines, parallel capacity, distance-dependent travel, horizon censoring, arrivals, determinism, invalid models, job conservation and utilization bounds.

A Linux desktop smoke check exercised initial layout rendering, simulation, baseline pinning, station dragging and comparative results. Moving the exit conveyor closer in the demo changed simulated output from 30 to 32 jobs within the same 180-second horizon. JSON/CSV report generation was also exercised through the CLI. A full automated GUI suite is not included.

## Scope and next milestones

No robot kinematics, collision checking, reachability overlays, finite buffers, failures, shared operators, transport fleet limits, loops, branching routes or 3D physics. Next steps are finite-buffer semantics and reach overlays, with new analytical checks before adding richer visualizations. This is an independent implementation of a small workcell-planning workflow.

MIT licensed; see LICENSE.
