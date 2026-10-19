import math,unittest
import numpy as np
from robotics.core import default_scene,transform
from robotics.house import house_demo
from robotics.estimating import quantity_takeoff,cost_estimate
from robotics.drawings import drawing_sheets,pdf_bytes
from robotics.visuals import feature_edges
from robotics.import_geometry import box_mesh

class BuildingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.geometry=default_scene()[1]

    def test_two_storeys_stair_clearance_and_sequence(self):
        for layout in ['rectangle','L','U']:
            h=house_demo(self.geometry,layout,levels=2);items=h['items'];hole=h['stair_opening_mm']
            self.assertEqual(len({i['id'] for i in items}),len(items))
            self.assertTrue(all(i['level'] in [1,2] for i in items))
            self.assertFalse(any(i['category']=='door' and i['level']==2 for i in items))
            upper=[i for i in items if i['level']==2 and i['category']=='floor']
            for it in upper:
                points=np.array([transform(v,it['rotation'],it['translation']) for v in h['meshes'][it['key']]['v']])
                lo,hi=points.min(0),points.max(0)
                self.assertAlmostEqual(lo[2],2400,places=0)
                # Source floor includes 18 mm projecting teeth above nominal datum.
                self.assertGreaterEqual(hi[2],2780);self.assertLessEqual(hi[2],2798.01)
                self.assertFalse(min(hi[0],hole[2])-max(lo[0],hole[0])>1 and min(hi[1],hole[3])-max(lo[1],hole[1])>1)
            self.assertEqual(sum(i['category']=='stair' for i in items),15)
            self.assertLess(max(n for n,i in enumerate(items) if i['level']==1 and i['category']=='wall'),min(n for n,i in enumerate(items) if i['level']==2 and i['category']=='floor'))
            self.assertLess(max(n for n,i in enumerate(items) if i['category']=='wall'),min(n for n,i in enumerate(items) if i['category']=='roof'))
            self.assertAlmostEqual(h['floor_area_m2'],2*h['footprint_area_m2']-1.208*4.2)
            self.assertAlmostEqual(h['dimensions_m']['height']-house_demo(self.geometry,layout)['dimensions_m']['height'],2.780)

    def test_bom_reconciles_and_cost_changes(self):
        h=house_demo(self.geometry,levels=2);q=quantity_takeoff(h);cost=cost_estimate(h,q)
        self.assertEqual(sum(r['數量'] for r in q['bom']),len(h['items']))
        self.assertEqual(sum(r['modules'] for r in q['rows']),len(h['items']))
        self.assertAlmostEqual(q['area_m2'],q['source_area_m2']+q['provisional_area_m2'])
        self.assertEqual(cost['sheets_budget'],math.ceil(q['area_m2']/2.9768/.8*1.05))
        self.assertAlmostEqual(cost['total'],sum(r['小計 TWD'] for r in cost['lines'])*1.1)
        changed=cost_estimate(h,q,{'sheet_price':1900})
        self.assertAlmostEqual(changed['total']-cost['total'],cost['sheets_budget']*110)
        self.assertEqual(cost_estimate(h,q,area_override=0)['sheets_budget'],0)
        for rates in [{'sheet_price':float('nan')},{'utilization':0},{'crew_hour':-1}]:
            with self.assertRaises(ValueError):cost_estimate(h,q,rates)

    def test_feature_edges_drop_coplanar_diagonals(self):
        v,f=box_mesh([[0,0,0],[100,200,18]])
        self.assertEqual(len(feature_edges(v,f))//3,12)
        duplicated=[v[i] for face in f for i in face]
        self.assertEqual(len(feature_edges(duplicated,np.arange(len(duplicated)).reshape(-1,3)))//3,12)

    def test_drawing_set_and_pdf(self):
        import io
        h=house_demo(self.geometry,levels=2);q=quantity_takeoff(h);s=drawing_sheets(h,q,cost_estimate(h,q))
        self.assertEqual([p.code for p in s],['A101','A102','A201','A202','A501','A502','A503','A601'])
        data=pdf_bytes(s)
        from pypdf import PdfReader
        pdf=PdfReader(io.BytesIO(data));self.assertEqual(len(pdf.pages),8)
        for page in pdf.pages:self.assertIn('研究',page.extract_text())
        self.assertIn('2780',pdf.pages[1].extract_text())
        self.assertIn('TWD',pdf.pages[-1].extract_text())

if __name__=='__main__':unittest.main()
