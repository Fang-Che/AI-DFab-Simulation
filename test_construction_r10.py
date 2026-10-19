import unittest
import numpy as np
from robotics.core import read_json,GEOMETRY,site_scenario,task_graph,topological_order,transform
from robotics.construction import library,site_scene
from robotics.house import house_demo
from robotics.interior import apply,DEFAULT
from robotics.assembly import factory_scene

class ConstructionR10Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry=library(read_json(GEOMETRY))
        cls.original=house_demo(cls.geometry,levels=2)
        cls.house=apply(cls.original,{**DEFAULT,'floor':2})

    def test_interior_before_enclosure_preserves_geometry_and_ids(self):
        h=self.house
        ix=lambda cat:[n for n,i in enumerate(h['items']) if i['level']==2 and i['category']==cat]
        self.assertLess(max(ix('floor')),min(ix('partition')))
        self.assertLess(max(ix('partition')),min(ix('wall')))
        old={i['id']:i for i in self.original['items']}
        for i in h['items']:
            if i['id'] in old:
                self.assertEqual(i['translation'],old[i['id']]['translation'])
                self.assertEqual(i['key'],old[i['id']]['key'])

    def test_upper_lift_matches_display_and_predecessors(self):
        scene,geometry=site_scene(self.house)
        target=next(m for m in scene['modules'] if m['level']==2 and m['category']=='wall')
        scenario=site_scenario(scene,target['instance_id'])
        self.assertGreater(target['bbox_mm'][0][2],2700)
        self.assertTrue(all(o['sequence_index']<target['sequence_index'] for o in scenario['obstacles']))
        item=next(i for i in self.house['items'] if i['id']==target['instance_id'])
        pts=np.array([transform(p,item['rotation'],item['translation']) for p in self.house['meshes'][item['key']]['v']])
        np.testing.assert_allclose(target['bbox_mm'],[pts.min(0),pts.max(0)],atol=.001)
        ordered=topological_order(task_graph(scene['modules']))
        positions={name:i for i,name in enumerate(ordered)}
        for a,b in zip(scene['modules'],scene['modules'][1:]):
            self.assertLess(positions[a['instance_id']+':site'],positions[b['instance_id']+':site'])

    def test_all_unit_frames_preserve_source_scale(self):
        for unit,block in self.geometry['blocks'].items():
            if len(block['parts'])<2:continue
            data=factory_scene(self.geometry,unit)
            self.assertEqual(len(data['parts']),len(block['parts']))
            for p in data['parts']:
                source=next(v for v in block['parts'] if v['part_id']==p['id'])
                a=np.asarray(p['v']);b=np.asarray(source['vertices_mm'])
                self.assertAlmostEqual(np.linalg.norm(a[0]-a[-1]),np.linalg.norm(b[0]-b[-1]),places=3)
                self.assertAlmostEqual(np.linalg.det(p['frame']),1.)

if __name__=='__main__':unittest.main()
