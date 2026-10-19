"""Controlled 2D station/access experiment, with reproducible event logs.

This is an access-envelope study, NOT full arm IK, physics, safety or accuracy validation.
All methods share geometry; B/C share every numerical assumption and evaluator.
"""
import math, json, hashlib
from collections import deque
from .interior import layout

ASSUMPTIONS=dict(grid_mm=150.,robot_radius_mm=550.,clearance_mm=50.,human_radius_mm=250.,
    robot_reach_mm=2400.,human_reach_mm=850.,robot_speed_m_s=.25,human_speed_m_s=.7,
    robot_minutes_piece=8.,human_minutes_piece=8.,station_minutes=2.,
    robot_setup_minutes=60.,human_setup_minutes=20.,human_crew_twd_h=1200.,
    robot_supervision_twd_h=600.,robot_equipment_twd_h=600.,
    failure_review_minutes=2.,fallback_handoff_minutes=15.,human_crew_people=2.,robot_supervision_people=1.,
    radar_hours_per_piece=.4,radar_cost_per_piece=600.,radar_path_per_piece=5.,radar_person_hours_per_piece=.6)
AI_PROPOSAL=dict(author='本次 Codex 助理',created='2026-10-13',mode='offline_assistant_proposal',api_called=False,
    request='在不變更構件與閾值下，改善室內隔間的施工通行與順序。',
    strategy='far_first_gate_last',
    rationale='先處理遠端隔間，公共區分界延後封閉，門楣於牆段後安裝；每一步仍需通過共同的到達與撤離檢查。',
    scope='本次助理提出、由程式重播的策略；不代表執行時呼叫模型或 AI 普遍優於其他規劃器。')

def assumptions(values=None):
    a={**ASSUMPTIONS,**(values or {})}
    if any(not isinstance(v,(float,int)) or not math.isfinite(v) or v<0 for v in a.values()):raise ValueError('比較參數需為有限非負值')
    if a['grid_mm']<100 or a['grid_mm']>300:raise ValueError('格網需介於 100–300 mm')
    for k in ['robot_speed_m_s','human_speed_m_s','robot_reach_mm','human_reach_mm']:
        if not a[k]>0:raise ValueError(k+' 必須大於零')
    for k in ['human_crew_people','robot_supervision_people','radar_hours_per_piece','radar_cost_per_piece','radar_path_per_piece','radar_person_hours_per_piece']:
        if not a[k]>0:raise ValueError(k+' 必須大於零')
    for k in ['human_crew_people','robot_supervision_people']:
        if int(a[k])!=a[k]:raise ValueError('在場人數需為正整數')
    return a

def nodes(a):
    step=a['grid_mm'];return [(round(318+step*i,4),round(318+step*j,4))
        for i in range(1,int(4800/step)) for j in range(1,int(12564/step))]

def clear(point, radius, placed, obstacle=None):
    x,y=point
    if x-radius<318 or x+radius>5118 or y-radius<318 or y+radius>12882:return False
    obstacles=[(p['lo'],p['hi']) for p in placed if not p['header']]
    if obstacle:
        boxes=obstacle if isinstance(obstacle[0],(list,tuple)) else [obstacle]
        for box in boxes:obstacles.append(([box[0],box[1],0],[box[2],box[3],2400]))
    for lo,hi in obstacles:
        dx=max(lo[0]-x,0,x-hi[0]);dy=max(lo[1]-y,0,y-hi[1])
        if math.hypot(dx,dy)<radius-1e-6:return False
    return True

def graph(points,radius,placed,a,obstacle):
    # Inflate by half a grid step to conservatively cover between-node motion.
    return {p for p in points if clear(p,radius+a['grid_mm']/2,placed,obstacle)}

def bfs(free,start,step):
    if start not in free:return {},{}
    distances={start:0};parents={start:None};q=deque([start])
    while q:
        p=q.popleft()
        for dx,dy in [(step,0),(-step,0),(0,step),(0,-step)]:
            n=(round(p[0]+dx,4),round(p[1]+dy,4))
            if n in free and n not in distances:
                distances[n]=distances[p]+step;parents[n]=p;q.append(n)
    return distances,parents

