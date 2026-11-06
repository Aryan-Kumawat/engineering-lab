"""Deterministic joint-servo backend and structured experiment diagnostics."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import uuid
import numpy as np
from . import __version__
from .experiment import normalize, target_at
from .robot import forward, clearance


def integrate_servo(q, velocity, effort, inertia, damping, dt):
    """Exact held-effort update for I*qdd + damping*qd = effort."""
    damping = np.asarray(damping); inertia = np.asarray(inertia)
    rate = damping/inertia; z = rate*dt
    # Stable limits for small damping; avoids cancellation in 1-exp(-z).
    response = np.ones_like(z)
    mask = np.abs(z) > 1e-7
    response[mask] = -np.expm1(-z[mask])/z[mask]
    response[~mask] = 1-z[~mask]/2+z[~mask]**2/6
    displacement_acceleration = np.empty_like(z)
    displacement_acceleration[mask] = (1-response[mask])/z[mask]
    displacement_acceleration[~mask] = .5-z[~mask]/6+z[~mask]**2/24
    new_q = q + velocity*dt*response + effort/inertia*dt**2*displacement_acceleration
    new_velocity = velocity*np.exp(-z) + effort/inertia*dt*response
    return new_q, new_velocity


def run_experiment(config, robot, cancel=None, progress=None):
    c = normalize(config, robot); n = len(robot.active); dt = c['dt_s']; steps = round(c['duration_s']/dt)
    rng = np.random.default_rng(c['seed'])
    q = np.asarray(c['initial_rad'],dtype=float); velocity = np.zeros(n); integral = np.zeros(n)
    kp,ki,kd = [np.asarray(c['controller'][k]) for k in ['kp','ki','kd']]
    inertia,damping = [np.asarray(c['dynamics'][k]) for k in ['inertia','damping']]
    limits = np.asarray([j.effort for j in robot.active]); speed_limits = np.asarray([j.velocity for j in robot.active])
    lower = np.asarray([j.lower for j in robot.active]); upper = np.asarray([j.upper for j in robot.active])
    saturated = np.zeros(n,dtype=bool); speed_clipped = np.zeros(n,dtype=bool); counts = np.zeros(n,dtype=int)
    samples = []; events = []; status = 'completed'; reason = None; pending_limit = []
    def event(time, level, code, message):
        events.append({'time_s':float(time),'level':level,'code':code,'message':message})
    event(0, 'info', 'run_started', c['name'])
    for k in range(steps+1):
        time = k*dt
        target, target_velocity = target_at(c['waypoints'],time)
        measured = q+rng.normal(0,c['position_noise_std_rad'],n)
        measured_velocity = velocity+rng.normal(0,c['velocity_noise_std_rad_s'],n)
        error = target-measured; candidate = integral+error*dt
        raw = kp*error+ki*candidate+kd*(target_velocity-measured_velocity)
        effort = np.clip(raw,-limits,limits)
        accept = (raw==effort) | ((raw-effort)*error<0)
        integral = np.where(accept,candidate,integral)
        raw = kp*error+ki*integral+kd*(target_velocity-measured_velocity)
        effort = np.clip(raw,-limits,limits)
        now_saturated = np.abs(raw)>limits
        for index,joint in enumerate(robot.active):
            if now_saturated[index] and not saturated[index]:
                event(time,'warning','effort_saturated',joint.name+' reached its effort limit')
            elif saturated[index] and not now_saturated[index]:
                event(time,'info','effort_recovered',joint.name+' left effort saturation')
        saturated = now_saturated
        points,tip = forward(robot,q,c['tool_offset_m'])
        distance,obstacle = clearance(points,c['obstacles'],c['link_radius_m'])
        samples.append({'time_s':time,'positions_rad':q.tolist(),'velocities_rad_s':velocity.tolist(),
                        'measured_positions_rad':measured.tolist(),'targets_rad':target.tolist(),
                        'target_velocities_rad_s':target_velocity.tolist(),'effort_nm':effort.tolist(),
                        'tip_m':tip.tolist(),'clearance_m':distance})
        if progress and (k%50==0 or k==steps):progress(k/steps)
        if cancel is not None and cancel.is_set():
            status='cancelled';reason='user_cancelled';event(time,'info',reason,'Experiment cancelled at a sample boundary');break
        if pending_limit:
            status='failed';reason='joint_limit';event(time,'error',reason,'Hard joint limit reached: '+', '.join(pending_limit));break
        if distance is not None and distance<=0:
            status='failed';reason='collision';event(time,'error',reason,'Link capsule intersects sphere '+obstacle);break
        if k==steps:break
        counts += now_saturated
        next_q,next_velocity = integrate_servo(q,velocity,effort,inertia,damping,dt)
        if not np.isfinite(next_q).all() or not np.isfinite(next_velocity).all():
            status='failed';reason='numeric_failure';event(time,'error',reason,'Joint dynamics became nonfinite');break
        current_clip = np.abs(next_velocity)>speed_limits
        for index,joint in enumerate(robot.active):
            if current_clip[index] and not speed_clipped[index]:event(time+dt,'warning','velocity_clipped',joint.name+' reached velocity limit')
        speed_clipped=current_clip
        # Velocity bounding is a simplified actuator limit, not a collision/contact impulse solver.
        next_velocity = np.clip(next_velocity,-speed_limits,speed_limits)
        pending_limit=[j.name for i,j in enumerate(robot.active) if next_q[i]<lower[i] or next_q[i]>upper[i]]
        q=np.clip(next_q,lower,upper);velocity=next_velocity
    times=np.asarray([s['time_s'] for s in samples]);errors=np.asarray([s['targets_rad'] for s in samples])-np.asarray([s['positions_rad'] for s in samples])
    elapsed=float(times[-1])
    squared=errors**2
    if elapsed:
        mse=np.sum((squared[:-1]+squared[1:])*.5*np.diff(times)[:,None],axis=0)/elapsed
    else:mse=squared[0]
    final_error=errors[-1]
    final_goal_error=np.asarray(c['waypoints'][-1]['positions_rad'])-np.asarray(samples[-1]['positions_rad'])
    goal_reached=bool(np.all(np.abs(final_goal_error)<=c['goal_tolerance_rad']))
    if status=='completed' and not goal_reached:
        status='failed';reason='goal_missed';event(elapsed,'error',reason,'Final tracking error exceeds the configured goal tolerance')
    clearances=[s['clearance_m'] for s in samples if s['clearance_m'] is not None]
    metrics={'observed_duration_s':elapsed,'rms_error_rad':float(np.sqrt(np.mean(mse))),
             'rms_per_joint_rad':np.sqrt(mse).tolist(),'final_error_rad':final_error.tolist(),'final_goal_error_rad':final_goal_error.tolist(),
             'peak_abs_error_rad':np.max(np.abs(errors),axis=0).tolist(),
             'effort_saturation_fraction':(counts/max(1,len(samples)-1)).tolist(),
             'minimum_clearance_m':min(clearances) if clearances else None,'goal_reached':goal_reached}
    event(elapsed,'info','run_finished',status+((': '+reason) if reason else ''))
    config_hash=hashlib.sha256(json.dumps({'experiment':c,'robot':robot.snapshot()},sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {'schema_version':1,'engine_version':__version__,'backend':'decoupled_joint_servo_v1',
            'run_id':uuid.uuid4().hex,'created_at':datetime.now(timezone.utc).isoformat(),
            'config_sha256':config_hash,'joint_names':robot.names,'robot':robot.snapshot(),
            'experiment':copy.deepcopy(c),'status':status,'failure_reason':reason,'metrics':metrics,
            'events':events,'samples':samples}
