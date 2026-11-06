"""Restricted serial URDF model and independent forward kinematics."""
from dataclasses import asdict, dataclass
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import numpy as np


@dataclass(frozen=True)
class Joint:
    name: str
    kind: str
    parent: str
    child: str
    xyz: tuple
    rpy: tuple
    axis: tuple
    lower: float = 0.
    upper: float = 0.
    effort: float = 0.
    velocity: float = 0.


@dataclass(frozen=True)
class Robot:
    name: str
    base: str
    joints: tuple

    @property
    def active(self):
        return tuple(j for j in self.joints if j.kind == 'revolute')

    @property
    def names(self):
        return [j.name for j in self.active]

    def snapshot(self):
        joints = []
        for joint in self.joints:
            value = asdict(joint)
            for key in ['xyz', 'rpy', 'axis']: value[key] = list(value[key])
            joints.append(value)
        return {'name': self.name, 'base': self.base, 'joints': joints}

    @classmethod
    def restore(cls, value):
        try:
            robot = cls(value['name'], value['base'], tuple(Joint(**j) for j in value['joints']))
            _validate_robot(robot)
            return robot
        except (KeyError, TypeError) as exc:
            raise ValueError('Invalid robot snapshot') from exc


def vector(text, default):
    values = tuple(float(x) for x in (text or default).split())
    if len(values) != 3 or not all(math.isfinite(v) and abs(v) <= 1000 for v in values):
        raise ValueError('Expected three finite URDF vector components within +/-1000')
    return values


def _validate_robot(robot):
    if not isinstance(robot.name, str) or not robot.name or not isinstance(robot.base, str):
        raise ValueError('Robot name/base required')
    if not 1 <= len(robot.active) <= 8 or len(robot.joints) > 32:
        raise ValueError('Support is limited to 1..8 revolute joints and 32 total joints')
    names = set(); links = {robot.base}; parent = robot.base
    for j in robot.joints:
        if not isinstance(j.name, str) or not j.name or j.name in names:
            raise ValueError('Joint names must be nonempty and unique')
        if j.kind not in {'fixed', 'revolute'} or j.parent != parent or j.child in links:
            raise ValueError('Expected one acyclic serial chain of fixed/revolute joints')
        names.add(j.name); links.add(j.child); parent = j.child
        for value in [j.xyz, j.rpy, j.axis]:
            if len(value) != 3 or not all(math.isfinite(v) and abs(v) <= 1000 for v in value):
                raise ValueError('Invalid joint vector')
        if j.kind == 'revolute':
            if not np.isclose(np.linalg.norm(j.axis), 1, atol=1e-8):
                raise ValueError('Joint axes must be unit vectors')
            if not all(math.isfinite(v) for v in [j.lower, j.upper, j.effort, j.velocity]):
                raise ValueError('Joint limits must be finite')
            if not -100 <= j.lower < j.upper <= 100 or not 0 < j.effort <= 10000 or not 0 < j.velocity <= 100:
                raise ValueError('Joint bounds, effort or velocity outside supported ranges')


