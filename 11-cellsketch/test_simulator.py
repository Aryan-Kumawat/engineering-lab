import copy
import unittest
from simulator import example,simulate


def station(key,cycle,capacity=1,x=0):
    return {'id':key,'name':key,'kind':'robot','x':x,'y':0.,'cycle_s':cycle,'capacity':capacity}


def model(stations,jobs=3,interval=0,horizon=20):
    return {'schema_version':1,'stations':stations,'jobs':jobs,'arrival_interval_s':interval,'horizon_s':horizon,'travel_speed_m_s':1.}


class SimulatorTests(unittest.TestCase):
    def test_single_station_hand_calculation(self):
        r=simulate(model([station('a',2)],horizon=6))
        self.assertEqual(r['summary']['completed_jobs'],3)
        self.assertEqual(r['summary']['mean_lead_time_s_completed_jobs'],4)
        self.assertEqual(r['stations'][0]['average_queue'],1)
        self.assertEqual(r['stations'][0]['mean_wait_s_started_jobs'],2)
        self.assertEqual(r['stations'][0]['utilization'],1)
    def test_two_stage_pipeline(self):
        r=simulate(model([station('a',2),station('b',3)]))
        times=[e['time_s'] for e in r['events'] if e['event']=='job_complete']
        self.assertEqual(times,[5,8,11])
    def test_layout_changes_travel(self):
        close=simulate(model([station('a',2),station('b',3)],jobs=1))
        far=simulate(model([station('a',2),station('b',3,x=10)],jobs=1))
        self.assertEqual(far['summary']['last_completion_s']-close['summary']['last_completion_s'],10)
    def test_parallel_capacity(self):
        r=simulate(model([station('a',2,capacity=2)],jobs=4,horizon=4))
        self.assertEqual([e['time_s'] for e in r['events'] if e['event']=='job_complete'],[2,2,4,4])
        self.assertEqual(r['stations'][0]['utilization'],1)
    def test_horizon_accounts_for_in_service_and_queued_jobs(self):
        r=simulate(model([station('a',2)],horizon=1))
        self.assertEqual(r['summary']['wip_at_end'],3)
        self.assertEqual(r['stations'][0]['queue_at_end'],2)
        self.assertEqual(r['stations'][0]['busy_at_end'],1)
        self.assertEqual(r['stations'][0]['average_queue'],2)
        self.assertIsNone(r['summary']['mean_lead_time_s_completed_jobs'])
    def test_arrivals_after_horizon_excluded(self):
        r=simulate(model([station('a',1)],jobs=10,interval=10,horizon=5))
        self.assertEqual(r['summary']['arrived_jobs'],1)
        self.assertEqual(r['summary']['completed_jobs'],1)
    def test_determinism_and_input_not_mutated(self):
        m=example();before=copy.deepcopy(m);a=simulate(m);b=simulate(m)
        self.assertEqual(a,b);self.assertEqual(m,before)
    def test_invalid_models(self):
        for key,value in [('jobs',True),('arrival_interval_s',-1),('travel_speed_m_s',0),('horizon_s',float('nan'))]:
            m=example();m[key]=value
            with self.assertRaises(ValueError):simulate(m)
    def test_conservation_and_utilization(self):
        r=simulate(example());s=r['summary']
        self.assertEqual(s['arrived_jobs'],s['completed_jobs']+s['wip_at_end'])
        for station_report in r['stations']:self.assertTrue(0<=station_report['utilization']<=1)


if __name__=='__main__':unittest.main(verbosity=2)
