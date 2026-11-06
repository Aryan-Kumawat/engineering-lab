"""Generate calibration fixtures with known truth and independent measurement noise."""
import csv
import json
from pathlib import Path
import numpy as np
from core import POSE_COLUMNS, POINT_COLUMNS


def rotation(axis, angle):
    axis = np.asarray(axis, dtype=float)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * (skew @ skew)


def generate(directory, noise_mm=0.05):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    tool = np.array([12., -8., 105.])
    pivot = np.array([400., 60., 250.])
    rotations = np.array([rotation(rng.normal(size=3), rng.uniform(-np.pi, np.pi)) for _ in range(30)])
    translations = pivot - np.einsum('nij,j->ni', rotations, tool) + rng.normal(0, noise_mm, (30, 3))
    with (path / 'tcp.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file); writer.writerow(POSE_COLUMNS)
        for i, (r, t) in enumerate(zip(rotations, translations)):
            writer.writerow([f'pose_{i:02d}', *r.ravel(), *t])
    source = rng.uniform(-100, 100, (30, 3))
    r = rotation([1., 2., 3.], 0.7)
    t = np.array([100., -20., 35.])
    target = source @ r.T + t + rng.normal(0, noise_mm, source.shape)
    with (path / 'registration.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file); writer.writerow(POINT_COLUMNS)
        for i, (a, b) in enumerate(zip(source, target)):
            writer.writerow([f'point_{i:02d}', *a, *b])
    truth = {'seed': 7, 'translation_noise_std_mm': noise_mm, 'tool_offset_mm': tool.tolist(),
             'pivot_base_mm': pivot.tolist(), 'rotation_source_to_target': r.tolist(), 'translation_mm': t.tolist()}
    (path / 'truth.json').write_text(json.dumps(truth, indent=2) + '\n', encoding='utf-8')
    return truth