def route(parents,end):
    out=[]
    while end is not None:out.append(list(end));end=parents[end]
    return out[::-1]

def sequence(parts,method):
    if method in ['A','B']:return sorted(parts,key=lambda p:(p['header'],sum(p['a'][1:]+p['b'][1:]),p['id']))
    return sorted(parts,key=lambda p:(p['gate'],p['header'],-(p['a'][1]+p['b'][1]),p['id']))

def evaluate(interior,method,a=None,levels=1,initial_parts=None,pending_parts=None,extra_obstacle=None):
    a=assumptions(a);robot=method!='A';prefix='robot' if robot else 'human'
    radius=a[prefix+'_radius_mm']+a['clearance_mm'];reach=a[prefix+'_reach_mm'];speed=a[prefix+'_speed_m_s']
    points=nodes(a);obstacle=[604,2940,1872,7360] if levels==2 else None
    if extra_obstacle:obstacle=([obstacle] if obstacle else [])+[extra_obstacle]
    placed=list(initial_parts or [])
    free=graph(points,radius,placed,a,obstacle)
    desired=(5118-interior['config']['corridor']/2,1200)
    if not free:raise ValueError('底座尺寸超過研究範圍')
    start=min(free,key=lambda p:(math.dist(p,desired),p));current=start;events=[];moving=0.;stations=0
    for index,p in enumerate(sequence(interior['parts'] if pending_parts is None else pending_parts,method)):
        if p['header']:
            supports={q['id'] for q in interior['parts'] if not q['header'] and q['label']==p['label'].removesuffix(' 門楣')}
            if not supports.issubset({q['id'] for q in placed}):
                events.append(dict(step=index+1,part=p['id'],label=p['label'],success=False,route=[],move_m=0.,station_change=False,minutes=0.,reason='同一入口牆段未全部完成，門楣前置工序不足'))
                continue
        free=graph(points,radius,placed,a,obstacle);dist,parents=bfs(free,current,a['grid_mm'])
        after=graph(points,radius,placed+[p],a,obstacle);retreat,_=bfs(after,start,a['grid_mm'])
        centre=((p['a'][0]+p['b'][0])/2,(p['a'][1]+p['b'][1])/2)
        candidates=[n for n in dist if n in retreat and max(math.dist(n,p['a']),math.dist(n,p['b']))<=reach]
        if candidates:
            station=min(candidates,key=lambda n:(dist[n],math.dist(n,centre),n))
            path=route(parents,station);distance=dist[station]/1000;changed=station!=current
            moving+=distance;stations+=int(changed);placed.append(p);current=station
            events.append(dict(step=index+1,part=p['id'],label=p['label'],success=True,station=list(station),route=path,
                               move_m=distance,station_change=changed,minutes=a[prefix+'_minutes_piece']+distance/speed/60+(a['station_minutes'] if robot and changed else 0),reason='2D 通道、投影半徑與撤離預檢通過'))
        else:
            events.append(dict(step=index+1,part=p['id'],label=p['label'],success=False,route=[],move_m=0.,station_change=False,minutes=0.,
                               reason='無同時滿足通行、投影作業半徑及撤離的格網站位；可能為格網保守性造成'))
    free=graph(points,radius,placed,a,obstacle);dist,parents=bfs(free,current,a['grid_mm'])
    exit_route=route(parents,start) if start in dist else [];exit_m=dist.get(start,0)/1000
    moving+=exit_m;minutes=a[prefix+'_setup_minutes']+sum(e['minutes'] for e in events)+exit_m/speed/60
    success=sum(e['success'] for e in events);n=len(events);complete=success==n and bool(exit_route)
    hourly=a['human_crew_twd_h'] if not robot else a['robot_supervision_twd_h']+a['robot_equipment_twd_h']
    return dict(method=method,tasks=n,success=success,failed=n-success,access_rate=success/n if n else 1.,
        complete=complete,path_m=moving,station_changes=stations,attempted_hours=minutes/60,
        completion_hours=minutes/60 if complete else None,attempted_cost_twd=minutes/60*hourly,
        completion_cost_twd=minutes/60*hourly if complete else None,events=events,exit_route=exit_route,
        start=list(start),radius_mm=radius,reach_mm=reach)

