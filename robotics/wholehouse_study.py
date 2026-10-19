"""Author-hypothesis whole-house work breakdown. Not calibrated performance evidence.

Ranks are inspected after computing work; no objective fits values to desired ranks.
"""
import math,json,hashlib,copy
from .estimating import quantity_takeoff

VERSION='R9-wholehouse-hypothesis-1'
NAMES={'A':'A 傳統數位製造／全人工組裝','B':'B 機器人製造與組裝','C':'C AI／孿生＋自動化'}
COMMON=[('sheet_price','板材 TWD/張',1800.),('utilization','板材利用率',.8),('waste','追加板材耗損比例',.05),
 ('cnc_minutes','CNC 加工 min/張（三組相同）',22.5),('cnc_rate','CNC 機台 TWD/h',800.),
 ('worker_rate','施工／操作員 TWD/人時',600.),('engineer_rate','設計校核／校正 TWD/人時',1000.),
 ('robot_rate','機器人運轉 TWD/h（B/C 相同）',600.),('robot_mobilization','機器人租用／治具／進退場暫列金 B=C',200000.),
 ('ai_services_twd','C 孿生／AI 軟體服務暫列 TWD',10000.),('hardware_twd','接頭／緊固件暫列 TWD',12000.),('foundation_h_m2','基礎／基地班組 h/占地m²',.6),('foundation_material_m2','基礎／基地材料暫列 TWD/m²',1200.),
 ('finish_h_m2','機電／門窗／防水／裝修班組 h/m²',1.),('finish_material_m2','機電／門窗／防水／裝修材料暫列 TWD/m²',4000.),
 ('delivery_hours','每批運輸／吊運銜接 h',2.),('delivery_cost','每批運輸固定額 TWD',2500.),
 ('tolerance_mm','平面裝配位置公差半徑 mm',2.),('cut_sigma','CNC 誤差 σ mm',.3),
 ('hours_cap_m2','工期雷達 0 分上限 h/m²',12.),('cost_cap_m2','成本雷達 0 分上限 TWD/m²',45000.),
 ('labor_cap_m2','人力雷達 0 分上限 人時/m²',35.),('exposure_cap_m2','暴露雷達 0 分上限 人時/m²',8.),
 ('change_cap_hours','適應能力 0 分：平均變更處理工期 h',48.)]
FIELDS=[('design_h','設計建模 h'),('review_h_module','設計校核／校稿 h/模組'),
 ('program_h','CAM／機器人程式準備 h'),('twin_h','孿生建模／模擬審查 h'),
 ('factory_setup_h','工廠準備／校正 h'),('factory_cycle_h','工廠單元組裝 h/模組'),
 ('factory_check_h','工廠人工校正 h/模組'),('site_layout_h_m2','現場放樣／定位 h/m²'),
 ('site_cycle_h','現場組裝 h/模組'),('site_check_h','現場人工校正 h/模組'),
 ('factory_people','工廠組裝在場人數'),('site_people','現場組裝在場人數'),
 ('batch_modules','每批生產／交付模組數'),('position_sigma','殘餘定位誤差 σ mm'),
 ('registration_sigma','殘餘放樣／座標誤差 σ mm'),('grip_sigma','抓持／治具誤差 σ mm'),
 ('exposure_fraction','主動作業危險區占比'),('change_response_h','變更辨識／規劃回應 h'),
 ('change_review_h_module','變更重校核 h/受影響模組')]
VALUES={
 'A':[60.,.6,12.,0.,4.,.5,.1,.3,.55,.12,2.,4.,10000.,3.,2.,1.,.15,4.,.1],
 'B':[60.,1.2,32.,0.,32.,.16,.2,.15,.18,.16,1.,2.,40.,1.,1.2,.4,.6,10.,.3],
 'C':[16.,.08,8.,20.,12.,.16,.025,.05,.18,.02,1.,1.,20.,.5,.3,.4,.04,4.,.1]}
DEFAULT={'common':{k:v for k,_,v in COMMON},'methods':{m:dict(zip([k for k,_ in FIELDS],vs)) for m,vs in VALUES.items()}}
TARGETS={'hours':['C','B','A'],'cost_twd':['C','A','B'],'person_hours':['C','B','A'],
         'tolerance_pct':['C','B','A'],'exposure_person_hours':['C','A','B']}
METRICS=[('工期效率','hours','hours_cap_m2','h'),('成本效率','cost_twd','cost_cap_m2','TWD'),
 ('人力投入效率','person_hours','labor_cap_m2','人時'),('公差符合率','tolerance_pct',None,'%'),
 ('危險區暴露控制','exposure_person_hours','exposure_cap_m2','人時'),('條件變動適應能力','adaptability_pct',None,'%')]