def load_urdf(path):
    path = Path(path)
    if path.stat().st_size > 1_000_000:
        raise ValueError('URDF exceeds 1 MB')
    text = path.read_text(encoding='utf-8')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('URDF document/entity declarations are unsupported')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError('Malformed URDF: ' + str(exc)) from exc
    if root.tag != 'robot':
        raise ValueError('Expected a robot element')
    links = [e.get('name') for e in root.findall('link')]
    if not links or any(not n for n in links) or len(set(links)) != len(links):
        raise ValueError('URDF links must have unique names')
    joints = []
    for element in root.findall('joint'):
        kind = element.get('type')
        if kind not in {'fixed', 'revolute'}:
            raise ValueError('Only fixed and bounded revolute URDF joints are supported')
        if element.find('mimic') is not None:
            raise ValueError('Mimic joints are unsupported')
        try:
            parent = element.find('parent').attrib['link']; child = element.find('child').attrib['link']
            origin = element.find('origin'); axis = element.find('axis')
            xyz = vector(origin.get('xyz') if origin is not None else None, '0 0 0')
            rpy = vector(origin.get('rpy') if origin is not None else None, '0 0 0')
            direction = np.asarray(vector(axis.get('xyz') if axis is not None else None, '1 0 0'))
            norm = np.linalg.norm(direction)
            if norm == 0: raise ValueError('Joint axis cannot be zero')
            direction = tuple(direction / norm)
            bounds = [0., 0., 0., 0.]
            if kind == 'revolute':
                limit = element.find('limit')
                if limit is None: raise ValueError('Revolute joint requires limits')
                bounds = [float(limit.attrib[k]) for k in ['lower', 'upper', 'effort', 'velocity']]
            joints.append(Joint(element.attrib['name'], kind, parent, child, xyz, rpy, direction, *bounds))
        except (KeyError, AttributeError, TypeError) as exc:
            raise ValueError('Joint is missing required URDF fields') from exc
    children = [j.child for j in joints]
    if len(set(children)) != len(children): raise ValueError('A link has multiple parents')
    roots = set(links) - set(children)
    if len(roots) != 1: raise ValueError('Expected one connected URDF root link')
    base = roots.pop(); ordered = []; parent = base
    while True:
        following = [j for j in joints if j.parent == parent]
        if not following: break
        if len(following) != 1: raise ValueError('Branched URDFs are unsupported; use a serial arm model')
        j = following[0]
        if j in ordered: raise ValueError('URDF contains a cycle')
        if j.child not in links or j.parent not in links: raise ValueError('Joint references a missing link')
        ordered.append(j); parent = j.child
    if len(ordered) != len(joints) or len(links) != len(joints) + 1:
        raise ValueError('URDF is disconnected or cyclic')
    robot = Robot(root.get('name') or 'robot', base, tuple(ordered)); _validate_robot(robot)
    return robot


def axis_rotation(axis, angle):
    x, y, z = axis
    k = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    return np.eye(3) + math.sin(angle) * k + (1-math.cos(angle)) * (k @ k)


def rpy_rotation(rpy):
    roll, pitch, yaw = rpy
    return axis_rotation((0, 0, 1), yaw) @ axis_rotation((0, 1, 0), pitch) @ axis_rotation((1, 0, 0), roll)


def forward(robot, positions, tool_offset=(0., 0., 0.)):
    positions = np.asarray(positions, dtype=float)
    if positions.shape != (len(robot.active),) or not np.isfinite(positions).all():
        raise ValueError('Expected one finite position per active joint')
    rotation = np.eye(3); translation = np.zeros(3); points = [translation.copy()]; index = 0
    for joint in robot.joints:
        translation = translation + rotation @ np.asarray(joint.xyz)
        rotation = rotation @ rpy_rotation(joint.rpy)
        points.append(translation.copy())
        if joint.kind == 'revolute':
            rotation = rotation @ axis_rotation(joint.axis, positions[index]); index += 1
    tip = translation + rotation @ np.asarray(tool_offset, dtype=float)
    points.append(tip)
    return np.asarray(points), tip


def clearance(points, obstacles, link_radius):
    """Minimum signed capsule/sphere clearance; no swept or self collision test."""
    best = None; obstacle_id = None
    for obstacle in obstacles:
        center = np.asarray(obstacle['center_m']); radius = obstacle['radius_m'] + link_radius
        for a, b in zip(points, points[1:]):
            direction = b-a; norm = float(direction @ direction)
            fraction = np.clip(float((center-a) @ direction) / norm, 0, 1) if norm else 0.
            distance = float(np.linalg.norm(center-(a+fraction*direction))) - radius
            if best is None or distance < best: best = distance; obstacle_id = obstacle['id']
    return best, obstacle_id
