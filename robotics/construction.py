"""Shared display sequencing and site geometry, always in source millimetres."""
import numpy as np
from .core import ROOT, read_json, digest, transform, corners

def library(geometry):
    blocks=dict(geometry['blocks']);sources=list(geometry.get('sources',[]))
    for name in ['demo_geometry.json','gable_geometry.json']:
        extra=read_json(ROOT/'robotics/assets'/name)
        blocks.update(extra['blocks']);sources.extend(extra.get('sources',[]))
    return dict(blocks=blocks,sources=sources)

def sequence(house):
    """Stable IDs; floor-by-floor display sequence, not structural certification."""
    phases={'floor':1,'trimmer':0,'guard':2,'stair':3,'partition':4,
            'corner':5,'wall':6,'door':6,'window':6,'filler':6,'closure':7,'roof':8}
    # Stair is installed after the upper floor is in place, before upper infill.
    def order(item):
        level=2 if item['category']=='stair' and house['levels']==2 else item.get('level',1)
        return level,phases.get(item['category'],6)
    house['items']=sorted(house['items'],key=order)
    for n,item in enumerate(house['items']):item['sequence_index']=n+1
    house['schedule_basis']='floor_interior_enclosure_display_sequence'
    house['sequence_note']='逐層樓板／洞口補強及防護 → 室內隔間 → 外牆 → 山牆／屋頂；展示順序，臨時支撐與穩定待工程確認。'
    return house

def site_scene(house):
    """Use the exact same transformed meshes and IDs as whole-house assembly."""
    catalog={b['id']:b for b in read_json(ROOT/'data/blocks_full.json')['blocks']}
    modules=[];blocks={};issues=[]
    bounds={k:[np.min(m['v'],axis=0).tolist(),np.max(m['v'],axis=0).tolist()] for k,m in house['meshes'].items()}
    for n,it in enumerate(house['items']):
        mesh=house['meshes'][it['key']]
        v=np.asarray([transform(p,it['rotation'],it['translation']) for p in corners(bounds[it['key']])])
        weight=catalog.get(it['key'],{}).get('details',{}).get('weight_kg')
        try:weight=float(weight);weight=weight if np.isfinite(weight) and weight>0 else None
        except (TypeError,ValueError):weight=None
        if it['evidence']!='source_mesh':weight=None
        if weight is None:issues.append(dict(rule_id='DATA_MASS',instance_id=it['id'],status='unknown',message='此構件重量未確認。'))
        modules.append(dict(instance_id=it['id'],source_index=n,block_id=it['key'],category=it['category'],
            level=it['level'],label=it['label'],sequence_index=n+1,bbox_mm=[v.min(0).tolist(),v.max(0).tolist()],
            translation_mm=it['translation'],rotation_deg=it['rotation'],datum_shift_mm=0.,mass_kg=weight,
            geometry_status=it['evidence'],parts_count=1))
        blocks[it['key']]=dict(parts=[dict(vertices_mm=mesh['v'],triangles=mesh['f'])])
    scene=dict(schema_version='2.0',units='mm',datum_mode='current_house',modules=modules,issues=issues,
        source_hash=digest([house.get('design_id'),house['items']]),sources=house['sources'],design_id=house.get('design_id'))
    return scene,dict(blocks=blocks,sources=house['sources'])
