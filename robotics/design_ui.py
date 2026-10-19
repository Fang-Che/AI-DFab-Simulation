"""Interactive infill, traceable public prices and reproducible comparisons."""
import io,json,zipfile,datetime
import streamlit as st
from .core import ROOT,digest
from .interior import DEFAULT,validate,suggestions
from .study import compare,rows,ASSUMPTIONS,sensitivity
from .lifecycle import enrich,rows as completed_rows,radar_data,condition_rows,PARAMS,DEFAULTS,validate as validate_lifecycle
from .study_drawings import plan_figure,sheets,radar_figure,completion_figure
from .prices import FX,converted,benchmark

STATE=ROOT/'robotics/runs/interior_state.json'

def current(levels):
    if 'interior_config' not in st.session_state:
        saved={}
        if STATE.exists():
            try:saved=json.loads(STATE.read_text(encoding='utf8'))
            except (OSError,ValueError):pass
        st.session_state.interior_config={**DEFAULT,**saved.get('config',{})}
        st.session_state.design_history=saved.get('history',[])
    if not st.session_state.get('housing_r11_initialized'):
        from .housing_plan import preset
        if st.session_state.interior_config.get('planning_version')!=11:
            st.session_state.interior_legacy_config=dict(st.session_state.interior_config)
            st.session_state.interior_config=preset(levels=levels)
        st.session_state.housing_r11_initialized=True
    c=dict(st.session_state.interior_config);c['floor']=min(c['floor'],levels)
    if c.get('planning')=='residential':c['common_end']=8400 if levels==2 else 7200
    if levels==2:c['common_end']=max(7800,c['common_end'])
    return validate(c,levels)

def commit(c,reason,levels):
    c=validate(c,levels);history=st.session_state.get('design_history',[])
    history.append(dict(time=datetime.datetime.now().isoformat(timespec='seconds'),reason=reason,before=current(levels),after=c))
    st.session_state.design_history=history;st.session_state.interior_config=c
    STATE.parent.mkdir(parents=True,exist_ok=True)
    STATE.write_text(json.dumps(dict(config=c,history=history),ensure_ascii=False,indent=2),encoding='utf8')
    st.rerun()

@st.cache_data(show_spinner=False,max_entries=24)
def study_cached(config_json,levels,assumptions_json,revision):
    return compare(json.loads(config_json),levels,json.loads(assumptions_json))

def calculate(c,levels):
    revision=max((ROOT/'robotics'/p).stat().st_mtime_ns for p in ['study.py','interior.py'])
    return study_cached(json.dumps(c,sort_keys=True),levels,json.dumps(st.session_state.get('study_assumptions',ASSUMPTIONS),sort_keys=True),revision)

@st.cache_data(show_spinner=False,max_entries=12)
def lifecycle_cached(config_json,levels,access_json,params_json,revision):
    return enrich(compare(json.loads(config_json),levels,json.loads(access_json)),json.loads(params_json))

def calculate_lifecycle(c,levels):
    revision=max((ROOT/'robotics'/name).stat().st_mtime_ns for name in ['study.py','interior.py','lifecycle.py'])
    return lifecycle_cached(json.dumps(c,sort_keys=True),levels,
        json.dumps(st.session_state.get('study_assumptions',ASSUMPTIONS),sort_keys=True),
        json.dumps(st.session_state.get('lifecycle_params',DEFAULTS),sort_keys=True),revision)

def editor(h):
    from .housing_plan import preset
    from .drawings import plan
    c=h['interior']['config'];residential=c.get('planning')=='residential'
    st.markdown('#### 住宅空間配置')
    with st.form('residential_form'):
        name=st.selectbox('住宅配置',['two_bed','one_bed'],index=0 if c.get('preset','two_bed')=='two_bed' else 1,
            format_func=lambda n:{'two_bed':'均衡兩房一衛 · 開放客餐廳','one_bed':'舒適一房一衛 · 彈性工作區'}[n])
        floor=st.selectbox('配置樓層',list(range(1,h['levels']+1)),index=c['floor']-1,key='residential_floor')
        enabled=st.checkbox('顯示隔間與家具尺度',value=c['enabled'])
        if st.form_submit_button('套用住宅配置並同步圖面',type='primary'):
            commit({**preset(name,h['levels'],floor),'enabled':enabled},'住宅配置更新',h['levels'])
    if not residential:
        legacy_editor(h);return
    st.image(plan(h,c['floor']).svg(),width='stretch')
    st.caption('臥室取消長走道切割；以家具尺寸檢視床側、門扇與公共動線。家具不計入結構材料與成本。')
    st.dataframe([{'空間':r['name'],'淨面積 m²':r['area_m2'],'配置目標 m²':r['min_area']} for r in h['interior']['rooms']],hide_index=True,width='stretch')
    for note in h['interior'].get('planning_notes',[]):st.caption(note)
    st.caption('目前配置主屋指定樓層；其他樓層與側翼維持開放。')
    with st.expander('自訂隔間與版本紀錄'):
        if st.button('切換原有自訂隔間參數'):
            old={**DEFAULT,**st.session_state.get('interior_legacy_config',{}),'floor':c['floor']}
            if h['levels']==2:old['common_end']=max(7800,old['common_end'])
            commit(old,'切換自訂隔間',h['levels'])
        st.download_button('下載配置與修改紀錄',json.dumps(dict(config=c,history=st.session_state.get('design_history',[])),ensure_ascii=False,indent=2),file_name='residential_history.json')

