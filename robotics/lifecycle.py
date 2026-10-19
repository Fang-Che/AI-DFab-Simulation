"""R8 fabrication + assembly scenarios. Every score has an auditable, uncalibrated model.

This is an offline digital-twin prototype: no physical-state synchronization or live LLM.
No method receives an automatic precision/safety/speed bonus.
"""
import copy, hashlib, json, math
from . import study as access

VERSION='R8-six-axis-v1'
NAMES={'A':'A 數位製造＋人工組裝','B':'B 數位製造＋機器人組裝','C':'C 孿生模擬＋自動化'}
# Defaults are scenario inputs, not supplier claims or measured robot performance.
PARAMS=[
 ('sheet_area_m2','板材面積 m²/張',2.9768),('sheet_utilization','板材利用率',.8),
 ('sheet_waste','板材追加耗損比例',.05),('sheet_twd','板材 TWD/張',1800.),
 ('cnc_minutes_sheet','CNC 加工 min/張',22.5),('cnc_setup_minutes','CNC 準備 min',30.),
 ('cnc_equipment_twd_h','CNC 設備 TWD/h',800.),('operator_twd_h','工廠操作員 TWD/人時',600.),
 ('factory_manual_minutes_piece','A 工廠搬料／單元組裝 min/件',8.),
 ('factory_robot_minutes_piece','B=C 工廠搬料／單元組裝 min/件',8.),
 ('factory_manual_setup','A 工廠單元組裝準備 min',20.),
 ('factory_robot_setup','B=C 工廠單元組裝準備 min',45.),
 ('base_planning_minutes','三組基礎製程規劃 min',30.),
 ('robot_programming_minutes','B=C 機器人程式／檢查 min',20.),
 ('twin_setup_minutes','C 孿生模型建立／核對 min',30.),
 ('twin_candidate_minutes','C 每候選方案審查 min',5.),
 ('planning_twd_h','規劃人員 TWD/人時',600.),
 ('manufacture_sigma_mm','共用 CNC 尺寸誤差 σ mm',.3),
 ('grip_sigma_mm','共用抓持／治具誤差 σ mm',.4),
 ('registration_sigma_mm','共用座標定位誤差 σ mm',.8),
 ('manual_place_sigma_mm','人工最終定位誤差 σ mm',.8),
 ('robot_place_sigma_mm','B=C 最終定位誤差 σ mm',.8),
 ('tolerance_mm','裝配平面位置公差半徑 mm',2.),
 ('cnc_exposure_fraction','CNC 作業人時的危險區占比',.25),
 ('manual_exposure_fraction','人工主动作業人時的危險區占比',.25),
 ('robot_exposure_fraction','機器人監督人時的危險區占比',.25),
 ('hours_bound_piece','工期 0 分上限 h/件',1.5),
 ('cost_bound_piece','成本 0 分上限 TWD/件',6000.),
 ('person_hours_bound_piece','人力 0 分上限 人時/件',2.),
 ('exposure_bound_piece','暴露 0 分上限 人時/件',.5),
]
DEFAULTS={k:v for k,_,v in PARAMS}
METRICS=[('工期效率','hours','hours_bound_piece','h'),
 ('成本效率','cost_twd','cost_bound_piece','TWD'),
 ('人力投入效率','person_hours','person_hours_bound_piece','人時'),
 ('公差符合率','tolerance_pct',None,'%'),
 ('危險區暴露控制','exposure_person_hours','exposure_bound_piece','人時'),
 ('條件變動適應能力','adaptability_pct',None,'%')]

def validate(values=None):
    p={**DEFAULTS,**(values or {})}
    if set(p)!=set(DEFAULTS):raise ValueError('未知製造／六軸參數')
    if any(not isinstance(v,(float,int)) or not math.isfinite(v) or v<0 for v in p.values()):raise ValueError('參數需為有限非負數')
    for k in ['sheet_area_m2','sheet_utilization','hours_bound_piece','cost_bound_piece','person_hours_bound_piece','exposure_bound_piece']:
        if p[k]<=0:raise ValueError(k+' 必須大於零')
    for k in ['sheet_utilization','sheet_waste','cnc_exposure_fraction','manual_exposure_fraction','robot_exposure_fraction']:
        if p[k]>1:raise ValueError(k+' 需介於 0 與 1')
    return p

