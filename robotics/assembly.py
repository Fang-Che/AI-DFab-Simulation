"""Rectangular demonstration, separate from the user's original placement.

All library meshes retain their scale. Slope closures are explicitly conceptual.
The progress value is an animation schedule, not elapsed construction time.
"""
import json
import math
import numpy as np
from .core import ROOT,read_json,transform,bounds_of
from .import_geometry import box_mesh

def pack_block(g):
    v=[];f=[]
    for p in g['parts']:
        offset=len(v);v.extend(p['vertices_mm']);f.extend([[x+offset for x in face] for face in p['triangles']])
    return {'v':v,'f':f}

def old_rectangle_demo(geometry):
    extra=read_json(ROOT/'robotics/assets/demo_geometry.json')
    blocks={**geometry['blocks'],**extra['blocks']}
    wanted=['SKYLARK250_FLOOR-M-0','SKYLARK200_CORNER-M','SKYLARK250_WALL-M',
            'SKYLARK250_DOOR-M1','SKYLARK250_WINDOW-M2','SKYLARK250_ROOF-M10']
    meshes={k:pack_block(blocks[k]) for k in wanted}
    items=[]
    def add(key,cat,rot,translation,label=None,evidence='source_mesh'):
        items.append({'id':f'H{len(items)+1:03d}','key':key,'category':cat,'rotation':rot,
            'translation':translation,'label':label or key.replace('SKYLARK250_','').replace('SKYLARK200_',''),
            'evidence':evidence})
    width=5436.;length=4800.;wallheight=2400.
    for i in range(8):add(wanted[0],'floor',-90,[0,i*600,0])
    # Use the measured corner insertion offsets without scaling or reflection.
    for rot,t in [(0,[268,25,0]),(90,[width-25,268,0]),(180,[width-268,length-25,0]),(270,[25,length-268,0])]:
        add(wanted[1],'corner',rot,t)
    for y,rot in [(0,0),(length,180)]:
        for n in range(8):
            x=618+n*600
            if y==0 and n in [3,4]:
                if n==3:add(wanted[3],'door',0,[x+900,318,2100])
                continue
            if y==length and n in [3,4]:
                if n==3:add(wanted[4],'window',180,[x+300,length,0])
                continue
            add(wanted[2],'wall',rot,[x,y,0])
    # Six standard walls and two 282 mm infill strips close each short facade.
    for x,rot in [(0,270),(width,90)]:
        for n in range(6):add(wanted[2],'wall',rot,[x,600+n*600,0])
    def prism(key,verts,faces):meshes[key]={'v':verts,'f':faces}
    def custom_box(key,cat,lo,hi,label):
        v,f=box_mesh([lo,hi]);prism(key,v,f);add(key,cat,0,[0,0,0],label,'conceptual_closure')
    for x in [0,width-318]:
        for lo,hi in [(318,300),(3900,length-318)]:
            if hi>lo:custom_box(f'INFILL_{x}_{lo}','filler',[x,lo,0],[x+318,hi,wallheight],'端部補板（示意）')
    # Top closures connect the rectangular wall zone to the source mono-pitched roof.
    slope=math.tan(math.radians(10))
    for y in [0,length-318]:
        v=[[0,y,wallheight],[width,y,wallheight],[width,y,wallheight+slope*width],
           [0,y+318,wallheight],[width,y+318,wallheight],[width,y+318,wallheight+slope*width]]
        f=[[0,1,2],[3,5,4],[0,3,4],[0,4,1],[1,4,5],[1,5,2],[2,5,3],[2,3,0]]
        key=f'SLOPE_END_{y}';prism(key,v,f);add(key,'closure',0,[0,0,0],'斜屋頂端部封板（示意）','conceptual_closure')
    custom_box('HIGH_WALL','closure',[width-318,318,2400],[width,length-318,2400+slope*(width-318)],'高側牆補段（示意）')
    for i in range(8):add(wanted[-1],'roof',0,[0,600*i,2400])
    return {'mode':'house','meshes':meshes,'items':items,'width':width,'length':length,
            'roof_pitch_deg':10,'schedule_basis':'category_template_not_joint_validation',
            'sources':geometry['sources']+extra['sources']}

def assembly_state(count,progress):
    if count<=0:raise ValueError('No assembly items')
    t=max(0,min(100,float(progress)))*count/100
    finished=min(count,int(t))
    return {'installed':finished,'active':finished if finished<count else None,'fraction':t-finished}

def rectangle_demo(geometry,layout='rectangle',**kwargs):
    from .house import house_demo
    return house_demo(geometry,layout,**kwargs)

