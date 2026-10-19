import unittest
from robotics.housing_plan import preset
from robotics.interior import layout
from robotics.core import read_json,GEOMETRY
from robotics.construction import library
from robotics.panel_layout import pack

class ResidentialChecks(unittest.TestCase):
    def test_presets_fit_furniture_and_area(self):
        for levels in [1,2]:
            for kind in ['one_bed','two_bed']:
                d=layout(preset(kind,levels,levels),levels)
                self.assertTrue(all(r['meets_area'] for r in d['rooms']))
                self.assertTrue(all(p['lo'][i]<=p['hi'][i] for p in d['parts'] for i in range(3)))
                for f in d['furniture']:
                    a,b,x,y=f['box'];self.assertTrue(318<=a<x<=5118 and 318<=b<y<=12882)
                    if levels==2:self.assertFalse(a<1812 and x>604 and b<7200 and y>3000)
                beds=[f for f in d['furniture'] if f['kind']=='bed']
                self.assertEqual(len(beds),1 if kind=='one_bed' else 2)
                for bed in beds:
                    a,b,x,y=bed['box'];self.assertTrue(any(r['id'].startswith('R') and a>=r['box'][0] and b>=r['box'][1] and x<=r['box'][2] and y<=r['box'][3] for r in d['rooms']))

    def test_all_parts_accounted_and_packing_keeps_spacing(self):
        g=library(read_json(GEOMETRY))
        for unit in ['SKYLARK250_WALL-M','SKYLARK250_WINDOW-M2','SKYLARK250_ROOF-M10']:
            d=pack(g,unit);parts=[p for b in d['boards'] for p in b['parts']]
            self.assertEqual(len(parts)+len(d['unplaced']),len(g['blocks'][unit]['parts']))
            self.assertEqual(len({p['id'] for p in parts+d['unplaced']}),d['source_part_count'])
            for board in d['boards']:
                for i,p in enumerate(board['parts']):
                    a,b,x,y=p['bounds'];self.assertGreaterEqual(a,9.99);self.assertGreaterEqual(b,9.99)
                    self.assertLessEqual(x,1210.01);self.assertLessEqual(y,2430.01)
                    self.assertAlmostEqual((x-a)*(y-b),p['size'][0]*p['size'][1],places=3)
                    for q in board['parts'][i+1:]:
                        c,e,z,w=q['bounds'];self.assertTrue(x+5.99<=c or z+5.99<=a or y+5.99<=e or w+5.99<=b)

if __name__=='__main__':unittest.main()
