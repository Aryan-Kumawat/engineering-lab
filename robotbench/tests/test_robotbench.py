import copy
import csv
import json
from pathlib import Path
import tempfile
import threading
import unittest
import numpy as np
from robotbench.engine import integrate_servo,run_experiment
from robotbench.experiment import load_experiment,normalize,prepare_experiment,target_at
from robotbench.results import atomic_json,load_run,compare_runs,export_csv
from robotbench.robot import load_urdf,Robot,forward,clearance
from robotbench.workspace import initialize,save_workspace_run,discover_runs


class RobotBenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.workspace=initialize(Path(self.temp.name)/'workspace')
        self.config,self.robot=load_experiment(self.workspace/'reach.json')

    def test_forward_kinematics_known_positions(self):
        _,tip=forward(self.robot,[0,0,0],[.08,0,0]);np.testing.assert_allclose(tip,[.98,0,.25],atol=1e-12)
        _,tip=forward(self.robot,[np.pi/2,0,0],[.08,0,0]);np.testing.assert_allclose(tip,[0,.98,.25],atol=1e-12)
        _,tip=forward(self.robot,[0,-np.pi/2,0],[.08,0,0]);np.testing.assert_allclose(tip,[0,0,1.23],atol=1e-12)

    def test_robot_snapshot_roundtrip(self):
        snapshot=self.robot.snapshot();restored=Robot.restore(json.loads(json.dumps(snapshot)))
        self.assertEqual(snapshot,restored.snapshot())

    def test_urdf_unsupported_type(self):
        path=self.workspace/'bad.urdf';path.write_text((self.workspace/'arm.urdf').read_text().replace('type="revolute"','type="continuous"',1))
        with self.assertRaisesRegex(ValueError,'bounded revolute'):load_urdf(path)

    def test_urdf_invalid_limits(self):
        path=self.workspace/'bad.urdf';path.write_text((self.workspace/'arm.urdf').read_text().replace('effort="15"','effort="-1"'))
        with self.assertRaises(ValueError):load_urdf(path)

    def test_urdf_cycle_or_branch_rejected(self):
        path=self.workspace/'bad.urdf';path.write_text((self.workspace/'arm.urdf').read_text().replace('parent link="forearm"','parent link="base"'))
        with self.assertRaises(ValueError):load_urdf(path)

    def test_no_damping_matches_constant_acceleration(self):
        q,v=integrate_servo(np.zeros(2),np.zeros(2),np.array([2.,4.]),np.ones(2),np.zeros(2),.1)
        np.testing.assert_allclose(q,[.01,.02],atol=1e-14);np.testing.assert_allclose(v,[.2,.4],atol=1e-14)

    def test_damped_integrator_exact_solution(self):
        q,v=integrate_servo(np.array([0.]),np.array([0.]),np.array([2.]),np.array([1.]),np.array([.5]),2)
        self.assertAlmostEqual(v[0],4*(1-np.exp(-1)))
        self.assertAlmostEqual(q[0],4*(2-2*(1-np.exp(-1))))

    def test_target_endpoints_and_smooth_velocity(self):
        w=[{'time_s':0,'positions_rad':[0,0]},{'time_s':2,'positions_rad':[1,2]}]
        for time,expected in [(0,[0,0]),(2,[1,2]),(3,[1,2])]:
            q,v=target_at(w,time);np.testing.assert_allclose(q,expected);np.testing.assert_allclose(v,0,atol=1e-12)
        np.testing.assert_allclose(target_at(w,1)[0],[.5,1])

    def test_seeded_runs_are_numerically_reproducible(self):
        a=run_experiment(self.config,self.robot);b=run_experiment(self.config,self.robot)
        self.assertEqual(a['samples'],b['samples']);self.assertEqual(a['events'],b['events']);self.assertEqual(a['metrics'],b['metrics'])
        self.assertNotEqual(a['run_id'],b['run_id'])

    def test_nominal_controller_reaches_goal(self):
        r=run_experiment(self.config,self.robot)
        self.assertEqual(r['status'],'completed');self.assertLess(r['metrics']['rms_error_rad'],.02)
        self.assertEqual(len(r['samples']),801)

    def test_poor_controller_is_a_diagnosed_failure(self):
        c,robot=load_experiment(self.workspace/'poor_tuning.json');r=run_experiment(c,robot)
        self.assertEqual(r['status'],'failed');self.assertEqual(r['failure_reason'],'goal_missed')

    def test_noise_seed_changes_measurements(self):
        c=copy.deepcopy(self.config);c['seed']+=1
        a=run_experiment(self.config,self.robot);b=run_experiment(c,self.robot)
        self.assertNotEqual(a['samples'][0]['measured_positions_rad'],b['samples'][0]['measured_positions_rad'])

    def test_capsule_clearance(self):
        points=np.array([[0.,0,0],[1,0,0]])
        value,key=clearance(points,[{'id':'sphere','center_m':[.5,.2,0],'radius_m':.1}],.025)
        self.assertAlmostEqual(value,.075);self.assertEqual(key,'sphere')

    def test_collision_stops_on_first_sample(self):
        c=copy.deepcopy(self.config);c['initial_rad']=[0,0,0];c['obstacles']=[{'id':'blocker','center_m':[.7,0,.25],'radius_m':.1}]
        r=run_experiment(c,self.robot)
        self.assertEqual(r['failure_reason'],'collision');self.assertEqual(len(r['samples']),1)

    def test_joint_limit_has_structured_failure(self):
        c=copy.deepcopy(self.config);c['duration_s']=.5;c['initial_rad']=[2.7,-.4,.8]
        c['waypoints']=[{'time_s':0,'positions_rad':[2.8,-.4,.8]},{'time_s':.1,'positions_rad':[2.8,-.4,.8]}]
        c['controller']={'kp':1000,'ki':0,'kd':0};c['position_noise_std_rad']=0;c['velocity_noise_std_rad_s']=0
        r=run_experiment(c,self.robot);self.assertEqual(r['failure_reason'],'joint_limit')
        self.assertTrue(any(e['code']=='effort_saturated' for e in r['events']))
        self.assertTrue(all(abs(row['effort_nm'][0])<=15 for row in r['samples']))

    def test_cancellation_is_saved_as_result(self):
        cancel=threading.Event();cancel.set();r=run_experiment(self.config,self.robot,cancel)
        self.assertEqual(r['status'],'cancelled');self.assertEqual(len(r['samples']),1)
        path=save_workspace_run(self.workspace,r);self.assertEqual(load_run(path)['status'],'cancelled')

    def test_invalid_configuration(self):
        for key,value in [('seed',True),('dt_s',0),('duration_s',8.003),('goal_tolerance_rad',float('nan'))]:
            c=copy.deepcopy(self.config);c[key]=value
            with self.assertRaises(ValueError):normalize(c,self.robot)
        c=copy.deepcopy(self.config);c['waypoints'][1]['positions_rad'][0]=100
        with self.assertRaises(ValueError):normalize(c,self.robot)

    def test_robot_path_cannot_escape_workspace(self):
        c=copy.deepcopy(self.config);c['robot']='../arm.urdf'
        with self.assertRaisesRegex(ValueError,'inside'):prepare_experiment(c,self.workspace)

    def test_run_artifact_roundtrip_and_csv(self):
        r=run_experiment(self.config,self.robot);path=save_workspace_run(self.workspace,r)
        self.assertEqual(load_run(path),r);self.assertEqual(discover_runs(self.workspace),[path])
        csv_path=self.workspace/'signals.csv';export_csv(r,csv_path)
        with csv_path.open(newline='') as file:rows=list(csv.reader(file))
        self.assertEqual(len(rows),len(r['samples'])+1);self.assertIn('yaw.positions_rad',rows[0])

    def test_loaded_baseline_compares_with_fresh_run(self):
        a=run_experiment(self.config,self.robot);path=save_workspace_run(self.workspace,a)
        b=run_experiment(self.config,self.robot);comparison=compare_runs(load_run(path),b)
        self.assertTrue(comparison['same_experiment_context']);self.assertEqual(comparison['rms_error_delta_rad'],0)

    def test_context_changes_are_reported(self):
        a=run_experiment(self.config,self.robot);c=copy.deepcopy(self.config);c['seed']=10
        b=run_experiment(c,self.robot);comparison=compare_runs(a,b)
        self.assertFalse(comparison['same_experiment_context']);self.assertIn('seed',comparison['context_changes'])

    def test_malformed_run_rejected(self):
        r=run_experiment(self.config,self.robot);r['samples'][1]['time_s']=0
        path=self.workspace/'bad.run.json';atomic_json(path,r)
        with self.assertRaisesRegex(ValueError,'timestamps'):load_run(path)

    def test_collision_demo_fails_after_motion(self):
        c,robot=load_experiment(self.workspace/'collision.json');result=run_experiment(c,robot)
        self.assertEqual(result['failure_reason'],'collision')
        self.assertGreater(result['metrics']['observed_duration_s'],0)
        self.assertFalse(result['metrics']['goal_reached'])

    def test_cli_failure_returns_one_and_keeps_artifact(self):
        import contextlib,io
        from robotbench.cli import main
        path=self.workspace/'failure.run.json'
        with contextlib.redirect_stdout(io.StringIO()):
            code=main(['run',str(self.workspace/'poor_tuning.json'),'--output',str(path)])
        self.assertEqual(code,1);self.assertEqual(load_run(path)['failure_reason'],'goal_missed')

    def test_initialization_never_overwrites_existing_workspace(self):
        with self.assertRaises(ValueError):initialize(self.workspace)


if __name__=='__main__':unittest.main(verbosity=2)
