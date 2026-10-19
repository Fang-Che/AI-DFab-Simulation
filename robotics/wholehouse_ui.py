"""Full-house hypothesis scenarios, with raw results and editable mechanisms."""
import copy,io,json,zipfile
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .wholehouse_study import DEFAULT,COMMON,FIELDS,NAMES,METRICS,evaluate,validate,rows,radar_data,boundaries

COLORS={'A':'#537f90','B':'#cb8755','C':'#427b64'}

def radar_figure(s):
    data=radar_data(s);fig=go.Figure()
    for m in NAMES:
        rr=[r for r in data if r['method']==m];rr=rr+[rr[0]]
        fig.add_trace(go.Scatterpolar(r=[r['score'] for r in rr],theta=[r['metric'] for r in rr],
            name=NAMES[m],mode='lines+markers',line=dict(color=COLORS[m],width=2.5),
            customdata=[[r['raw'],r['unit'],r['cap'] or 100] for r in rr],
            hovertemplate='%{theta}<br>分數 %{r:.1f}<br>原值 %{customdata[0]:,.2f} %{customdata[1]}<extra>%{fullData.name}</extra>'))
    fig.update_layout(height=490,margin=dict(l=105,r=105,t=70,b=110),
        title=dict(text='全屋六軸｜研究假設情境（未校準）',font=dict(size=15)),
        polar=dict(radialaxis=dict(range=[0,100],dtick=25),angularaxis=dict(rotation=90,direction='clockwise')),paper_bgcolor='white',
        legend=dict(orientation='h',y=-.25,x=0,font=dict(size=11)),font=dict(family='Microsoft JhengHei, sans-serif',size=12))
    return fig

def gantt(s,method):
    r=next(r for r in s['results'] if r['method']==method);fig=go.Figure()
    for e in r['events']:
        if not e['hours']:continue
        fig.add_trace(go.Bar(x=[e['hours']],base=[e['start_h']],y=[e['phase']],orientation='h',
            marker_color=COLORS[method],showlegend=False,name=e['scope'],
            customdata=[[e['start_h'],e['end_h'],e['person_hours']]],
            hovertemplate='%{y}｜%{fullData.name}<br>%{customdata[0]:.1f} → %{customdata[1]:.1f} h<br>人力 %{customdata[2]:.1f} 人時<extra></extra>'))
    fig.update_layout(height=560,barmode='overlay',margin=dict(l=0,r=15,t=20,b=35),
        xaxis_title='排程工作小時（非日曆日期）',yaxis=dict(autorange='reversed'),paper_bgcolor='white')
    return fig

def stage_rows(s):
    result=[]
    for r in s['results']:
        groups={}
        for e in r['events']:
            g=groups.setdefault(e['phase'],dict(流程=r['method'],工序=e['phase'],工序時數=0.,人力投入=0.,成本_TWD=0.,危險區暴露=0.))
            for dest,src in [('工序時數','hours'),('人力投入','person_hours'),('成本_TWD','cost_twd'),('危險區暴露','exposure_person_hours')]:g[dest]+=e[src]
        result.extend(groups.values())
    return result

