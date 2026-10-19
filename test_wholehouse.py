import copy,math,unittest
from robotics.core import read_json,GEOMETRY
from robotics.house import house_demo
from robotics.interior import apply,DEFAULT
from robotics.wholehouse_study import evaluate,validate,schedule,quality,boundaries,radar_data

class WholehouseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=apply(house_demo(read_json(GEOMETRY)),DEFAULT);cls.s=evaluate(cls.h)

    def test_coverage_resource_precedence_and_totals(self):
        expected=sorted(i['id'] for i in self.h['items'])
        self.assertGreater(len(expected),len(self.h['interior']['parts']))
        cnc=[]
        for r in self.s['results']:
            events=r['events'];index={e['id']:e for e in events};last={}
            for phase in ['CNC 製造','工廠單元組裝','現場組裝']:
                self.assertEqual(sorted(i for e in events if e['phase']==phase for i in e['modules']),expected)
            for e in events:
                for dep in e['dependencies']:self.assertGreaterEqual(e['start_h']+1e-8,index[dep]['end_h'])
                if e['resource']:
                    self.assertGreaterEqual(e['start_h']+1e-8,last.get(e['resource'],0))
                    last[e['resource']]=e['end_h']
                self.assertAlmostEqual(e['person_hours'],e['hours']*e['people'])
                self.assertAlmostEqual(e['exposure_person_hours'],e['person_hours']*e['exposure_fraction'])
            for k in ['cost_twd','person_hours','exposure_person_hours']:self.assertAlmostEqual(r[k],sum(e[k] for e in events))
            self.assertAlmostEqual(r['hours'],max(e['end_h'] for e in events))
            self.assertLess(r['hours'],r['process_hours'])
            cnc.append(sum(e['hours'] for e in events if e['phase']=='CNC 製造'))
        self.assertAlmostEqual(cnc[0],cnc[1]);self.assertAlmostEqual(cnc[1],cnc[2])

    def test_thresholds_predict_changes_without_fitting(self):
        b=boundaries(self.s);p=copy.deepcopy(self.s['params'])
        # These values test algebra on either side of the break-even point, not default rankings.
        for delta in [-100,100]:
            p['common']['robot_mobilization']=b['robot_fixed_cost_lower']+delta
            r=schedule(self.h,self.s['quantity'],'B',p)
            self.assertAlmostEqual(r['cost_twd']-self.s['results'][0]['cost_twd'],delta)
        threshold=b['b_exposure_fraction_lower']
        p=copy.deepcopy(self.s['params']);p['methods']['B']['exposure_fraction']=threshold
        r=schedule(self.h,self.s['quantity'],'B',p)
        self.assertAlmostEqual(r['exposure_person_hours'],self.s['results'][0]['exposure_person_hours'])

    def test_no_forced_rank_and_error_probabilities(self):
        p=copy.deepcopy(self.s['params']);p['methods']['C']['design_h']=10000
        changed=evaluate(self.h,p)
        self.assertFalse(next(x for x in changed['hypothesis_check'] if x['metric']=='hours')['matches'])
        self.assertEqual(next(x for x in changed['hypothesis_check'] if x['metric']=='hours')['calculated_best_to_worst'][-1],'C')
        for r in changed['results']:
            self.assertTrue(0<=r['tolerance_pct']<=100)
            self.assertLessEqual(r['exposure_person_hours'],r['person_hours'])
        self.assertTrue(all(0<=x['score']<=100 for x in radar_data(changed)))
        self.assertTrue(any(x['clipped'] for x in radar_data(changed)))
        c=dict(self.s['params']['common'],tolerance_mm=0)
        self.assertEqual(quality(c,self.s['params']['methods']['A']),0)
        with self.assertRaises(ValueError):validate({'methods':{'B':{'exposure_fraction':1.1}}})

    def test_second_floor_foundation_uses_footprint(self):
        h=copy.deepcopy(self.h);h['levels']=2;h['floor_area_m2']*=2
        r=schedule(h,self.s['quantity'],'A',self.s['params'])
        e=next(e for e in r['events'] if e['id']=='foundation')
        original=next(e for e in self.s['results'][0]['events'] if e['id']=='foundation')
        self.assertEqual(e['hours'],original['hours'])

if __name__=='__main__':unittest.main()