def legacy_editor(h):
    c=h['interior']['config'];st.markdown('#### 室內配置')
    st.caption('調整主屋指定樓層的非承重隔間。其餘樓層與側翼保留開放；面積是空間配置研究，未包含衛浴／機電設計。')
    with st.form('interior_form'):
        enabled=st.checkbox('顯示室內隔間',value=c['enabled'])
        a,b=st.columns(2)
        bedrooms=a.selectbox('房間數',[1,2,3],index=c['bedrooms']-1)
        floor=b.selectbox('配置樓層',list(range(1,h['levels']+1)),index=c['floor']-1)
        common=a.slider('公共區分界距前端 mm',7800 if h['levels']==2 else 4800,8400,int(c['common_end']),300)
        corridor=b.slider('走道寬 mm',1200,1800,int(c['corridor']),100)
        door=a.slider('內門淨寬 mm',700,1400,int(c['door_width']),100)
        offset=b.slider('公共區門位偏移 mm',-100,100,int(c['door_offset']),50)
        split=a.slider('兩房前後面積比例 %',35.,65.,float(c['split_ratio']),.5)
        names=[st.text_input(f'空間 {i+1} 名稱',value=c['room_names'][i],max_chars=16) for i in range(3)]
        lock_common=a.checkbox('鎖定公共區分界（回饋修改時）',value=c['lock_common'])
        lock_door=b.checkbox('鎖定門寬與门位（回饋修改時）',value=c['lock_door'])
        if st.form_submit_button('套用隔間並同步模型、圖面與材料',type='primary',width='stretch'):
            try:commit(dict(enabled=enabled,bedrooms=bedrooms,floor=floor,common_end=common,corridor=corridor,
                            door_width=door,door_offset=offset,split_ratio=split,lock_common=lock_common,lock_door=lock_door,room_names=names),'手動調整室內配置',h['levels'])
            except ValueError as exc:st.error(str(exc))
    st.plotly_chart(plan_figure(h['interior']),width='stretch',key='editor_plan',config={'displaylogo':False})
    st.caption('橙色虛線：門洞；深色：隔間；淡紅色房間：低於本研究面積目標。可縮放、平移、懸停檢視。')
    room_rows=[dict(空間=r['name'],面積_m2=r['area_m2'],研究面積目標_m2=r['min_area'],結果='符合' if r['meets_area'] else '需調整') for r in h['interior']['rooms']]
    st.dataframe(room_rows,hide_index=True,width='stretch')
    st.caption('房間 8 m²／公共區 18 m² 為研究需求設定，並非法規符合性判定。隔間材料以雙面板面積估算，骨架與接頭尚未詳設。')
    history=st.session_state.get('design_history',[])
    if history:
        if st.button('撤回上一次設計修改'):
            commit(history[-1]['before'],'撤回上一版',h['levels'])
        st.download_button('下載設計版本紀錄',json.dumps(history,ensure_ascii=False,indent=2),file_name='design_history.json')

