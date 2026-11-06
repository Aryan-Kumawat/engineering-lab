"""Atomic run artifacts, portable CSV exports and context-aware comparison."""
import csv
import json
import os
from pathlib import Path
import tempfile
import numpy as np
from .experiment import normalize
from .robot import Robot


def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(value,indent=2,allow_nan=False)+'\n';temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as file:
            temporary=file.name;file.write(content)
        os.replace(temporary,path)
    finally:
        if temporary and os.path.exists(temporary):os.unlink(temporary)


def load_run(path):
    path=Path(path)
    if path.stat().st_size>100_000_000:raise ValueError('Run exceeds 100 MB')
    run=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(run,dict) or run.get('schema_version')!=1:raise ValueError('Unsupported run schema')
    try:
        for key in ['run_id','engine_version','backend','created_at','config_sha256']:
            if not isinstance(run[key],str) or not run[key]:raise ValueError('Invalid run metadata '+key)
        robot=Robot.restore(run['robot']);config=normalize(run['experiment'],robot);n=len(robot.active)
        if run['joint_names']!=robot.names:raise ValueError('Run joint names do not match its robot snapshot')
        if run['status'] not in {'completed','failed','cancelled'}:raise ValueError('Invalid run status')
        samples=run['samples']
        if not isinstance(samples,list) or not 1<=len(samples)<=20001:raise ValueError('Invalid sample count')
        previous=-1.
        for row in samples:
            t=row['time_s']
            if not isinstance(t,(int,float)) or not np.isfinite(t) or t<=previous or not 0<=t<=config['duration_s']+1e-8:raise ValueError('Run timestamps must increase within its duration')
            previous=t
            for key in ['positions_rad','velocities_rad_s','measured_positions_rad','targets_rad','target_velocities_rad_s','effort_nm']:
                vector=np.asarray(row[key],dtype=float)
                if vector.shape!=(n,) or not np.isfinite(vector).all():raise ValueError('Invalid sample vector '+key)
            if np.asarray(row['tip_m']).shape!=(3,) or not np.isfinite(row['tip_m']).all():raise ValueError('Invalid tip position')
            if row['clearance_m'] is not None and not np.isfinite(row['clearance_m']):raise ValueError('Invalid clearance')
        for event in run['events']:
            if not isinstance(event,dict) or not isinstance(event['message'],str) or not 0<=event['time_s']<=config['duration_s']+1e-8:raise ValueError('Invalid event')
        if not isinstance(run['metrics'],dict) or not np.isfinite(run['metrics']['rms_error_rad']):raise ValueError('Invalid metrics')
    except (KeyError,TypeError,OverflowError) as exc:raise ValueError('Run artifact is missing or has invalid fields') from exc
    return run


def export_csv(run,path):
    names=run['joint_names']
    header=['time_s']
    keys=['positions_rad','targets_rad','velocities_rad_s','effort_nm']
    for key in keys:header.extend(f'{name}.{key}' for name in names)
    header.extend(['tip_x_m','tip_y_m','tip_z_m','clearance_m'])
    with Path(path).open('w',newline='',encoding='utf-8') as file:
        writer=csv.writer(file);writer.writerow(header)
        for row in run['samples']:writer.writerow([row['time_s'],*[v for key in keys for v in row[key]],*row['tip_m'],row['clearance_m']])


def compare_runs(baseline,current):
    if baseline['robot']!=current['robot']:raise ValueError('Comparison requires the same robot geometry and limits')
    fields=['waypoints','initial_rad','dt_s','duration_s','obstacles','tool_offset_m','link_radius_m','seed',
            'position_noise_std_rad','velocity_noise_std_rad_s','dynamics','goal_tolerance_rad']
    changes=[key for key in fields if baseline['experiment'].get(key)!=current['experiment'].get(key)]
    if baseline['backend']!=current['backend'] or baseline['engine_version']!=current['engine_version']:changes.append('backend_or_engine_version')
    a,b=baseline['metrics']['rms_error_rad'],current['metrics']['rms_error_rad']
    return {'baseline_id':baseline['run_id'],'current_id':current['run_id'],
            'same_experiment_context':not changes,'context_changes':changes,
            'baseline_status':baseline['status'],'current_status':current['status'],
            'rms_error_delta_rad':b-a,'rms_error_change_percent':(b-a)/a*100 if a else None,
            'baseline_rms_error_rad':a,'current_rms_error_rad':b,
            'baseline_observed_duration_s':baseline['metrics']['observed_duration_s'],
            'current_observed_duration_s':current['metrics']['observed_duration_s'],
            'status_regressed':baseline['status']=='completed' and current['status']!='completed',
            'note':'Controller changes are allowed. Other context changes are flagged. Early-terminated runs cover different time intervals.'}
