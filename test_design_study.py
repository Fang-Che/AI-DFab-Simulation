import unittest,math
from robotics.interior import DEFAULT,layout,apply,suggestions
from robotics.study import compare,ASSUMPTIONS,clear,radar_data,sensitivity
from robotics.prices import converted,FX,benchmark
from robotics.core import read_json,GEOMETRY
from robotics.house import house_demo
from robotics.estimating import quantity_takeoff,cost_estimate

class DesignChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=compare(DEFAULT);cls.after=compare(dict(DEFAULT,door_width=1400))

    def test_shared_geometry_failures_and_completed_cost(self):
        ids={p['id'] for p in self.before['interior']['parts']}
        for r in self.before['results']:
            self.assertEqual({e['part'] for e in r['events']},ids)
            self.assertEqual(r['success']+r['failed'],len(ids))
            self.assertAlmostEqual(r['attempted_cost_twd'],1200*r['attempted_hours'])
            if not r['complete']:
                self.assertIsNone(r['completion_hours']);self.assertIsNone(r['completion_cost_twd'])
        self.assertEqual(self.before['results'][1]['reach_mm'],self.before['results'][2]['reach_mm'])
        self.assertEqual(self.before['results'][1]['radius_mm'],self.before['results'][2]['radius_mm'])
        self.assertEqual(self.before['results'][0]['success'],len(ids))
        self.assertLess(self.before['results'][1]['success'],self.after['results'][1]['success'])

    def test_paths_safe_at_midpoints_and_exit(self):
        for case in [self.before,self.after]:
            parts={p['id']:p for p in case['interior']['parts']}
            for r in case['results']:
                placed=[]
                for e in r['events']:
                    for a,b in zip(e['route'],e['route'][1:]):
                        self.assertTrue(clear([(a[k]+b[k])/2 for k in [0,1]],r['radius_mm'],placed))
                    if e['success']:
                        placed.append(parts[e['part']]);self.assertTrue(clear(e['station'],r['radius_mm'],placed))
                if r['complete']:self.assertEqual(r['exit_route'][-1],r['start'])

    def test_room_validity_locks_and_all_footprints(self):
        self.assertEqual(suggestions(dict(DEFAULT,lock_door=True,lock_common=True)),[])
        with self.assertRaises(ValueError):layout(dict(DEFAULT,door_width=1400,corridor=1200))
        with self.assertRaises(ValueError):layout(dict(DEFAULT,common_end=6000),2)
        base=house_demo(read_json(GEOMETRY));baseline=len(base['items'])
        h=apply(base,DEFAULT);self.assertEqual(len(base['items']),baseline)
        self.assertEqual(len(h['items']),baseline+len(h['interior']['parts']))
        self.assertEqual(len({p['id'] for p in h['items']}),len(h['items']))
        changed=apply(base,dict(DEFAULT,door_width=1400));self.assertNotEqual(h['design_id'],changed['design_id'])
        q=quantity_takeoff(h);q2=quantity_takeoff(changed)
        self.assertGreater(q['area_m2'],q2['area_m2']);self.assertGreater(cost_estimate(h,q)['total'],cost_estimate(changed,q2)['total'])
        for n in [1,2,3]:
            info=layout(dict(DEFAULT,bedrooms=n));self.assertEqual(len([r for r in info['rooms'] if r['id'].startswith('R')]),n)
            self.assertTrue(all(r['area_m2']>0 for r in info['rooms']))

    def test_public_currency_provenance(self):
        q=converted();self.assertEqual(q[0]['twd_low'],17072.)
        self.assertEqual(q[0]['twd_high'],19206.)
        self.assertTrue(all(p['url'].startswith('https://') for p in q))
        self.assertEqual(converted(40.)[1]['twd_low'],48000.)
        for v in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):converted(v)

    def test_fallback_preserves_installed_geometry_and_accounts_for_all_work(self):
        for case in [self.before,self.after]:
            parts={p['id']:p for p in case['interior']['parts']}
            for r in case['results']:
                w=r['completed_work'];self.assertTrue(w['complete'])
                self.assertEqual(w['success'],r['tasks'])
                for key in ['hours','cost_twd','path_m','person_hours']:
                    self.assertAlmostEqual(w[key],sum(p[key] for p in w['phases']))
                fb=w['fallback']
                if fb:
                    placed=[parts[e['part']] for e in r['events'] if e['success']]
                    self.assertEqual({e['part'] for e in fb['events']},{e['part'] for e in r['events'] if not e['success']})
                    self.assertAlmostEqual(w['path_m'],r['path_m']+fb['path_m'])
                    for e in fb['events']:
                        for p,q in zip(e['route'],e['route'][1:]):
                            self.assertTrue(clear([(p[k]+q[k])/2 for k in [0,1]],fb['radius_mm'],placed))
                        if e['success']:
                            placed.append(parts[e['part']]);self.assertTrue(clear(e['station'],fb['radius_mm'],placed))
                    for p,q in zip(fb['exit_route'],fb['exit_route'][1:]):
                        self.assertTrue(clear([(p[k]+q[k])/2 for k in [0,1]],fb['radius_mm'],placed))
                    self.assertEqual(fb['exit_route'][-1],fb['start'])
                else:self.assertAlmostEqual(w['hours'],r['attempted_hours'])
        b=self.before['results'][1]['completed_work']
        self.assertEqual(b['fallback_count'],8)
        self.assertAlmostEqual(b['phases'][1]['cost_twd'],600.)
        self.assertAlmostEqual(b['phases'][1]['person_hours'],.75)
        self.assertAlmostEqual(b['cost_twd'],4875.314285714286)

    def test_unresolved_work_stays_missing_and_scores_use_common_fixed_bounds(self):
        case=compare(DEFAULT,values=dict(human_reach_mm=50.))
        a=case['results'][0];self.assertFalse(a['completed_work']['complete'])
        self.assertIsNone(a['completed_work']['hours'])
        self.assertTrue(all(d['score'] is None for d in radar_data(case) if d['method']=='A'))
        for key in ['hours','cost_twd','path_m','person_hours']:
            ps=[d for d in radar_data(self.before) if d['key']==key]
            self.assertEqual(len({p['zero_score_bound'] for p in ps}),1)
            for p in ps:self.assertAlmostEqual(p['score'],100*(1-p['raw']/p['zero_score_bound']))
        for d in sensitivity(self.before):
            if d['piece_time_factor']==1.:
                w=next(r for r in self.before['results'] if r['method']==d['method'])['completed_work']
                self.assertAlmostEqual(d['hours'],w['hours']);self.assertAlmostEqual(d['cost_twd'],w['cost_twd'])

if __name__=='__main__':unittest.main()
