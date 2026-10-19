"""Load only the active feature; keep scenario data cached and immutable."""
import io,json,os,time,zipfile
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from .core import ROOT,GEOMETRY,read_json,digest
from .assembly import rectangle_demo,factory_scene,viewer_html,export_house
from .estimating import quantity_takeoff,cost_estimate,DEFAULT_RATES
from .knowledge import SOURCES,RULES,TOOLS,JOINTS

@st.cache_resource(show_spinner=False)
def geometry_data(revision):
    from .construction import library
    return library(read_json(GEOMETRY))
@st.cache_resource(show_spinner=False)
def house_data(layout,levels,minutes,setup,efficiency,hours,revision,interior_json=''):
    h=rectangle_demo(geometry_data(revision),layout,levels=levels,minutes=minutes,setup_hours=setup,efficiency=efficiency,hours_day=hours)
    if interior_json:
        from .interior import apply
        h=apply(h,json.loads(interior_json))
    return h
@st.cache_resource(show_spinner=False)
def house_html(layout,levels,minutes,setup,efficiency,hours,revision,interior_json=''):
    return viewer_html(house_data(layout,levels,minutes,setup,efficiency,hours,revision,interior_json))
@st.cache_resource(show_spinner=False)
def robot_view(revision,unit='SKYLARK250_WALL-M'):
    data=factory_scene(geometry_data(revision),unit);return data,viewer_html(data)
@st.cache_resource(show_spinner=False)
def takeoff_data(layout,levels,minutes,setup,efficiency,hours,revision,interior_json=''):
    return quantity_takeoff(house_data(layout,levels,minutes,setup,efficiency,hours,revision,interior_json))
def csv_bytes(rows):return pd.DataFrame(rows).to_csv(index=False).encode('utf-8-sig')

def inputs():
    if 'scheme' not in st.session_state:st.session_state.scheme=dict(layout='rectangle',levels=1,minutes=12.,setup=4.,efficiency=.75,hours=8.)
    c=st.session_state.scheme
    with st.sidebar:
        st.markdown('### 方案設定')
        with st.form('scheme_form'):
            layout=st.selectbox('布局',['rectangle','L','U'],index=['rectangle','L','U'].index(c['layout']),format_func=lambda x:{'rectangle':'矩形','L':'L 型','U':'凹型 / U 型'}[x])
            levels=st.radio('樓層',[1,2],index=c['levels']-1,format_func=lambda n:f'{n} 層',horizontal=True)
            with st.expander('裝配時間假設'):
                minutes=st.number_input('每件定位固定（分鐘）',1.,120.,c['minutes'])
                setup=st.number_input('準備（小時）',0.,72.,c['setup'])
                efficiency=st.slider('班組效率',.1,1.,c['efficiency'],.05)
                hours=st.number_input('每日工時',1.,24.,c['hours'])
            if st.form_submit_button('套用方案',type='primary',width='stretch'):
                st.session_state.scheme=dict(layout=layout,levels=levels,minutes=minutes,setup=setup,efficiency=efficiency,hours=hours)
        st.caption('主屋模數 5.436 × 13.2 m。二樓與非標準接點屬設計研究。')
        st.divider();st.caption('目前功能才載入三維畫面');st.caption('幣別 TWD · 單價可修改');st.caption('ROS／實機：未連線')
    return st.session_state.scheme