def choose_twin(b,c):
    """Same hardware/evaluator; select from two recorded, assistant-authored candidate rules."""
    candidates=[('近端優先',b),('遠端優先／延後封閉',c)]
    strategy,chosen=min(candidates,key=lambda pair:(not pair[1]['complete'],pair[1]['failed'],pair[1]['attempted_hours'],pair[0]))
    result=copy.deepcopy(chosen);result['method']='C'
    record=dict(selected=strategy,mode='offline_candidate_evaluation',live_ai=False,physical_sync=False,
        candidates=[dict(strategy=label,success=r['success'],tasks=r['tasks'],complete=r['complete'],
                         attempted_hours=r['attempted_hours'],path_m=r['path_m']) for label,r in candidates])
    return result,record

def condition_suite(base):
    """Five prespecified scenarios, common across methods. No success multiplier."""
    a=base['assumptions'];interior=base['interior'];levels=base['levels']
    variants=[('S0','基準',{},None),('S1','額外淨空 +50 mm',{'clearance_mm':a['clearance_mm']+50},None),
       ('S2','定位工具使有效作業半徑減少 100 mm',
        {'robot_reach_mm':max(1,a['robot_reach_mm']-100),'human_reach_mm':max(1,a['human_reach_mm']-100)},None),
       ('S3','公共區臨時堆料',{},[3400,3600,4150,4350]),
       ('S4','額外淨空與臨時堆料同時發生',{'clearance_mm':a['clearance_mm']+50},[3400,3600,4150,4350])]
    out=[]
    for sid,label,delta,obstacle in variants:
        settings={**a,**delta}
        if sid=='S0':rs=base['results'];cr,record=choose_twin(rs[1],rs[2]);rs=[rs[0],rs[1],cr]
        else:
            rs=[access.evaluate(interior,m,settings,levels,extra_obstacle=obstacle) for m in ['A','B','C']]
            cr,record=choose_twin(rs[1],rs[2]);rs=[rs[0],rs[1],cr]
        for r in rs:
            out.append(dict(scenario=sid,label=label,method=r['method'],tasks=r['tasks'],success=r['success'],
                complete=r['complete'],path_m=r['path_m'],attempted_hours=r['attempted_hours'],
                settings_delta=delta,extra_obstacle=obstacle,events=r['events'],exit_route=r['exit_route'],start=r['start'],
                radius_mm=r['radius_mm'],twin=record if r['method']=='C' else None))
    return out

def tolerance(p,robot):
    """Analytical isotropic 2D Gaussian error budget; NOT observed dimensional accuracy."""
    components={k:p[k] for k in ['manufacture_sigma_mm','grip_sigma_mm','registration_sigma_mm']}
    components['placement_sigma_mm']=p['robot_place_sigma_mm' if robot else 'manual_place_sigma_mm']
    variance=sum(v*v for v in components.values())
    probability=1.-math.exp(-p['tolerance_mm']**2/(2*variance)) if variance else 1.
    return dict(components=components,sigma_mm=math.sqrt(variance),probability=probability,
                tolerance_mm=p['tolerance_mm'],model='independent_zero_mean_isotropic_2d_gaussian')