def bundle(h,s):
    from .wholehouse_drawings import sheets
    from .drawings import pdf_bytes
    pages=sheets(h,s);pdf=pdf_bytes(pages);buff=io.BytesIO()
    with zipfile.ZipFile(buff,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('全屋研究假設比較.pdf',pdf)
        z.writestr('evidence.json',json.dumps(s,ensure_ascii=False,indent=2))
        z.writestr('parameters.json',json.dumps(s['params'],ensure_ascii=False,indent=2))
        z.writestr('boundaries.json',json.dumps(boundaries(s),ensure_ascii=False,indent=2))
        for name,data in [('comparison',rows(s)),('radar',radar_data(s)),('stages',stage_rows(s)),
            ('schedule',[dict(method=r['method'],**e) for r in s['results'] for e in r['events']]),
            ('adaptation',[dict(method=r['method'],**e) for r in s['results'] for e in r['changes']])]:
            z.writestr(name+'.csv',pd.DataFrame(data).to_csv(index=False).encode('utf-8-sig'))
        for page in pages:z.writestr(page.code+'.svg',page.svg())
    return pdf,buff.getvalue()

def panel(h):
    st.markdown('#### 設計 → 製造 → 裝配 → 全屋')
    st.info('研究假設情境：示範初值可修改；尚未實測校準。C 假設孿生自動校核及閉迴路校正已部署。')
    st.caption(f"同一設計 {h['design_id']}｜{len(h['items'])} 模組｜{h['floor_area_m2']:.2f} m²｜含基地／基礎及完工工程暫列")
    with st.expander('調整工序、人數、誤差與費率'):
        st.caption('排序是待檢驗假設。以下數值是程式示範初值，無實測或報價支持；成本包含人工校核／校稿與校正。')
        old=copy.deepcopy(st.session_state.get('wholehouse_params',DEFAULT))
        with st.form('wholehouse_form'):
            method_frame=pd.DataFrame([{'參數':label,**{m:old['methods'][m][k] for m in NAMES}} for k,label in FIELDS])
            values=st.data_editor(method_frame,hide_index=True,disabled=['參數'],key='wh_methods',width='stretch')
            common_frame=pd.DataFrame([{'參數':label,'值':old['common'][k]} for k,label,_ in COMMON])
            shared=st.data_editor(common_frame,hide_index=True,disabled=['參數'],key='wh_shared',width='stretch')
            if st.form_submit_button('套用全屋情境參數'):
                p={'common':{k:float(shared.iloc[i]['值']) for i,(k,_,_) in enumerate(COMMON)},
                    'methods':{m:{k:float(values.iloc[i][m]) for i,(k,_) in enumerate(FIELDS)} for m in NAMES}}
                try:st.session_state.wholehouse_params=validate(p);st.rerun(scope='fragment')
                except (ValueError,TypeError) as exc:st.error(str(exc))
    s=evaluate(h,st.session_state.get('wholehouse_params'));b=boundaries(s)
    st.markdown('**六軸比較｜外圍代表較佳**')
    st.plotly_chart(radar_figure(s),width='stretch',config={'displaylogo':False},key='wholehouse_radar')
    st.dataframe(pd.DataFrame(rows(s)),hide_index=True,width='stretch')
    st.caption('人力投入與暴露單位為「人時」。公差率是模型預期一次符合率；適應能力是平均變更處理工期換算分數。')
    a,bb,c=s['results']
    if a['hours']>0 and bb['hours']>0:
        st.write(f"此情境：C 比 A 工期縮短 {(1-c['hours']/a['hours'])*100:.1f}%；比 B 縮短 {(1-c['hours']/bb['hours'])*100:.1f}%。倍率由工序計算。")
    detail=st.radio('檢視比較內容',['工期與投入分解','排序假設與成立條件','條件變動','定義與輸出'],horizontal=True,key='wh_details')
    if detail=='工期與投入分解':
        m=st.selectbox('排程流程',list(NAMES),format_func=lambda k:NAMES[k],key='wh_gantt_method')
        st.plotly_chart(gantt(s,m),width='stretch',config={'displaylogo':False},key='wh_gantt')
        st.caption('不同資源可同時工作；同資源依批次排程。工期為最後工序結束時間，不能把各工序時數相加當工期。')
        st.dataframe(pd.DataFrame(stage_rows(s)).round(2),hide_index=True,width='stretch')
    elif detail=='排序假設與成立條件':
        names={k:label for label,k,_,_ in METRICS}
        st.dataframe(pd.DataFrame([{'指標':names[r['metric']],'期待（佳→差）':' > '.join(r['expected_best_to_worst']),
            '計算（佳→差）':' > '.join(r['calculated_best_to_worst']),'是否一致':'是' if r['matches'] else '否'} for r in s['hypothesis_check']]),hide_index=True,width='stretch')
        st.markdown('**其餘條件固定時**')
        st.write(f"成本原值要 B > A > C：B/C 共用設備固定暫列金需介於 TWD {b['robot_fixed_cost_lower']:,.0f} 與 {b['robot_fixed_cost_upper']:,.0f}；目前 TWD {s['params']['common']['robot_mobilization']:,.0f}。")
        if b['b_exposure_fraction_lower'] is not None:
            st.write(f"B 暴露人時要高於 A：B 主動作業危險區占比需大於 {b['b_exposure_fraction_lower']:.1%}；目前 {s['params']['methods']['B']['exposure_fraction']:.1%}。超過 100% 代表此條件下無法成立。")
        st.write(f"C 平均變更處理要快於 A：C 辨識／規劃回應時間需低於 {b['c_response_h_upper']:.2f} h；目前 {s['params']['methods']['C']['change_response_h']:.2f} h。")
        st.caption('分界是模型反算的條件，不能作為校準證據；系統不會自動改參數追求排序。成本區間若上下限倒置，代表此單參數無解。')
    elif detail=='條件變動':
        st.caption('五種變更的工作包試算；受影響比例三組相同，未驗證三維路徑。C 效益取決於辨識／重規劃時間。')
        st.dataframe(pd.DataFrame([{'流程':r['method'],'情境':x['scenario'],'受影響模組':x['affected_modules'],'處理工期_h':round(x['recovery_hours'],2)} for r in s['results'] for x in r['changes']]),hide_index=True,width='stretch')
        fig=go.Figure()
        for r in s['results']:
            ss=r['adaptability_sensitivity'];fig.add_trace(go.Scatter(x=[x['response_h'] for x in ss],y=[x['mean_recovery_hours'] for x in ss],name=r['method'],line=dict(color=COLORS[r['method']]),mode='lines+markers'))
        fig.update_layout(height=310,xaxis_title='各流程辨識／規劃時間假設 h',yaxis_title='平均變更處理工期 h',margin=dict(l=10,r=10,t=10,b=40))
        st.plotly_chart(fig,width='stretch',key='wh_adaptation')
    else:
        for line in s['assumptions']:st.write('• '+line)
        st.caption('低投入軸 = max(0, 100 × (1 - 原值 / 尺度上限))；上限為可編輯展示尺度，不是業界門檻。工期與成本相關，不以雷達面積判定總排名。')
        st.dataframe(pd.DataFrame(radar_data(s)),hide_index=True,width='stretch')
        if st.button('產生全屋比較圖說與計算證據',key='wh_export'):
            st.session_state.wholehouse_export=(s['id'],*bundle(h,s))
        saved=st.session_state.get('wholehouse_export')
        if saved and saved[0]==s['id']:
            st.download_button('下載全屋比較 PDF',saved[1],f"全屋比較_{s['id']}.pdf",'application/pdf',key='wh_pdf')
            st.download_button('下載計算證據 ZIP',saved[2],f"全屋比較_{s['id']}.zip",'application/zip',key='wh_zip')
    st.caption('模型 '+s['version']+'｜情境 '+s['id']+'｜R8 隔間通行測試可在上方切換；其完成率不能代替全屋施工完成率。')
