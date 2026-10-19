"""Measured vector views from cached meshes; conceptual details are labelled NTS."""
import math
from functools import lru_cache
import numpy as np
from .drawings import Sheet
from .visuals import feature_edges
from .core import transform

INK='#263b44';LIGHT='#b4bfc4';ACCENT='#527d86'

def convex_hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    chains=[]
    for seq in [pts,pts[::-1]]:
        chain=[]
        for pt in seq:
            while len(chain)>=2 and cross(chain[-2],chain[-1],pt)<=0:chain.pop()
            chain.append(pt)
        chains.extend(chain[:-1])
    return np.array(chains)

def polyline(s,pts,color=INK,width=.8,dash=False):
    for a,b in zip(pts,pts[1:]):s.line(*a,*b,color,width,dash)

def circle(s,x,y,r,color=INK,width=.8):
    pts=[(x+r*math.cos(t),y+r*math.sin(t)) for t in np.linspace(0,2*math.pi,33)]
    polyline(s,pts,color,width)

def arrow(s,a,b,label=None):
    s.line(*a,*b,ACCENT,1,True)
    v=np.array(b)-a;v=v/max(np.linalg.norm(v),1);n=np.array([-v[1],v[0]])
    for sign in [-1,1]:s.line(*b,*(np.array(b)-v*7+n*sign*3),ACCENT,1)
    if label:s.text(b[0]+8,b[1]-5,label,11)

def hatch(s,x,y,w,h,step=9):
    for k in np.arange(-h,w,step):
        a=max(0,-k);b=min(h,w-k)
        if b>a:s.line(x+k+a,y+h-a,x+k+b,y+h-b,LIGHT,.5)

@lru_cache(maxsize=64)
def cached_edges(vertices,faces):
    pts=feature_edges(vertices,faces)
    return np.asarray([[pts[i],pts[i+1]] for i in range(0,len(pts),3)])

def edges(part):
    return cached_edges(tuple(map(tuple,part['vertices_mm'])),tuple(map(tuple,part['triangles'])))

def panel_basis(part):
    v=np.asarray(part['vertices_mm'],float);origin=v.mean(0)
    _,axes=np.linalg.eigh(np.cov((v-origin).T));q=(v-origin)@axes
    order=np.argsort(np.ptp(q,axis=0))[::-1]
    basis=axes[:,order]
    return origin,basis

def view(s,segments,box,title,dimensions=False,labels=None):
    """All segments already projected to mm; returns paper map and mm scale."""
    x,y,w,h=box;s.text(x,y,title,15)
    data=np.asarray(segments,float)
    lo=data.reshape(-1,2).min(0);hi=data.reshape(-1,2).max(0)
    span=np.maximum(hi-lo,1);scale=min((w-70)/span[0],(h-88)/span[1])
    ox=x+(w-span[0]*scale)/2;oy=y+35+(h-88-span[1]*scale)/2
    def p(q):return (ox+(q[0]-lo[0])*scale,oy+(hi[1]-q[1])*scale)
    seen=set()
    for a,b in data:
        key=tuple(sorted((tuple(np.round(a,3)),tuple(np.round(b,3)))))
        if key in seen or np.linalg.norm(b-a)<.05:continue
        seen.add(key);s.line(*p(a),*p(b),INK,.7)
    if dimensions:
        left,top=p([lo[0],hi[1]]);right,bottom=p([hi[0],lo[1]])
        for xx in [left,right]:s.line(xx,bottom+3,xx,bottom+24,LIGHT,.6)
        s.dimension(left,bottom+19,right,bottom+19,f'{span[0]:.1f}')
        for yy in [top,bottom]:s.line(left-3,yy,left-27,yy,LIGHT,.6)
        s.dimension(left-20,top,left-20,bottom,f'{span[1]:.1f}')
    if labels:
        for q,label in labels:
            px,py=p(q);circle(s,px,py,10);s.rect(px-8,py-7,16,14,'white','white',0);s.text(px-7,py+4,label,9)
    s.text(x,y+h-4,'線稿取自來源網格；尺寸 mm' if dimensions else 'NTS · 等角投影／非透視',10,ACCENT)
    return p,scale

