import unittest
from simulator.engine import Task,Job,allocation,simulate
from simulator.model import Profile,Settings,job_cost,overhead

class SimulatorTests(unittest.TestCase):
    def job(self,id='j',origin='expensive',arrival=0,duration=10,klass=0,tasks=None):
        return Job(id,origin,arrival,duration,duration,klass,.5,tasks or (Task(.5,.5),))
    def profiles(self,name,t):return Profile(name,20,10 if name=='cheap' else 100)
    def run_sim(self,jobs,horizon=20,nodes=None,scheduler='geosched',settings=Settings()):
        return simulate(jobs,nodes or {'cheap':[(1,1)],'expensive':[(1,1)]},self.profiles,horizon,scheduler,settings)
    def test_atomic_reservations_and_fragmentation(self):
        nodes=[[.5,.5],[.5,.5]]
        self.assertIsNone(allocation(nodes,[Task(.6,.1)]))
        self.assertIsNone(allocation(nodes,[Task(.4,.4)]*3))
        self.assertEqual(nodes,[[.5,.5],[.5,.5]])
        self.assertEqual(allocation(nodes,[Task(.4,.4)]*2),[0,1])
    def test_batch_moves_and_latency_stays(self):
        r=self.run_sim([self.job(),self.job('sensitive',klass=2)])
        self.assertEqual(r['sites']['cheap']['moved'],1)
        self.assertEqual(r['sites']['expensive']['started'],1)
    def test_idle_power_counted_once_and_window_clipped(self):
        settings=Settings(static_w_per_core=1,dynamic_w_per_core=2,cores_per_normalized_cpu=1)
        r=self.run_sim([self.job(duration=100)],horizon=10,settings=settings)
        self.assertAlmostEqual(r['sites']['cheap']['it_j'],15) # 10 idle + 5 dynamic joules
        self.assertAlmostEqual(r['sites']['expensive']['it_j'],10)
        self.assertEqual(r['sites']['cheap']['running'],1)
        self.assertAlmostEqual(r['sites']['cheap']['energy_j'],15*1.05)
    def test_snapshot_overbooking_queues_without_dropping(self):
        r=self.run_sim([self.job('a',tasks=(Task(1,1),)),self.job('b',tasks=(Task(1,1),))],horizon=30)
        self.assertEqual(r['sites']['cheap']['completed'],2)
        self.assertEqual(r['sites']['cheap']['wait_s'],10)
    def test_rejection_and_pending_work_are_reported(self):
        r=self.run_sim([self.job('big',tasks=(Task(2,2),)),self.job('long',duration=100),self.job('late',arrival=50)])
        self.assertEqual(sum(x['rejected'] for x in r['sites'].values()),1)
        self.assertEqual(r['not_arrived'],1)
        self.assertEqual(sum(x['completed']+x['running']+x['queued']+x['rejected'] for x in r['sites'].values()),r['arrived_jobs'])
    def test_cost_units_and_cooling_boundaries(self):
        p=Profile('x',20,100)
        s=Settings(dynamic_w_per_core=1000,cores_per_normalized_cpu=1)
        self.assertAlmostEqual(job_cost(1,1,3600,p,s),.105)
        self.assertAlmostEqual(overhead(Profile('x',25,100)),.07)
        self.assertGreater(overhead(Profile('x',65,100)),.17)
    def test_local_baseline_never_moves(self):
        r=self.run_sim([self.job()],scheduler='local')
        self.assertEqual(sum(x['moved'] for x in r['sites'].values()),0)
    def test_profile_changes_integrated_over_time(self):
        s=Settings(static_w_per_core=1,cores_per_normalized_cpu=1)
        r=simulate([],{'cheap':[(1,1)]},lambda n,t:Profile(n,20,100 if t<5 else 200),10,settings=s)
        self.assertAlmostEqual(r['sites']['cheap']['cost_usd'],(5*100+5*200)*1.05/3.6e9)
if __name__=='__main__':unittest.main()