def compare(config,levels=1,values=None):
    a=assumptions(values);interior=layout(config,levels)
    identity=hashlib.sha256(json.dumps(['R7-completion-v1',interior,a,levels],sort_keys=True).encode()).hexdigest()[:12]
    results=[evaluate(interior,m,a,levels) for m in ['A','B','C']]
    for r in results:r['completed_work']=complete_work(interior,r,a,levels)
    return dict(id=identity,version='R7-completion-v1',levels=levels,interior=interior,assumptions=a,results=results,ai_proposal=AI_PROPOSAL,
        scope='主屋指定樓層非承重隔間的二維施工通道／站位情境；三組共用構件；B/C 共用设备參數與檢查器',
        limitations=['未驗證 ABB 六軸逆解、自碰撞、夾具、承載、接頭插入或實際施工精度。',
        '底座已就位於公共區；不含進場、跨樓層運送、CNC、搬料補給、外殼與機電工程。',
        '全高隔間視為障礙；門楣以下 2100 mm 可通過，未檢查設備總高度。',
        '格網保守膨脹可能導致假陰性；未找到路徑不等同證明實際無解。',
        '工時與 TWD 班組／設備費率均為可編輯假設，沒有實測或供應商報價。',
        'A/B 使用近至遠順序，C 使用本次助理的遠至近及延後封閉策略；結果也受策略本身影響，不能推論一般 AI 效果。',
        '原流程失敗工序不安裝且繼續其他任務；保留原流程完成率。共同規則：原流程撤離後，由人工班組按原近至遠順序補作未完成件。',
        '補作沿用已安裝障礙及相同檢查器；若仍無法完成，不繪製該組完整工作雷達。無拆除、強制成功或比例外推。',
        '工期採串行：原作業、失敗評估、交接、人工進場準備及補作；設備計費至交接結束，補作階段釋放設備。',
        '人工補作班組起點仍在公共區，進場準備僅以工時計，不模擬外部進場路徑；失敗評估不含實體嘗試或返工。',
        '雷達為固定可編輯上限的 0–100 情境分數，越外圍投入越少；不是實测評等。工期與成本相關，不以多邊形面積排名。'])


def complete_work(interior,r,a,levels):
    """Preserve the original run and finish only its outstanding tasks, without resetting obstacles."""
    robot=r['method']!='A'
    installed={e['part'] for e in r['events'] if e['success']}
    placed=[p for p in interior['parts'] if p['id'] in installed]
    pending=[p for p in interior['parts'] if p['id'] not in installed]
    review_h=r['failed']*a['failure_review_minutes']/60
    original_h=r['attempted_hours']+review_h
    original_rate=a['human_crew_twd_h'] if not robot else a['robot_supervision_twd_h']+a['robot_equipment_twd_h']
    people=a['robot_supervision_people'] if robot else a['human_crew_people']
    phases=[dict(phase='原流程（含失敗評估）',hours=original_h,cost_twd=original_h*original_rate,
                 person_hours=original_h*people,path_m=r['path_m'])]
    fallback=None
    can_exit=bool(r['exit_route'])
    if pending and can_exit:
        handoff_h=a['fallback_handoff_minutes']/60
        # Robot supervisor + incoming human crew attend handoff; A uses the same crew.
        handoff_rate=original_rate+(a['human_crew_twd_h'] if robot else 0)
        handoff_people=people+(a['human_crew_people'] if robot else 0)
        phases.append(dict(phase='交接／重新安排',hours=handoff_h,cost_twd=handoff_h*handoff_rate,
                           person_hours=handoff_h*handoff_people,path_m=0.))
        fallback=evaluate(interior,'A',a,levels,placed,pending)
        fallback_h=fallback['attempted_hours']+fallback['failed']*a['failure_review_minutes']/60
        phases.append(dict(phase='人工準備與補作',hours=fallback_h,cost_twd=fallback_h*a['human_crew_twd_h'],
                           person_hours=fallback_h*a['human_crew_people'],path_m=fallback['path_m']))
    success=r['success']+(fallback['success'] if fallback else 0)
    complete=can_exit and success==r['tasks'] and (fallback is None or fallback['complete'])
    totals={k:sum(p[k] for p in phases) for k in ['hours','cost_twd','person_hours','path_m']}
    return dict(complete=complete,success=success,tasks=r['tasks'],fallback_count=fallback['success'] if fallback else 0,
                fallback=fallback,phases=phases,attempted_totals=totals,
                **{k:v if complete else None for k,v in totals.items()})


