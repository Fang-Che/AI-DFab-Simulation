"""Six-axis evidence sheets; vector paths for both SVG and PDF."""
import math
from .drawings import Sheet
from .lifecycle import METRICS,NAMES,radar_data
COLORS={'A':'#537f90','B':'#cb8755','C':'#427b64'}

def radar_sheet(h,study):
    s=Sheet('R102','製造與組裝｜六軸比較＋原流程完成率',h);data=radar_data(study)
    c=study['interior']['config'];s.text(70,139,f"{c['floor']}F 研究隔間 | {c['bedrooms']} 房 | 門寬 {c['door_width']} mm | {len(study['interior']['parts'])} 件",12)
    s.text(70,165,'外圍較高；全部為情境模型，非實測績效評等',13,'#a04a31')
    cx,cy,rad=330,355,140
    def point(i,value):
        angle=-math.pi/2+i*math.pi/3;return cx+rad*value/100*math.cos(angle),cy+rad*value/100*math.sin(angle)
    for tick in [25,50,75,100]:
        s.poly([point(i,tick) for i in range(6)],'none','#c4d2d9',.8)
        x,y=point(0,tick);s.text(x+5,y+12,str(tick),10,'#6f8290')
    for i,(label,_,_,_) in enumerate(METRICS):
        s.line(cx,cy,*point(i,100),'#c4d2d9',.8);x,y=point(i,126)
        s.text(x-len(label)*6.5,y+5,label,13)
    for r in study['results']:
        ps=[p for p in data if p['method']==r['method']]
        if all(p['score'] is not None for p in ps):s.poly([point(i,p['score']) for i,p in enumerate(ps)],'none',COLORS[r['method']],2.7)
    s.text(655,157,'現場原流程完成率（補作前）',17)
    for i,r in enumerate(study['results']):
        y=190+i*72;w=r['completed_work'];s.text(645,y+17,r['method'],14)
        s.rect(675,y,280*r['access_rate'],23,COLORS[r['method']],COLORS[r['method']])
        s.text(970,y+17,f"{r['access_rate']*100:.1f}%",14)
        s.text(675,y+42,f"原流程 {r['success']}/{r['tasks']}；補作 {w['fallback_count']}；最終 {w['success']}/{r['tasks']}",12)
    for i,m in enumerate(['A','B','C']):s.text(650,439+i*25,NAMES[m],13,COLORS[m])
    s.text(650,521,'C：離線候選模擬原型，未接實體感測／ROS。',12)
    xs=[65,152,298,483,650,815,985]
    for x,t in zip(xs,['流程','工期 h','成本 TWD','投入 人時','公差率 %','暴露 人時','適應率 %']):s.text(x,583,t,13)
    s.line(65,596,1125,596,'#c4d2d9')
    for i,r in enumerate(study['results']):
        values=[r['method']]+[f"{r['lifecycle'][k]:,.2f}" if r['lifecycle'][k] is not None else 'NA' for _,k,_,_ in METRICS]
        for x,v in zip(xs,values):s.text(x,621+i*29,v,13,COLORS[r['method']])
    s.text(70,711,'工期／成本含規劃、板材、CNC、工廠單元組裝、現場装配與補作。移動距離保留於作業紀錄。',12)
    s.text(70,733,'公差率：解析誤差模型；暴露：占比假設；適應率：五個指定通行情境。完整定義與尺度見 R106。',12)
    s.text(70,754,'本圖不代表全屋施工、真實品質驗收或安全認證；成本與工期相關，不以雷達面積排名。',11,'#a04a31')
    return s

def definitions_sheet(h,study):
    s=Sheet('R106','六軸定義與假設｜共同尺度、可追溯證據',h);p=study['lifecycle_params'];n=len(study['interior']['parts'])
    blocks=[
        ('工期效率','製程規劃＋CNC 準備／加工＋工廠單元組裝＋現場装配／補作，串行累加。',f"0 分上限：{p['hours_bound_piece']:g} h/件 × {n} = {p['hours_bound_piece']*n:g} h。"),
        ('成本效率','板材預算＋各階段班組、機台及規劃費率；不與全屋材料預算重複相加。',f"0 分上限：{p['cost_bound_piece']:g} TWD/件 × {n} = {p['cost_bound_piece']*n:,.0f} TWD。"),
        ('人力投入效率','每階段工時 × 在場人數；班組 TWD/h 已包含整班，費率不再乘人數。',f"0 分上限：{p['person_hours_bound_piece']:g} 人時/件 × {n} = {p['person_hours_bound_piece']*n:g} 人時。"),
        ('公差符合率','P = 1 - exp(-t² / (2σ²))；σ² 為加工、抓持、座標定位與最終定位的變異數總和。',
         f"公差半徑 t={p['tolerance_mm']:g} mm；σ 分量：{p['manufacture_sigma_mm']:g} / {p['grip_sigma_mm']:g} / {p['registration_sigma_mm']:g} / 人工 {p['manual_place_sigma_mm']:g}、機器人 {p['robot_place_sigma_mm']:g} mm。"),
        ('危險區暴露控制','主动作業人時 × 危險區占比；準備／評估／交接假設停機隔離，未追蹤人員位置。',
         f"占比：CNC {p['cnc_exposure_fraction']:.0%}、人工 {p['manual_exposure_fraction']:.0%}、機器人監督 {p['robot_exposure_fraction']:.0%}；0 分上限 {p['exposure_bound_piece']*n:g} 人時。"),
        ('條件變動適應能力','五種指定條件中，原流程完成全部二維通行／站位任務的比例；不含人工補作挽救。',
         'A/B 固定順序、均重新找站位；C 額外比較兩種候選順序。含基準在內共 5 案，詳 R108。')]
    for i,(title,definition,detail) in enumerate(blocks):
        y=145+i*86;s.text(70,y,title,16);s.text(70,y+26,definition,12);s.text(70,y+49,detail,12,'#527180')
    s.text(70,687,'低投入軸：分數 = max(0, 100 × (1 - 原值／上限))；百分比軸直接使用 0–100。',12)
    s.text(70,710,'上限為固定可改展示假設，非業界標準。未完成組不連線；原值、上限、截斷標記皆保留。',12)
    s.text(70,733,'誤差為獨立零均值二維常態假設；未含角度、偏差、變形、接頭接觸與品質返工。',12,'#a04a31')
    s.text(70,755,'實驗辨識碼 '+study['id']+' | 所有數值尚未實測校準；B/C 使用相同硬體誤差與費率。',11)
    return s