def public_prices(h):
    st.markdown('#### WikiHouse 公開價格｜GBP → TWD')
    fx=st.number_input('換算匯率：1 GBP = TWD',min_value=.01,value=FX['gbp_twd'],step=.01,key='public_fx')
    st.caption(f"已查證快照：{FX['kind']} {FX['gbp_twd']}，{FX['quote_time']}；頁面不自動更新匯率。")
    st.markdown(f"[臺灣銀行匯率來源]({FX['url']})")
    default=benchmark(h,fx);area=st.number_input('構架參考室內面積 m²',min_value=0.,value=default['area_m2'],step=.001,format='%.3f',key='uk_area_'+h['design_id'])
    b=benchmark(h,fx,area)
    st.info(f"英國構架價格換算：TWD {b['twd_low']:,.0f}–{b['twd_high']:,.0f}\n\n£400–450／m² × {area:.2f} m² × {fx:.2f}")
    st.caption(b['area_basis']+'。'+b['status'])
    for r in converted(fx):
        with st.expander(r['title'],expanded=r['id']=='UK-CHASSIS'):
            st.write(f"£{r['gbp_low']:,.0f}–{r['gbp_high']:,.0f}／{r['unit']} → TWD {r['twd_low']:,.0f}–{r['twd_high']:,.0f}")
            st.write(r['scope']);st.caption(r['date']);st.markdown(f"[查看原始價格頁面]({r['url']})")
    st.download_button('下載英國價格、範圍與匯率證據',json.dumps(dict(fx=FX,selected_fx=fx,benchmark=b,references=converted(fx)),ensure_ascii=False,indent=2),file_name='public_price_evidence.json')

