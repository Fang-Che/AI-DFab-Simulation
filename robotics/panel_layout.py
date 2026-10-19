"""Rigid, conservative flat-panel packing. No CAM compensation or part resizing."""
import json,math
import numpy as np
from .technical_drawings import edges,panel_basis,INK,LIGHT
from .drawings import Sheet

def flatten(part):
    origin,basis=panel_basis(part)
    e=(edges(part)-origin)@basis
    # Minimum-area rectangle in the board plane avoids PCA skew in asymmetric parts.
    points=e[:,:,:2].reshape(-1,2)
    from .technical_drawings import convex_hull
    hull=convex_hull(points);best=None
    for a,b in zip(hull,np.roll(hull,-1,axis=0)):
        v=b-a;n=np.linalg.norm(v)
        if n<.01:continue
        u=v/n;rot=np.array([[u[0],-u[1]],[u[1],u[0]]]);q=points@rot
        lo=q.min(0);size=q.max(0)-lo;area=float(np.prod(size))
        if best is None or area<best[0]:best=(area,rot,lo,size)
    _,rot,lo,size=best
    projected=e[:,:,:2]@rot-lo
    thick=float(np.ptp(e[:,:,2]));size=np.maximum(size,0)
    # Deduplicate opposite faces; retain inner holes and slots in projection.
    unique={}
    for a,b in projected:
        if np.linalg.norm(a-b)<.05:continue
        key=tuple(sorted((tuple(np.round(a,3)),tuple(np.round(b,3)))))
        unique[key]=[a.tolist(),b.tolist()]
    return dict(size=size.tolist(),thickness_mm=thick,segments=list(unique.values()))

def pack(geometry,unit,stock=(1220.,2440.),gap=6.,margin=10.):
    parts=[];unplaced=[];boards=[]
    for i,p in enumerate(geometry['blocks'][unit]['parts']):
        q=flatten(p);q.update(id=f'P{i+1:02}',source_id=p.get('part_id',str(i)),label=p.get('label',''))
        if q['thickness_mm']>35:
            q['reason']='非單一平板或厚度包絡超過 35 mm，須回 CAD 拆分';unplaced.append(q)
        elif not any(w<=stock[0]-2*margin+.01 and h<=stock[1]-2*margin+.01 for w,h in [q['size'],q['size'][::-1]]):
            q['reason']='超出所選原板尺寸；保留原尺度，未縮放或任意切段';unplaced.append(q)
        else:parts.append(q)
    for q in sorted(parts,key=lambda x:-math.prod(x['size'])):
        best=None
        for bi,board in enumerate(boards):
            for free in board['free']:
                for turn in [0,1]:
                    w,h=q['size'][::(-1 if turn else 1)];rw,rh=w+gap,h+gap
                    if rw<=free[2]+.01 and rh<=free[3]+.01:
                        score=(min(free[2]-rw,free[3]-rh),max(free[2]-rw,free[3]-rh),bi)
                        if best is None or score<best[0]:best=(score,bi,free[0],free[1],w,h,turn)
        if best is None:
            boards.append(dict(free=[[margin,margin,stock[0]-2*margin+gap,stock[1]-2*margin+gap]],parts=[]))
            w,h=q['size'];turn=0
            if w>stock[0]-2*margin:w,h=h,w;turn=1
            best=(None,len(boards)-1,margin,margin,w,h,turn)
        _,bi,x,y,w,h,turn=best;board=boards[bi];used=[x,y,w+gap,h+gap];new=[]
        for a,b,fw,fh in board['free']:
            if x>=a+fw or x+w+gap<=a or y>=b+fh or y+h+gap<=b:new.append([a,b,fw,fh]);continue
            if x>a:new.append([a,b,x-a,fh])
            if x+w+gap<a+fw:new.append([x+w+gap,b,a+fw-x-w-gap,fh])
            if y>b:new.append([a,b,fw,y-b])
            if y+h+gap<b+fh:new.append([a,y+h+gap,fw,b+fh-y-h-gap])
        board['free']=[f for i,f in enumerate(new) if f[2]>.01 and f[3]>.01 and not any(j!=i and g[0]<=f[0] and g[1]<=f[1] and g[0]+g[2]>=f[0]+f[2] and g[1]+g[3]>=f[1]+f[3] and (g!=f or j<i) for j,g in enumerate(new))]
        seg=np.asarray(q['segments'])
        if turn:seg=np.stack([q['size'][1]-seg[:,:,1],seg[:,:,0]],axis=-1)
        placed={**q,'sheet':bi+1,'rotation_deg':90*turn,'bounds':[x,y,x+w,y+h],'segments':(seg+[x,y]).tolist()}
        board['parts'].append(placed)
    return dict(unit=unit,stock_mm=list(stock),gap_mm=gap,margin_mm=margin,boards=[{'parts':b['parts']} for b in boards],unplaced=unplaced,
        source_part_count=len(geometry['blocks'][unit]['parts']),basis='來源網格板面剛體投影、外框保守排版；非 CNC 刀路，未計刀徑與固定橋。')

