"""Vector plans, comparable axes and evidence sheets for the controlled study."""
from .drawings import Sheet
from .study import rows,sensitivity,RADAR_METRICS
from .lifecycle import radar_data
import math
from .prices import FX,converted,benchmark

COLORS={'A':'#537f90','B':'#cb8755','C':'#427b64'}

def radar_figure(study):
    import plotly.graph_objects as go
    fig=go.Figure();data=radar_data(study)
    for r in study['results']:
        points=[p for p in data if p['method']==r['method']]
        if any(p['score'] is None for p in points):continue
        points=points+[points[0]]
        fig.add_trace(go.Scatterpolar(r=[p['score'] for p in points],theta=[p['metric'] for p in points],
            mode='lines+markers',name=({'A':'A 製造＋人工','B':'B 製造＋機器人','C':'C 孿生＋自動化'}[r['method']] if 'lifecycle_params' in study else r['method'])+(' 含人工補作' if r['completed_work']['fallback'] else ' 原流程'),
            line=dict(color=COLORS[r['method']],width=2),
            customdata=[[p['raw'],p['unit'],str(p['zero_score_bound']) if p['zero_score_bound'] is not None else '百分比直接評分'] for p in points],
            hovertemplate='%{theta}<br>情境分數 %{r:.1f}<br>原值 %{customdata[0]:.2f} %{customdata[1]}<br>尺度 %{customdata[2]}<extra>%{fullData.name}</extra>'))
    fig.update_layout(title=dict(text='製造＋組裝｜六軸情境模型' if 'lifecycle_params' in study else '完整工作投入效率',font=dict(size=13)),height=420,margin=dict(l=80,r=80,t=45,b=55),paper_bgcolor='white',
        polar=dict(radialaxis=dict(range=[0,100],tickvals=[0,25,50,75,100]),angularaxis=dict(rotation=90,direction='clockwise')),
        legend=dict(orientation='h',y=-.15,x=.5,xanchor='center'))
    return fig

def completion_figure(study):
    import plotly.graph_objects as go
    rs=study['results'];fig=go.Figure(go.Bar(x=[r['access_rate']*100 for r in rs],y=[r['method'] for r in rs],orientation='h',
        marker_color=[COLORS[r['method']] for r in rs],text=[f"{r['access_rate']*100:.1f}% ({r['success']}/{r['tasks']})" for r in rs],textposition='auto'))
    fig.update_layout(height=220,margin=dict(l=25,r=25,t=10,b=40),xaxis=dict(range=[0,100],title='補作前完成率 (%)'),yaxis=dict(autorange='reversed'),paper_bgcolor='white')
    return fig

def radar_sheet(h,study):
    if 'lifecycle_params' in study:
        from .lifecycle_drawings import radar_sheet as six_sheet
        return six_sheet(h,study)
    s=Sheet('R102','全部工作投入比較＋原流程完成率',h);data=radar_data(study)
    s.text(80,145,'完成相同構件後的情境效率（外圍較高）',17)
    c=study['interior']['config']
    s.text(80,169,f"{c['floor']}F 隔間 | {c['bedrooms']} 房 | 門寬 {c['door_width']} mm | {len(study['interior']['parts'])} 件",11,'#527180')
    cx,cy,rad=340,355,155
    def vertex(i,v):
        angle=-math.pi/2+i*math.pi/2
        return (cx+rad*v/100*math.cos(angle),cy+rad*v/100*math.sin(angle))
    for tick in [25,50,75,100]:
        s.poly([vertex(i,tick) for i in range(4)],'none','#c4d2d9',.8)
        x,y=vertex(0,tick);s.text(x+5,y+13,str(tick),10,'#6f8290')
    for i,(label,_,_,_) in enumerate(RADAR_METRICS):
        s.line(cx,cy,*vertex(i,100),'#c4d2d9',.8)
        x,y=vertex(i,127);s.text(x-35,y+5,label,13)
    for r in study['results']:
        ps=[p for p in data if p['method']==r['method']]
        if all(p['score'] is not None for p in ps):s.poly([vertex(i,p['score']) for i,p in enumerate(ps)],'none',COLORS[r['method']],2.7)
    s.text(650,145,'原流程完成率（人工補作前）',17)
    for i,r in enumerate(study['results']):
        y=190+i*74;w=r['completed_work']
        s.text(640,y+16,r['method'],15);s.rect(670,y,290*r['access_rate'],24,COLORS[r['method']],COLORS[r['method']])
        s.text(977,y+17,f"{r['access_rate']*100:.1f}%",14)
        s.text(670,y+43,f"原流程 {r['success']}/{r['tasks']}；補作 {w['fallback_count']} 件；最終 {w['success']}/{r['tasks']}",12)
    s.text(650,446,'A 人工裝配 | B 固定順序機器人',13)
    s.text(650,470,'C AI 提案重播／機器人',13)
    s.text(650,501,'三組均適用：未完成件交由人工補作。',13)
    s.text(650,525,'補作仍未完成者不畫雷達，不記為 0 分。',12)
    headers=['流程','完整工期 h','完整成本 TWD','完整移動 m','人力投入 人時']
    xs=[80,250,470,720,930]
    for x,t in zip(xs,headers):s.text(x,589,t,14)
    s.line(75,601,1120,601,'#c4d2d9')
    for i,r in enumerate(study['results']):
        w=r['completed_work'];vals=[r['method']+('＋人工補作' if w['fallback'] else '')]+[f"{w[k]:,.2f}" if w[k] is not None else '未完成' for k in ['hours','cost_twd','path_m','person_hours']]
        for x,t in zip(xs,vals):s.text(x,627+i*31,t,14,COLORS[r['method']])
    s.text(80,727,'分數 = max(0, 100 × (1 − 原值／共同上限))；上限依構件數設定，詳 R106。',12)
    s.text(80,749,'範圍：隔間二維情境；費率／人數／速度為假設。成本與工期相關，不以雷達面積排名。',12,'#a04a31')
    return s