def validate(params=None):
    p=copy.deepcopy(DEFAULT)
    if params:
        p['common'].update(params.get('common',{}))
        for m in ['A','B','C']:p['methods'][m].update(params.get('methods',{}).get(m,{}))
    if set(p['common'])!=set(DEFAULT['common']):raise ValueError('未知共同參數')
    for values in [p['common']]+list(p['methods'].values()):
        if any(not isinstance(x,(float,int)) or not math.isfinite(x) or x<0 for x in values.values()):raise ValueError('參數需為有限非負數')
    c=p['common']
    if not 0<c['utilization']<=1 or c['waste']>1:raise ValueError('利用率需在 (0,1]，耗損比例需在 [0,1]')
    for k in ['hours_cap_m2','cost_cap_m2','labor_cap_m2','exposure_cap_m2','change_cap_hours']:
        if c[k]<=0:raise ValueError('雷達尺度需大於零')
    for v in p['methods'].values():
        if set(v)!=set(DEFAULT['methods']['A']):raise ValueError('未知流程參數')
        for k in ['factory_people','site_people','batch_modules']:
            if v[k]<1 or int(v[k])!=v[k]:raise ValueError('人數與批量需為正整數')
        if v['exposure_fraction']>1:raise ValueError('暴露占比需在 [0,1]')
    return p

def quality(c,v):
    variance=sum(x*x for x in [c['cut_sigma'],v['position_sigma'],v['registration_sigma'],v['grip_sigma']])
    return 1-math.exp(-c['tolerance_mm']**2/(2*variance)) if variance else 1.

def schedule(h,q,method,p):
    c=p['common'];v=p['methods'][method];area=h['floor_area_m2'];footprint=h.get('footprint_area_m2',area/h['levels']);n=len(h['items']);robot=method!='A'
    sheets=math.ceil(q['area_m2']/2.9768/c['utilization']*(1+c['waste']))
    events=[];ends={};resources={}
    def task(key,label,hours,dependencies=(),resource=None,people=0.,rate=0.,equipment=0.,fixed=0.,exposure=0.,scope='全屋',modules=None):
        start=max([ends[d] for d in dependencies]+[resources.get(resource,0.)] if resource else [ends[d] for d in dependencies]+[0.])
        end=start+hours;ends[key]=end
        if resource:resources[resource]=end
        events.append(dict(id=key,phase=label,start_h=start,end_h=end,hours=hours,dependencies=list(dependencies),resource=resource,
            people=people,person_hours=hours*people,cost_twd=hours*(people*rate+equipment)+fixed,
            exposure_person_hours=hours*people*exposure,exposure_fraction=exposure,scope=scope,modules=modules or []))
    task('design','設計與建模',v['design_h'],people=1,rate=c['engineer_rate'])
    task('review','設計校核／校稿',n*v['review_h_module'],['design'],people=1,rate=c['engineer_rate'])
    task('program','CAM／程式準備',v['program_h'],['review'],people=1,rate=c['engineer_rate'])
    task('twin','孿生建模／模擬審查',v['twin_h'],['program'],people=1,rate=c['engineer_rate'])
    task('purchase','板材預算及設備進退場',0,['twin'],fixed=sheets*c['sheet_price']+(c['robot_mobilization'] if robot else 0)+c['hardware_twd']+(c['ai_services_twd'] if method=='C' else 0))
    task('foundation','基礎／基地（暫列工序）',footprint*c['foundation_h_m2'],['review'],people=3,rate=c['worker_rate'],
         fixed=footprint*c['foundation_material_m2'],exposure=.1)
    task('factory_setup','工廠準備／校正',v['factory_setup_h'],['twin'],resource='factory',people=1,rate=c['engineer_rate'])
    task('layout','現場放樣／定位',area*v['site_layout_h_m2'],['foundation','twin'],resource='site',people=v['site_people'],rate=c['worker_rate'])
    size=int(v['batch_modules']);batches=[h['items'][i:i+size] for i in range(0,n,size)]
    # Proportional sheet allocation conserves the whole-house sheet budget exactly.
    previous_site='layout';quality_p=quality(c,v);expected_rework=0.
    for i,batch in enumerate(batches):
        count=len(batch);ids=[it['id'] for it in batch];prefix=f'b{i+1}_';scope=f'第 {i+1} 批／{count} 模組'
        task(prefix+'cnc','CNC 製造',sheets*count/n*c['cnc_minutes']/60,['factory_setup'],resource='cnc',people=1,rate=c['worker_rate'],equipment=c['cnc_rate'],exposure=.05,scope=scope,modules=ids)
        task(prefix+'factory','工廠單元組裝',count*v['factory_cycle_h'],[prefix+'cnc'],resource='factory',people=v['factory_people'],rate=c['worker_rate'],equipment=c['robot_rate'] if robot else 0,exposure=v['exposure_fraction'],scope=scope,modules=ids)
        task(prefix+'check','工廠校正／檢查',count*v['factory_check_h'],[prefix+'factory'],resource='factory',people=1,rate=c['engineer_rate'],scope=scope,modules=ids)
        task(prefix+'delivery','運輸／吊運銜接',c['delivery_hours'],[prefix+'check'],resource='delivery',people=2,rate=c['worker_rate'],fixed=c['delivery_cost'],exposure=.1,scope=scope,modules=ids)
        task(prefix+'site','現場組裝',count*v['site_cycle_h'],[prefix+'delivery',previous_site],resource='site',people=v['site_people'],rate=c['worker_rate'],equipment=c['robot_rate'] if robot else 0,exposure=v['exposure_fraction'],scope=scope,modules=ids)
        task(prefix+'calibration','現場校正／檢查',count*v['site_check_h'],[prefix+'site'],resource='site',people=1,rate=c['engineer_rate'],scope=scope,modules=ids)
        # One expected correction pass; not a claim that all joints are finally accepted.
        qty=count*(1-quality_p);expected_rework+=qty
        task(prefix+'rework','預期一次返工',qty*(v['site_cycle_h']+v['site_check_h']),[prefix+'calibration'],resource='site',people=v['site_people'],rate=c['worker_rate'],equipment=c['robot_rate'] if robot else 0,exposure=v['exposure_fraction'],scope=scope,modules=ids)
        previous_site=prefix+'rework'
    task('finish','機電／門窗／防水／裝修（暫列）',area*c['finish_h_m2'],[previous_site],people=3,rate=c['worker_rate'],fixed=area*c['finish_material_m2'],exposure=.1)
    totals={k:sum(e[k] for e in events) for k in ['cost_twd','person_hours','exposure_person_hours']}
    totals['hours']=max(ends.values());totals['process_hours']=sum(e['hours'] for e in events)
    totals['tolerance_pct']=quality_p*100
    return dict(method=method,events=events,sheets=sheets,batches=len(batches),modules=n,expected_rework_modules=expected_rework,**totals)

