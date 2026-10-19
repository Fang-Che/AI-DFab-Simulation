"""R9 hypothesis report; no measured or ranked-as-proven performance claims."""
import math,textwrap
from .drawings import Sheet
from .wholehouse_study import METRICS,NAMES,COMMON,FIELDS,radar_data,boundaries
COLORS={'A':'#537f90','B':'#cb8755','C':'#427b64'}

def base(code,title,h,s):
    page=Sheet(code,title,h)
    for kind,a in page.ops:
        if kind=='text':a[2]=a[2].replace('研究草圖 R8','研究假設 R9')
    page.text(65,137,f"情境 {s['id']} | {len(h['items'])} 模組 | {s['area_m2']:.2f} m² | 研究假設，未經實測校準",13,'#a04a31')
    return page

def radar_sheet(h,s):
    p=base('R901','全屋流程比較｜六軸假設情境',h,s);data=radar_data(s)
    cx,cy,radius=322,351,140
    def point(i,v):
        angle=-math.pi/2+i*math.pi/3
        return cx+radius*v/100*math.cos(angle),cy+radius*v/100*math.sin(angle)
    for tick in [25,50,75,100]:
        p.poly([point(i,tick) for i in range(6)],'none','#c4d2d9',.8)
        x,y=point(0,tick);p.text(x+5,y+10,str(tick),10,'#6f8290')
    for i,(label,_,_,_) in enumerate(METRICS):
        p.line(cx,cy,*point(i,100),'#c4d2d9');x,y=point(i,127);p.text(x-len(label)*6,y+5,label,12)
    for m in NAMES:
        rr=[r for r in data if r['method']==m];p.poly([point(i,r['score']) for i,r in enumerate(rr)],'none',COLORS[m],2.6)
    p.text(620,186,'同一全屋設計、共同板材與 CNC 週期',17)
    for i,m in enumerate(NAMES):p.text(620,225+i*30,NAMES[m],14,COLORS[m])
    p.text(620,337,'成本／人力／暴露：原值越低，分數越高。',13)
    p.text(620,362,'外圍代表較佳；不以雷達面積判定總排名。',13)
    p.text(620,399,'含設計、校核、製造、組裝、一次期望返工；',13)
    p.text(620,424,'基礎與完工工程採面積暫列，不是施工報價。',13)
    p.text(620,461,'全屋完成為排程假設，未驗證全屋可達／碰撞。',12,'#a04a31')
    p.text(620,486,'R8 的隔間通行完成率保留於獨立診斷介面。',12)
    xs=[65,155,300,489,653,817,996]
    for x,label in zip(xs,['流程','工期 h','成本 TWD','人力 人時','公差率 %','暴露 人時','適應分數']):p.text(x,558,label,13)
    p.line(65,571,1130,571,'#c4d2d9')
    for i,r in enumerate(s['results']):
        vals=[r['method']]+[f"{r[k]:,.2f}" for _,k,_,_ in METRICS]
        for x,value in zip(xs,vals):p.text(x,600+i*33,value,13,COLORS[r['method']])
    p.text(65,709,'工期為排程終點，非各工序相加；公差率為一次符合率模型，適應能力為變更處理工期代理。',12)
    p.text(65,734,'圖形依工序與假設計算；期待排序與計算排序分開檢查，成立條件見 R904。',12)
    p.text(65,757,'所有費率、誤差及自動化成效均未校準；不代表實測效率、安全認證或工程品質驗收。',11,'#a04a31')
    return p

def schedule_sheet(h,s):
    p=base('R902','工期模型｜工序投入與並行排程',h,s)
    p.text(65,171,'工序時數／人時／成本 TWD（不同資源可重疊，工序時數總和不等於工期）',14)
    phases=list(dict.fromkeys(e['phase'] for r in s['results'] for e in r['events']))
    for x,m in [(443,'A'),(680,'B'),(914,'C')]:p.text(x,203,m,15,COLORS[m])
    for i,phase in enumerate(phases):
        y=234+i*24;p.text(65,y,phase,12)
        for x,r in zip([380,619,858],s['results']):
            ee=[e for e in r['events'] if e['phase']==phase]
            values=[sum(e[k] for e in ee) for k in ['hours','person_hours','cost_twd']]
            p.text(x,y,f'{values[0]:.1f} / {values[1]:.1f} / {values[2]:,.0f}',12,COLORS[r['method']])
    p.line(65,610,1130,610,'#c4d2d9')
    p.text(65,638,'實際排程終點',14)
    for x,r in zip([380,619,858],s['results']):p.text(x,638,f"{r['hours']:.2f} h / {r['batches']} 批",14,COLORS[r['method']])
    p.text(65,674,'一台 CNC、獨立工廠資源與現場班組、一運輸資源；批次製造完成後交付，現場依序接續。',12)
    p.text(65,699,'B/C 的工廠與現場為不同機器人資源；每個資源不重疊。批次按現有全屋清單順序，非最優排程。',12)
    p.text(65,724,'基礎可與製造重疊；完工工程於構件裝配與一次返工後開始。運輸／吊運只是時間及成本暫列。',12)
    p.text(65,749,'未含採購等待、混凝土養護、休假及班次日曆；CSV 逐工序列出起訖、相依項、資源與構件 ID。',12)
    return p