def export_house(data,path):
    import rhino3dm as rh
    doc=rh.File3dm();doc.Settings.ModelUnitSystem=rh.UnitSystem.Millimeters
    colors={'floor':(135,178,160,255),'corner':(75,117,133,255),'wall':(199,164,112,255),
        'roof':(184,134,70,255),'door':(139,176,190,255),'window':(139,176,190,255),'closure':(201,155,164,255)}
    layers={};definitions={}
    for item in data['items']:
        cat=item['category']
        if cat not in layers:
            layer=rh.Layer();layer.Name=cat;layer.Color=colors.get(cat,(170,170,170,255));layers[cat]=doc.Layers.Add(layer)
        key=item['key']
        if key not in definitions:
            src=data['meshes'][key];mesh=rh.Mesh()
            for p in src['v']:mesh.Vertices.Add(*p)
            for f in src['f']:mesh.Faces.AddFace(*f)
            mesh.Normals.ComputeNormals();part_attr=rh.ObjectAttributes();part_attr.LayerIndex=layers[cat]
            index=doc.InstanceDefinitions.Add(key,'Assembly module','','',rh.Point3d(0,0,0),(mesh,),(part_attr,))
            definitions[key]=doc.InstanceDefinitions[index].Id
        angle=math.radians(item['rotation']);c,s=math.cos(angle),math.sin(angle);xf=rh.Transform.Identity()
        xf.M00=c;xf.M01=-s;xf.M10=s;xf.M11=c
        xf.M03,xf.M13,xf.M23=item['translation']
        attr=rh.ObjectAttributes();attr.LayerIndex=layers[cat];attr.Name=item['id']+' '+item['label']
        attr.SetUserString('evidence',item['evidence']);attr.SetUserString('sequence',str(item.get('sequence_index',item['id'])))
        attr.SetUserString('level',str(item.get('level',1)));attr.SetUserString('scheme',data.get('layout','rectangle'))
        doc.Objects.AddInstanceObject(rh.InstanceReference(definitions[key],xf),attr)
    if not doc.Write(str(path),8):raise RuntimeError('3dm export failed')

def factory_scene(geometry,unit='SKYLARK250_WALL-M'):
    wall=geometry['blocks'][unit];parts=[]
    raw=np.concatenate([np.asarray(p['vertices_mm'],float) for p in wall['parts']])
    lo,hi=raw.min(0),raw.max(0)
    # Rigid rotation only: choose the thinnest axis vertical, longest along bench.
    sizes=hi-lo;thin=int(np.argmin(sizes));longest=int(np.argmax(sizes));wide=next(i for i in range(3) if i not in [thin,longest])
    basis=np.eye(3)[[wide,longest,thin]]
    if np.linalg.det(basis)<0:basis[0]*=-1
    projected=(raw-(lo+hi)/2)@basis.T
    shift=np.array([1900.,0.,750.-projected[:,2].min()])
    for part in wall['parts']:
        # Rigid rotation puts the 2.4 m wall length along the assembly bench.
        points=np.asarray(part['vertices_mm'],float)
        vertices=(points-(lo+hi)/2)@basis.T+shift
        centre=vertices.mean(0);q=vertices-centre
        vals,axes=np.linalg.eigh(np.cov(q.T));normal=axes[:,0]
        if np.dot(normal,-centre)<0:normal=-normal
        if abs(normal[2])>.7:normal=np.array([0.,0.,1.])
        # Local coordinates flattened into a stack; target rotation is retained.
        long=axes[:,2];long-=normal*np.dot(long,normal);long/=np.linalg.norm(long)
        if long[1]<-1e-6 or (abs(long[1])<1e-6 and long[0]<0):long=-long
        across=np.cross(normal,long)
        frame=np.column_stack([long,across,normal])
        local=q@frame
        parts.append({'id':part['part_id'],'label':part['label'],'v':local.round(4).tolist(),
            'f':part['triangles'],'target':centre.tolist(),'frame':frame.tolist(),'normal':normal.tolist()})
    targets=np.array([p['target'] for p in parts]);bottom,top=targets[:,2].min(),targets[:,2].max()
    far,near=targets[:,0].max(),targets[:,0].min()
    for p in parts:
        x,y,z=p['target'];normal=np.asarray(p['normal'])
        horizontal=abs(normal[2])>.7
        p['role']='bottom' if horizontal and abs(z-bottom)<25 else 'top' if horizontal and abs(z-top)<25 and top-bottom>30 else 'far' if abs(x-far)<25 and far-near>30 else 'near' if abs(x-near)<25 and far-near>30 else 'internal'
        p['role_label']={'bottom':'底板','far':'遠側板','internal':'內部肋板','near':'近側封板','top':'最後頂板'}[p['role']]
        p['insertion_vector']=[0,0,-1]
    priority={'bottom':0,'far':1,'internal':2,'near':3,'top':4}
    parts.sort(key=lambda p:(priority[p['role']],-np.linalg.norm(p['target'][:2]),p['id']))
    from .abb import model
    return {'mode':'robot','parts':parts,'robot':model(),'unit':unit,
        'bench_size_mm':[float(sizes[wide]+300),float(sizes[longest]+300)],
        'source':unit+' cached source mesh','manis_executed':False,
        'limitations':['六軸工業機械手臂使用既有幾何與關節參數，尚未實機標定；大型單元可能超出固定站位可及範圍。',
                       '碰撞為逐幀 AABB 保守預檢；不含自碰撞、連續掃掠與精確接頭咬合。',
                       '吸盤夾具為示意；抓取強度、載重與板材變形未驗證。']}

def viewer_html(data):
    root=ROOT/'robotics'
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=(root/'assembly_viewer.html').read_text(encoding='utf8')
    return template.replace('__THREE__',(root/'assets/vendor/three.min.js').read_text(encoding='utf8')).replace('__ORBIT__',(root/'assets/vendor/OrbitControls.js').read_text(encoding='utf8')).replace('__ABB__',(root/'abb_viewer.js').read_text(encoding='utf8')).replace('__DATA__',payload)