CHANGES=[('設計修改／重新出圖',.05,0.),('尺寸偏差／重製',.03,0.),('設備中斷／重排',.02,8.),('現場障礙／順序調整',.03,0.),('構件損傷／補件',.02,0.)]

def changes(result,p,method,response_override=None):
    c=p['common'];v=p['methods'][method];out=[]
    for label,fraction,downtime in CHANGES:
        qty=max(1,math.ceil(result['modules']*fraction));sheets=result['sheets']*qty/result['modules']
        response=v['change_response_h'] if response_override is None else response_override
        # Explicit serial recovery work package after issue identification; no risk/physics claims.
        stages={'辨識／規劃':response,'重校核':qty*v['change_review_h_module'],'設備停機':downtime,
                '重製 CNC':sheets*c['cnc_minutes']/60 if label!='現場障礙／順序調整' else 0.,
                '單元重組裝':qty*v['factory_cycle_h'] if label!='現場障礙／順序調整' else 0.,
                '現場重定位':qty*(v['site_cycle_h']+v['site_check_h'])}
        out.append(dict(scenario=label,affected_modules=qty,stages=stages,recovery_hours=sum(stages.values())))
    return out

def evaluate(h,params=None):
    p=validate(params);q=quantity_takeoff(h);rs=[schedule(h,q,m,p) for m in ['A','B','C']]
    for r in rs:
        r['changes']=changes(r,p,r['method']);mean=sum(x['recovery_hours'] for x in r['changes'])/len(CHANGES)
        r['mean_recovery_hours']=mean;r['adaptability_pct']=max(0,100*(1-mean/p['common']['change_cap_hours']))
        r['adaptability_sensitivity']=[dict(response_h=hrs,mean_recovery_hours=sum(x['recovery_hours'] for x in changes(r,p,r['method'],hrs))/len(CHANGES)) for hrs in [1.,4.,8.,16.]]
    check=[]
    for key,target in TARGETS.items():
        order=[r['method'] for r in sorted(rs,key=lambda r:r[key],reverse=key=='tolerance_pct')]
        check.append(dict(metric=key,expected_best_to_worst=target,calculated_best_to_worst=order,matches=order==target))
    identity=hashlib.sha256(json.dumps([VERSION,h['design_id'],q,p],sort_keys=True).encode()).hexdigest()[:12]
    return dict(id=identity,version=VERSION,design_id=h['design_id'],layout=h['layout_name'],levels=h['levels'],area_m2=h['floor_area_m2'],
        params=p,results=rs,quantity=q,hypothesis_check=check,
        status='研究假設情境；非實測驗證；未用排序反推或自動校準參數',
        scope='全屋模型構件＋基地／基礎及機電／門窗／防水／裝修暫列工序；同一方案與材料面積，非核准施工預算',
        assumptions=[
            '數值是依使用者機制假設建立的可編輯示範初值，非供應商報價或實測；目標排序另列，結果由工序計算。',
            'A 含人工放樣、工廠與現場組裝。B 含機器人程式、人工校核與校正。C 假設孿生自動校核、批次交付與閉迴路校正已部署。',
            'C 的上述自動化成效目前未由平台或實機驗證；數值不是現有離線 AI 提案工具的量測能力。',
            'B/C 物理組裝週期與機器人運轉費率預設相同，差異主要為設計校核、校正、批量、返工與在場人數。',
            '每組一台 CNC、獨立工廠組裝資源及現場班組、一運輸資源；B/C 工廠與現場為不同機器人資源；不同資源可重疊，同資源不重疊。批次依目前全屋裝配清單。',
            '機器人固定暫列金 B/C 相同，運轉時費另計；固定額假設為租用、治具及進退場，不再包含已列人工校正工時。',
            '公差為獨立零均值二維常態誤差模型；C 較低殘餘誤差是閉迴路校正研究假設，非實際精度。',
            '返工只計一次期望處理量，不宣稱完成後全部接頭合格；未建立多次返工或角度／變形／接觸模型。',
            '危險區暴露為作業人時乘假設占比。B 較高占比、C 較低占比屬風險防護情境，不代表安全性驗證。',
            '適應能力以五類變更的平均處理工期作代理；尚未重建變更後三維幾何或機器人路徑。A/C 回應時間附敏感度，不預設普遍優劣。',
            '基礎以占地面積、完工工程以樓板面積暫列；未含土地、規費、稅費、採購等待與養護日曆。工期為排定的工作小時，非實際日期。',
            '設計、校核與校正假設在隔離狀態作業，暴露暫計零；其餘主動作業採各流程占比，共同 CNC 5%、運輸及基礎裝修 10%。',
            '各類模組暫用同一平均週期，未按板件數、接頭及尺寸分級估時。',
            '人數、批量、誤差及校核策略同步變更；此情境比較不能單獨辨識 AI 技術的因果效應。',
            '來源構件面積與示意構件面積依現有清單估算；未精確排版、材料與接點詳設。此報告不能與舊全屋預算相加。'])

