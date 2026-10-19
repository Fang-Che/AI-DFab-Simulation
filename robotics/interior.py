"""Parameterized non-loadbearing infill. Millimetres; no structural edits."""
import copy, hashlib, json, math
from collections import Counter
from .import_geometry import box_mesh

DEFAULT = dict(enabled=True, bedrooms=2, common_end=7800, corridor=1500,
               door_width=900, door_offset=0, split_ratio=50.5, floor=1,
               lock_common=False, lock_door=False,room_names=['臥室 1','臥室 2','書房'])

def validate(config, levels=1):
    c={**DEFAULT, **config}
    if c['bedrooms'] not in [1,2,3] or c['floor'] not in range(1,levels+1):
        raise ValueError('房間數或樓層無效')
    if not isinstance(c['room_names'],list) or len(c['room_names'])!=3 or not all(isinstance(n,str) and 0<len(n.strip())<=16 for n in c['room_names']):
        raise ValueError('三個空間名稱各需 1–16 字')
    for k,lo,hi in [('common_end',4800,8400),('corridor',1200,1800),('door_width',700,1400),('door_offset',-100,100),('split_ratio',35,65)]:
        if not isinstance(c[k],(int,float)) or not math.isfinite(c[k]) or not lo<=c[k]<=hi:
            raise ValueError(f'{k} 超出允許範圍')
    if c['door_width']>c['corridor']-100:raise ValueError('門寬需比走道寬至少小 100 mm')
    if abs(c['door_offset'])+c['door_width']/2>c['corridor']/2-50:raise ValueError('門位偏移超過走道邊界')
    if levels==2 and c['common_end']<7800:raise ValueError('二層方案公共區分界至少 7800 mm，以保留既有樓梯區')
    return c

def layout(config, levels=1):
    c=validate(config,levels);parts=[];doors=[];rooms=[]
    if not c['enabled']:return dict(config=c,parts=[],doors=[],rooms=[],wall_area_m2=0.,skin_area_m2=0.)
    if c.get('planning')=='residential':
        from .housing_plan import residential
        return residential(c,levels)
    x0,x1,y0,y1=318.,5118.,318.,12882.;yc=c['common_end'];xc=x1-c['corridor'];t=100.;height=2400.
    def wall(a,b,name,gate=False):
        length=math.dist(a,b);n=max(1,math.ceil(length/1200))
        for i in range(n):
            p=[a[k]+(b[k]-a[k])*i/n for k in range(2)];q=[a[k]+(b[k]-a[k])*(i+1)/n for k in range(2)]
            vertical=abs(q[0]-p[0])<1
            lo=[min(p[0],q[0])-(t/2 if vertical else 0),min(p[1],q[1])-(0 if vertical else t/2),0]
            hi=[max(p[0],q[0])+(t/2 if vertical else 0),max(p[1],q[1])+(0 if vertical else t/2),height]
            parts.append(dict(id=f'P{len(parts)+1:03}',lo=lo,hi=hi,a=p,b=q,label=name,gate=gate,header=False))
    def opening(a,b,center,width,name,gate=False):
        length=math.dist(a,b);u=[(b[k]-a[k])/length for k in range(2)]
        p=[a[k]+u[k]*(center-width/2) for k in range(2)];q=[a[k]+u[k]*(center+width/2) for k in range(2)]
        wall(a,p,name,gate);wall(q,b,name,gate)
        v=abs(u[1])>.5
        lo=[min(p[0],q[0])-(t/2 if v else 0),min(p[1],q[1])-(0 if v else t/2),2100]
        hi=[max(p[0],q[0])+(t/2 if v else 0),max(p[1],q[1])+(0 if v else t/2),height]
        parts.append(dict(id=f'P{len(parts)+1:03}',lo=lo,hi=hi,a=p,b=q,label=name+' 門楣',gate=gate,header=True))
        doors.append(dict(id=f'D{len(doors)+1:02}',a=p,b=q,width=width,label=name))
    opening([x0,yc],[x1,yc],xc+c['corridor']/2+c['door_offset']-x0,c['door_width'],'公共區分界',True)
    if c['bedrooms']==2:ys=[yc,yc+(y1-yc)*c['split_ratio']/100,y1]
    else:ys=[yc+(y1-yc)*i/c['bedrooms'] for i in range(c['bedrooms']+1)]
    for i,(a,b) in enumerate(zip(ys,ys[1:])):
        width=min(c['door_width'],b-a-200)
        opening([xc,a],[xc,b],(b-a)/2,width,f'房間 {i+1} 入口')
        if i:wall([x0,a],[xc,a],'房間分界')
        rooms.append(dict(id=f'R{i+1}',name=c['room_names'][i],box=[x0,yc+50 if i==0 else a+50,xc-50,b-50 if i<len(ys)-2 else b],
                          min_area=8.,level=c['floor']))
    rooms.insert(0,dict(id='COMMON',name='客餐廳／開放公共區',box=[x0,y0,x1,yc-50],min_area=18.,level=c['floor']))
    rooms.append(dict(id='HALL',name='走道',box=[xc+50,yc+50,x1,y1],min_area=0.,level=c['floor']))
    for r in rooms:
        a,b,d,e=r['box'];area=(d-a)*(e-b)/1e6
        if r['id']=='COMMON' and levels==2:area-=1.208*4.2
        r['area_m2']=round(area,3);r['meets_area']=area>=r['min_area']
    area=sum(math.dist(p['a'],p['b'])*(p['hi'][2]-p['lo'][2])/1e6 for p in parts)
    return dict(config=c,parts=parts,doors=doors,rooms=rooms,wall_area_m2=area,skin_area_m2=2*area,
                obstacle_mm=[604,2940,1872,7360] if levels==2 else None,
                scope='主屋指定樓層的非承重隔間；側翼保留開放，未配置衛浴設備、機電或結構接頭')

