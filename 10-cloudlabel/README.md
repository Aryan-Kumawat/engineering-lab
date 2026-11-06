# CloudLabel

A local point-cloud annotation tool with an orbitable 3D view, editable axis-aligned boxes, undo/redo, cloud-identity checks and atomic JSON saving. This is an independent implementation of a small point-cloud labeling workflow.

## Install and run

Python 3.10+, NumPy and Tkinter:

```sh
python -m pip install -r requirements.txt
python cloudlabel.py
```

No server, paid API or account is needed. Tkinter is normally included with Python on Windows; Linux may require a separate OS package. The application starts with a deterministic 6,100-point synthetic scene.

## Label a cloud

1. **Open cloud**: choose an ASCII PLY or PCD file. Or use the built-in scene.
2. Drag with the left mouse button to orbit, right-drag to pan, and scroll to zoom.
3. **New box** creates an editable box at the cloud center. Alternatively, Shift-drag a rectangle to bound projected sampled points.
4. Select a box in the annotation list. Edit its class label and XYZ bounds, then click **Apply box edits**.
5. Use **Undo/Redo** or Ctrl+Z/Ctrl+Y. History retains up to 50 edits. Camera changes are not annotation edits.
6. **Save labels** chooses an output JSON. Subsequent edits autosave to that file after 800 milliseconds. File replacement is atomic; save failures are reported in the status line. Unsaved edits prompt on cloud replacement or close.
7. **Load labels** restores a saved document only if its coordinate fingerprint and point count match the current cloud.

All box coordinates use the original cloud's XYZ axes and units. No units, viewpoints or sensor-frame transformations are inferred. The view is orthographic; boxes stay aligned with source XYZ regardless of camera rotation.

Rectangle selection operates on the projected rendering sample and includes points at all depths in the rectangle, including occluded points. It does not perform depth-aware picking. Bounds are padded slightly to produce positive volume. Inspect and edit XYZ bounds before exporting.

## Formats and limits

- PLY: ASCII 1.0, scalar vertex properties, x/y/z required; extra scalar properties are ignored. Vertices must be the first nonempty element. Later mesh/face data is ignored.
- PCD: DATA ascii, x/y/z fields and POINTS required, unique scalar fields with COUNT 1. Additional fields are ignored. VIEWPOINT is not applied.
- Binary/compressed PLY or PCD, meshes, rotated boxes and semantic point-by-point labels are not supported.
- Input limit: 50 MB and 1,000,000 points. Coordinates must be finite and within ±1e9 source units.
- Renderer: a deterministic strided sample of at most 15,000 points, drawn on a CPU Tk canvas. All source points are retained for identity checks. Rendering every large cloud at interactive rates is not guaranteed.
- Annotation limit: 500 positive-volume boxes. Labels/IDs contain 1–80 characters. JSON imports are limited to 2 MB.

## Portable annotation schema

```json
{
  "schema_version": 1,
  "coordinates": "source_xyz",
  "box_type": "axis_aligned",
  "cloud_sha256": "...",
  "point_count": 407,
  "boxes": [
    {"id": "object_1", "label": "part", "min": [-1, -1, 0], "max": [1, 1, 2]}
  ]
}
```

The fingerprint hashes ordered XYZ values as little-endian float64 bytes, not the original file bytes or optional color fields. Reordering or changing point coordinates changes the fingerprint. The JSON stores exact floating-point bounds without display rounding. Exports do not bundle cloud data, camera state or undo history.

Included examples contain the same 407-point scene in PLY and PCD, with two sample annotations. Open `examples/demo.ply` first, then load `examples/demo.annotations.json`. The demo annotations also match the PCD because both files preserve the same ordered coordinates. These reduced examples differ from the 6,100-point built-in scene and therefore must be loaded before their labels.

## Headless inspection and checks

```sh
python inspect_cloud.py examples/demo.ply --labels examples/demo.annotations.json
python -m unittest -v
python benchmark.py --points 100000
```

Seven tests cover PLY property order, PCD parsing, binary/nonfinite/truncated input rejection, exact annotation round trips, cloud mismatch, invalid boxes, duplicate IDs and preserving an existing file after validation failure.

A Linux desktop smoke check exercised the 6,100-point view, box creation, numeric/label editing, saving, orbiting and undo/redo. Full file-format compatibility and every desktop interaction are not covered. No automated GUI regression suite is included.

One importer benchmark loaded a 100,000-point, approximately 3.45 MB ASCII PLY in 0.110 seconds with Python 3.12.14 and NumPy 2.3.5 on Linux x86-64. This is a single environment-dependent measurement, not an FPS or memory benchmark. Run `benchmark.py` to measure your own environment.

## Next milestones

Depth-aware picking, rotated boxes, GPU rendering, semantic labels and documented training-format converters. Current JSON is a project-owned schema, not a claim of compatibility with a commercial labeler.

MIT licensed; see LICENSE.