def completion_sheet(h,study):
    if 'lifecycle_params' in study:
        from .lifecycle_drawings import definitions_sheet
        return definitions_sheet(h,study)
    s=Sheet('R106','人工補作規則、投入分解與雷達尺度',h);a=study['assumptions']
    notes=[f"相同補作規則：原流程完成並退出後，人工補作未完成件；保留已安裝障礙，重新檢查路徑與撤離。",
        f"每件失敗評估 {a['failure_review_minutes']:g} min；有補作才收交接 {a['fallback_handoff_minutes']:g} min、人工準備 {a['human_setup_minutes']:g} min。",
        f"人工班組 {a['human_crew_people']:g} 人，{a['human_crew_twd_h']:g} TWD/h（整班）；機器人監督 {a['robot_supervision_people']:g} 人，{a['robot_supervision_twd_h']:g} TWD/h。",
        f"設備 {a['robot_equipment_twd_h']:g} TWD/h，計至交接結束。機器人交接時計入監督、人工班組與設備；各階段串行。",
        '僅公共區起點內的移動；不含外部進場、跨樓層運輸、供料、拆除返工、共同材料／CNC 或全屋工程。']
    for i,t in enumerate(notes):s.text(70,145+i*25,t,12)
    s.text(70,294,'流程／階段',14)
    for x,t in [(470,'工時 h'),(630,'成本 TWD'),(810,'移動 m'),(980,'人時')]:s.text(x,294,t,14)
    y=319
    for r in study['results']:
        for p in r['completed_work']['phases']:
            s.text(70,y,r['method']+' '+p['phase'],13,COLORS[r['method']])
            for x,k in [(470,'hours'),(630,'cost_twd'),(810,'path_m'),(980,'person_hours')]:s.text(x,y,f"{p[k]:,.2f}",13)
            y+=20
    s.text(70,508,'固定展示上限（非業界標準；可在介面修改，不依 A/B/C 結果自動縮放）',15)
    for i,(label,key,capkey,unit) in enumerate(RADAR_METRICS):
        n=len(study['interior']['parts']);s.text(70,537+i*27,f"{label}：每件 {a[capkey]:g} {unit} × {n} 件 = {a[capkey]*n:g} {unit}（0 分）；零投入 = 100 分。",13)
    s.text(70,655,'超過上限截為 0 分，原值與截斷標記保留於 radar.csv。未完成為 NA，不連線成多邊形。',12)
    s.text(70,680,'人時 = 每阶段工時 × 在場人數；費率為整班費率，不再乘人數。A 組補作視為原班組重新安排。',12)
    s.text(70,705,'實際施工精度、六軸碰撞、安全性與多情境適應能力未驗證，不列入本雷達評分。',12,'#a04a31')
    s.text(70,736,'研究編號 '+study['id']+' | R7 全工作比較；原流程逐件紀錄另存，不覆寫。',12)
    return s

