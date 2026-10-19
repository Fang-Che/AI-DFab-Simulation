import copy, math, unittest
from robotics.interior import DEFAULT
from robotics.study import compare, clear
from robotics.lifecycle import enrich,radar_data,tolerance,validate,DEFAULTS,choose_twin

class LifecycleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=compare(DEFAULT);cls.case=enrich(cls.base)

    def test_complete_scope_conservation_and_shared_manufacturing(self):
        s=self.case;self.assertEqual(s['fabrication']['sheets'],23)
        cnc=[]
        for r in s['results']:
            w=r['lifecycle'];self.assertTrue(w['complete'])
            for key in ['hours','cost_twd','person_hours','exposure_person_hours']:
                self.assertAlmostEqual(w[key],sum(p[key] for p in w['phases']))
            self.assertGreater(w['hours'],r['completed_work']['hours'])
            self.assertLessEqual(w['exposure_person_hours'],w['person_hours'])
            cnc.append([(p['hours'],p['cost_twd']) for p in w['phases'] if p['phase'].startswith('CNC')])
        self.assertEqual(cnc[0],cnc[1]);self.assertEqual(cnc[1],cnc[2])
        self.assertNotIn('lifecycle',self.base['results'][0])

    def test_error_budget_does_not_award_ai_bonus(self):
        p=validate();manual=tolerance(p,False);robot=tolerance(p,True)
        self.assertEqual(manual['probability'],robot['probability'])
        sigma2=.3**2+.4**2+.8**2+.8**2
        self.assertAlmostEqual(robot['probability'],1-math.exp(-2**2/(2*sigma2)))
        self.assertEqual(tolerance(dict(p,tolerance_mm=0),True)['probability'],0)
        self.assertGreater(tolerance(dict(p,tolerance_mm=3),True)['probability'],robot['probability'])
        self.assertEqual(self.case['results'][1]['lifecycle']['tolerance_pct'],self.case['results'][2]['lifecycle']['tolerance_pct'])
        with self.assertRaises(ValueError):validate({'robot_exposure_fraction':1.01})

    def test_twin_selection_and_conditions_use_real_evaluations(self):
        s=self.case
        self.assertFalse(s['twin_plan']['live_ai']);self.assertFalse(s['twin_plan']['physical_sync'])
        self.assertEqual(s['twin_plan']['selected'],'遠端優先／延後封閉')
        better=copy.deepcopy(self.base['results'][2]);better['attempted_hours']=1
        chosen,record=choose_twin(better,self.base['results'][2])
        self.assertEqual(record['selected'],'近端優先');self.assertEqual(chosen['method'],'C')
        self.assertEqual(len(s['conditions']),15)
        parts={p['id']:p for p in s['interior']['parts']}
        for r in s['results']:
            cases=[v for v in s['conditions'] if v['method']==r['method']]
            self.assertEqual(r['lifecycle']['adaptability_pct'],sum(v['complete'] for v in cases)/5*100)
        for v in s['conditions']:
            placed=[]
            for e in v['events']:
                for a,b in zip(e['route'],e['route'][1:]):
                    self.assertTrue(clear([(a[k]+b[k])/2 for k in [0,1]],v['radius_mm'],placed,v['extra_obstacle']))
                if e['success']:
                    placed.append(parts[e['part']]);self.assertTrue(clear(e['station'],v['radius_mm'],placed,v['extra_obstacle']))

    def test_six_axes_scales_and_unfinished_work_not_zero(self):
        data=radar_data(self.case);self.assertEqual(len(data),18)
        for d in data:
            if d['direction']=='higher':self.assertEqual(d['score'],d['raw'])
            else:self.assertAlmostEqual(d['score'],max(0,100*(1-d['raw']/d['zero_score_bound'])))
        case=copy.deepcopy(self.case);case['results'][1]['lifecycle']['complete']=False
        self.assertTrue(all(p['score'] is None for p in radar_data(case) if p['method']=='B'))

if __name__=='__main__':unittest.main()
