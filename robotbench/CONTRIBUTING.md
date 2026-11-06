# Contributing

Install locally with `python -m pip install -e .`, then run `python -m unittest discover -s tests -v` from this directory.

Keep GUI code separate from numerical work. UI widgets must only be accessed on Tk's main thread. Preserve the distinction between an editable draft and an immutable run snapshot.

For mathematical changes, add a check against a known analytical solution or independently derived geometry. For format changes, update the version/validation rules, include a migration plan if needed, and document compatibility. Do not add dependencies solely to avoid a small, inspectable implementation.

For backend integrations, document physical assumptions, cancellation behavior and reproducibility limits. Do not describe the built-in surrogate dynamics as a complete rigid-body model. Hardware-control integrations require a separately designed execution path; the current project emits no hardware commands.

Use synthetic or redistributable examples. Do not commit API keys, proprietary robot assets, user-generated run files or unlicensed software. Include the exact reproduction steps, expected behavior and observed result when reporting a bug.