def manufacturing_sheets(geometry,unit,index=0):
    block=geometry['blocks'][unit];part=block['parts'][index]
    meta=dict(layout_name=unit.replace('SKYLARK',''),levels=1,design_id=f'P{index+1:02}')
    s=Sheet('M101','板件正投影與尺寸',meta)
    origin,basis=panel_basis(part);e=(edges(part)-origin)@basis
    view(s,e[:,:,[0,1]],(75,140,690,440),'01  板面正視／孔槽輪廓',True)
    view(s,e[:,:,[0,2]],(75,600,690,145),'02  板厚側視',True)
    view(s,e[:,:,[1,2]],(805,140,315,215),'03  端視',True)
    ext=np.ptp((np.asarray(part['vertices_mm'])-origin)@basis,axis=0)
    notes=[f'板件索引 P{index+1:02}',f"來源名稱 {part['label'][:26]}",
           f'主軸包絡 {ext[0]:.1f} × {ext[1]:.1f}',f'厚度包絡 {ext[2]:.2f} mm',
           '尺寸按來源網格 PCA 主軸量測。','非平板包絡不等同實際板厚。','輪廓保留孔槽；尚未排版或補償。',
           '刀徑、內角、公差須以 CAD 核對。','依據 MFG pp.4–9／來源構件模型。']
    for i,t in enumerate(notes):s.text(805,399+i*28,t,12)
    assembled=Sheet('M201','單元等角圖與板件索引',meta)
    exploded=Sheet('M301','單元拆解圖與組裝對照',meta)
    # Standard isometric projection, equal foreshortening on all three axes.
    iso=np.array([[1/math.sqrt(2),1/math.sqrt(6)],[-1/math.sqrt(2),1/math.sqrt(6)],[0,-2/math.sqrt(6)]])
    # view() flips y, so choose Z upward in drawing coordinates.
    iso[:,1]*=-1
    allv=np.concatenate([np.asarray(p['vertices_mm']) for p in block['parts']]);mid=(allv.min(0)+allv.max(0))/2
    full=[];exp=[];tags=[];extags=[];centers=[]
    for i,p in enumerate(block['parts']):
        ev=edges(p);pc=np.asarray(p['vertices_mm']).mean(0)
        normal=panel_basis(p)[1][:,2]
        if np.dot(normal,pc-mid)<0:normal=-normal
        offset=normal*(300+60*(i%4))
        full.extend(ev@iso);exp.extend((ev+offset)@iso)
        tags.append((pc@iso,f'{i+1:02}'));extags.append(((pc+offset)@iso,f'{i+1:02}'))
        centers.append((pc@iso,(pc+offset)@iso))
    view(assembled,full,(70,150,760,570),'01  完整單元等角線稿',labels=tags)
    mapping,_=view(exploded,exp,(70,150,760,570),'01  板件分離／裝配位置',labels=extags)
    for a,b in centers:polyline(exploded,[mapping(a),mapping(b)],LIGHT,.6,True)
    for sheet in [assembled,exploded]:
        sheet.text(865,151,'板件索引',16)
        for i,p in enumerate(block['parts']):
            if i>=20:break
            sheet.text(865,184+24*i,f"{i+1:02}  {p['label'][:20]}",10)
        sheet.text(865,710,'同一編號對應 2D／等角／拆解。',11)
        sheet.text(70,748,'拆解方向依板件主軸作視覺分離；不表示已驗證的接頭插入方向。',11,ACCENT)
    return [s,assembled,exploded]

def facade_sheet(h):
    s=Sheet('A202','四向立面／模型投影',h)
    for number,(axis,sign,title,box) in enumerate([
        (0,1,'01  正立面 X-Z',(75,145,490,280)),(0,-1,'02  背立面 X-Z',(650,145,490,280)),
        (1,1,'03  側立面 Y-Z',(75,450,490,285)),(1,-1,'04  側立面 Y-Z',(650,450,490,285))]):
        segments=[]
        for it in h['items']:
            if it['category'] in ['partition','stair','guard','trimmer']:continue
            mesh=h['meshes'][it['key']]
            # Exterior projection of each module bounds, not triangulated wireframe.
            vv=np.array([transform(p,it['rotation'],it['translation']) for p in mesh['v']])
            points=np.unique(np.round(vv[:,[axis,2]],3),axis=0)
            if len(points)<3:continue
            poly=convex_hull(points);poly[:,0]*=sign
            segments.extend([[a,b] for a,b in zip(poly,np.roll(poly,-1,axis=0))])
        view(s,segments,box,title,True)
    s.text(75,756,'構件外輪廓疊合投影；未作隱線消除。門窗為洞口配置，非門窗成品詳圖。',11,ACCENT)
    return s