def sheets(data):
    pages=[];meta=dict(layout_name=data['unit'],levels=1,design_id='FLAT-R11')
    boards=data['boards'];sw,sh=data['stock_mm']
    for start in range(0,max(1,len(boards)),3):
        s=Sheet(f'M{401+start//3}','單元平面放樣板／原尺度排版',meta)
        s.text(65,140,f"全部 {data['source_part_count']} 件 · 已排 {sum(len(b['parts']) for b in boards)} 件 · 待處理 {len(data['unplaced'])} 件",14)
        for col,b in enumerate(boards[start:start+3]):
            scale=min(300/sw,500/sh);ox=90+col*365;oy=200
            s.text(ox,177,f'原板 {start+col+1:02} · {sw:.0f} × {sh:.0f}',14)
            s.rect(ox,oy,sw*scale,sh*scale,'white',INK,1)
            for p in b['parts']:
                for a,c in p['segments']:s.line(ox+a[0]*scale,oy+a[1]*scale,ox+c[0]*scale,oy+c[1]*scale,'#222222',.55)
                x,y,xx,yy=p['bounds'];cx=ox+(x+xx)*scale/2;cy=oy+(y+yy)*scale/2
                s.rect(cx-15,cy-9,30,14,'white','white',0);s.text(cx-13,cy+2,p['id'],9)
            s.dimension(ox,oy+sh*scale+24,ox+sw*scale,oy+sh*scale+24,f'{sw:.0f}')
        if not boards:s.text(90,250,'本單元無可直接放入所選原板的平板，請檢查待處理索引。',17)
        s.text(65,751,f"板邊預留 {data['margin_mm']:.0f} mm · 板件間距 {data['gap_mm']:.0f} mm · 未依孔洞互嵌最佳化；DXF 單位 mm。",12)
        pages.append(s)
    allparts=[p for b in boards for p in b['parts']]+data['unplaced']
    for start in range(0,len(allparts),18):
        s=Sheet(f'M{451+start//18}','單元板件索引／放樣核對',meta)
        s.text(65,145,'編號       板面包絡 mm                厚度包絡 mm       原板／待處理',14)
        for i,p in enumerate(allparts[start:start+18]):
            y=181+i*28;s.text(65,y,p['id'],12);s.text(160,y,f"{p['size'][0]:.1f} × {p['size'][1]:.1f}",12);s.text(390,y,f"{p['thickness_mm']:.2f}",12)
            s.text(550,y,f"原板 {p['sheet']:02}" if 'sheet' in p else p['reason'],11)
        s.text(65,722,'來源子物件逐件對照；孔槽按投影保留。曲面、複合件與超長件需原 CAD 拆分及再排版。',12)
        s.text(65,749,'原板大小與間距是排版情境；加工前核對板材規格、刀徑、固定橋、紋理方向與試配。',12)
        pages.append(s)
    return pages

def dxf(data):
    out=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
    def line(a,b,layer):out.extend(['0','LINE','8',layer,'10',str(a[0]),'20',str(a[1]),'30','0','11',str(b[0]),'21',str(b[1]),'31','0'])
    w,h=data['stock_mm']
    for i,board in enumerate(data['boards']):
        dx=i*(w+200)
        corners=[[dx,0],[dx+w,0],[dx+w,h],[dx,h],[dx,0]]
        for a,b in zip(corners,corners[1:]):line(a,b,'STOCK')
        for p in board['parts']:
            for a,b in p['segments']:line([dx+a[0],h-a[1]],[dx+b[0],h-b[1]],p['id'])
    out+=['0','ENDSEC','0','EOF'];return '\n'.join(out)

def extras(data):
    meta={**data,'boards':[{'parts':[{k:v for k,v in p.items() if k!='segments'} for p in b['parts']]} for b in data['boards']],
          'unplaced':[{k:v for k,v in p.items() if k!='segments'} for p in data['unplaced']]}
    return {'panel_layout_mm.dxf':dxf(data),'panel_layout.json':json.dumps(meta,ensure_ascii=False,indent=2)}
