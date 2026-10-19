"""Residential planning presets; dimensions are design targets, not code approval."""
import math

def preset(name='two_bed',levels=1,floor=1):
    from .interior import DEFAULT
    return {**DEFAULT,'planning':'residential','preset':name,'planning_version':11,
        'bedrooms':2 if name=='two_bed' else 1,'common_end':8400 if levels==2 else 7200,
        'corridor':1200,'door_width':900,'door_offset':0,'split_ratio':50.,'floor':min(floor,levels),
        'room_names':['主臥室','次臥室','彈性工作區']}

def residential(c,levels):
    parts=[];doors=[];rooms=[];furniture=[];height=2400.;t=100.
    x0,x1,y0,y1=318.,5118.,318.,12882.;front=8400. if levels==2 else 7200.
    def wall(a,b,label,gate=False):
        length=math.dist(a,b)
        if length<1:return
        n=math.ceil(length/1200)
        for i in range(n):
            p=[a[k]+(b[k]-a[k])*i/n for k in range(2)];q=[a[k]+(b[k]-a[k])*(i+1)/n for k in range(2)]
            vertical=abs(q[0]-p[0])<1
            lo=[min(p[0],q[0])-(t/2 if vertical else 0),min(p[1],q[1])-(0 if vertical else t/2),0]
            hi=[max(p[0],q[0])+(t/2 if vertical else 0),max(p[1],q[1])+(0 if vertical else t/2),height]
            parts.append(dict(id=f'P{len(parts)+1:03}',lo=lo,hi=hi,a=p,b=q,label=label,gate=gate,header=False))
    def opening(a,b,at,width,label,sign=1,gate=False):
        length=math.dist(a,b);u=[(b[k]-a[k])/length for k in range(2)]
        p=[a[k]+u[k]*(at-width/2) for k in range(2)];q=[a[k]+u[k]*(at+width/2) for k in range(2)]
        wall(a,p,label,gate);wall(q,b,label,gate);v=abs(u[1])>.5
        parts.append(dict(id=f'P{len(parts)+1:03}',lo=[p[0]-(50 if v else 0),p[1]-(0 if v else 50),2100],
            hi=[q[0]+(50 if v else 0),q[1]+(0 if v else 50),2400],a=p,b=q,label=label+' 門楣',gate=gate,header=True))
        doors.append(dict(id=f'D{len(doors)+1:02}',a=p,b=q,width=width,label=label,swing_sign=sign))
    def room(uid,name,box,target):
        a,b,d,e=box;area=(d-a)*(e-b)/1e6
        rooms.append(dict(id=uid,name=name,box=box,min_area=target,level=c['floor'],area_m2=round(area,3),
                          meets_area=area>=target,clear_width_mm=min(d-a,e-b)))
    def furniture_item(name,box,z,kind):furniture.append(dict(name=name,box=box,height_mm=z,kind=kind))
    # Wet core remains to the right of the stair, leaving >1200 mm circulation.
    opening([3150,4250],[3150,6700],1000,800,'衛浴入口',sign=-1)
    wall([3150,4250],[x1,4250],'衛浴前牆');wall([3150,6700],[x1,6700],'衛浴後牆')
    room('BATH','衛浴',[3200,4300,x1,6650],4.)
    if c['bedrooms']==2:
        split=(x0+x1)/2
        opening([x0,front],[split,front],1700,900,'主臥入口',gate=True)
        opening([split,front],[x1,front],1200,900,'次臥入口',gate=True)
        wall([split,front],[split,y1],'臥室分界')
        room('R1','主臥室',[x0,front+50,split-50,y1],10.)
        room('R2','次臥室',[split+50,front+50,x1,y1],10.)
    else:
        opening([x0,front],[x1,front],3500,900,'主臥入口',gate=True)
        room('R1','主臥／彈性工作區',[x0,front+50,x1,y1],16.)
    # Public area excludes the wet core envelope and, when present, stair opening.
    room('COMMON','客餐廳／開放廚房',[x0,y0,x1,front-50],18.)
    common=rooms[-1];common['exclusion_boxes']=[[3100,4200,x1,6750]]
    if levels==2:common['exclusion_boxes'].append([604,3000,1812,7200])
    common['area_m2']=round(common['area_m2']-sum((b[2]-b[0])*(b[3]-b[1])/1e6 for b in common['exclusion_boxes']),3)
    common['meets_area']=common['area_m2']>=common['min_area']
    # Furniture is a fit check and is excluded from the structural BOM/cost model.
    for r in rooms:
        if not r['id'].startswith('R'):continue
        a,b,d,e=r['box'];bedwidth=1500 if r['id']=='R1' else 1000
        furniture_item('雙人床' if bedwidth==1500 else '單人床',[a+100,b+1000,a+100+bedwidth,b+3000],450,'bed')
        furniture_item('衣櫃',[a+150,e-600,min(d-150,a+1950),e],2100,'wardrobe')
        if c['bedrooms']==1:furniture_item('工作桌',[d-650,b+500,d,b+1700],750,'desk')
    furniture_item('沙發',[500,1250,2400,2050],750,'sofa')
    furniture_item('餐桌',[2850,1750,3650,2950],750,'table')
    furniture_item('廚具／水槽',[3250,318,5050,918],850,'kitchen')
    furniture_item('淋浴區',[4118,5650,5118,6650],100,'shower')
    furniture_item('馬桶',[4300,4450,5000,5200],450,'wc')
    furniture_item('洗手台',[3350,4300,3900,4800],800,'basin')
    area=sum(math.dist(p['a'],p['b'])*(p['hi'][2]-p['lo'][2])/1e6 for p in parts)
    return dict(config=c,parts=parts,doors=doors,rooms=[common]+[r for r in rooms if r is not common],furniture=furniture,wall_area_m2=area,skin_area_m2=area*2,
        obstacle_mm=[604,2940,1872,7360] if levels==2 else None,
        scope='住宅空間配置建議：臥室、客餐廳、廚房與衛浴；家具與衛浴為尺度檢視，不納入結構材料／成本。',
        planning_notes=['取消長走道分割；臥室由前側公共動線進入。',
            '兩房以主臥雙人床、次臥單人床配置；衛浴約 4.5 m²。',
            '二樓方案保留既有樓梯與洞口，濕區設於右側；相鄰淨通道約 1.23 m。',
            '10 m² 臥室、18 m² 公共區為本方案設計目標；採光、通風、消防與無障礙另需專業核對。'])