def rows(s):
    return [dict(流程=NAMES[r['method']],總工期_h=round(r['hours'],2),總成本_TWD=round(r['cost_twd']),
        人力投入_人時=round(r['person_hours'],2),公差符合率_pct=round(r['tolerance_pct'],2),
        危險區暴露_人時=round(r['exposure_person_hours'],2),平均變更處理_h=round(r['mean_recovery_hours'],2),
        適應分數=round(r['adaptability_pct'],2)) for r in s['results']]

def radar_data(s):
    out=[]
    for r in s['results']:
        for label,k,capkey,unit in METRICS:
            cap=s['params']['common'][capkey]*s['area_m2'] if capkey else None
            score=max(0,100*(1-r[k]/cap)) if capkey else r[k]
            out.append(dict(method=r['method'],metric=label,raw=r[k],unit=unit,score=score,cap=cap,
                source='研究假設情境／未校準',clipped=cap is not None and r[k]>cap))
    return out


def boundaries(s):
    """One-variable break-even conditions, not automatic fitting."""
    a,b,c=s['results'];p=s['params'];fixed=p['common']['robot_mobilization']
    lower=a['cost_twd']-(b['cost_twd']-fixed)
    upper=a['cost_twd']-(c['cost_twd']-fixed)
    # Only assembly and rework have the method-specific exposure factor.
    coefficient=sum(e['person_hours'] for e in b['events'] if e['phase'] in ['工廠單元組裝','現場組裝','預期一次返工'])
    intercept=b['exposure_person_hours']-coefficient*p['methods']['B']['exposure_fraction']
    exposure_threshold=(a['exposure_person_hours']-intercept)/coefficient if coefficient else None
    response_threshold=a['mean_recovery_hours']-(c['mean_recovery_hours']-p['methods']['C']['change_response_h'])
    return dict(robot_fixed_cost_lower=lower,robot_fixed_cost_upper=upper,
        b_exposure_fraction_lower=exposure_threshold,c_response_h_upper=response_threshold,
        basis='其餘參數固定；成本、暴露、適應分別做單參數損益分界，不自動套用。')
