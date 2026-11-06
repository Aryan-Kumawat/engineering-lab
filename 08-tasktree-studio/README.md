# TaskTree Studio

An independent behavior-tree editor and execution debugger for simulated robot tasks. Python 3.10+, standard library only. It includes a JSON editor, hierarchical task viewer, single stepping, playback, pause/cancel, blackboard snapshots and exported execution traces.

```sh
python tasktree.py
python tasktree.py --example
python tasktree.py --run my_tree.json
python -m unittest -v
```

Desktop mode needs Tkinter and a display. CLI execution works headlessly. Use Prepare/reset after editing JSON: an execution always uses its prepared snapshot. Playback advances events every 250 milliseconds; this is a presentation interval, not robot time. Wait counts logical ticks. Pause suspends playback, Step advances one event, Cancel cooperatively stops execution at the next event boundary.

Sequence stops on the first failure. Fallback stops on the first success. Retry reexecutes its child up to `attempts` times. Action fails its first `fail_first` invocations within a run, then succeeds and optionally assigns `key`/`value` to the shared blackboard. Invocation counts are per node path and reset with a new Runner. Blackboard effects persist across retries; there is no transaction rollback. The included pick-and-place example demonstrates a failed grasp followed by recovery.

Tree JSON supports nodes of type Sequence/Fallback (`children`), Retry (`child`, `attempts`), Wait (`ticks`) and Action (`fail_first`, optional `key` and `value`). Every node needs a `name`. Limits are 200 nodes, depth 30, and at most 1000 attempts/ticks per node. Nested retries can produce long traces: cancel or pause execution when needed.

Run tests to check retry recovery, fallback behavior, cancellation and deterministic traces. Desktop layout and interaction have not been visually verified in this environment.

This release simulates synchronous actions and provides a JSON-based editor, not drag-and-drop node authoring. No robot commands are sent. Future milestones: graphical node insertion, explicit asynchronous action lifecycles, replay viewer and an isolated ROS 2 adapter. This is not MoveIt Pro compatibility software.
