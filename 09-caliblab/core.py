"""Calibration mathematics, input contracts and independent validation."""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

POSE_COLUMNS = ['id'] + [f'r{i}{j}' for i in range(1, 4) for j in range(1, 4)] + ['tx', 'ty', 'tz']
POINT_COLUMNS = ['id', 'source_x', 'source_y', 'source_z', 'target_x', 'target_y', 'target_z']


def read_csv(path, mode):
    columns = POSE_COLUMNS if mode == 'tcp' else POINT_COLUMNS
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != columns:
            raise ValueError('Expected exact CSV header: ' + ','.join(columns))
        ids, values = [], []
        for line, row in enumerate(reader, 2):
            if len(ids) >= 10000:
                raise ValueError('At most 10,000 observations are supported')
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'Row {line}: wrong number of fields')
            key = row['id'].strip()
            if not key or key in ids:
                raise ValueError(f'Row {line}: IDs must be nonempty and unique')
            try:
                vector = [float(row[c]) for c in columns[1:]]
            except ValueError as exc:
                raise ValueError(f'Row {line}: nonnumeric measurement') from exc
            if not np.isfinite(vector).all():
                raise ValueError(f'Row {line}: measurements must be finite')
            ids.append(key)
            values.append(vector)
    if len(ids) < 8:
        raise ValueError('Provide at least 8 observations for fitting and held-out validation')
    data = np.asarray(values)
    if mode == 'tcp':
        rotations, translations = data[:, :9].reshape(-1, 3, 3), data[:, 9:]
        validate_poses(rotations, translations)
        return ids, (rotations, translations)
    return ids, (data[:, :3], data[:, 3:])


def validate_poses(rotations, translations):
    r, t = np.asarray(rotations), np.asarray(translations)
    if r.ndim != 3 or r.shape[1:] != (3, 3) or t.shape != (len(r), 3):
        raise ValueError('Expected N rotation matrices and N translation vectors')
    if not np.isfinite(r).all() or not np.isfinite(t).all():
        raise ValueError('All pose entries must be finite')
    if not np.allclose(r.transpose(0, 2, 1) @ r, np.eye(3), atol=1e-5, rtol=0):
        raise ValueError('Rotation matrices must be orthonormal; no automatic repair is applied')
    if not np.allclose(np.linalg.det(r), 1, atol=1e-5, rtol=0):
        raise ValueError('Rotation determinant must be +1 (right-handed frame)')


def fit_tcp(rotations, translations):
    """Solve R_i * tool + t_i = pivot for tool and common base-frame pivot."""
    validate_poses(rotations, translations)
    if len(rotations) < 3:
        raise ValueError('At least 3 varied poses are required')
    matrix = np.concatenate([rotations, np.broadcast_to(-np.eye(3), rotations.shape)], axis=2).reshape(-1, 6)
    vector = -translations.reshape(-1)
    solution, _, rank, singular = np.linalg.lstsq(matrix, vector, rcond=None)
    if rank != 6:
        raise ValueError('Unobservable TCP: use rotations about multiple different axes')
    condition = float(singular[0] / singular[-1])
    if condition > 1e8:
        raise ValueError('Ill-conditioned pose set: collect more diverse orientations')
    return {'tool_offset_mm': solution[:3].tolist(), 'pivot_base_mm': solution[3:].tolist(),
            'design_condition_number': condition}


def fit_registration(source, target):
    """Kabsch rigid transform: target = R * source + t; no scale fitting."""
    source, target = np.asarray(source, dtype=float), np.asarray(target, dtype=float)
    if source.ndim != 2 or source.shape[1:] != (3,) or source.shape != target.shape or len(source) < 3:
        raise ValueError('Provide at least 3 paired 3D points of matching shape')
    if not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError('Points must be finite')
    a, b = source - source.mean(axis=0), target - target.mean(axis=0)
    for cloud in (a, b):
        s = np.linalg.svd(cloud, compute_uv=False)
        if s[0] == 0 or s[1] / s[0] < 1e-6:
            raise ValueError('Points are coincident or nearly collinear; spread them over a plane or volume')
    u, _, vt = np.linalg.svd(a.T @ b)
    correction = np.eye(3)
    correction[2, 2] = np.linalg.det(vt.T @ u.T)
    rotation = vt.T @ correction @ u.T
    translation = target.mean(axis=0) - rotation @ source.mean(axis=0)
    return {'rotation_source_to_target': rotation.tolist(), 'translation_mm': translation.tolist()}


def calibrate(path, mode='tcp', warning_mm=0.5):
    if mode not in {'tcp', 'registration'}:
        raise ValueError('Mode must be tcp or registration')
    if not np.isfinite(warning_mm) or warning_mm <= 0:
        raise ValueError('Warning threshold must be positive and finite')
    ids, (a, b) = read_csv(path, mode)
    # Every fifth observation is held out BEFORE any fitting, with no random split drift.
    test = np.arange(len(ids)) % 5 == 0
    train = ~test
    if mode == 'tcp':
        model = fit_tcp(a[train], b[train])
        errors = np.einsum('nij,j->ni', a, model['tool_offset_mm']) + b - model['pivot_base_mm']
    else:
        model = fit_registration(a[train], b[train])
        errors = a @ np.asarray(model['rotation_source_to_target']).T + model['translation_mm'] - b
    lengths = np.linalg.norm(errors, axis=1)
    observations = [{'id': key, 'split': 'held_out' if test[i] else 'fit',
                     'residual_mm': float(lengths[i]), 'error_xyz_mm': errors[i].tolist(),
                     'above_warning_threshold': bool(lengths[i] > warning_mm)} for i, key in enumerate(ids)]
    def summary(mask):
        e = lengths[mask]
        return {'count': int(mask.sum()), 'rms_mm': float(np.sqrt(np.mean(e**2))),
                'max_mm': float(e.max()), 'median_mm': float(np.median(e))}
    warnings = []
    if any(row['above_warning_threshold'] for row in observations):
        warnings.append('Some residuals exceed the chosen warning threshold; inspect observations and frame conventions.')
    if mode == 'tcp' and model['design_condition_number'] > 100:
        warnings.append('Limited orientation diversity: the TCP fit is sensitive to measurement error.')
    report = {'schema_version': 1, 'mode': mode, 'units': 'mm',
              'input_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
              'split_rule': 'zero-based rows 0,5,10,... held out; all remaining rows fitted',
              'warning_threshold_mm': warning_mm, 'model': model,
              'fit': summary(train), 'held_out': summary(test),
              'observations': observations, 'warnings': warnings}
    if not all(np.isfinite(row['residual_mm']) for row in observations):
        raise ValueError('Numerical overflow; check measurement magnitudes')
    return report


def save_report(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    with (directory / 'residuals.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'split', 'residual_mm', 'error_x_mm', 'error_y_mm', 'error_z_mm', 'above_warning_threshold'])
        for row in report['observations']:
            writer.writerow([row['id'], row['split'], row['residual_mm'], *row['error_xyz_mm'], row['above_warning_threshold']])