def detail_sheets(h):
    s=Sheet('A502','板件接合詳圖／加工與固定原則',h)
    cells=[(65,145),(635,145),(65,440),(635,440)]
    titles=['J01  板槽乾式插接','J02  壓配試件／厚度與槽寬','J03  螺絲固定剖面原則','J04  內角刀具避空']
    for (x,y),title in zip(cells,titles):
        s.text(x,y,title,16);s.line(x,y+12,x+500,y+12,LIGHT)
    x,y=cells[0]
    s.poly([(x+65,y+120),(x+230,y+120),(x+230,y+145),(x+260,y+145),(x+260,y+120),(x+440,y+120),(x+440,y+167),(x+65,y+167)],'#f0eee9',INK,1.5)
    s.rect(x+232,y+45,26,72,'#e2e9e8',INK,1.5);hatch(s,x+232,y+45,26,72)
    arrow(s,(x+245,y+92),(x+245,y+140));s.dimension(x+230,y+197,x+260,y+197,'槽寬 w')
    s.text(x,y+240,'定位夾具＋木槌；槽寬與實測板厚經首件試配確認。',12)
    x,y=cells[1]
    s.rect(x+80,y+70,130,100,'#f0eee9');s.rect(x+126,y+70,38,75,'white');hatch(s,x+80,y+70,40,100)
    s.rect(x+290,y+45,44,105,'#e2e9e8');s.dimension(x+126,y+195,x+164,y+195,'w');s.dimension(x+290,y+182,x+334,y+182,'t')
    arrow(s,(x+312,y+155),(x+312,y+205),'試配量測')
    s.text(x,y+240,'壓配量 δ＝t－w；數值依材料、加工及試組結果決定。',12)
    x,y=cells[2]
    s.rect(x+65,y+90,370,32,'#e2e9e8',INK,1.5);s.rect(x+155,y+122,190,65,'#f0eee9',INK,1.5)
    hatch(s,x+155,y+122,190,65);s.rect(x+239,y+78,14,86,'white',INK,1.3);s.rect(x+229,y+73,34,8,'white',INK,1.3)
    for yy in range(int(y+105),int(y+163),8):s.line(x+237,yy,x+255,yy+5,INK,.8)
    arrow(s,(x+380,y+50),(x+252,y+78),'固定件');s.dimension(x+155,y+215,x+246,y+215,'邊距 e')
    s.text(x,y+260,'規格、間距、埋入深度與扭矩依結構設計；未定值。',12)
    x,y=cells[3]
    s.rect(x+75,y+65,340,145,'#f0eee9',INK,1.5);s.rect(x+160,y+65,170,94,'white',INK,1.2)
    for xx in [x+160,x+330]:circle(s,xx,y+159,12,INK,1.3)
    arrow(s,(x+400,y+242),(x+342,y+169),'刀具避空')
    s.text(x,y+280,'NTS；圓刀內角避空不是獨立結構接頭。',12)
    s.text(65,756,'本頁均為接合原理 NTS。MFG pp.7–9／USE p.8；不套用未核定的緊固件或公差數值。',11,ACCENT)
    t=Sheet('A503','組裝工具配置與二樓洞口節點',h)
    t.text(70,145,'01  作業工具索引／NTS',17)
    # Line drawings of caliper, mallet, driver and clamp with operation labels.
    for i,(name,stage) in enumerate([('量測卡尺','板厚／槽寬試配'),('木槌與定位治具','乾式敲合與對位'),('電動起子','指定緊固件鎖固'),('夾具','臨時定位與夾持')]):
        x=80+(i%2)*265;y=185+(i//2)*220
        t.rect(x,y,235,190,'white',LIGHT);t.text(x+12,y+24,f'T0{i+1}  {name}',14)
        if i==0:
            t.rect(x+40,y+82,155,12,'#ecf0f1');t.rect(x+55,y+65,10,68,'white');t.rect(x+125,y+64,15,69,'white')
            for k in range(12):t.line(x+65+10*k,y+83,x+65+10*k,y+89,INK,.6)
        elif i==1:
            t.rect(x+105,y+75,15,78,'#f0eee9');t.rect(x+65,y+57,95,38,'#ecf0f1',INK,1.5)
        elif i==2:
            t.poly([(x+55,y+70),(x+145,y+70),(x+145,y+100),(x+120,y+100),(x+125,y+145),(x+95,y+145),(x+87,y+105),(x+55,y+100)],'#ecf0f1',INK,1.5)
            t.line(x+145,y+85,x+193,y+85,INK,3)
        else:
            polyline(t,[(x+65,y+65),(x+65,y+140),(x+155,y+140),(x+155,y+110)],INK,4)
            t.line(x+65,y+75,x+165,y+75,INK,2);t.rect(x+117,y+68,14,36,'white');t.line(x+130,y+85,x+185,y+85,INK,2)
        t.text(x+12,y+174,stage,12)
    t.text(660,145,'J05  樓板／洞口補強概念剖面',17)
    t.rect(690,460,350,35,'#e2e9e8',INK,1.5);t.rect(690,495,110,110,'#f0eee9',INK,1.5);hatch(t,690,495,110,110)
    t.rect(1000,290,18,170,'#ecf0f1',INK,1.5);t.rect(945,280,100,15,'#ecf0f1');t.rect(945,350,100,12,'#ecf0f1')
    arrow(t,(830,240),(1000,290),'臨時護欄');arrow(t,(830,635),(800,550),'洞口補強梁')
    arrow(t,(830,415),(950,460),'樓板邊緣')
    for i,txt in enumerate(['剖面為 NTS 原理圖；無核定截面。','臨時支撐、護欄錨固與承載需專項設計。','依據 DFMA pp.19–21；工具屬作業配置建議。']):t.text(660,675+i*27,txt,12)
    t.text(70,740,'工具以作業類型編碼；品牌、型號與數量依現場條件選定。',12,ACCENT)
    return [s,t]

def enhance_plan(s,h,level):
    scale=min(490/h['length'],680/h['width']);ox=170;oy=170
    def p(x,y):return ox+x*scale,oy+y*scale
    # Reference grids, tied to module dimensions instead of geographic north.
    for i,x in enumerate([0,5436]+([10872] if h['width']>5436 else [])):
        px,_=p(x,0);s.line(px,oy-16,px,oy+h['length']*scale+20,LIGHT,.6,True)
        circle(s,px,oy-57,10);s.text(px-4,oy-53,chr(65+i),11)
    for i,y in enumerate([0,5400,7800,13200]):
        _,py=p(0,y);s.line(ox-18,py,ox+h['width']*scale+18,py,LIGHT,.6,True)
        circle(s,ox-87,py,10);s.text(ox-91,py+4,str(i+1),11)
    interior=h.get('interior',{})
    if interior.get('config',{}).get('floor')==level:
        for d in interior['doors']:
            a=np.asarray(d['a']);b=np.asarray(d['b']);v=b-a;n=np.array([-v[1],v[0]])*d.get('swing_sign',1)
            s.line(*p(*a),*p(*(a+n)),INK,1)
            pts=[p(*(a+v*math.cos(t)+n*math.sin(t))) for t in np.linspace(0,math.pi/2,20)]
            polyline(s,pts,INK,.65)
            s.text(*p(*(a+(v+n)*.45)),d['id'],8)
    arrow(s,(1075,644),(1075,595));s.text(1020,675,'配置上方（非真北）',10)
    s.text(850,700,'粗線：牆體／切面；細線：定位與開口。',11)
    s.text(850,724,'門扇弧為建議開啟方向，待使用者確認。',11)
    return s

def architectural_plan(h,level):
    s=Sheet(f'A10{level}',f'{level}F 平面配置／尺寸與開口定位',h)
    scale=min(650/h['length'],430/h['width']);ox=145;oy=205
    def p(x,y):return ox+y*scale,oy+(h['width']-x)*scale
    def rect(lo,hi,fill='none',stroke=INK,width=1):
        a=p(*lo);b=p(*hi);s.rect(min(a[0],b[0]),min(a[1],b[1]),abs(a[0]-b[0]),abs(a[1]-b[1]),fill,stroke,width)
    for i,j in h['footprint_cells']:rect((i*604,j*600),((i+1)*604,(j+1)*600),'#fbfcfc','#dce2e4',.3)
    interior=h.get('interior',{});active=interior.get('config',{}).get('floor')==level
    if active:
        for r in interior['rooms']:
            x,y,xx,yy=r['box'];rect((x,y),(xx,yy),'#f8faf9','#e0e5e4',.3)
            cx,cy=p((x+xx)/2,(y+yy)/2)
            if interior.get('furniture') and r['id'].startswith('R'):
                cx,cy=p((x+xx)/2,(y+3000+yy-600)/2)
            label=r['name'];label=label[:8] if len(label)>8 else label
            s.text(cx-len(label)*5,cy-6,label,10);s.text(cx-20,cy+9,f"{r['area_m2']:.1f} m²",10)
        for f in interior.get('furniture',[]):
            x,y,xx,yy=f['box'];rect((x,y),(xx,yy),'none','#798b8e',.65)
            if f['kind']=='bed':
                rect((x+80,y+80),(xx-80,y+420),'none','#798b8e',.5)
                s.line(*p(x,y+500),*p(xx,y+500),'#798b8e',.5)
            elif f['kind'] in ['wardrobe','kitchen','shower']:
                s.line(*p(x,y),*p(xx,yy),'#a9b6b8',.5)
            elif f['kind'] in ['wc','basin']:
                circle(s,*p((x+xx)/2,(y+yy)/2),min(xx-x,yy-y)*scale*.3,'#798b8e',.6)
        for it in interior['parts']:
            if not it['header']:rect(it['lo'][:2],it['hi'][:2],'#a5afb2',INK,1)
        for d in interior['doors']:
            a=np.asarray(d['a']);b=np.asarray(d['b']);v=b-a;n=np.array([-v[1],v[0]])*d.get('swing_sign',1)
            s.line(*p(*a),*p(*(a+n)),INK,1)
            polyline(s,[p(*(a+v*math.cos(t)+n*math.sin(t))) for t in np.linspace(0,math.pi/2,20)],INK,.6)
            s.text(*p(*(a+(v+n)*.42)),d['id'],9)
    for it in h['items']:
        if it['level']!=level or it['category'] not in ['wall','door','window','corner']:continue
        v=np.array([transform(q,it['rotation'],it['translation']) for q in h['meshes'][it['key']]['v']]);lo=v.min(0);hi=v.max(0)
        cat=it['category'];rect(lo[:2],hi[:2],'#58676d' if cat in ['wall','corner'] else 'white',INK,1.1)
        if cat=='window':
            mid=(lo+hi)/2
            if hi[0]-lo[0]>hi[1]-lo[1]:s.line(*p(lo[0],mid[1]),*p(hi[0],mid[1]),INK,.7)
            else:s.line(*p(mid[0],lo[1]),*p(mid[0],hi[1]),INK,.7)
        if cat=='door':
            a=p(*lo[:2]);b=p(*hi[:2]);s.line(*a,*b,ACCENT,.6,True)
    if h['stair_opening_mm']:
        x,y,xx,yy=h['stair_opening_mm'];rect((x,y),(xx,yy),'white',INK,1.5)
        for k in range(16):s.line(*p(x,y+k*280),*p(xx,y+k*280),INK,.6)
        arrow(s,p((x+xx)/2,y+250),p((x+xx)/2,yy-250),'UP' if level==1 else 'DN')
    # Grid references and chained setting-out dimensions.
    bottom=oy+h['width']*scale
    for i,y in enumerate([0,5400,7800,13200]):
        px=ox+y*scale;s.line(px,oy-20,px,bottom+20,LIGHT,.5,True)
        circle(s,px,oy-54,10);s.text(px-4,oy-50,str(i+1),11)
    xs=[0,5436]+([10872] if h['width']>5436 else [])
    for i,x in enumerate(xs):
        _,py=p(x,0);s.line(ox-18,py,ox+h['length']*scale+18,py,LIGHT,.5,True)
        circle(s,ox-72,py,10);s.text(ox-76,py+4,chr(65+i),11)
    s.dimension(ox,bottom+60,ox+h['length']*scale,bottom+60,f"{h['length']:.0f}")
    s.dimension(ox-35,oy,ox-35,bottom,f"{h['width']:.0f}")
    for a,b in zip([0,5400,7800],[5400,7800,13200]):
        s.dimension(ox+a*scale,bottom+30,ox+b*scale,bottom+30,f'{b-a:.0f}')
    for y in [0,5400,7800,13200]:s.line(ox+y*scale,bottom+5,ox+y*scale,bottom+66,LIGHT,.6)
    a=p(-300,9300);b=p(h['width']+300,9300);polyline(s,[a,b],ACCENT,1,True)
    for pt in [a,b]:circle(s,*pt,11);s.text(pt[0]-4,pt[1]+4,'B',10)
    s.text(865,145,'圖說與定位基準',16)
    notes=[f"樓層標高 +{(level-1)*h['storey_height_mm']:.0f} mm",'粗線／深填色：牆體切面','細線：尺寸、門扇與構件分格','B-B 剖面：見 A201','門窗表示洞口，非成品設計','圖面採配置座標，未指定真北']
    for i,t in enumerate(notes):s.text(865,180+i*26,t,12)
    y=365;s.text(865,y,'空間／開口索引',15)
    if active:
        for r in interior['rooms']:
            y+=25;s.text(865,y,r['name'][:12],11);s.text(1050,y,f"{r['area_m2']:.1f} m²",11)
        y+=23
        for d in interior['doors']:
            y+=22;s.text(865,y,f"{d['id']}  淨寬 {d['width']:.0f} × 高 2100",11)
    else:s.text(865,y+30,'本層未配置室內隔間。',12)
    s.text(865,680,'門扇弧：建議方向，需確認。',11)
    s.text(865,705,'樓梯洞口 1208 × 4200' if h['stair_opening_mm'] else '尺寸以模型模數與標註為準。',11)
    if active and interior.get('furniture') and h['width']<6000:
        y=max(bottom+105,560);s.text(145,y,'住宅配置與家具尺度',15)
        s.text(145,y+27,'主臥床 1500 × 2000 · 次臥床 1000 × 2000 · 衣櫃深 600 · 廚具深 600 mm',11)
        s.text(145,y+51,'衛浴約 4.5 m²；薄線家具用於通行、門扇與使用尺度檢視，不列入結構材料數量。',11)
        s.text(145,y+75,'非承重隔間配置建議；採光、通風、機電、防水與法規符合性需依基地深化。',11,ACCENT)
    s.line(ox,736,ox+2000*scale,736,INK,3);s.text(ox,755,'0',10);s.text(ox+2000*scale-12,755,'2000 mm',10)
    return s

def section_sheet(h):
    s=Sheet('A201','B-B 橫向剖面／樓層與裝配對照',h)
    cut_y=9300.01;segments=[]
    for it in h['items']:
        mesh=h['meshes'][it['key']];v=np.asarray(mesh['v'],float)
        angle=math.radians(it['rotation']);c=math.cos(angle);sn=math.sin(angle)
        v=v@np.array([[c,sn,0],[-sn,c,0],[0,0,1]])+np.array(it['translation'])
        tri=v[np.asarray(mesh['f'],int)]
        crossing=tri[(tri[:,:,1].min(1)<cut_y)&(tri[:,:,1].max(1)>cut_y)]
        for face in crossing:
            pts=[]
            for a,b in zip(face,np.roll(face,-1,axis=0)):
                if (a[1]-cut_y)*(b[1]-cut_y)<0:
                    q=a+(b-a)*(cut_y-a[1])/(b[1]-a[1]);pts.append(q[[0,2]])
            if len(pts)==2:segments.append(pts)
    mapping,scale=view(s,segments,(95,150,620,575),'01  B-B 模型實際切面 · Y＝9300',True)
    for l in range(h['levels']):
        z=l*h['storey_height_mm'];x,y=mapping([h['width'],z])
        s.line(x,y,x+65,y,ACCENT,.8);s.text(x+8,y-7,f'{l+1}F +{z:.0f}',11)
    s.text(785,155,'逐層裝配順序',17)
    steps=['1F 樓板','1F 室內隔間 → 外牆']
    if h['levels']==2:steps+=['洞口補強／2F 樓板','樓梯與臨時防護','2F 室內隔間 → 外牆']
    steps+=['山牆封板 → 屋頂']
    for i,t in enumerate(steps):
        y=192+i*51;s.rect(780,y-22,340,38,'#f3f7f7','#d8e2e3',.7);s.text(794,y+2,f'{i+1:02}  {t}',13)
    for i,t in enumerate(['本剖面由同一模型切取，保留構件厚度。','配置隔間只出現在使用者選定樓層。','各層展示前須具備支承與臨時穩定措施。','屋面、防水與機電構造尚未納入模型。']):s.text(780,575+i*29,t,11)
    s.text(95,752,'切面粗細依網格輪廓；構件尺寸供協調。接頭與結構承載須以詳設文件確認。',11,ACCENT)
    return s
