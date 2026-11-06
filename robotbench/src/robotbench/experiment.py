"""Versioned experiment input validation and target generation."""
import copy
import json
import math
from pathlib import Path
import numpy as np
from .robot import load_urdf


def number(value, name, lower, upper):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f'{name} must be finite and between {lower} and {upper}')
    return float(value)


def joint_vector(value, count, name, lower=-100, upper=100):
    if isinstance(value, (int, float)) and not isinstance(value, bool): value = [value] * count
    if not isinstance(value, list) or len(value) != count: raise ValueError(name + ' needs one value per joint (or a scalar)')
    return [number(v, name, lower, upper) for v in value]


def normalize(raw, robot):
    if not isinstance(raw, dict) or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
        raise ValueError('Experiment schema_version must be 1')
    allowed = {'schema_version','name','robot','dt_s','duration_s','seed','initial_rad','waypoints','controller','dynamics',
               'position_noise_std_rad','velocity_noise_std_rad_s','obstacles','link_radius_m','tool_offset_m','goal_tolerance_rad'}
    if set(raw)-allowed: raise ValueError('Unknown experiment fields: '+', '.join(sorted(set(raw)-allowed)))
    c = copy.deepcopy(raw); n = len(robot.active)
    if not isinstance(c.get('name'), str) or not 1 <= len(c['name']) <= 100: raise ValueError('Experiment name required (1..100 characters)')
    if not isinstance(c.get('robot'), str) or not c['robot']: raise ValueError('robot must name a URDF path')
    c['dt_s'] = number(c.get('dt_s', .01), 'dt_s', .001, .1)
    c['duration_s'] = number(c.get('duration_s', 8), 'duration_s', c['dt_s'], 120)
    steps = c['duration_s']/c['dt_s']
    if not math.isclose(steps, round(steps), abs_tol=1e-7) or steps > 20000: raise ValueError('Duration must be an integer multiple of dt, at most 20,000 intervals')
    c['seed'] = c.get('seed', 7)
    if type(c['seed']) is not int or not 0 <= c['seed'] < 2**32: raise ValueError('Seed must be an integer in [0, 2^32)')
    c['initial_rad'] = joint_vector(c.get('initial_rad', [0.] * n), n, 'initial_rad')
    c['tool_offset_m'] = joint_vector(c.get('tool_offset_m', [0., 0., 0.]), 3, 'tool_offset_m', -10, 10)
    c['link_radius_m'] = number(c.get('link_radius_m', .025), 'link_radius_m', .001, 1)
    c['goal_tolerance_rad'] = number(c.get('goal_tolerance_rad', .03), 'goal_tolerance_rad', 1e-6, 1)
    c['position_noise_std_rad'] = number(c.get('position_noise_std_rad', 0), 'position noise', 0, .5)
    c['velocity_noise_std_rad_s'] = number(c.get('velocity_noise_std_rad_s', 0), 'velocity noise', 0, 5)
    for group, defaults in [('controller', {'kp':35., 'ki':0., 'kd':9.}), ('dynamics', {'inertia':1., 'damping':.3})]:
        values = c.get(group, {})
        if not isinstance(values, dict) or set(values)-set(defaults): raise ValueError('Unknown '+group+' parameters')
        c[group] = {key:joint_vector(values.get(key, default), n, group+'.'+key, .001 if key=='inertia' else 0, 1000) for key, default in defaults.items()}
    waypoints = c.get('waypoints')
    if not isinstance(waypoints, list) or not 2 <= len(waypoints) <= 100: raise ValueError('Provide 2..100 waypoints, beginning at t=0')
    previous = -1.; clean = []
    for waypoint in waypoints:
        if not isinstance(waypoint, dict) or set(waypoint) != {'time_s','positions_rad'}: raise ValueError('Waypoint needs time_s and positions_rad')
        t = number(waypoint['time_s'], 'waypoint time', 0, c['duration_s'])
        if t <= previous: raise ValueError('Waypoint times must strictly increase')
        clean.append({'time_s':t, 'positions_rad':joint_vector(waypoint['positions_rad'], n, 'positions_rad')}); previous = t
    if clean[0]['time_s'] != 0: raise ValueError('First waypoint must be at time zero')
    c['waypoints'] = clean
    for vector in [c['initial_rad'], *[w['positions_rad'] for w in clean]]:
        if any(not j.lower <= q <= j.upper for j, q in zip(robot.active, vector)): raise ValueError('Initial/target position exceeds URDF joint limits')
    obstacles = c.get('obstacles', [])
    if not isinstance(obstacles, list) or len(obstacles) > 20: raise ValueError('At most 20 sphere obstacles are supported')
    ids = set(); clean = []
    for obstacle in obstacles:
        if not isinstance(obstacle, dict) or set(obstacle) != {'id','center_m','radius_m'}: raise ValueError('Obstacle needs id, center_m and radius_m')
        key = obstacle['id']
        if not isinstance(key,str) or not 1 <= len(key) <= 80 or key in ids: raise ValueError('Obstacle IDs must be unique and nonempty')
        ids.add(key);clean.append({'id':key,'center_m':joint_vector(obstacle['center_m'],3,'obstacle center',-100,100),
                                  'radius_m':number(obstacle['radius_m'],'obstacle radius',.001,10)})
    c['obstacles'] = clean
    return c


def load_experiment(path):
    path = Path(path).resolve()
    if path.stat().st_size > 200000: raise ValueError('Experiment JSON exceeds 200 KB')
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or not isinstance(raw.get('robot'), str): raise ValueError('Expected experiment object with a robot path')
    return prepare_experiment(raw, path.parent)


def prepare_experiment(raw, directory):
    if not isinstance(raw, dict) or not isinstance(raw.get('robot'), str): raise ValueError('Expected an experiment object with a robot path')
    directory = Path(directory).resolve()
    robot_path = Path(raw['robot'])
    if robot_path.is_absolute(): raise ValueError('URDF path must be relative to the experiment directory')
    resolved = (directory/robot_path).resolve()
    if not resolved.is_relative_to(directory): raise ValueError('URDF must be inside the experiment directory')
    robot = load_urdf(resolved)
    return normalize(raw, robot), robot


def target_at(waypoints, time):
    for a,b in zip(waypoints,waypoints[1:]):
        if time <= b['time_s']:
            duration=b['time_s']-a['time_s'];u=max(0.,(time-a['time_s'])/duration)
            blend=10*u**3-15*u**4+6*u**5;rate=(30*u**2-60*u**3+30*u**4)/duration
            start=np.asarray(a['positions_rad']);delta=np.asarray(b['positions_rad'])-start
            return start+delta*blend,delta*rate
    return np.asarray(waypoints[-1]['positions_rad']),np.zeros(len(waypoints[-1]['positions_rad']))