def pack(h,study,after=None,rates=None):
    from .drawings import pdf_bytes,drawing_sheets
    from .estimating import quantity_takeoff,cost_estimate
    takeoff=quantity_takeoff(h);cost=cost_estimate(h,takeoff,rates)
    pages=drawing_sheets(h,takeoff,cost)+sheets(h,study,after)
    pdf=pdf_bytes(pages);out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('comparison_drawings.pdf',pdf)
        for s in pages:z.writestr(s.code+'.svg',s.svg())
        z.writestr('evidence.json',json.dumps(dict(study=study,after=after,fx=FX,prices=converted(),design_id=h['design_id'],takeoff=takeoff,cost=cost),ensure_ascii=False,indent=2))
        import pandas as pd
        z.writestr('comparison.csv',pd.DataFrame(completed_rows(study)).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('original_comparison.csv',pd.DataFrame(rows(study)).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('radar.csv',pd.DataFrame(radar_data(study)).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('conditions.csv',pd.DataFrame(condition_rows(study)).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('lifecycle_phases.csv',pd.DataFrame([dict(method=r['method'],**p) for r in study['results'] for p in r.get('lifecycle',{}).get('phases',[])]).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('sensitivity.csv',pd.DataFrame(sensitivity(study)).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('BOM.csv',pd.DataFrame(takeoff['bom']).to_csv(index=False).encode('utf-8-sig'))
        z.writestr('cost_assumptions.csv',pd.DataFrame(cost['lines']).to_csv(index=False).encode('utf-8-sig'))
    return pdf,out.getvalue()

def partition_study_panel(h):
    st.markdown('#### 三種流程受控模擬')
    st.caption('同一批研究隔間：製程規劃 → CNC 製造 → 工廠單元組裝 → 現場裝配。A 數位製造＋人工組裝；B 數位製造＋機器人組裝；C 孿生模擬＋自動化。')
    st.caption('C 為離線孿生流程原型：模型、候選模擬與條件變動後重規劃。未接實體感測、線上 AI 或 ROS。')
    if not h['interior']['parts']:st.info('請先啟用室內隔間。');return
    with st.expander('共同參數與情境費率'):
        with st.form('study_params'):
            old={**ASSUMPTIONS,**st.session_state.get('study_assumptions',{})};new=dict(old)
            for key,label in [('robot_radius_mm','底座半徑 mm'),('clearance_mm','通行淨空 mm'),('robot_reach_mm','投影作業半徑 mm'),('human_minutes_piece','A 單件作業 min'),('robot_minutes_piece','B=C 單件作業 min'),('station_minutes','B=C 換站 min'),('human_crew_twd_h','A 班組 TWD/h'),('robot_supervision_twd_h','B=C 人員 TWD/h'),('robot_equipment_twd_h','B=C 設備 TWD/h'),('failure_review_minutes','每件失敗評估 min'),('fallback_handoff_minutes','人工補作交接 min'),('human_setup_minutes','人工準備 min'),('human_crew_people','人工班組人數'),('robot_supervision_people','機器人監督人數')]:
                new[key]=st.number_input(label,min_value=0.,value=float(old[key]),key='study_'+key)
            if st.form_submit_button('更新比較假設'):
                from .study import assumptions
                try:st.session_state.study_assumptions=assumptions(new);st.rerun(scope='fragment')
                except ValueError as exc:st.error(str(exc))
        st.json(old,expanded=False)
    with st.expander('製造、公差、暴露與六軸假設'):
        st.caption('預設值均為情境假設，尚未校準。B/C 共用硬體參數；人工作業與機器人作業的誤差預設相同。')
        with st.form('lifecycle_params_form'):
            old_p={**DEFAULTS,**st.session_state.get('lifecycle_params',{})};new_p=dict(old_p)
            for k,label,_ in PARAMS:
                new_p[k]=st.number_input(label,min_value=0.,value=float(old_p[k]),key='lc_'+k,format='%.4f')
            if st.form_submit_button('更新製造與六軸假設'):
                try:st.session_state.lifecycle_params=validate_lifecycle(new_p);st.rerun(scope='fragment')
                except ValueError as exc:st.error(str(exc))
    with st.spinner('計算製造與組裝，重新測試五種條件；首次約需半分鐘…'):
        study=calculate_lifecycle(h['interior']['config'],h['levels'])
    st.caption('研究編號 '+study['id']+'；同一情境為確定性計算，重播不算獨立實驗。')
    st.markdown('##### 製造＋組裝｜六軸情境比較')
    st.caption('工期、成本與人力包含製造及組裝。未完成的現場任務沿用共同人工補作規則。公差模型尚未連動品質返工。')
    for rr in study['results']:
        if not rr['completed_work']['complete']:st.warning(rr['method']+' 補作後仍未完成；完整指標留空，不繪製雷達。')
    st.plotly_chart(radar_figure(study),width='stretch',key='study_radar',config={'displaylogo':False})
    st.caption('越外圍表示投入／暴露較少，或公差／適應率較高。公差為誤差模型、暴露為占比估算、適應率為五種二維情境測試；不以雷達面積排名。')
    st.markdown('##### 現場原流程完成率｜人工補作前')
    st.plotly_chart(completion_figure(study),width='stretch',key='study_original_completion',config={'displaylogo':False})
    st.dataframe(completed_rows(study),hide_index=True,width='stretch')
    with st.expander('投入分解、原始數值與雷達尺度'):
        st.caption('工期／成本／人力／暴露：max(0,100×(1−原值/上限))；上限按每件值×構件數。公差率與適應率直接使用百分比。')
        st.dataframe(radar_data(study),hide_index=True,width='stretch')
        st.dataframe([dict(流程=rr['method'],**p) for rr in study['results'] for p in rr['lifecycle']['phases']],hide_index=True,width='stretch')
        st.caption('人時按在場人數計算；TWD/h 是整班費率。機器人設備計費至交接結束，人工補作期間釋放。')
        st.download_button('下載雷達原值與評分 CSV',__import__('pandas').DataFrame(radar_data(study)).to_csv(index=False).encode('utf-8-sig'),file_name='radar_'+study['id']+'.csv')
    with st.expander('孿生候選方案與條件測試'):
        st.json(study['twin_plan'])
        st.dataframe(condition_rows(study),hide_index=True,width='stretch')
        st.caption('五種條件：基準、淨空增加、作業半徑縮小、臨時堆料、淨空增加＋堆料。每案在同一條件下比較三組，計算補作前全任務完成率；不代表一般成功機率。')
    with st.expander('公差模型與危險區暴露依據'):
        st.write('公差：假設加工、治具／抓持、座標定位及最終定位為獨立零均值二維常態誤差；依公差半徑計算符合機率。B/C 沒有精度加成，人工補作按人工誤差混合。')
        st.json({r['method']:r['lifecycle']['error_budget'] for r in study['results']})
        st.write('暴露：各主动作業人時 × 所設定危險區占比。準備、失敗評估與交接假設停機隔離；未追蹤人員軌跡，不等同碰撞機率或安全認證。')
        st.json(study['fabrication'])
    with st.expander('補作前的現場原流程結果'):st.dataframe(rows(study),hide_index=True,width='stretch')
    method=st.selectbox('檢視流程',['A','B','C'],key='study_method');r=next(x for x in study['results'] if x['method']==method)
    display_result=r
    if r['completed_work']['fallback']:
        phase=st.radio('路徑階段',['原流程','人工補作'],horizontal=True,key='study_route_phase')
        if phase=='人工補作':
            display_result=r['completed_work']['fallback']
            st.caption('圖中深色含原流程已完成構件；路徑為後續人工補作。')
    st.plotly_chart(plan_figure(study['interior'],display_result),width='stretch',config={'displaylogo':False},key='study_path')
    with st.expander('逐件作業與未通過原因'):st.dataframe([{k:v for k,v in e.items() if k not in ['route','station']} for e in display_result['events']],hide_index=True,width='stretch')
    with st.expander('假設、AI 提案與驗證界線'):
        st.json(study['ai_proposal'])
        for line in study['limitations']:st.write('• '+line)
    options=suggestions(h['interior']['config'],h['levels']);after=calculate(options[0]['config'],h['levels']) if options else None
    key='study_pack_'+digest([study['id'],st.session_state.get('cost_rates'),after['id'] if after else None])[:16]
    if st.button('產出比較圖面 PDF 與證據包',type='primary'):
        with st.spinner('產生圖面與可重算紀錄…'):st.session_state[key]=pack(h,study,after,st.session_state.get('cost_rates'))
    if key in st.session_state:
        pdf,bundle=st.session_state[key];st.download_button('下載比較圖面 PDF',pdf,file_name='comparison_'+study['id']+'.pdf')
        st.download_button('下載完整比較 ZIP',bundle,file_name='comparison_'+study['id']+'.zip')

def feedback_panel(h):
    st.markdown('#### 模擬問題 → 修改預覽 → 重新驗證')
    c=h['interior']['config']
    if not h['interior']['parts']:st.info('請先啟用室內隔間。');return
    with st.spinner('檢查目前配置…'):before=calculate(c,h['levels'])
    b=before['results'][1]
    st.write(f"B 組目前通過 {b['success']}/{b['tasks']} 項通道與站位預檢。")
    for r in h['interior']['rooms']:
        if not r['meets_area']:st.warning(f"{r['name']} {r['area_m2']:.2f} m²，低於研究需求 {r['min_area']:.0f} m²。")
    st.caption('研究需求與使用者鎖定條件會保留；預檢通過不表示完成結構、設備承載或精度驗證。')
    history=st.session_state.get('design_history',[])
    if history and history[-1]['after']==c:
        with st.expander('最近已接受修改的前後紀錄',expanded=True):
            entry=history[-1];st.caption(entry['time']+'｜'+entry['reason'])
            previous=calculate(entry['before'],h['levels']);prior=previous['results'][1]
            st.write(f"B 組通過：{prior['success']}/{prior['tasks']} → {b['success']}/{b['tasks']}")
            st.write(f"隔間面積：{previous['interior']['wall_area_m2']:.2f} → {before['interior']['wall_area_m2']:.2f} m²")
            st.download_button('下載已接受修改的完整紀錄',json.dumps(dict(history=entry,before=previous,after=before),ensure_ascii=False,indent=2),file_name='accepted_feedback.json')
    options=suggestions(c,h['levels'])
    if not options:
        st.info('目前沒有符合鎖定條件的幾何修改建議。可在流程比較檢視延後封閉策略，或手動調整配置。');return
    chosen=st.selectbox('修改選項',range(len(options)),format_func=lambda i:options[i]['title'])
    option=options[chosen];st.write(option['reason'])
    with st.spinner('以相同參數重新驗證修改方案…'):after=calculate(option['config'],h['levels'])
    ar=after['results'][1]
    st.dataframe([dict(版本=label,門寬_mm=case['interior']['config']['door_width'],通過=f"{result['success']}/{result['tasks']}",
                       隔間面積_m2=round(case['interior']['wall_area_m2'],2),補作前工期_h=result['completion_hours'],含補作工期_h=result['completed_work']['hours'],含補作成本_TWD=result['completed_work']['cost_twd'])
                  for label,case,result in [('修改前',before,b),('修改後',after,ar)]],hide_index=True,width='stretch')
    st.plotly_chart(plan_figure(after['interior'],ar),width='stretch',config={'displaylogo':False},key='feedback_plan')
    st.caption('上圖為修改預覽，紅色仍是未通過任務。構件數可能因分板改變，因此此處屬設計前後比較。')
    if st.button('接受修改並更新整屋方案',type='primary'):
        commit(option['config'],option['title'],h['levels'])
    st.download_button('下載修改前後檢查',json.dumps(dict(before=before,after=after,proposal=option),ensure_ascii=False,indent=2),file_name='design_feedback.json')


def study_panel(h):
    mode=st.radio('比較範圍',['全屋研究假設','隔間通行驗證（R8）'],horizontal=True,key='study_scope_r9')
    if mode=='全屋研究假設':
        from .wholehouse_ui import panel
        panel(h)
    else:partition_study_panel(h)
