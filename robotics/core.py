"""Deterministic, auditable construction checks. All geometry uses millimetres.

Site sweeps are continuous translated AABBs with fixed orientation, not sampled
robot trajectories. They cannot establish joint-space, rigging or structural safety.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
GEOMETRY=ROOT/'robotics/assets/geometry.json'
STAGE_ORDER={'floor':0,'end':0,'corner':1,'wall':2,'window':2,'door':2,'filler':2,'partition':2,'roof':3,'connector':4}

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def center(bounds):
    return [(bounds[0][i]+bounds[1][i])/2 for i in range(3)]

def size(bounds):
    return [bounds[1][i]-bounds[0][i] for i in range(3)]

def corners(bounds):
    lo,hi=bounds
    return [[x,y,z] for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]

def bounds_of(points):
    return [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]

def transform(point, rotation, translation):
    a=math.radians(rotation);c,s=math.cos(a),math.sin(a)
    x,y,z=point
    return [c*x-s*y+translation[0],s*x+c*y+translation[1],z+translation[2]]

def translated_box(bounds, new_center):
    half=[s/2 for s in size(bounds)]
    return [[new_center[i]-half[i] for i in range(3)], [new_center[i]+half[i] for i in range(3)]]

def overlap(a,b,tolerance=0):
    return all(min(a[1][i],b[1][i])-max(a[0][i],b[0][i]) > tolerance for i in range(3))

def sweep_box(a,b,half,obstacle,clearance=0):
    """Slab intersection with Minkowski-expanded obstacle, including endpoints.

    Return first contact fraction on [0,1], or None. Tangency is conservatively
    considered contact. This catches thin obstacles between animation frames.
    """
    enter,leave=0.,1.
    for i in range(3):
        lo=obstacle[0][i]-half[i]-clearance
        hi=obstacle[1][i]+half[i]+clearance
        d=b[i]-a[i]
        if abs(d)<1e-12:
            if a[i]<lo or a[i]>hi:
                return None
        else:
            t0,t1=(lo-a[i])/d,(hi-a[i])/d
            enter=max(enter,min(t0,t1));leave=min(leave,max(t0,t1))
            if enter>leave:
                return None
    return enter

def catalogue_bounds(block):
    desc=block.get('description','')
    found={k:float(v) for k,v in re.findall(r'\b([wlh])\s+(\d+(?:\.\d+)?)',desc)}
    if set(found)=={'w','l','h'}:
        return [[0.,0.,0.],[found['w'],found['l'],found['h']]]
    return None

def normalize(placements, catalogue, geometry, datum_mode='design_levels'):
    if not isinstance(placements,list) or not placements:
        raise ValueError('配置必須是非空 JSON 陣列。')
    catalog={b['id']:b for b in catalogue}
    blocks=geometry.get('blocks',{})
    modules=[];issues=[]
    for i,p in enumerate(placements):
        if not isinstance(p,dict) or 'block_id' not in p or 'position_mm' not in p:
            raise ValueError(f'第 {i+1} 筆缺少 block_id 或 position_mm。')
        bid=p['block_id'];uid=p.get('instance_id') or f'M{i+1:03d}'
        cat=p.get('category','unknown');entry=catalog.get(bid,{})
        geo=blocks.get(bid)
        bounds=geo['bbox_mm'] if geo else catalogue_bounds(entry)
        if bounds is None:
            issues.append({'rule_id':'DATA_GEOMETRY','instance_id':uid,'block_id':bid,'status':'unknown','message':'缺少三維幾何與可解析尺寸；排除幾何運算。'})
            continue
        raw=[float(p['position_mm'].get(k,0)) for k in ('x_mm','y_mm','z_mm')]
        rot=float(p.get('rotation',0));wall_h=float(p.get('wall_height_mm',2400))
        if not all(math.isfinite(v) for v in raw+[rot,wall_h]):
            raise ValueError(f'{uid} 含非有限座標。')
        if any(v<=0 for v in size(bounds)):
            raise ValueError(f'{uid} 有無效尺寸。')
        placed=list(raw)
        # Match the original Rhino script's roof override in source-coordinate mode.
        if cat=='roof':
            placed[2]=wall_h
        source_translation=list(placed)
        if datum_mode=='design_levels':
            if cat in ('floor','end'):
                placed[2]=-bounds[1][2]
            elif cat=='roof':
                placed[2]=wall_h-bounds[0][2]
            else:
                placed[2]=-bounds[0][2]
        bbox=bounds_of([transform(v,rot,placed) for v in corners(bounds)])
        weight=entry.get('details',{}).get('weight_kg')
        try:
            weight=float(weight)
            if not math.isfinite(weight) or weight<=0:
                weight=None
        except (ValueError,TypeError):
            weight=None
        module={'instance_id':uid,'source_index':i,'block_id':bid,'category':cat,
            'bbox_mm':bbox,'local_bbox_mm':bounds,'translation_mm':placed,
            'source_translation_mm':source_translation,'rotation_deg':rot,
            'datum_shift_mm':placed[2]-source_translation[2],
            'mass_kg':weight,'mass_source':entry.get('page_url') if weight is not None else None,
            'geometry_source':geo.get('source') if geo else {'type':'catalogue_description','page_url':entry.get('page_url')},
            'geometry_status':geo['geometry_status'] if geo else 'catalogue_envelope',
            'parts_count':len(geo['parts']) if geo else None,
            'catalogue_parts':entry.get('parts',[]),'original_placement':p}
        modules.append(module)
        if geo is None:
            issues.append({'rule_id':'DATA_GEOMETRY','instance_id':uid,'block_id':bid,'status':'unknown','message':'使用資料庫尺寸外框；尚無同名三維構件。'})
        if weight is None:
            issues.append({'rule_id':'DATA_MASS','instance_id':uid,'block_id':bid,'status':'unknown','message':'缺少構件重量，無法判斷負載。'})
    if len({m['instance_id'] for m in modules})!=len(modules):
        raise ValueError('instance_id 必須唯一；block_id 可以重複。')
    return {'schema_version':'1.0','units':'mm','datum_mode':datum_mode,'source_hash':digest(placements),
            'modules':modules,'issues':issues,'sources':geometry.get('sources',[])}

def task_graph(modules):
    """Conservative category precedence template; not validated joint precedence."""
    tasks=[]
    ordered=sorted(modules,key=lambda m:m.get('sequence_index',0))
    previous={m['instance_id']:ordered[i-1]['instance_id'] for i,m in enumerate(ordered) if i}
    explicit=bool(modules) and all('sequence_index' in m for m in modules)
    by_stage={i:[m['instance_id'] for m in modules if STAGE_ORDER.get(m['category'],4)==i] for i in range(5)}
    for m in modules:
        uid=m['instance_id'];phase=STAGE_ORDER.get(m['category'],4)
        site_pre=[f'{x}:site' for j in range(phase) for x in by_stage[j]]
        if explicit:site_pre=[previous[uid]+':site'] if uid in previous else []
        for op,needs in [('fabricate',[]),('assemble',[f'{uid}:fabricate']),('transport',[f'{uid}:assemble']),('site',[f'{uid}:transport']+site_pre)]:
            tasks.append({'task_id':f'{uid}:{op}','instance_id':uid,'block_id':m['block_id'],
                          'operation':op,'predecessors':needs,'evidence':'display_sequence_template' if explicit else 'category_template','execution_status':'not_executed'})
    return tasks

def topological_order(tasks):
    pending={t['task_id']:set(t['predecessors']) for t in tasks}
    if len(pending)!=len(tasks):
        raise ValueError('Duplicate task IDs.')
    if any(d not in pending for deps in pending.values() for d in deps):
        raise ValueError('Missing predecessor.')
    result=[]
    while pending:
        ready=sorted(k for k,v in pending.items() if not v)
        if not ready:
            raise ValueError('Assembly dependencies contain a cycle.')
        result.extend(ready)
        for k in ready:del pending[k]
        for v in pending.values():v.difference_update(ready)
    return result

def path_length(points):
    return sum(math.dist(a,b) for a,b in zip(points,points[1:]))

def path_position(points,progress):
    total=path_length(points);left=max(0,min(1,progress))*total
    for a,b in zip(points,points[1:]):
        d=math.dist(a,b)
        if left<=d and d>0:
            t=left/d
            return [a[i]+(b[i]-a[i])*t for i in range(3)]
        left-=d
    return points[-1]

def site_scenario(scene,target_id,clearance_mm=250,staging_offset_mm=5000):
    target=next(m for m in scene['modules'] if m['instance_id']==target_id)
    obstacles=[m for m in scene['modules'] if m['instance_id']!=target_id and
        (m['sequence_index']<target['sequence_index'] if 'sequence_index' in target else m['category']!='roof')]
    half=[s/2 for s in size(target['bbox_mm'])]
    goal=center(target['bbox_mm'])
    # End at a preinstallation pose, above the full installed envelope. Final joint
    # insertion is deliberately an unvalidated task rather than an implied success.
    max_top=max((m['bbox_mm'][1][2] for m in obstacles),default=0)
    goal[2]=max(goal[2],max_top+half[2]+clearance_mm)
    xmin=min(m['bbox_mm'][0][0] for m in scene['modules'])
    start=[xmin-staging_offset_mm-half[0],goal[1],half[2]+200]
    baseline=[start,goal]
    high=max_top+half[2]+clearance_mm+100
    corrected=[start,[start[0],start[1],high],[goal[0],goal[1],high],goal]
    return {'target':target,'obstacles':obstacles,'baseline':baseline,'corrected':corrected,
            'clearance_mm':clearance_mm,'endpoint':'preinstallation_pose',
            'final_insertion_status':'not_evaluated'}

def evaluate_site(scenario,route,payload_kg=250,rigging_kg=15,reach_mm=20000,max_height_mm=10000,crane_base=None):
    target=scenario['target'];half=[s/2 for s in size(target['bbox_mm'])]
    if crane_base is None:crane_base=[route[0][0],route[0][1]-2500,0]
    collisions=[]
    for obstacle in scenario['obstacles']:
        for segment,(a,b) in enumerate(zip(route,route[1:])):
            t=sweep_box(a,b,half,obstacle['bbox_mm'])
            if t is not None:
                collisions.append({'obstacle_id':obstacle['instance_id'],'block_id':obstacle['block_id'],
                    'segment':segment,'fraction':round(t,6),
                    'contact_center_mm':[round(a[i]+t*(b[i]-a[i]),3) for i in range(3)]})
                break
    mass=target['mass_kg']
    checks=[{'rule_id':'LIFT_ENVELOPE','status':'fail' if collisions else 'pass',
             'message':f'路徑與 {len(collisions)} 個已安裝構件的外框相交。' if collisions else '固定姿態的平移路徑未與已安裝構件外框相交。',
             'method':'continuous_AABB_sweep','collision_count':len(collisions)},
            {'rule_id':'LIFT_PAYLOAD','status':'unknown' if mass is None else ('pass' if mass+rigging_kg<=payload_kg else 'fail'),
             'mass_kg':mass,'rigging_kg':rigging_kg,'limit_kg':payload_kg,
             'message':'以資料庫重量加假設吊具重量，對照情境設定的固定負載上限；尚未使用吊車負載曲線。'},
            {'rule_id':'LIFT_REACH','status':'pass' if max(math.dist(p[:2],crane_base[:2]) for p in route)<=reach_mm else 'fail',
             'max_radius_mm':max(math.dist(p[:2],crane_base[:2]) for p in route),'limit_mm':reach_mm,
             'message':'平面半徑預檢；未計算吊臂姿態與工作幅度負載曲線。'},
            {'rule_id':'LIFT_HEIGHT','status':'pass' if max(p[2]+half[2] for p in route)<=max_height_mm else 'fail',
             'limit_mm':max_height_mm,'message':'構件頂面高度預檢；未計入吊索長度。'},
            {'rule_id':'FINAL_INSERTION','status':'unknown','message':'路徑終點為安裝前接近點；接頭插入、吊點、受力、臨時支撐與設備碰撞尚未驗證。'}]
    return {'instance_id':target['instance_id'],'block_id':target['block_id'],'checks':checks,
            'collisions':collisions,'path_length_m':round(path_length(route)/1000,3),
            'route_mm':route,'crane_base_mm':crane_base,'geometry_approved':False,
            'counts':{s:sum(c['status']==s for c in checks) for s in ('pass','fail','unknown')}}

def fabrication_checks(block_geometry,bed_mm=(2440,1220)):
    """PCA-oriented panel envelope fit, not CAM or tool accessibility validation."""
    import numpy as np
    rows=[]
    if not block_geometry:return rows
    for part in block_geometry['parts']:
        points=np.asarray(part['vertices_mm'],dtype=float)
        origin=points.mean(axis=0)
        vals,axes=np.linalg.eigh(np.cov((points-origin).T))
        local=(points-origin)@axes
        ext=np.ptp(local,axis=0)
        order=np.argsort(ext)
        thick,width,length=[float(ext[i]) for i in order]
        fits=length<=max(bed_mm) and width<=min(bed_mm)
        rows.append({'part_id':part['part_id'],'label':part['label'],
                     'length_mm':round(length,1),'width_mm':round(width,1),'thickness_envelope_mm':round(thick,1),
                     'status':('pass' if fits else 'fail') if thick<35 else 'unknown',
                     'method':'PCA_envelope_prescreen','bed_mm':list(bed_mm),
                     'note':'僅檢查方向估計外框；不是排版率、刀路、加工公差或切削驗證。'})
    return rows

def recommendations(result):
    suggestions=[]
    for check in result['checks']:
        if check['status']!='fail':continue
        rule=check['rule_id']
        if rule=='LIFT_ENVELOPE':
            suggestions.append({'rule_id':rule,'target':'construction.lift_clearance_mm','scope':'施工規劃',
                'action':'先垂直提升，再水平移動，最後下降至安裝前接近點；重新檢查整段路徑。',
                'can_apply_in_preview':True})
        elif rule=='LIFT_PAYLOAD':
            suggestions.append({'rule_id':rule,'target':'design.span_or_module_grouping','scope':'前期設計',
                'action':'檢視跨距與預組裝分組，提出較輕的標準模組候選；修改需重新通過 FADDG 與結構審查。亦可檢討設備選型。',
                'can_apply_in_preview':False})
        elif rule=='LIFT_REACH':
            suggestions.append({'rule_id':rule,'target':'site.crane_base_and_staging','scope':'基地與施工配置',
                'action':'調整設備與堆置位置，再檢查搬運路徑、吊裝半徑及基地通道。','can_apply_in_preview':False})
        elif rule=='LIFT_HEIGHT':
            suggestions.append({'rule_id':rule,'target':'design.height_and_construction_sequence','scope':'設計與施工',
                'action':'檢討建築高度、模組姿態或作業順序；以實際吊車資料重新規劃。','can_apply_in_preview':False})
    return suggestions

def build_report(scene,scenario,before,after,fabrication):
    tasks=task_graph(scene['modules']);topological_order(tasks)
    return {'schema_version':'1.0','created_at':datetime.now(timezone.utc).isoformat(),
            'source_hash':scene['source_hash'],'units':'mm','datum_mode':scene['datum_mode'],
            'sources':scene['sources'],'input_issues':scene['issues'],
            'normalization':[{'instance_id':m['instance_id'],'block_id':m['block_id'],'datum_shift_mm':m['datum_shift_mm']}
                             for m in scene['modules'] if abs(m['datum_shift_mm'])>0.01],
            'baseline':before,'candidate':after,'recommendations':recommendations(before),
            'fabrication':fabrication,'tasks':tasks,'llm_used':False,
            'evidence_level':'digital_geometric_prescreen',
            'limitations':['姿態固定的外框連續碰撞預檢，尚非精確實體碰撞。',
                           '機器人逆運動學、關節限制、夾具、吊索、力學及現場安全未驗證。',
                           '安裝順序為類別相依模板；未以接頭拓撲證明可裝配。',
                           '設計樓層基準為可回溯的顯示正規化；未改寫輸入配置。']}

def default_scene(datum_mode='design_levels'):
    geometry=read_json(GEOMETRY)
    scene=normalize(read_json(ROOT/'output_placement.json'),read_json(ROOT/'data/blocks_full.json')['blocks'],geometry,datum_mode)
    return scene,geometry