def parameters_sheet(h,s):
    p=base('R903','可重現參數｜全部為示範假設初值或使用者設定',h,s)
    p.text(65,173,'共同材料、費率與尺度',17);p.text(630,173,'流程參數',16)
    for x,m in zip([923,1000,1077],NAMES):p.text(x,173,m,16,COLORS[m])
    for i,(k,label,_) in enumerate(COMMON):
        y=200+i*19;p.text(65,y,label,10.5);p.text(515,y,f"{s['params']['common'][k]:g}",11)
    for i,(k,label) in enumerate(FIELDS):
        y=208+i*24;p.text(630,y,label,10.5)
        for x,m in zip([923,1000,1077],NAMES):p.text(x,y,f"{s['params']['methods'][m][k]:g}",11,COLORS[m])
    p.text(630,706,'B/C 共用 CNC、機器人運轉費率及物理週期初值。',11)
    p.text(630,728,'C 差異為校核／校正、殘餘誤差、人數與交付批量。',11)
    p.text(630,750,'所有數值可改；不是論文實測或供應商報價。',11,'#a04a31')
    return p

def conditions_sheet(h,s):
    p=base('R904','假設檢查｜排序成立條件與適應能力',h,s);b=boundaries(s)
    p.text(65,180,'指標',14);p.text(350,180,'期待（佳 → 差）',14);p.text(605,180,'計算（佳 → 差）',14);p.text(900,180,'是否一致',14)
    labels={key:label for label,key,_,_ in METRICS}
    for i,r in enumerate(s['hypothesis_check']):
        y=216+i*30
        for x,v in zip([65,350,605,900],[labels[r['metric']],' > '.join(r['expected_best_to_worst']),' > '.join(r['calculated_best_to_worst']),'是' if r['matches'] else '否']):p.text(x,y,v,13)
    p.line(65,353,1130,353,'#c4d2d9');p.text(65,385,'單參數分界（其他參數固定；不自動改值追求排序）',16)
    p.text(65,412,f"成本原值 B > A > C：B/C 共用固定設備暫列金 {b['robot_fixed_cost_lower']:,.0f} < 費用 < {b['robot_fixed_cost_upper']:,.0f} TWD。",12)
    p.text(65,437,f"目前 {s['params']['common']['robot_mobilization']:,.0f} TWD；區間倒置表示此單參數無解。分界是反算條件，不是校準證據。",12)
    threshold=b['b_exposure_fraction_lower']
    p.text(65,462,('B 暴露高於 A：B 主動作業危險區占比 > '+f'{threshold:.1%}' if threshold is not None else 'B 暴露占比無可識別分界')+'；高於 100% 則此單參數無解。',12)
    p.text(65,487,f"C 變更處理快於 A：C 辨識／規劃回應 < {b['c_response_h_upper']:.2f} h；目前 {s['params']['methods']['C']['change_response_h']:.2f} h。",12)
    p.text(65,529,'變更工作包｜平均處理工期代理，非三維路徑測試',16)
    for x,t in [(65,'共同變更'),(620,'A / h'),(790,'B / h'),(960,'C / h')]:p.text(x,559,t,13)
    for i,event in enumerate(s['results'][0]['changes']):
        y=588+i*25;p.text(65,y,f"{event['scenario']}（{event['affected_modules']} 模組）",12)
        for x,r in zip([620,790,960],s['results']):p.text(x,y,f"{r['changes'][i]['recovery_hours']:.2f}",12,COLORS[r['method']])
    p.text(65,725,'適應分數 = max(0, 100 × (1 - 平均處理工期 / 上限))；A/C 回應時間分別掃描 1、4、8、16 h。',12)
    p.text(65,749,'回應時間與返工比例尚未量測；條件變動的適應優劣隨設定改變，不預設普遍排序。',12,'#a04a31')
    return p

def definitions_sheet(h,s):
    p=base('R905','定義、範圍與研究使用界線',h,s)
    lines=[
        '低投入四軸：max(0, 100 × (1 - 原值 / 尺度上限))。上限 = 樓板面積 × 每 m² 尺度；非業界評等標準。',
        '公差率：100 × (1 - exp(-t² / (2 × Σσ²)))；t 為位置公差半徑，各 σ 為獨立零均值平面誤差分量。',
        '預期一次返工量 = 模組數 × (1 - 公差符合率)；追加一次校正工時，不保證最終全部合格。',
        '暴露人時 = 各工序時數 × 在場人數 × 危險區占比；暴露不是事故機率，也不代表事故嚴重度。',
    ]+s['assumptions']
    y=177
    for line in lines:
        wrapped=textwrap.wrap(line,width=70,break_long_words=True,break_on_hyphens=False)
        for j,text in enumerate(wrapped):p.text(65 if j==0 else 79,y,('• ' if j==0 else '')+text,11.5);y+=21
        y+=5
    return p

def sheets(h,s):return [radar_sheet(h,s),schedule_sheet(h,s),parameters_sheet(h,s),conditions_sheet(h,s),definitions_sheet(h,s)]
