"""ASCII PLY/PCD loading and portable axis-aligned 3D annotations."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

MAX_POINTS = 1_000_000
MAX_BYTES = 50_000_000


def load_cloud(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('Point cloud exceeds the 50 MB input limit')
    with path.open(encoding='utf-8-sig') as stream:
        if path.suffix.lower() == '.ply':
            names, count = _ply_header(stream)
        elif path.suffix.lower() == '.pcd':
            names, count = _pcd_header(stream)
        else:
            raise ValueError('Choose an ASCII .ply or .pcd file')
        if not 1 <= count <= MAX_POINTS:
            raise ValueError('Point count must be between 1 and 1,000,000')
        positions = []
        try:
            indices = [names.index(axis) for axis in ['x', 'y', 'z']]
        except ValueError as exc:
            raise ValueError('Point properties must contain x, y and z') from exc
        for i in range(count):
            line = stream.readline()
            if not line:
                raise ValueError(f'File ended before point {i + 1}')
            fields = line.split()
            if len(fields) != len(names):
                raise ValueError(f'Point {i + 1}: wrong field count')
            try:
                positions.append([float(fields[index]) for index in indices])
            except ValueError as exc:
                raise ValueError(f'Point {i + 1}: invalid coordinate') from exc
    return validate_points(positions)


def _ply_header(stream):
    if stream.readline().strip() != 'ply':
        raise ValueError('Invalid PLY magic')
    names, count, current = [], None, None
    format_ok = False
    vertex_seen = False
    for _ in range(500):
        line = stream.readline()
        if not line:
            break
        fields = line.split()
        if not fields or fields[0] in {'comment', 'obj_info'}:
            continue
        if fields[0] == 'format':
            format_ok = fields == ['format', 'ascii', '1.0']
        elif fields[0] == 'element':
            if len(fields) != 3:
                raise ValueError('Invalid PLY element header')
            current = fields[1]
            if current == 'vertex':
                if vertex_seen:
                    raise ValueError('Duplicate vertex element')
                vertex_seen = True
                count = int(fields[2])
            elif not vertex_seen and int(fields[2]) != 0:
                raise ValueError('PLY vertex element must be the first nonempty element')
        elif fields[0] == 'property' and current == 'vertex':
            if len(fields) != 3 or fields[1] == 'list':
                raise ValueError('PLY vertex properties must be scalar')
            names.append(fields[2])
        elif fields[0] == 'end_header':
            if not format_ok or count is None or len(names) != len(set(names)):
                raise ValueError('Expected ASCII PLY 1.0 with unique vertex properties')
            return names, count
    raise ValueError('Missing PLY end_header or oversized header')


def _pcd_header(stream):
    header = {}
    for _ in range(500):
        line = stream.readline()
        if not line:
            break
        fields = line.split()
        if not fields or fields[0].startswith('#'):
            continue
        key = fields[0].upper()
        if key in header:
            raise ValueError('Duplicate PCD header field: ' + key)
        header[key] = fields[1:]
        if key == 'DATA':
            if fields[1:] != ['ascii']:
                raise ValueError('Only ASCII PCD is supported')
            names = header.get('FIELDS', [])
            if not names or len(names) != len(set(names)):
                raise ValueError('PCD FIELDS must be unique')
            counts = [int(x) for x in header.get('COUNT', ['1'] * len(names))]
            if len(counts) != len(names) or any(x != 1 for x in counts):
                raise ValueError('PCD requires scalar COUNT 1 for each field')
            if 'POINTS' not in header or len(header['POINTS']) != 1:
                raise ValueError('PCD POINTS count required')
            return names, int(header['POINTS'][0])
    raise ValueError('Missing PCD DATA header')


def validate_points(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not 1 <= len(points) <= MAX_POINTS:
        raise ValueError('Expected 1..1,000,000 XYZ points')
    if not np.isfinite(points).all() or np.abs(points).max() > 1e9:
        raise ValueError('Coordinates must be finite and within +/-1e9 input units')
    return points


def fingerprint(points):
    points = validate_points(points)
    # Explicit little-endian float64 encoding makes identity portable.
    return hashlib.sha256(np.asarray(points, dtype='<f8').tobytes()).hexdigest()


def validate_box(box):
    if not isinstance(box, dict) or set(box) != {'id', 'label', 'min', 'max'}:
        raise ValueError('Box needs exactly id, label, min and max fields')
    for key in ['id', 'label']:
        if not isinstance(box[key], str) or not 1 <= len(box[key]) <= 80:
            raise ValueError(key + ' must contain 1..80 characters')
    low, high = np.asarray(box['min'], dtype=float), np.asarray(box['max'], dtype=float)
    if low.shape != (3,) or high.shape != (3,) or not np.isfinite([low, high]).all():
        raise ValueError('Box bounds must be finite XYZ vectors')
    if np.any(high <= low) or np.abs([low, high]).max() > 1e9:
        raise ValueError('Box max must exceed min on every axis, within +/-1e9 units')
    return {'id': box['id'], 'label': box['label'], 'min': low.tolist(), 'max': high.tolist()}


def annotation_document(points, boxes):
    if len(boxes) > 500:
        raise ValueError('At most 500 boxes are supported')
    boxes = [validate_box(box) for box in boxes]
    if len({b['id'] for b in boxes}) != len(boxes):
        raise ValueError('Box IDs must be unique')
    return {'schema_version': 1, 'coordinates': 'source_xyz', 'box_type': 'axis_aligned',
            'cloud_sha256': fingerprint(points), 'point_count': len(points), 'boxes': boxes}


def load_annotations(path, points):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError('Annotation file exceeds 2 MB')
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or document.get('schema_version') != 1:
        raise ValueError('Unsupported annotation schema')
    if document.get('coordinates') != 'source_xyz' or document.get('box_type') != 'axis_aligned':
        raise ValueError('Expected source-coordinate axis-aligned boxes')
    if not isinstance(document.get('boxes'), list):
        raise ValueError('Expected boxes array')
    checked = annotation_document(points, document['boxes'])
    if document.get('cloud_sha256') != checked['cloud_sha256'] or document.get('point_count') != len(points):
        raise ValueError('Annotation cloud identity does not match the loaded points')
    return checked['boxes']


def save_annotations(path, points, boxes):
    path = Path(path)
    document = annotation_document(points, boxes)
    data = json.dumps(document, indent=2, allow_nan=False) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
            temporary = file.name
            file.write(data)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def demo_points():
    rng = np.random.default_rng(21)
    ground = np.column_stack((rng.uniform(-5, 5, (2500, 2)), rng.normal(0, 0.01, 2500)))
    objects = [rng.uniform([-1, -1, 0], [0.2, 0.3, 1.8], (1800, 3)),
               rng.uniform([1, 1, 0], [3, 2.3, 1.1], (1800, 3))]
    return np.vstack([ground, *objects])
