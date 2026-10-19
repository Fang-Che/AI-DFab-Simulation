import copy
import unittest
import tempfile
from pathlib import Path
import rhino3dm
from robotics.core import *
from robotics.export import scene_snapshot,rhino_file
from robotics.llm import validate_plan

class RoboticsChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scene,cls.geometry=default_scene()
        roofs=[m for m in cls.scene['modules'] if m['category']=='roof']
        cls.sc=site_scenario(cls.scene,roofs[len(roofs)//2]['instance_id'])

    def test_continuous_collision_catches_thin_obstacle(self):
        self.assertIsNotNone(sweep_box([0,0,0],[1000,0,0],[1,1,1],[[499,-2,-2],[500,2,2]]))
        self.assertIsNone(sweep_box([0,10,0],[1000,10,0],[1,1,1],[[499,-2,-2],[500,2,2]]))
        self.assertEqual(sweep_box([0,0,0],[0,0,0],[1,1,1],[[-1,-1,-1],[1,1,1]]),0)

    def test_real_scene_replan_and_unknowns(self):
        before=evaluate_site(self.sc,self.sc['baseline'])
        after=evaluate_site(self.sc,self.sc['corrected'])
        self.assertGreater(len(before['collisions']),0)
        self.assertEqual(after['collisions'],[])
        self.assertFalse(after['geometry_approved'])
        self.assertEqual(after['checks'][-1]['status'],'unknown')
        unknown=copy.deepcopy(self.sc);unknown['target']['mass_kg']=None
        self.assertEqual(evaluate_site(unknown,unknown['corrected'])['checks'][1]['status'],'unknown')
        self.assertEqual(evaluate_site(self.sc,self.sc['corrected'],payload_kg=1)['checks'][1]['status'],'fail')

    def test_sequence_and_cycles(self):
        tasks=task_graph(self.scene['modules']);order=topological_order(tasks)
        self.assertEqual(len(order),len(self.scene['modules'])*4)
        positions={v:i for i,v in enumerate(order)}
        for t in tasks:
            for predecessor in t['predecessors']:self.assertLess(positions[predecessor],positions[t['task_id']])
        with self.assertRaises(ValueError):topological_order([{'task_id':'a','predecessors':['a']}])

    def test_export_roundtrip(self):
        result=evaluate_site(self.sc,self.sc['corrected'])
        snapshot=scene_snapshot(self.scene,self.geometry,self.sc,result)
        self.assertEqual(snapshot['target_center_mm'],path_position(result['route_mm'],.45))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.3dm';rhino_file(snapshot,path)
            model=rhino3dm.File3dm.Read(str(path))
            self.assertIsNotNone(model)
            self.assertEqual(model.Settings.ModelUnitSystem,rhino3dm.UnitSystem.Millimeters)
            self.assertGreater(len(model.Objects),1)

    def test_invalid_ai_action_rejected(self):
        with self.assertRaises(ValueError):validate_plan({'action':'execute_robot','explanation':'','design_feedback':'','rule_ids':[]},[])

    def test_whole_house_sequence_boundaries(self):
        from robotics.assembly import rectangle_demo,assembly_state
        demo=rectangle_demo(self.geometry);n=len(demo['items'])
        self.assertEqual(assembly_state(n,0)['installed'],0)
        self.assertIsNone(assembly_state(n,100)['active'])
        self.assertEqual(assembly_state(n,100)['installed'],n)
        cats=[m['category'] for m in demo['items']]
        for c in ['floor','corner','wall','door','window','roof']:self.assertIn(c,cats)
        self.assertLess(max(i for i,c in enumerate(cats) if c=='floor'),cats.index('corner'))
        self.assertLess(max(i for i,c in enumerate(cats) if c=='wall'),cats.index('roof'))
        self.assertEqual(demo['roof_pitch_deg'],42)
        self.assertEqual(len({m['id'] for m in demo['items']}),n)

    def test_abb_registered_model_and_kinematics(self):
        import numpy as np
        from robotics.abb import forward,inverse,model,LIMITS
        robot=model();self.assertEqual(len(robot['links']),7)
        np.testing.assert_allclose(forward([0]*6)[-1][:3,3],[1960,0,2075],atol=1e-7)
        rng=np.random.default_rng(22)
        for _ in range(50):
            q=[rng.uniform(lo+1,hi-1) for lo,hi in LIMITS]
            target=forward(q)[-1];solved=inverse(target,q)
            self.assertIsNotNone(solved)
            np.testing.assert_allclose(forward(solved)[-1],target,atol=1e-6)
        invalid=np.eye(4);invalid[:3,3]=[10000,10000,10000]
        self.assertIsNone(inverse(invalid))

    def test_factory_order_and_rigid_plate_frames(self):
        import numpy as np
        from robotics.assembly import factory_scene
        f=factory_scene(self.geometry)
        self.assertEqual([p['role'] for p in f['parts']],['bottom','far','internal','internal','internal','near','top'])
        self.assertGreater(f['parts'][1]['target'][0],f['parts'][-2]['target'][0])
        for p in f['parts']:
            self.assertAlmostEqual(np.linalg.det(p['frame']),1.)
            self.assertEqual(p['insertion_vector'],[0,0,-1])

    def test_connected_layouts_dimensions_and_time(self):
        from robotics.assembly import rectangle_demo
        for layout in ['rectangle','L','U']:
            data=rectangle_demo(self.geometry,layout)
            cells={tuple(c) for c in data['footprint_cells']};seen={next(iter(cells))};todo=list(seen)
            while todo:
                x,y=todo.pop()
                for cell in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                    if cell in cells and cell not in seen:seen.add(cell);todo.append(cell)
            self.assertEqual(seen,cells)
            self.assertEqual(len(data['boundary_edges']),len({(tuple(a),tuple(b)) for a,b,_ in data['boundary_edges']}))
            self.assertAlmostEqual(data['dimensions_m']['length'],13.2,places=2)
            if layout=='rectangle':self.assertAlmostEqual(data['dimensions_m']['width'],5.436,places=2)
            self.assertAlmostEqual(data['time_estimate']['hours'],4+len(data['items'])*12/60/.75)

    def test_six_axis_surrogate_roundtrip(self):
        from robotics.kinematics import forward,inverse
        for joints in [[20,-60,70,30,45,-20],[-40,-80,100,-50,90,10]]:
            p,R=forward(joints);out=inverse(p,R)
            self.assertLess(out['position_error_mm'],1e-5)
            self.assertLess(out['rotation_error'],1e-6)
        self.assertEqual(inverse([100,0,0],[[1,0,0],[0,1,0],[0,0,1]])['status'],'unreachable')

if __name__=='__main__':unittest.main()