RADAR_METRICS=[('工期效率','hours','radar_hours_per_piece','h'),
               ('成本效率','cost_twd','radar_cost_per_piece','TWD'),
               ('移動效率','path_m','radar_path_per_piece','m'),
               ('人力投入效率','person_hours','radar_person_hours_per_piece','人時')]

def radar_data(study):
    data=[]
    for r in study['results']:
        w=r['completed_work']
        for label,key,cap_key,unit in RADAR_METRICS:
            cap=study['assumptions'][cap_key]*r['tasks'];value=w[key]
            score=max(0.,min(100.,100*(1-value/cap))) if value is not None and cap else None
            data.append(dict(method=r['method'],metric=label,key=key,raw=value,unit=unit,zero_score_bound=cap,
                             score=score,clipped=value is not None and value>cap))
    return data

def completed_rows(study):
    return [dict(流程=r['method']+(' 原流程＋人工補作' if r['completed_work']['fallback'] else ' 原流程'),
        原流程完成率_pct=round(r['access_rate']*100,2),原流程完成件=r['success'],人工補作件=r['completed_work']['fallback_count'],
        最終完成=f"{r['completed_work']['success']}/{r['tasks']}",
        **{label:round(r['completed_work'][key],2) if r['completed_work'][key] is not None else None
           for label,key in [('完整工期_h','hours'),('完整成本_TWD','cost_twd'),('完整移動_m','path_m'),('人力投入_人時','person_hours')]},
        狀態='全部完成二維預檢' if r['completed_work']['complete'] else '補作後仍未完成') for r in study['results']]

def rows(study):
    names={'A':'A 人工装配情境','B':'B 機器人／固定順序','C':'C AI 提案／機器人'}
    return [dict(流程=names[r['method']],完成構件=f"{r['success']}/{r['tasks']}",通道站位通過率=round(r['access_rate']*100,1),
                 移動距離_m=round(r['path_m'],2),換站次數=r['station_changes'],
                 完整工期_h=round(r['completion_hours'],2) if r['complete'] else None,
                 完整作業成本_TWD=round(r['completion_cost_twd']) if r['complete'] else None,
                 已嘗試工時_h=round(r['attempted_hours'],2),狀態='完成二維預檢' if r['complete'] else '未完成') for r in study['results']]

def sensitivity(study):
    """Reprice the same logs. No fabricated measurements or additional experiments."""
    out=[]
    for factor in [.75,1.,1.25]:
        for r in study['results']:
            a=study['assumptions'];robot=r['method']!='A';prefix='robot' if robot else 'human'
            w=r['completed_work'];base_delta=r['success']*a[prefix+'_minutes_piece']*(factor-1)/60
            fallback_delta=w['fallback_count']*a['human_minutes_piece']*(factor-1)/60
            h=w['attempted_totals']['hours']+base_delta+fallback_delta
            rate=a['human_crew_twd_h'] if not robot else a['robot_supervision_twd_h']+a['robot_equipment_twd_h']
            cost=w['attempted_totals']['cost_twd']+base_delta*rate+fallback_delta*a['human_crew_twd_h']
            out.append(dict(method=r['method'],piece_time_factor=factor,hours=h,cost_twd=cost,complete=w['complete']))
    return out
