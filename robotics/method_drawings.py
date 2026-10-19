"""Model-derived axonometric callouts, with separately labelled assembly advice."""
import math
import numpy as np
from .technical_drawings import edges,view,circle,polyline,INK,LIGHT,ACCENT
from .drawings import Sheet

def clip_circle(a,b,center,radius):
    a=np.asarray(a);b=np.asarray(b);c=np.asarray(center);d=b-a;f=a-c
    aa=np.dot(d,d)
    if aa<1e-12:return None
    bb=2*np.dot(f,d);cc=np.dot(f,f)-radius**2;disc=bb*bb-4*aa*cc
    if disc<0:return None
    roots=((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa))
    lo=max(0,roots[0]);hi=min(1,roots[1])
    return (a+lo*d,a+hi*d) if hi>=lo else None

def method_sheets(geometry,unit):
    parts=geometry['blocks'][unit]['parts'];iso=np.array([[1/math.sqrt(2),-1/math.sqrt(6)],[-1/math.sqrt(2),-1/math.sqrt(6)],[0,2/math.sqrt(6)]])
    segments=np.concatenate([edges(p)@iso for p in parts]);lo=segments.reshape(-1,2).min(0);hi=segments.reshape(-1,2).max(0)
    meta=dict(layout_name=unit.replace('SKYLARK250_',''),levels=1,design_id='DETAIL-R11')
    s=Sheet('A504','單元工法圖／局部放大與作業建議',meta)
    mapping,scale=view(s,segments,(315,180,570,485),'01  來源單元等角線稿')
    points=segments.reshape(-1,2)
    specs=[((170,265),(.22,.8),'局部 01  板槽與邊緣','首件量測板厚、槽口，再乾式試配。'),
           ((1030,265),(.78,.8),'局部 02  肋板交會','核對編碼與槽位，依方向插入定位。'),
           ((170,545),(.15,.2),'局部 03  外側封板','先確認內部接合，再關閉近側板。'),
           ((1030,545),(.8,.15),'局部 04  收口與固定','檢查對角與板縫，依核定方式鎖固。')]
    for center,ratio,title,note in specs:
        target=lo+(hi-lo)*ratio;anchor=points[np.argmin(np.linalg.norm((points-target)/(hi-lo),axis=1))]
        # Segment leaders terminate at the circle boundary, outside all caption rows.
        start=np.array(mapping(anchor));c=np.array(center);direction=start-c;direction/=max(np.linalg.norm(direction),1)
        end=c+direction*86;s.line(*start,*end,LIGHT,.9);circle(s,*start,3,ACCENT,1)
        circle(s,*center,86,INK,1)
        zoom=scale*2.7
        for a,b in segments:
            aa=c+(a-anchor)*[zoom,-zoom];bb=c+(b-anchor)*[zoom,-zoom]
            clipped=clip_circle(aa,bb,c,82)
            if clipped:s.line(*clipped[0],*clipped[1],INK,.6)
        s.text(center[0]-112,center[1]+112,title,15)
        s.text(center[0]-125,center[1]+136,note,10)
    s.text(330,690,'圓形放大為模型局部投影，非剖面或緊固件設計。',12,ACCENT)
    s.text(65,717,'建議：量測與試配 → 治具定位 → 遠側與內肋 → 近側封板 → 頂板收口 → 檢查與指定固定。',12)
    s.text(65,747,'依據：MFG pp.6–9、USE p.8；工具採卡尺、木槌、夾具及電動起子。固定件規格依工程設計。',11)
    # Reuse the exact part roles and sequence shown by the unit assembly viewer.
    from .assembly import factory_scene
    factory=factory_scene(geometry,unit);ordered=factory['parts']
    source={p.get('part_id'):p for p in parts}
    t=Sheet('A505','單元組裝步序／封板前檢查',meta)
    labels=['01  底板與治具定位','02  遠側板與內部肋板','03  近側封板','04  頂板收口與檢查']
    # Exact source identities retain original placement and scale in all four views.
    n=len(ordered);ends=[sum(p['role']=='bottom' for p in ordered),sum(p['role'] in ['bottom','far','internal'] for p in ordered),sum(p['role']!='top' for p in ordered),n]
    for j,(end,title) in enumerate(zip(ends,labels)):
        x=65+j*285;t.text(x,157,title,14)
        available=[source[p['id']] for p in ordered[:end] if p['id'] in source]
        data=np.concatenate([edges(p)@iso for p in available]) if available else []
        width,height=240,380;sc=min(width/max(hi[0]-lo[0],1),height/max(hi[1]-lo[1],1))
        for a,b in data:
            pa=[x+10+(a[0]-lo[0])*sc,215+(hi[1]-a[1])*sc];pb=[x+10+(b[0]-lo[0])*sc,215+(hi[1]-b[1])*sc]
            t.line(*pa,*pb,INK,.6)
        t.text(x,620,f'完成 {min(end,n)} / {n} 件',12,ACCENT)
        if j<3:t.line(x+250,410,x+273,410,ACCENT,1.2);t.line(x+267,405,x+273,410,ACCENT);t.line(x+267,415,x+273,410,ACCENT)
    t.text(65,677,'步序依本平台單元板件排序呈現；仍須核對原接頭插入方向、夾持空間與臨時穩定。',12)
    t.text(65,710,'施工建議：封板前確認肋板到位、內部固定與品質紀錄；避免封閉後無法接近接頭。',12)
    t.text(65,745,'細部原理與工具索引見 A502／A503；本圖未指定螺絲直徑、間距、鎖固扭矩或吊點。',12)
    return [s,t]