def enrich(base,values=None):
    p=validate(values);result=copy.deepcopy(base);a=result['assumptions'];n=len(result['interior']['parts'])
    if not n:raise ValueError('六軸比較需要至少一件隔間構件')
    original_c=copy.deepcopy(result['results'][2])
    c,proposal=choose_twin(result['results'][1],original_c)
    c['completed_work']=access.complete_work(result['interior'],c,a,result['levels'])
    result['results'][2]=c
    suite=condition_suite(base)
    area=result['interior']['skin_area_m2'];sheets=math.ceil(area/p['sheet_area_m2']/p['sheet_utilization']*(1+p['sheet_waste']))
    fabrication=dict(panel_area_m2=area,sheets=sheets,sheet_area_m2=p['sheet_area_m2'],
        basis='研究隔間雙面板面積／板張面積／利用率 × (1+耗損)，向上取整；未排版、未產生 CNC 刀路、未含內肋與接頭詳設。')
    for r in result['results']:
        robot=r['method']!='A';w=r['completed_work'];phases=[]
        def add(name,hours,people,rate,equipment=0.,exposure=0.,material=0.,basis='參數情境估算'):
            phases.append(dict(phase=name,hours=hours,person_hours=hours*people,cost_twd=hours*(rate+equipment)+material,
                exposure_person_hours=hours*people*exposure,exposure_fraction=exposure,basis=basis))
        planning=(p['base_planning_minutes']+(p['robot_programming_minutes'] if robot else 0)+
                  (p['twin_setup_minutes']+len(proposal['candidates'])*p['twin_candidate_minutes'] if r['method']=='C' else 0))/60
        add('製程規劃'+('／孿生候選審查' if r['method']=='C' else ''),planning,1,p['planning_twd_h'])
        add('板材採購（僅計材料額）',0,0,0,material=sheets*p['sheet_twd'])
        add('CNC 準備',p['cnc_setup_minutes']/60,1,p['operator_twd_h'],p['cnc_equipment_twd_h'])
        add('CNC 製造',sheets*p['cnc_minutes_sheet']/60,1,p['operator_twd_h'],p['cnc_equipment_twd_h'],p['cnc_exposure_fraction'])
        crew=a['robot_supervision_people'] if robot else a['human_crew_people']
        rate=a['robot_supervision_twd_h'] if robot else a['human_crew_twd_h'];equipment=a['robot_equipment_twd_h'] if robot else 0
        add('工廠單元組裝準備',p['factory_robot_setup' if robot else 'factory_manual_setup']/60,crew,rate,equipment)
        add('工廠搬料／單元組裝',n*p['factory_robot_minutes_piece' if robot else 'factory_manual_minutes_piece']/60,
            crew,rate,equipment,p['robot_exposure_fraction' if robot else 'manual_exposure_fraction'])
        # Use actual access-model work logs. Setup, review and handoff assume energy isolated.
        for phase in w['phases']:
            q={k:v for k,v in phase.items() if k!='path_m'};q['phase']='現場 '+q['phase'];q['basis']='二維逐件紀錄＋準備／交接假設'
            if phase['phase'].startswith('原流程'):
                active=sum(e['minutes'] for e in r['events'])/60
                speed=a['robot_speed_m_s' if robot else 'human_speed_m_s']
                exit_m=sum(math.dist(x,y) for x,y in zip(r['exit_route'],r['exit_route'][1:]))/1000
                active+=exit_m/speed/3600;fraction=p['robot_exposure_fraction' if robot else 'manual_exposure_fraction']
                q['exposure_person_hours']=active*crew*fraction
            elif phase['phase']=='人工準備與補作':
                fb=w['fallback'];active=max(0,fb['attempted_hours']-a['human_setup_minutes']/60)
                fraction=p['manual_exposure_fraction'];q['exposure_person_hours']=active*a['human_crew_people']*fraction
            else:fraction=0.;q['exposure_person_hours']=0.
            q['exposure_fraction']=fraction;phases.append(q)
        totals={k:sum(q[k] for q in phases) for k in ['hours','cost_twd','person_hours','exposure_person_hours']}
        primary=tolerance(p,robot);manual=tolerance(p,False)
        # Weight only successfully installed pieces; no fabricated quality for unresolved work.
        conformity=(r['success']*primary['probability']+w['fallback_count']*manual['probability'])/n*100 if w['complete'] else None
        cases=[v for v in suite if v['method']==r['method']];passed=sum(v['complete'] for v in cases)
        r['lifecycle']=dict(complete=w['complete'],phases=phases,attempted_totals=totals,
            **{k:v if w['complete'] else None for k,v in totals.items()},tolerance_pct=conformity,
            error_budget=dict(primary=primary,fallback=manual,primary_count=r['success'],fallback_count=w['fallback_count']),
            adaptability_pct=passed/len(cases)*100,scenario_success=passed,scenario_count=len(cases))
    result['id']=hashlib.sha256(json.dumps([VERSION,base['id'],p],sort_keys=True).encode()).hexdigest()[:12]
    result['version']=VERSION;result['lifecycle_params']=p;result['fabrication']=fabrication;result['conditions']=suite;result['twin_plan']=proposal
    result['scope']='指定樓層研究隔間：製程規劃、板材預算、CNC 製造、工廠單元組裝、現場裝配及人工補作。工序串行。'
    result['limitations']=[
        '六軸是未校準的情境估算；單件代表研究隔間單元，不能外推為整屋或真實 WikiHouse 接頭性能。',
        'C 是離線數位孿生流程原型：幾何／狀態模型、候選方案模擬與重規劃；未同步實體感測、未呼叫線上 AI 或 ROS。',
        'A/B 固定近端優先；C 從同一檢查器評估的兩種已保存策略中選擇。三組均重算站位；這是特定規劃政策比較。',
        '三組共用 CNC 板材及加工假設；工廠機器人搬料／單元組裝以週期估算，尚未逐板執行機械手臂軌跡。',
        '公差率為獨立零均值二維常態誤差合成的解析機率，未含角度、系統偏差、變形與接頭接觸；不是量測合格率。',
        '危險區暴露 = 主动作業人時 × 假設占比；未追蹤人員位置、未做風險評估。準備、評估、交接假設停機隔離。',
        '適應能力是五個指定情境中，補作前完成全部通行／站位任務的比例；不是統計成功機率或整體製造可靠度。',
        '條件測試是離線評估，不將五次試算全部算成建造工時；C 基準方案另計兩候選審查與孿生建模工時假設。',
        '相同人工補作規則保留原流程已安裝障礙。完整工期包含製造及組裝，不含物流、跨樓層搬運、骨架詳設及品質返工。',
        '公差率未回饋返工成本，所以全部完成指排程／通行完成，不代表全部品質驗收合格。',
        '製造材料成本獨立於全屋預算，兩者不能直接相加；板材、工時、誤差與暴露參數皆為可編輯示範值。',
        '前三軸與暴露軸採固定可改的展示上限；公差率與適應率直接用百分比。不按雷達面積排名。']
    return result