def apply(house, config):
    interior=layout(config,house['levels']);h=dict(house);h['meshes']=dict(house['meshes']);h['items']=[dict(i) for i in house['items']]
    h['interior']=interior;h['design_id']=hashlib.sha256(json.dumps([house['layout'],house['levels'],interior['config']],sort_keys=True).encode()).hexdigest()[:10]
    for p in interior['parts']:
        key='infill_'+p['id'];v,f=box_mesh([p['lo'],p['hi']]);h['meshes'][key]=dict(v=v,f=f)
        h['items'].append(dict(id='IN-'+p['id'],key=key,category='partition',rotation=0,
                               translation=[0,0,(config['floor']-1)*house['storey_height_mm']],level=config['floor'],
                               label=p['label']+'（非承重示意）',evidence='interior_concept',panel_area_m2=2*math.dist(p['a'],p['b'])*(p['hi'][2]-p['lo'][2])/1e6))
    h['category_counts']=dict(Counter(i['category'] for i in h['items']))
    h['time_estimate']=dict(house['time_estimate']);te=h['time_estimate']
    te['hours']=te['setup_hours']+len(h['items'])*te['minutes_per_item']/60/te['efficiency'];te['days']=te['hours']/te['hours_per_day']
    from .construction import sequence
    return sequence(h)

def suggestions(config, levels=1):
    """Explicit alternatives, respecting locked dimensions."""
    c=validate(config,levels);out=[]
    if c.get('planning')=='residential':return out
    if not c['lock_door'] and c['door_width']<1400 and c['corridor']>=1500:
        n={**c,'door_width':1400,'door_offset':0}
        out.append(dict(title='增加內門淨寬至 1400 mm',reason='改善模擬底座與格網保守淨空；門楣與門片需另設計',config=n))
    if not c['lock_common'] and c['common_end']>7800 and c['bedrooms']>=2:
        out.append(dict(title='公共區分界移至 7800 mm',reason='增加後側房間面積；客餐廳面積減少',config={**c,'common_end':7800}))
    return out
