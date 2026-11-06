# ControlCanvas

A browser-based visual control-system editor and simulator. Open `index.html` in a desktop browser; no installation, build, account or network connection is required. Keep `engine.js` beside it.

## Workflow

1. Load P, PI or PID example; click **Simulate**.
2. Drag blocks to arrange them. Click a block, edit its JSON parameters, then apply.
3. Add blocks and connect them through the wire selectors. Each input accepts one wire; connecting replaces the previous wire.
4. Simulate again, inspect the graph, then export CSV.
5. Save JSON to preserve the diagram. Load it to resume later.

The initial release supports Step, Gain, Sum, PID, Saturation, Motor and Scope. Sum is input 0 minus input 1. Scope and Step signals appear in the plot; CSV contains all block outputs. Changing the model invalidates the previous result. Moving blocks changes only their layout.

## Engine

`engine.js` exports the same API to the browser and Node.js: `validate(model)`, `simulate(model, {dt, duration})`, and `example(kind)`. Graphs are versioned JSON. Every node has a unique string ID, type, parameter object and UI coordinates. Wires identify source, destination and zero-based destination port. Load accepts complete, valid graphs; use Save on partial graphs only after connecting all inputs if you intend to load them again.

The engine topologically evaluates direct-feedthrough blocks. A Motor exposes its previous plant state, breaking a feedback loop; its next state is calculated after all commands are available. Pure algebraic loops are rejected. Motor dynamics are `tau*dy/dt = input-y`, integrated exactly for a held input during each sample. Sampling still affects controller behavior.

PID uses a rectangular integral and a first-order filtered derivative of error, with a fixed 0.05-second filter time constant. It has no anti-windup; connecting a Saturation block can therefore demonstrate windup. Initial integral accumulation includes the first error sample. Motor states and controller states start at zero on every run. The engine accepts up to 60 blocks and 100,000 time intervals, rejects nonfinite parameters and stops divergent simulations. Use dt <= the smallest motor time constant / 10.

## Validation

```sh
node test.cjs
```

Checks cover the analytical open-loop response, P-controller steady state, PI error removal, algebraic-loop rejection, invalid sampling, missing connections and JSON round trips. Numerical checks passed. Browser drag/drop, file dialogs and visual rendering have not been verified in this build environment.

## Roadmap

Delivered: graphical blocks and wires, parameter inspector, deterministic simulation, plots, CSV, saved JSON and three examples.

Next: undo/redo; per-signal visibility; parameter sweeps; controller anti-windup; automated browser interaction checks. Discrete-time and generated-code support require separately specified execution semantics.

This is an independent educational implementation of a small control-simulation workflow. It does not import Simulink models or provide general-purpose solver, physical modeling or hardware deployment compatibility.