def radar_data(study):
    if 'lifecycle_params' not in study:return access.radar_data(study)
    p=study['lifecycle_params'];out=[]
    for r in study['results']:
        w=r['lifecycle']
        for label,key,boundkey,unit in METRICS:
            value=w[key];bound=p[boundkey]*r['tasks'] if boundkey else None
            score=(max(0,min(100,100*(1-value/bound))) if boundkey else value) if value is not None and w['complete'] else None
            out.append(dict(method=r['method'],metric=label,key=key,raw=value,unit=unit,zero_score_bound=bound,score=score,
                direction='lower' if boundkey else 'higher',clipped=bound is not None and value is not None and value>bound,
                evidence='未校準情境模型' if key!='adaptability_pct' else '5 個指定二維情境測試'))
    return out

def rows(study):
    if 'lifecycle_params' not in study:return access.completed_rows(study)
    return [dict(流程=NAMES[r['method']],原流程完成率_pct=round(r['access_rate']*100,2),人工補作件=r['completed_work']['fallback_count'],
        **{label:round(r['lifecycle'][key],2) if r['lifecycle'][key] is not None else None for label,key in
           [('製造與組裝工期_h','hours'),('材料與作業成本_TWD','cost_twd'),('人力投入_人時','person_hours'),
            ('公差符合率_pct','tolerance_pct'),('危險區暴露_人時','exposure_person_hours'),('適應能力_pct','adaptability_pct')]},
        狀態='排程／通行完成' if r['lifecycle']['complete'] else '尚有未完成件') for r in study['results']]

def condition_rows(study):
    return [dict(情境=v['scenario']+' '+v['label'],流程=v['method'],完成件=f"{v['success']}/{v['tasks']}",
                 原流程全完成=v['complete'],採用策略=v['twin']['selected'] if v['twin'] else '近端優先') for v in study.get('conditions',[])]