def fabrication_sheet(h,study):
    s=Sheet('R107','製造到裝配｜工序投入分解',h);f=study['fabrication'];p=study['lifecycle_params']
    s.text(65,141,f"雙面板面積 {f['panel_area_m2']:.2f} m² / {f['sheet_area_m2']:.4f} m²/張 / 利用率 {p['sheet_utilization']:.0%} × (1+{p['sheet_waste']:.0%}) → {f['sheets']} 張",14)
    s.text(65,166,'共同板材＋CNC；工廠搬料／單元組裝以週期估算，未產生排版、CNC 刀路或工廠機器人逐板軌跡。',12)
    for i,r in enumerate(study['results']):
        x=65+i*370;s.text(x,204,NAMES[r['method']],14,COLORS[r['method']]);s.text(x,230,'h / TWD / 人時 / 暴露人時',11)
        for j,q in enumerate(r['lifecycle']['phases']):
            y=262+j*45;s.text(x,y,q['phase'],12)
            s.text(x,y+19,f"{q['hours']:.2f} / {q['cost_twd']:,.0f} / {q['person_hours']:.2f} / {q['exposure_person_hours']:.2f}",12,'#527180')
    a=study['assumptions']
    s.text(65,695,f"補作共用：失敗評估 {a['failure_review_minutes']:g} min/件、交接 {a['fallback_handoff_minutes']:g} min、人工準備 {a['human_setup_minutes']:g} min。",12)
    s.text(65,720,'機器人設備計費至交接結束；補作沿用已安裝障礙。板材未含內肋、骨架與接頭詳設材料。',12)
    s.text(65,745,'品質公差不合格尚未觸發返工，因此排程全部完成不代表全部品質驗收合格。',12,'#a04a31')
    return s

def conditions_sheet(h,study):
    s=Sheet('R108','孿生候選選擇與五種條件測試',h);p=study['twin_plan']
    s.text(65,141,'基準 C 選擇：'+p['selected'],16)
    for i,c in enumerate(p['candidates']):s.text(65,169+i*24,f"候選 {i+1}：{c['strategy']} | 通過 {c['success']}/{c['tasks']} | 已嘗試 {c['attempted_hours']:.2f} h | {c['path_m']:.1f} m",12)
    s.text(65,225,'優先全部完成，再比較未完成件數、已嘗試工時。只比較兩種保存策略，無全域最佳保證。',12)
    for x,t in [(65,'條件'),(535,'流程'),(620,'完成件'),(775,'全完成'),(920,'C 選擇策略')]:s.text(x,264,t,13)
    for i,v in enumerate(study['conditions']):
        y=292+i*24
        label=v['scenario']+' '+v['label'] if v['method']=='A' else ''
        s.text(65,y,label,11);s.text(540,y,v['method'],12,COLORS[v['method']]);s.text(620,y,f"{v['success']}/{v['tasks']}",12)
        s.text(780,y,'是' if v['complete'] else '否',12)
        s.text(920,y,v['twin']['selected'] if v['twin'] else '固定近端順序',11)
    s.text(65,679,'S3/S4 臨時堆料矩形：x=3400–4150、y=3600–4350 mm；三組使用相同條件與檢查器。',12)
    s.text(65,703,'S1/S4：淨空 +50 mm；S2：人工／機器人有效作業半徑皆 -100 mm。三組均重新計算站位。',12)
    s.text(65,727,'此比率只代表這五種條件的通行／站位可行性，非現場成功機率，未檢查六軸碰撞或材料品質。',12,'#a04a31')
    s.text(65,751,'全部逐件路徑及候選結果存於 evidence.json；條件摘要存於 conditions.csv。',12)
    return s