def render_robotics():
    started=time.perf_counter()
    st.markdown('''<style>
    .stApp{background:#f5f8fa;color:#203a49}.block-container{padding-top:2.2rem;max-width:1800px;padding-left:1.5rem;padding-right:1.5rem}
    h1,h2,h3{letter-spacing:-.025em;color:#203a49!important}h1{font-size:2rem!important}
    [data-testid="stSidebar"]{background:#eaf1f4}[data-testid="stMetric"]{background:white;padding:14px 18px;border:1px solid #e0e9ee;border-radius:12px}
    [data-testid="stMetricValue"]{font-size:1.65rem;color:#176e7c}[data-testid="stMetricLabel"]{color:#6a808d}
    [role="radiogroup"]{gap:8px;flex-wrap:wrap}button[kind="primary"]{background:#176e7c;border-color:#176e7c}
    .eyebrow{font-size:11px;letter-spacing:.18em;color:#448893;font-weight:700}.subtitle{color:#6c818d;margin-top:-10px}
    </style>''',unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">AI-DFAB / DESIGN TO ASSEMBLY</div>',unsafe_allow_html=True)
    st.title('AI-DFab自動化模擬與建造代理');st.markdown('<div class="subtitle">方案配置 · 板件製造 · 組裝模擬 · 圖說與成本</div>',unsafe_allow_html=True)
    from .design_ui import current
    config=dict(inputs());config['interior_json']=json.dumps(current(config['levels']),sort_keys=True)
    files=['housing_plan.py','panel_layout.py','method_drawings.py','lift_viewer.py','lift_viewer.html','construction.py','technical_drawings.py','assembly.py','assembly_viewer.html','abb_viewer.js','house.py','estimating.py','interior.py','study.py','study_drawings.py','lifecycle.py','lifecycle_drawings.py','wholehouse_study.py','wholehouse_ui.py','wholehouse_drawings.py','drawings.py','design_ui.py','prices.py','visuals.py','assets/geometry.json','assets/demo_geometry.json','assets/gable_geometry.json']
    revision=max((ROOT/'robotics'/name).stat().st_mtime_ns for name in files)
    house=house_data(**config,revision=revision)
    a,b,c,d=st.columns(4)
    a.metric('目前方案',f"{house['layout_name']} · {house['levels']} 層");b.metric('裝配構件',f"{len(house['items'])} 件")
    c.metric('樓板面積',f"{house['floor_area_m2']:.1f} m²");d.metric('模型外框高度',f"{house['dimensions_m']['height']:.3f} m")
    if st.session_state.get('workspace_page') in ['平面與圖說','材料與成本']:
        st.session_state.assembly_data_view='平面與圖說' if st.session_state.workspace_page=='平面與圖說' else '成本與單價'
        st.session_state.workspace_page='整屋裝配'
    if st.session_state.get('workspace_page')=='ABB 單元組裝':st.session_state.workspace_page='單元組裝'
    page=st.radio('工作區',['整屋裝配','單元組裝','板件製造','工具與接頭','現場吊裝','依據與回饋'],horizontal=True,label_visibility='collapsed',key='workspace_page')
    key=f"{config['layout']}_{config['levels']}F_{house['design_id']}"
    if page=='整屋裝配':
        st.caption('左側整屋裝配；右側可調整室內配置、檢視圖說與價格、比較施工流程並接受回饋修改。每層樓板完成後先展示室內隔間，再封外牆；可按「室內完成／封牆前」檢視。此為展示順序，臨時穩定與支撐需另行確認。')
        model_col,data_col=st.columns([1.5,1],gap='medium')
        with model_col:
            components.html(house_html(**config,revision=revision),height=950,scrolling=False)
            with st.expander('下載模型與裝配順序'):
                st.download_button('下載裝配順序',json.dumps({k:v for k,v in house.items() if k!='meshes'},ensure_ascii=False,indent=2),file_name=key+'_sequence.json')
                if st.button('產生 Rhino 模型'):
                    path=ROOT/f'robotics/runs/{key}_complete.3dm';export_house(house,path);st.session_state['rhino_'+key]=path.read_bytes()
                if 'rhino_'+key in st.session_state:st.download_button('下載 Rhino 3dm',st.session_state['rhino_'+key],file_name=key+'.3dm')
            if house['levels']==2:st.caption('2F 標高 +2780 mm。洞口、補強、樓梯與護欄為研究示意，承載與接頭待設計。')
        with data_col:
            with st.container(height=950,border=True):render_assembly_data(config,revision)
    elif page=='單元組裝':
        st.caption('六軸機械手臂 · 底板 → 遠側板 → 內部肋板 → 近側封板 → 頂板')
        g=geometry_data(revision)
        units=[k for k,v in g['blocks'].items() if len(v['parts'])>1]
        unit=st.selectbox('組裝單元',units,index=units.index('SKYLARK250_WALL-M'),format_func=unit_label,key='robot_unit')
        st.caption('保持來源模型原尺寸；較大單元可能超出固定站位可及範圍，介面會顯示逆解／碰撞結果。')
        data,markup=robot_view(revision,unit);components.html(markup,height=875,scrolling=False)
        with st.expander('模型與檢查範圍'):
            for t in data['limitations']:st.write(t)
            st.caption('目前只驗證姿態取樣的逆解與當前幀外框重疊，尚未連接實體控制器或 ROS。')
    elif page=='板件製造':render_panels(geometry_data(revision),revision)
    elif page=='工具與接頭':
        from .technical_drawings import detail_sheets
        units=[u for u,b in geometry_data(revision)['blocks'].items() if len(b['parts'])>1]
        unit=st.selectbox('工法對照單元',units,index=units.index('SKYLARK250_WALL-M'),format_func=unit_label)
        drawing_view(cached_methods(revision,unit)+detail_sheets(house),'tools_'+key+'_'+unit)
        st.subheader('依工序準備工具')
        st.dataframe(pd.DataFrame(TOOLS).rename(columns={'stage':'工序','tools':'工具／設備','connection':'接合／作業形式','joint':'接頭／幾何形式','source':'依據','status':'核對項目'}),hide_index=True,width='stretch')
        st.subheader('接頭索引')
        for j in JOINTS:
            with st.expander(j['id']+' · '+j['name']):
                st.write(j['method']+'｜'+j['geometry']);st.write('工具：'+j['tools']);st.caption(j['source']+'｜'+j['verification'])
        st.download_button('下載工具與接頭清單 CSV',csv_bytes(TOOLS),file_name='assembly_tools.csv')
    elif page=='現場吊裝':render_site(geometry_data(revision),house)
    else:
        st.subheader('手冊依據與開發規則');st.caption('已讀取 3 份文件，共 81 頁。版本為 2018–2019 年；頁碼為 PDF 頁碼。')
        for r in RULES:
            with st.expander(r['id']+' · '+r['topic']+' · '+r['source']):
                st.write('文件內容：'+r['evidence']);st.write('平台應用：'+r['application'])
        st.dataframe(SOURCES,hide_index=True,width='stretch');st.subheader('目前方案的設計回饋')
        feedback=['槽口與板厚須做首件試組，未自動套用 0.25 mm offset。','接頭與緊固件尚無完整數量，成本暫列金不能當成採購表。']
        if house['levels']==2:feedback+=['二樓洞口周邊補強、樓板承載、臨時穩定及樓梯細部需深化。']
        if config['layout']!='rectangle':feedback+=['L／U 屋谷及非標準屋頂模組仍需建立可製造接頭。']
        for f in feedback:st.write('• '+f)
        st.download_button('下載依據與方案回饋',json.dumps({'sources':SOURCES,'rules':RULES,'scheme':config,'feedback':feedback},ensure_ascii=False,indent=2),file_name='design_evidence.json')
        st.caption('GPT 代理：可於「現場吊裝」分析幾何檢查摘要；未設定 API 金鑰時不呼叫。')
    st.caption(f'目前工作區：{page} · 伺服器準備 {time.perf_counter()-started:.2f} 秒（不含瀏覽器繪製）')

@st.fragment
def render_assembly_data(config,revision):
    house=house_data(**config,revision=revision);takeoff=takeoff_data(**config,revision=revision)
    key=f"{config['layout']}_{config['levels']}F_{house['design_id']}"
    cost=cost_estimate(house,takeoff,st.session_state.get('cost_rates',dict(DEFAULT_RATES)),st.session_state.get('area_override_'+key))
    st.markdown(f"#### {house['layout_name']} · {house['levels']} 層｜方案資料")
    st.caption(f"{key} · {len(house['items'])} 件 · {house['floor_area_m2']:.2f} m²")
    st.markdown(f"**TWD {cost['total']:,.0f}｜示範預算**")
    st.caption(f"板材預算 {cost['sheets_budget']:,} 張 · 裝配情境 {house['time_estimate']['hours']:.1f} 小時")
    st.caption('此處為構架裝配簡算；流程比較另含設計、製造與全屋暫列工序，兩者不可相加。單價尚未詢價。')
    view=st.radio('檢視本方案資料',['室內配置','平面與圖說','材料清單','成本與單價','流程比較','回饋修改'],horizontal=True,key='assembly_data_view',label_visibility='collapsed')
    from .design_ui import editor,study_panel,feedback_panel
    if view=='室內配置':editor(house);return
    if view=='流程比較':study_panel(house);return
    if view=='回饋修改':feedback_panel(house);return
    if view=='平面與圖說':render_drawings(house,takeoff,cost,key)
    elif view=='材料清單':render_materials(takeoff,key)
    else:render_cost(house,takeoff,cost,key,compact=True)

def unit_label(key):
    names={'WALL':'牆體','CORNER':'轉角','DOOR':'門洞','WINDOW':'窗洞','FLOOR':'樓板','ROOF':'屋頂','GABLE':'山牆','FILLER':'補板'}
    name=next((v for k,v in names.items() if k in key),'構件')
    return name+' · '+key.replace('SKYLARK250_','').replace('SKYLARK200_','').replace('WIKIHOUSE_','')

@st.cache_resource(show_spinner=False)
def cached_panel(revision,unit,index):
    from .visuals import panel_figure
    return panel_figure(geometry_data(revision)['blocks'][unit]['parts'][index])

@st.cache_resource(show_spinner=False)
def cached_manufacturing(revision,unit,index):
    from .technical_drawings import manufacturing_sheets
    return manufacturing_sheets(geometry_data(revision),unit,index)

def drawing_view(sheets,key,extras=None):
    from .drawings import pdf_bytes
    selected=st.selectbox('圖面檢視',range(len(sheets)),format_func=lambda i:sheets[i].code+' · '+sheets[i].title,key=key+'_sheet')
    sheet=sheets[selected];st.image(sheet.svg(),width='stretch')
    a,b=st.columns(2)
    a.download_button('下載本張 SVG',sheet.svg(),file_name=key+'_'+sheet.code+'.svg',mime='image/svg+xml',key=key+'_svg')
    if b.button('整理 A3 PDF／向量圖包',key=key+'_build'):
        pdf=pdf_bytes(sheets);buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(key+'.pdf',pdf)
            for page in sheets:z.writestr(page.code+'.svg',page.svg())
            for name,data in (extras or {}).items():z.writestr(name,data)
        st.session_state[key+'_files']=(pdf,buf.getvalue())
    if key+'_files' in st.session_state:
        pdf,bundle=st.session_state[key+'_files']
        a.download_button('下載 A3 PDF',pdf,file_name=key+'.pdf',key=key+'_pdf')
        b.download_button('下載完整 ZIP',bundle,file_name=key+'.zip',key=key+'_zip')

@st.cache_resource(show_spinner=False)
def cached_layout(revision,unit):
    from .panel_layout import pack,sheets,extras
    data=pack(geometry_data(revision),unit)
    return data,sheets(data),extras(data)

@st.cache_resource(show_spinner=False)
def cached_methods(revision,unit):
    from .method_drawings import method_sheets
    return method_sheets(geometry_data(revision),unit)

def render_panels(geometry,revision):
    from .core import fabrication_checks
    units=list(geometry['blocks'])
    unit=st.selectbox('製造單元',units,index=units.index('SKYLARK250_WALL-M'),format_func=unit_label,key='manufacturing_unit')
    parts=geometry['blocks'][unit]['parts'];rows=fabrication_checks(geometry['blocks'][unit])
    mode=st.radio('板件資料',['單元平面放樣板','板件詳圖／單元等角','3D 板件與外框'],horizontal=True)
    if mode=='單元平面放樣板':
        data,pages,files=cached_layout(revision,unit)
        st.caption(f"一個單元共 {data['source_part_count']} 件，排入 {len(data['boards'])} 張原板；{len(data['unplaced'])} 件待處理。全數保留原尺度，未縮放。")
        drawing_view(pages,'flat_'+unit+'_'+str(revision),files)
        st.download_button('下載 1:1 放樣 DXF（mm）',files['panel_layout_mm.dxf'],file_name=unit+'_flat_mm.dxf',mime='application/dxf')
        if data['unplaced']:
            with st.expander('未排入原板的構件與原因'):
                st.dataframe([{'板件':q['id'],'原因':q['reason']} for q in data['unplaced']],hide_index=True)
        st.caption('1220 × 2440 mm 原板、板邊 10 mm、板件距離 6 mm；外框保守排版，未做孔洞互嵌、紋理約束與刀徑補償。')
    else:
        index=st.selectbox('來源板件',range(len(parts)),format_func=lambda i:f"P{i+1:02d} · {parts[i]['label']}",key='part_'+unit)
        if mode=='板件詳圖／單元等角':drawing_view(cached_manufacturing(revision,unit,index),f'manufacture_{unit}_{index}')
        else:
            a,b=st.columns([3,1]);row=rows[index]
            with a:st.plotly_chart(cached_panel(revision,unit,index),width='stretch',config={'displaylogo':False})
            with b:
                st.metric('長度',f"{row['length_mm']:.0f} mm");st.metric('寬度',f"{row['width_mm']:.0f} mm");st.metric('厚度包絡',f"{row['thickness_envelope_mm']:.1f} mm")
                st.caption('深色為輪廓／孔槽；淺色為 2440 × 1220 板材範圍。');st.write('尺寸預檢：'+row['status'])
    st.caption('圖面投影來源幾何。放樣圖供排版與核對；加工前以原 CAD 確認輪廓、孔槽、公差與 CAM。')
    with st.expander('全部板件預檢'):st.dataframe(rows,hide_index=True,width='stretch')


def render_cost(h,takeoff,cost,key,compact=False):
    from .design_ui import public_prices
    public_prices(h)
    st.divider()
    st.subheader('材料統計與 TWD 成本試算');st.caption('來源幾何按外框面積、隔間按雙面板面積、其餘示意构件按半表面積暫估。未排版；隔間骨架與接頭待核對。')
    st.warning('這些 TWD 單價由程式設定供示範計算，尚未詢價，不能作為論文中的市場成本證據。')
    with st.expander('每一項單價與假設從哪裡來？',expanded=True):
        entries=cost['rate_provenance']
        choice=st.selectbox('檢查價格或假設的來源',range(len(entries)),format_func=lambda i:entries[i]['項目'])
        entry=entries[choice]
        st.write(f"**{entry['目前值']:,.2f} {entry['單位']}**")
        st.info(entry['來源／狀態'])
        st.download_button('全部單價與依據 CSV',csv_bytes(entries),file_name=key+'_rate_sources.csv')
    with st.expander('編輯單價、損耗與估算假設'):
        with st.form('rates_form'):
            if compact:
                a,b=st.columns(2);c=st.container()
            else:a,b,c=st.columns(3)
            r=cost['rates'];new={}
            for n,label in [('sheet_price','18 mm 板材 TWD／張'),('cnc_hour','CNC TWD／小時'),('crew_hour','現場整組班組 TWD／小時'),('equipment_hour','設備 TWD／小時')]:new[n]=a.number_input(label,min_value=0.,value=float(r[n]))
            for n,label in [('hardware_allowance','接頭／緊固件暫列金 TWD'),('transport_allowance','運輸暫列金 TWD'),('extra_materials','其他材料／外購件 TWD'),('contingency_percent','預備金 %')]:new[n]=b.number_input(label,min_value=0.,value=float(r[n]))
            new['cnc_minutes_sheet']=c.number_input('CNC 分鐘／張（歷史例 15–30）',min_value=0.,value=float(r['cnc_minutes_sheet']))
            new['utilization']=c.slider('排版利用率假設',.1,1.,float(r['utilization']),.05)
            new['waste_percent']=c.number_input('另加損耗 %',min_value=0.,value=float(r['waste_percent']))
            override=c.checkbox('自行填寫板材預算面積',value=('area_override_'+key in st.session_state))
            area=c.number_input('板材預算面積 m²',min_value=0.,value=float(cost['panel_area_m2']))
            if st.form_submit_button('更新成本試算',type='primary'):
                st.session_state.cost_rates=new
                if override:st.session_state['area_override_'+key]=area
                else:st.session_state.pop('area_override_'+key,None)
                st.rerun(scope='fragment')
    a,b=st.columns(2);a.metric('板材預算張數',f"{cost['sheets_budget']:,} 張");b.metric('CNC 情境工時',f"{cost['cnc_hours']:.1f} h")
    st.dataframe(cost['lines'],hide_index=True,width='stretch',column_config={'數量':st.column_config.NumberColumn(format='%.2f'),'單價 TWD':st.column_config.NumberColumn(format='%.0f'),'小計 TWD':st.column_config.NumberColumn(format='%.0f')})
    st.caption(f"費用小計 {cost['subtotal']:,.0f} + 預備金 {cost['contingency']:,.0f}。張數＝向上取整〔面積 ÷ 2.9768 ÷ 排版利用率 × (1＋損耗率)〕。")
    st.warning('未包含：'+'、'.join(cost['exclusions'])+'。接頭數量與非標準材料仍待確認，以上不是完整工程報價。')
    st.download_button('材料與成本 CSV（含單價依據）',csv_bytes(cost['lines']),file_name=key+'_cost.csv')
    st.download_button('完整估算 JSON',json.dumps({'takeoff':takeoff,'cost':cost},ensure_ascii=False,indent=2),file_name=key+'_estimate.json')


def render_materials(takeoff,key):
    st.subheader('本方案材料與構件')
    st.caption(takeoff['basis'])
    rows=[{'類別':x['name'],'模組數':x['modules'],'來源子物件數':x['source_parts'],'來源外框面積 m²':round(x['source_area'],2),'示意暫估面積 m²':round(x['provisional_area'],2)} for x in takeoff['rows']]
    st.dataframe(rows,hide_index=True,width='stretch')
    st.caption(f"超過單張尺寸的來源子物件：{takeoff['oversize']}；厚度包絡較大：{takeoff['nonplanar']}。來源子物件數不等同切割板件數。")
    with st.expander('依樓層與構件定義檢視明細'):st.dataframe(takeoff['bom'],hide_index=True,width='stretch')
    st.download_button('構件清單 CSV',csv_bytes(takeoff['bom']),file_name=key+'_BOM.csv')
    st.download_button('材料數量 CSV',csv_bytes(rows),file_name=key+'_materials.csv')


def render_drawings(h,takeoff,cost,key):
    from .drawings import drawing_sheets,pdf_bytes
    sheets=drawing_sheets(h,takeoff,cost);st.markdown('#### 平面與施工圖說')
    st.caption('A3 建築圖說格式 · 尺寸、定位軸線、開口與門扇、剖面索引、立面、接合詳圖。圖面右上角可放大；工程核定項目列於圖框。')
    selected=st.selectbox('圖紙',range(len(sheets)),format_func=lambda i:sheets[i].code+' · '+sheets[i].title,label_visibility='collapsed')
    s=sheets[selected];st.image(s.svg(),width='stretch');package_key='drawings_'+digest([key,cost,h['time_estimate']])[:16]
    a,b=st.columns(2);a.download_button('下載目前 SVG 向量圖',s.svg(),file_name=key+'_'+s.code+'.svg',mime='image/svg+xml')
    if b.button('產生完整 PDF 與圖說包',type='primary'):
        with st.spinner('正在整理圖說…'):
            pdf=pdf_bytes(sheets);bundle=io.BytesIO()
            with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr(key+'_drawings.pdf',pdf)
                for item in sheets:z.writestr(item.code+'.svg',item.svg())
                z.writestr('BOM.csv',csv_bytes(takeoff['bom']));z.writestr('cost.csv',csv_bytes(cost['lines']))
                z.writestr('evidence.json',json.dumps({'sources':SOURCES,'rules':RULES,'cost':cost},ensure_ascii=False,indent=2))
            st.session_state[package_key]=(pdf,bundle.getvalue())
    if package_key in st.session_state:
        pdf,bundle=st.session_state[package_key];a.download_button('下載 A3 PDF 圖說',pdf,file_name=key+'_drawings.pdf',mime='application/pdf')
        b.download_button('下載完整圖說包 ZIP',bundle,file_name=key+'_drawings.zip')

def render_site(geometry,house):
    source_geometry=geometry
    from .core import normalize,site_scenario,evaluate_site,fabrication_checks,build_report,recommendations
    from .visuals import site_figure
    from .export import export_run
    st.subheader('現場吊裝 · 目前整屋方案')
    from .construction import site_scene
    mode=st.radio('吊裝模型來源',['目前整屋方案','匯入原專案 JSON'],horizontal=True)
    if mode=='目前整屋方案':
        scene,geometry=site_scene(house)
        st.caption(f"{house['layout_name']} · {house['levels']} 層 · {house['design_id']}；由目前裝配順序建立已安裝障礙，二樓與屋頂採實際標高。")
    else:
        upload=st.file_uploader('匯入構件配置 JSON',type='json')
        if not upload:st.info('請選擇配置檔；一樓／二樓方案可直接使用「目前整屋方案」。');return
        try:scene=normalize(json.loads(upload.getvalue()),read_json(ROOT/'data/blocks_full.json')['blocks'],geometry)
        except (OSError,ValueError,KeyError,TypeError) as e:st.error(str(e));return
    levels=sorted({m.get('level',1) for m in scene['modules']})
    level=st.selectbox('吊裝樓層',levels,index=len(levels)-1,format_func=lambda n:f'{n}F',key='lift_level_'+str(len(levels)))
    candidates=[m for m in scene['modules'] if m.get('level',1)==level and m['category'] in ['floor','wall','window','door','roof','corner']]
    if not candidates:st.info('此層沒有可吊裝模組。');return
    categories=list(dict.fromkeys(m['category'] for m in candidates))
    category=st.selectbox('吊裝構件類型',categories,index=categories.index('roof') if 'roof' in categories else 0,format_func=lambda c:{'roof':'屋頂','floor':'樓板','wall':'牆體','window':'窗洞','door':'門洞','corner':'轉角'}.get(c,c))
    roofs=[m for m in candidates if m['category']==category]
    col,settings=st.columns([3,1])
    with settings:
        selected=st.selectbox('吊裝模組',[m['instance_id'] for m in roofs],format_func=lambda k:k+' · '+next(m.get('label',m['block_id']) for m in roofs if m['instance_id']==k));clearance=st.slider('接近點淨空 mm',100,1500,250,50)
        payload=st.number_input('情境負載上限 kg',1.,10000.,250.)
        max_height=st.number_input('構件頂面限高 m',1.,50.,12.)*1000
        reach=st.number_input('作業半徑上限 m',1.,80.,20.)*1000
        scenario=site_scenario(scene,selected,clearance)
        before=evaluate_site(scenario,scenario['baseline'],payload_kg=payload,max_height_mm=max_height,reach_mm=reach)
        after=evaluate_site(scenario,scenario['corrected'],payload_kg=payload,max_height_mm=max_height,reach_mm=reach)
        choice=st.radio('吊裝路徑',['原始路徑','提升後再移動']);result=before if choice=='原始路徑' else after
        route=scenario['baseline'] if choice=='原始路徑' else scenario['corrected']
        st.metric('構件底面標高',f"{scenario['target']['bbox_mm'][0][2]/1000:.3f} m")
        st.caption(f"已安裝障礙 {len(scenario['obstacles'])} 件；後續構件不列為障礙。")
    from .lift_viewer import viewer_html as lifting_html
    with col:components.html(lifting_html(geometry,scenario,result,route),height=735,scrolling=False)
    report=build_report(scene,scenario,before,after,fabrication_checks(source_geometry['blocks']['SKYLARK250_WALL-M']))
    st.caption('播放與拖曳只檢查當前位置；紅色僅在外框接觸時出現。可勾選接觸時暫停。')
    with st.expander('整條路徑預檢與修改建議（非當前接觸狀態）'):
        st.write(f"全路徑預檢：{len(result['collisions'])} 個構件外框相交。")
        st.dataframe([{'檢查':c['rule_id'],'結果':c['status'],'說明':c['message']} for c in result['checks']],hide_index=True,width='stretch')
        for r in recommendations(before):st.write(r['scope']+' · '+r['action'])
    with st.expander('Rhino 輸出快照位置'):
        progress=st.slider('輸出快照 %（獨立於播放進度）',0,100,0,5)/100
    st.download_button('下載幾何檢查報告',json.dumps(report,ensure_ascii=False,indent=2),file_name='construction_report.json')
    if st.button('輸出 Rhino 與證據包'):
        folder=export_run(scene,geometry,scenario,result,report,progress);st.session_state.site_export=str(folder)
    if st.session_state.get('site_export'):
        path=Path(st.session_state.site_export)/'simulation.3dm';st.download_button('下載吊裝 Rhino 模型',path.read_bytes(),file_name='site_simulation.3dm')
    with st.expander('GPT 代理分析'):
        model=st.selectbox('模型',['gpt-6-astra','gpt-6.1-sol'])
        if st.button('分析本次檢查',disabled=not bool(os.environ.get('OPENAI_API_KEY'))):
            from .llm import request_plan
            try:st.json(request_plan(report,model)['plan'])
            except Exception as e:st.error(str(e))