def plan_on(s,interior,ox,oy,scale,result=None,title=''):
    def p(x,y):return ox+x*scale,oy+y*scale
    s.text(ox,oy-40,title,16)
    s.rect(*p(318,318),4800*scale,12564*scale,'#f4f8f8','#35576b')
    for room in interior['rooms']:
        x,y,xx,yy=room['box'];s.rect(*p(x,y),(xx-x)*scale,(yy-y)*scale,'#e5efea' if room['meets_area'] else '#f8ded3','#c2d5d0',.5)
        s.text(*p(x+80,(y+yy)/2),room['name'],10);s.text(*p(x+80,(y+yy)/2+350),f"{room['area_m2']:.1f} m²",10)
    failed={e['part'] for e in result['events'] if not e['success']} if result else set()
    for part in interior['parts']:
        if part['header']:continue
        lo,hi=part['lo'],part['hi'];col='#bb4338' if part['id'] in failed else '#35576b'
        s.rect(*p(lo[0],lo[1]),(hi[0]-lo[0])*scale,(hi[1]-lo[1])*scale,col,col,.7)
    for d in interior['doors']:
        s.line(*p(*d['a']),*p(*d['b']),'#d59b42',2)
    if interior.get('obstacle_mm'):
        x,y,xx,yy=interior['obstacle_mm'];s.rect(*p(x,y),(xx-x)*scale,(yy-y)*scale,'#d9dce1','#86929d');s.text(*p(x+50,y+500),'樓梯／洞口保留區',9)
    if result:
        for e in result['events']:
            for a,b in zip(e['route'],e['route'][1:]):s.line(*p(*a),*p(*b),COLORS[result['method']],1.4)
            if e['success']:
                x,y=p(*e['station']);s.rect(x-2,y-2,4,4,COLORS[result['method']],COLORS[result['method']])
        for a,b in zip(result['exit_route'],result['exit_route'][1:]):s.line(*p(*a),*p(*b),'#82939a',1,True)
    s.dimension(*p(318,-100),*p(5118,-100),'4800')
    s.text(ox,oy+13200*scale+12,'主屋內緣 4800 × 12564 mm',11)

def sheets(h,study,after=None):
    out=[];s=Sheet('R101','三流程受控情境｜同一設計、構件與檢查器',h)
    for i,r in enumerate(study['results']):
        x=70+i*370;plan_on(s,study['interior'],x,190,.034,r,{'A':'A 人工裝配','B':'B 機器人／固定順序','C':'C AI 提案／機器人'}[r['method']])
        s.text(x,690,f"通過 {r['success']}/{r['tasks']} | 路徑 {r['path_m']:.1f} m",13)
        s.text(x,714,'原流程工期 '+(f"{r['completion_hours']:.2f} h" if r['complete'] else '未完成；另見 R102 補作結果'),12)
    s.text(65,745,'實線：底座／班組移動；虛線：退出；紅色：未通過任務；橙色：門洞。僅二維通行及站位預檢。',12)
    out.append(s)
    out.append(radar_sheet(h,study))
    if after:
        s=Sheet('R103','回饋修改前後｜B 組相同檢查器重新計算',h)
        for x,case,title in [(100,study,'修改前'),(680,after,'修改後')]:
            r=case['results'][1];plan_on(s,case['interior'],x,185,.033,r,title)
            c=case['interior']['config'];s.text(x,663,f"門寬 {c['door_width']} mm / 公共區分界 {c['common_end']} mm",13)
            s.text(x,689,f"通過 {r['success']}/{r['tasks']} | 隔間面積 {case['interior']['wall_area_m2']:.2f} m²",13)
            s.text(x,715,f"原流程工期：{r['completion_hours']:.2f} h" if r['complete'] else '原流程未完成；補作總計見比較資料',13)
        s.text(70,745,'此頁允許設計改變，因此與 R101 的固定設計流程比較分開解讀。保留房間數與使用者鎖定條件。',12)
        out.append(s)
    s=Sheet('R104','現場組裝子模型｜工時敏感度',h)
    s.text(70,150,'僅現場組裝及補作；單件工時 ×0.75／×1.00／×1.25（不含製造）',18)
    for i,r in enumerate(sensitivity(study)):
        y=190+i*31;s.text(70,y,f"{r['method']}  ×{r['piece_time_factor']:.2f}",14)
        s.text(280,y,f"全部工作 {r['hours']:.2f} h",14);s.text(530,y,f"TWD {r['cost_twd']:,.0f}",14)
        s.text(800,y,'含補作完成' if r['complete'] else '未完成；不是完整成本',13)
    for i,t in enumerate(['AI 提案：本次 Codex 助理，2026-10-13；本地保存並重播，未呼叫線上 API。',
        '採用策略：'+study.get('twin_plan',{}).get('selected','遠端優先，公共區分界延後封閉，門楣於牆段後安裝。'),
        '共同檢查器驗證到達、投影半徑與撤離。AI 沒有修改檢查閾值或直接給定績效數字。',
        '此為一個配置的策略個案比較，非統計實驗；未證明 AI 一般優於人工或傳統演算法。',
        'JSON 證據含每件順序、路徑、站位、成功／失敗、工時與全部參數，可重算。']):s.text(70,550+i*32,t,13)
    out.append(s)
    s=Sheet('R105','公開英國價格與台幣換算依據',h)
    s.text(70,148,f"1 GBP = {FX['gbp_twd']} TWD | {FX['kind']} | {FX['quote_time']}",15)
    y=191
    for r in converted():
        s.text(70,y,r['title'],15);s.text(70,y+25,f"GBP {r['gbp_low']:,.0f}–{r['gbp_high']:,.0f} / {r['unit']}  →  TWD {r['twd_low']:,.0f}–{r['twd_high']:,.0f}",13)
        # Compact scope notes; complete URLs and scopes in the accompanying JSON.
        s.text(70,y+48,r['scope'][:72],11,'#527180');y+=85
    b=benchmark(h);s.text(70,646,f"本方案室內面積概算 {b['area_m2']:.2f} m²：英國構架換匯約 TWD {b['twd_low']:,.0f}–{b['twd_high']:,.0f}",15)
    s.text(70,673,'來源：www.reframestudio.co.uk/wikihouse | www.wikihouse.cc/services | Architecture Unknown 案例貼文',11)
    s.text(70,697,'匯率：rate.bot.com.tw/xrt?Lang=zh-TW；全部來源 2026-10-13 查閱，完整連結見 evidence.json。',11)
    s.text(70,721,'UK 價格未經台灣在地化；不含匯費、進口稅運費調整；不與原材料預算相加。VAT 範圍依各來源。',11,'#a04a31')
    out.append(s)
    out.append(completion_sheet(h,study))
    if 'lifecycle_params' in study:
        from .lifecycle_drawings import fabrication_sheet,conditions_sheet
        out.extend([fabrication_sheet(h,study),conditions_sheet(h,study)])
    return out

