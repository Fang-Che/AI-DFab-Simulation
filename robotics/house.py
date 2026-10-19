"""Reference-inspired gable house and connected L/U footprint studies."""
import math
import numpy as np
from itertools import product
from collections import Counter
from .core import ROOT,read_json,transform
from .import_geometry import box_mesh

def house_demo(geometry,layout='rectangle',minutes=12.,setup_hours=4.,efficiency=.75,hours_day=8.,levels=1):
    from .assembly import pack_block
    extra=read_json(ROOT/'robotics/assets/demo_geometry.json')
    gable=read_json(ROOT/'robotics/assets/gable_geometry.json')
    blocks={**geometry['blocks'],**extra['blocks'],**gable['blocks']}
    meshes={k:pack_block(blocks[k]) for k in ['SKYLARK250_FLOOR-M-0','SKYLARK250_WALL-M','SKYLARK250_ROOF-M42']}
    items=[];dx=604.;dy=600.;width=5436.;length=13200.;eave=2400.;pitch=42.
    if layout not in ['rectangle','L','U']:raise ValueError('Unknown layout')
    if levels not in [1,2]:raise ValueError('One or two levels only')
    cells={(i,j) for i in range(9 if layout=='rectangle' else 18) for j in range(22)
           if i<9 or j<9 or (layout=='U' and j>=13)}
    def add(key,category,rotation=0,translation=None,label=None,evidence='source_mesh'):
        items.append({'id':f'H{len(items)+1:03d}','key':key,'category':category,'rotation':rotation,
                      'translation':translation or [0,0,0],'label':label or category,'evidence':evidence})
    def custom(v,f,cat,label):
        key=f'custom_{len(items)}';meshes[key]={'v':v,'f':f};add(key,cat,label=label,evidence='parametric_concept')
    def block(lo,hi,cat,label):custom(*box_mesh([lo,hi]),cat,label)
    for j in range(22):
        add('SKYLARK250_FLOOR-M-0','floor',-90,[0,j*dy,0],'來源樓板 · 主屋')
        if (9,j) in cells:add('SKYLARK250_FLOOR-M-0','floor',-90,[width,j*dy,0],'來源樓板 · 側翼')
    # Boundary edges only: connected wings have no duplicate interior walls.
    edges=[]
    for i,j in sorted(cells):
        for ni,nj,a,b,rot in [(i,j-1,(i,j),(i+1,j),0),(i+1,j,(i+1,j),(i+1,j+1),90),
                             (i,j+1,(i+1,j+1),(i,j+1),180),(i-1,j,(i,j+1),(i,j),270)]:
            if (ni,nj) not in cells:edges.append((a,b,rot))
    incoming={b:rot for a,b,rot in edges};outgoing={a:rot for a,b,rot in edges}
    for point,rot in outgoing.items():
        if incoming[point]!=rot:
            x,y=point[0]*dx,point[1]*dy
            # Small corner core, inside the occupied neighbouring cell.
            inside=next((i,j) for i,j in [(point[0],point[1]),(point[0]-1,point[1]),(point[0],point[1]-1),(point[0]-1,point[1]-1)] if (i,j) in cells)
            cx=x+90*(1 if inside[0]==point[0] else -1);cy=y+90*(1 if inside[1]==point[1] else -1)
            block([cx-90,cy-90,0],[cx+90,cy+90,eave],'corner','轉角核心（接點待深化）')
    for a,b,rot in edges:
        x0,y0=a[0]*dx,a[1]*dy;x1,y1=b[0]*dx,b[1]*dy
        # Repeated openings along outer long facades and the front gable.
        opening=None;idx=min(a[1],b[1]) if rot in [90,270] else min(a[0],b[0])
        if rot==90 and idx in [3,4]:opening='door'
        elif rot in [90,270] and idx in [9,10,16,17]:opening='window'
        elif rot==0 and idx%9 in [3,4]:opening='window'
        if opening:
            # Box assembly in the same local coordinate convention as WALL-M.
            vv=[];ff=[]
            pieces=[([-600,0,2100],[0,318,2400])]
            if opening=='window':pieces.append(([-600,0,0],[0,318,900]))
            side=-600 if idx in [3,9,16] or (rot==0 and idx%9==3) else -36
            pieces.append(([side,0,0],[side+36,318,2100]))
            for lo,hi in pieces:
                v,f=box_mesh([lo,hi]);offset=len(vv);vv.extend(transform(p,rot,[x1,y1,0]) for p in v);ff.extend([[k+offset for k in face] for face in f])
            custom(vv,ff,opening,'門洞模組' if opening=='door' else '窗洞模組')
        else:add('SKYLARK250_WALL-M','wall',rot,[(x0+x1)/2,(y0+y1)/2,0],'來源 WALL-M 牆模組')
    # A second level is a design study: openings and trimmers are not source kits.
    ground_items=[dict(it,translation=list(it['translation']),level=1) for it in items]
    for it in items:it['level']=1
    stair_opening=None;storey_height=2780.
    if levels==2:
        stair_opening=[604.,3000.,1812.,7200.]
        for it in ground_items:
            if it['category']!='floor':continue
            x,y,_=it['translation']
            if x==0 and 3000<=y<7200:
                for lo,hi in [(0,604),(1812,width)]:
                    block([lo,y,2400],[hi,y+600,2780],'floor','2F 樓梯洞旁樓板（非標準模組）');items[-1]['level']=2
            else:
                new=dict(it,translation=[x,y,storey_height],level=2,label='2F '+it['label']);items.append(new)
        # Trimmer volumes indicate the load path requiring engineering design.
        for lo,hi in [([544,2940,2400],[604,7260,2780]),([1812,2940,2400],[1872,7260,2780]),
                      ([604,2940,2400],[1812,3000,2780]),([604,7200,2400],[1812,7260,2780])]:
            block(lo,hi,'trimmer','樓梯洞補強梁（尺寸暫定）');items[-1]['level']=2
        for s in range(1,16):
            z=storey_height*s/16
            block([604,3000+(s-1)*280,z-36],[1812,3000+s*280,z],'stair',f'樓梯踏步 {s:02d}（示意）');items[-1]['level']=1
        for x in [604.,1812.]:
            for y in [3000.,4400.,5800.,7200.]:
                block([x-20,y-20,2780],[x+20,y+20,3880],'guard','樓梯洞臨時護欄立柱（示意）');items[-1]['level']=2
            block([x-20,3000,3840],[x+20,7200,3880],'guard','樓梯洞臨時護欄橫桿（示意）');items[-1]['level']=2
        # Upper walls follow the same perimeter; ground doors become upper windows.
        for it in ground_items:
            if it['category']=='floor':continue
            new=dict(it,translation=[it['translation'][0],it['translation'][1],storey_height],level=2,label='2F '+it['label'])
            if it['category']=='door':
                # Add a sill to remove the ground-level exterior doorway upstairs.
                src=meshes[it['key']];v=list(src['v']);f=list(src['f']);lo=np.min(v,axis=0);hi=np.max(v,axis=0)
                sv,sf=box_mesh([[lo[0],lo[1],0],[hi[0],hi[1],900]])
                offset=len(v);v+=sv;f+=[[n+offset for n in face] for face in sf]
                key='upper_'+it['key'];meshes[key]={'v':v,'f':f};new.update(key=key,category='window',label='2F 窗洞模組')
            items.append(new)
        eave+=storey_height
    slope=math.tan(math.radians(pitch))
    def roof_z(x,y):
        values=[]
        if x<=width+1e-5:values.append(eave+slope*max(0,width/2-abs(x-width/2)))
        if layout!='rectangle' and y<=5400+1e-5:values.append(eave+slope*max(0,2700-abs(y-2700)))
        if layout=='U' and y>=7800-1e-5:values.append(eave+slope*max(0,2700-abs(y-10500)))
        return max(values or [eave])
    # Close exposed gables, keeping all closure elements ahead of roof placement.
    for a,b,rot in edges:
        x0,y0=a[0]*dx,a[1]*dy;x1,y1=b[0]*dx,b[1]*dy
        h0,h1=roof_z(x0,y0),roof_z(x1,y1)
        if max(h0,h1)<=eave+.1:continue
        # A thin wall wedge, procedural and explicitly labelled.
        angle=math.radians(rot);nx=-math.sin(angle)*180;ny=math.cos(angle)*180
        v=[[x0,y0,eave],[x1,y1,eave],[x1,y1,h1],[x0,y0,h0],
           [x0+nx,y0+ny,eave],[x1+nx,y1+ny,eave],[x1+nx,y1+ny,h1],[x0+nx,y0+ny,h0]]
        custom(v,[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[3,2,6],[3,6,7],[0,3,7],[0,7,4],[1,5,6],[1,6,2]],'closure','山牆封板（參數化）')
    if layout=='rectangle':
        for j in range(22):
            add('SKYLARK250_ROOF-M42','roof',0,[0,j*dy,eave],'來源 ROOF-M42 · 左坡')
            add('SKYLARK250_ROOF-M42','roof',180,[width,(j+1)*dy,eave],'來源 ROOF-M42 · 右坡')
    else:
        # Two triangles per roof cell; add ridge grid lines to retain sharp ridges.
        roof_groups={}
        for i,j in sorted(cells):
            xs=sorted({i*dx,(i+1)*dx}|({width/2} if i*dx<width/2<(i+1)*dx else set()))
            ys=sorted({j*dy,(j+1)*dy}|{r for r in [2700,10500] if j*dy<r<(j+1)*dy})
            v=[];f=[]
            for x0,x1 in zip(xs,xs[1:]):
                for y0,y1 in zip(ys,ys[1:]):
                    pts=[[x0,y0,roof_z(x0,y0)],[x1,y0,roof_z(x1,y0)],[x1,y1,roof_z(x1,y1)],[x0,y1,roof_z(x0,y1)]]
                    off=len(v);v.extend(pts);v.extend([[x,y,z+180] for x,y,z in pts]);f.extend([[off+k for k in face] for face in [[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]]])
            group=roof_groups.setdefault((j,i//9,(i%9)//5),{'v':[],'f':[]})
            offset=len(group['v']);group['v'].extend(v);group['f'].extend([[offset+k for k in face] for face in f])
        for group in roof_groups.values():custom(group['v'],group['f'],'roof','交叉雙坡屋頂模組（屋谷與接頭待深化）')
    for i,it in enumerate(items):
        it['id']=f'H{i+1:03d}'
        it.setdefault('level',levels)
    # Dimensions come from displayed geometry, including teeth/eaves and floor depth.
    lows=[float('inf')]*3;highs=[float('-inf')]*3
    mesh_bounds={k:(np.min(v['v'],axis=0),np.max(v['v'],axis=0)) for k,v in meshes.items()}
    for item in items:
        lo,hi=mesh_bounds[item['key']]
        for p in product(*zip(lo,hi)):
            p=transform(p,item['rotation'],item['translation'])
            for k in range(3):lows[k]=min(lows[k],p[k]);highs[k]=max(highs[k],p[k])
    counts=dict(Counter(i['category'] for i in items));productive=len(items)*float(minutes)/60
    elapsed=float(setup_hours)+productive/float(efficiency)
    return {'mode':'house','layout':layout,'layout_name':{'rectangle':'矩形','L':'L 型','U':'凹型 / U 型'}[layout],
            'meshes':meshes,'items':items,'width':width*(1 if layout=='rectangle' else 2),'length':length,
            'levels':levels,'storey_height_mm':storey_height,'stair_opening_mm':stair_opening,
            'floor_area_m2':len(cells)*dx*dy/1e6*levels-(1.208*4.2 if levels==2 else 0),
            'design_status':'research_concept_not_structurally_validated',
            'bounds_mm':[lows,highs],'dimensions_m':{'width':(highs[0]-lows[0])/1000,'length':(highs[1]-lows[1])/1000,'height':(highs[2]-lows[2])/1000},
            'footprint_cells':sorted(cells),'footprint_area_m2':len(cells)*dx*dy/1e6,'boundary_edges':edges,
            'roof_pitch_deg':pitch,'category_counts':counts,'schedule_basis':'illustrative_sequential_single_crew',
            'time_estimate':{'scope':'現場構架定位與裝配；不含基礎、工廠加工、運輸、機電、裝修及養護',
                             'minutes_per_item':float(minutes),'setup_hours':float(setup_hours),'efficiency':float(efficiency),
                             'hours_per_day':float(hours_day),'hours':elapsed,'days':elapsed/float(hours_day)},
            'sources':geometry['sources']+extra['sources']+gable['sources']}