def plan_figure(interior,result=None):
    import plotly.graph_objects as go
    fig=go.Figure()
    for room in interior['rooms']:
        x,y,xx,yy=room['box'];fig.add_shape(type='rect',x0=x,y0=y,x1=xx,y1=yy,fillcolor='#e3eee8' if room['meets_area'] else '#f5d6c9',line=dict(color='#b4c9c2',width=1),layer='below')
        fig.add_trace(go.Scatter(x=[(x+xx)/2],y=[(y+yy)/2],mode='text',text=[room['name']+f"<br>{room['area_m2']:.1f} m²"],textfont=dict(size=12),hovertemplate=room['id']+'<extra></extra>',showlegend=False))
    failed={e['part'] for e in result['events'] if not e['success']} if result else set()
    for part in interior['parts']:
        if part['header']:continue
        fig.add_trace(go.Scatter(x=[part['a'][0],part['b'][0]],y=[part['a'][1],part['b'][1]],mode='lines',line=dict(width=6,color='#ba483b' if part['id'] in failed else '#35576b'),hovertemplate=part['id']+' '+part['label']+'<extra></extra>',showlegend=False))
    for d in interior['doors']:
        fig.add_trace(go.Scatter(x=[d['a'][0],d['b'][0]],y=[d['a'][1],d['b'][1]],mode='lines',line=dict(width=3,color='#ce963c',dash='dot'),hovertemplate=d['label']+f" {d['width']:.0f} mm<extra></extra>",showlegend=False))
    if interior.get('obstacle_mm'):
        x,y,xx,yy=interior['obstacle_mm'];fig.add_shape(type='rect',x0=x,y0=y,x1=xx,y1=yy,fillcolor='#d9dce1',line=dict(color='#86929d'))
        fig.add_annotation(x=(x+xx)/2,y=(y+yy)/2,text='樓梯／洞口<br>保留區',showarrow=False)
    if result:
        xs=[];ys=[]
        for e in result['events']:
            xs.extend([p[0] for p in e['route']]+[None]);ys.extend([p[1] for p in e['route']]+[None])
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color=COLORS[result['method']],width=2),name='移動路徑'))
    fig.update_layout(height=540,margin=dict(l=15,r=15,t=15,b=15),paper_bgcolor='white',plot_bgcolor='white',showlegend=False,
                      xaxis=dict(range=[0,5436],title='mm',constrain='domain'),yaxis=dict(range=[13200,0],scaleanchor='x',scaleratio=1,title='mm'),uirevision='infill-plan')
    return fig
