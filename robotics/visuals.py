import math
import numpy as np
import plotly.graph_objects as go
from .core import center,size,corners,transform,path_position
from .import_geometry import box_mesh

COLORS={'floor':'#c6d9d4','end':'#c6d9d4','wall':'#b7c9d7','window':'#a7c5d6',
        'door':'#cfc3a6','corner':'#94aabd','filler':'#c9bdc9','partition':'#d3dbe1','roof':'#e0b877'}

def mesh_trace(vertices,faces,color,name,opacity=1):
    v=np.asarray(vertices)/1000
    f=np.asarray(faces,dtype=int)
    return go.Mesh3d(x=v[:,0],y=v[:,1],z=v[:,2],i=f[:,0],j=f[:,1],k=f[:,2],
        color=color,opacity=opacity,name=name,hovertemplate=name+'<extra></extra>',
        flatshading=True,lighting=dict(ambient=.65,diffuse=.8,roughness=.9,specular=.08),
        lightposition=dict(x=-100,y=-100,z=300),showlegend=False)

def box_trace(bounds,color,name,opacity=1):
    v,f=box_mesh(bounds)
    return mesh_trace(v,f,color,name,opacity)

def polyline(points,color,name,width=4,dash=None):
    p=np.asarray(points)/1000
    return go.Scatter3d(x=p[:,0],y=p[:,1],z=p[:,2],mode='lines',
        line=dict(color=color,width=width,**({'dash':dash} if dash else {})),name=name,
        hoverinfo='name',showlegend=False)

def outline(bounds,color='#506c7d',width=1):
    v=corners(bounds)
    pairs=((0,1),(1,3),(3,2),(2,0),(4,5),(5,7),(7,6),(6,4),(0,4),(1,5),(2,6),(3,7))
    points=[]
    for a,b in pairs:points.extend([v[a],v[b],[float('nan')]*3])
    return polyline(points,color,'構件包絡',width)

def module_mesh(module,geometry,at_center=None):
    geo=geometry['blocks'].get(module['block_id'])
    if not geo:
        verts,faces=box_mesh(module['bbox_mm'])
    else:
        verts=[];faces=[]
        for part in geo['parts']:
            off=len(verts)
            verts.extend(transform(v,module['rotation_deg'],module['translation_mm']) for v in part['vertices_mm'])
            faces.extend([[off+i for i in f] for f in part['triangles']])
    if at_center is not None:
        c=center(module['bbox_mm']);shift=[at_center[i]-c[i] for i in range(3)]
        verts=[[v[i]+shift[i] for i in range(3)] for v in verts]
    return verts,faces

def style(fig,height=610,factory=False):
    ax=dict(showbackground=True,backgroundcolor='#f3f6f8',gridcolor='#dde5ea',zerolinecolor='#d1dbe2',
            tickfont=dict(size=10,color='#607281'),title_font=dict(size=11,color='#607281'))
    fig.update_layout(height=height,margin=dict(l=0,r=0,t=5,b=0),paper_bgcolor='#f7f9fb',
        font=dict(family='Arial, Microsoft JhengHei',color='#21384b'),
        scene=dict(xaxis=dict(title='X · m',**ax),yaxis=dict(title='Y · m',**ax),zaxis=dict(title='Z · m',**ax),
            aspectmode='data',camera=dict(eye=dict(x=-1.55,y=-1.8,z=1.3) if not factory else dict(x=1.6,y=-2.4,z=1.3))),
        uirevision='factory' if factory else 'site')
    return fig

def site_figure(scene,geometry,scenario,result,route,progress=.45,animate=True):
    fig=go.Figure();bad={x['obstacle_id'] for x in result['collisions']}
    target=scenario['target'];pos=path_position(route,progress)
    xmin=min(m['bbox_mm'][0][0] for m in scene['modules'])
    xmax=max(m['bbox_mm'][1][0] for m in scene['modules'])
    ymin=min(m['bbox_mm'][0][1] for m in scene['modules'])
    ymax=max(m['bbox_mm'][1][1] for m in scene['modules'])
    fig.add_trace(box_trace([[route[0][0]-3500,ymin-3000,-450],[xmax+2000,ymax+2500,-400]],'#e5e8e6','場地示意'))
    for m in scenario['obstacles']+[target]:
        if m['instance_id']==target['instance_id']:
            fig.add_trace(outline(m['bbox_mm'],'#b29a69',2));continue
        is_bad=m['instance_id'] in bad
        fig.add_trace(box_trace(m['bbox_mm'],'#d95b52' if is_bad else COLORS.get(m['category'],'#b7c9d7'),
            m['instance_id']+' · '+m['block_id'],.75 if is_bad else .45))
        fig.add_trace(outline(m['bbox_mm'],'#ac5a56' if is_bad else '#92a6b4',1))
    # A symbolic crane mast communicates equipment placement, not a validated model.
    base=result['crane_base_mm'];mast=[base[0],base[1],max(p[2] for p in route)+1800]
    fig.add_trace(box_trace([[base[0]-600,base[1]-900,-200],[base[0]+600,base[1]+900,250]],'#546978','設備位置示意'))
    fig.add_trace(polyline([base,mast], '#637985','設備示意 · 未做設備碰撞',12))
    fig.add_trace(polyline(route,'#1f8d85' if not bad else '#db8a46','候選路徑' if not bad else '原始路徑',6,'dash'))
    fig.add_trace(go.Scatter3d(x=[route[0][0]/1000,route[-1][0]/1000],y=[route[0][1]/1000,route[-1][1]/1000],
        z=[route[0][2]/1000,route[-1][2]/1000],mode='markers+text',text=['堆置點','安裝前接近點'],
        marker=dict(size=5,color='#176b77'),textposition='top center',showlegend=False,hoverinfo='text'))
    verts,faces=module_mesh(target,geometry,pos)
    active_index=len(fig.data)
    fig.add_trace(mesh_trace(verts,faces,'#d8aa64',target['instance_id']+' · 移動模組'))
    if animate:
        origin=np.asarray(verts)/1000
        frames=[]
        for step in range(31):
            q=path_position(route,step/30)
            xyz=origin+(np.asarray(q)-np.asarray(pos))/1000
            frames.append(go.Frame(name=str(step),data=[go.Mesh3d(x=xyz[:,0],y=xyz[:,1],z=xyz[:,2])],traces=[active_index]))
        fig.frames=frames
        fig.update_layout(updatemenus=[dict(type='buttons',direction='left',x=.02,y=.02,xanchor='left',yanchor='bottom',
            bgcolor='#ffffff',bordercolor='#d5dfe6',buttons=[
            dict(label='▶ 播放路徑',method='animate',args=[None,dict(frame=dict(duration=80,redraw=True),transition=dict(duration=0),fromcurrent=True,mode='immediate')]),
            dict(label='Ⅱ 暫停',method='animate',args=[[None],dict(frame=dict(duration=0,redraw=False),mode='immediate')])])])
    return style(fig)

def factory_figure(geo,assembled=3,explosion=1):
    fig=go.Figure();bbox=geo['bbox_mm'];c=center(bbox)
    fig.add_trace(box_trace([[-1200,-1400,-180],[1200,1100,-80]],'#cad5dc','工廠治具平面示意'))
    for index,part in enumerate(geo['parts']):
        points=np.asarray(part['vertices_mm']);pc=points.mean(axis=0)
        delta=np.zeros(3)
        if index>=assembled:
            vals,axes=np.linalg.eigh(np.cov(points.T));normal=axes[:,0]
            if np.dot(normal,pc-np.asarray(c))<0:normal=-normal
            delta=normal*(400+(index-assembled)*110)*explosion
        fig.add_trace(mesh_trace((points+delta).tolist(),part['triangles'],
            '#d7ac71' if index<assembled else '#6aa7b8',part['part_id']+' · '+part['label'],1 if index<assembled else .5))
        if index==assembled:
            fig.add_trace(polyline([list(pc+delta),list(pc)],'#277e98','候選插入方向 · 未驗證',5,'dash'))
            fig.add_trace(go.Scatter3d(x=[(pc+delta)[0]/1000],y=[(pc+delta)[1]/1000],z=[(pc+delta)[2]/1000],
                mode='markers',marker=dict(size=7,color='#e9993c',symbol='diamond'),showlegend=False,name='夾具參考點'))
    return style(fig,560,True)

def feature_edges(vertices,faces,angle=20):
    """Weld duplicate vertices and retain boundaries/creases, not triangle seams."""
    v=np.asarray(vertices,dtype=float)
    _,inverse=np.unique(np.round(v,5),axis=0,return_inverse=True)
    adjacency={}
    for face in faces:
        ids=[int(inverse[i]) for i in face]
        normal=np.cross(v[face[1]]-v[face[0]],v[face[2]]-v[face[0]])
        length=np.linalg.norm(normal)
        if length<1e-10:continue
        normal/=length
        for a,b in zip(range(3),[1,2,0]):
            key=tuple(sorted((ids[a],ids[b])))
            adjacency.setdefault(key,[]).append((normal,v[face[a]],v[face[b]]))
    points=[];threshold=math.cos(math.radians(angle))
    for entries in adjacency.values():
        if len(entries)==1 or any(abs(np.dot(entries[0][0],e[0]))<threshold for e in entries[1:]):
            points.extend([entries[0][1],entries[0][2],[float('nan')]*3])
    return points

def panel_figure(part,bed=(2440,1220)):
    points=np.asarray(part['vertices_mm']);origin=points.mean(axis=0)
    vals,axes=np.linalg.eigh(np.cov(points.T));projected=(points-origin)@axes
    ext=np.ptp(projected,axis=0);order=np.argsort(ext)
    # Display the two principal in-plane axes on the stock sheet; preserve the mesh.
    mapped=np.column_stack([projected[:,order[2]],projected[:,order[1]],projected[:,order[0]]])
    mapped-=mapped.min(axis=0);mapped[:,2]+=10
    fig=go.Figure([box_trace([[0,0,-18],[bed[0],bed[1],0]],'#dce4e4','設定的板材範圍',.3),
        mesh_trace(mapped.tolist(),part['triangles'],'#d5a66b',part['part_id'])])
    edges=feature_edges(mapped,part['triangles'])
    if edges:fig.add_trace(polyline(edges,'#493924','板件外框、孔洞與折邊',3))
    fig.add_trace(outline([[0,0,-18],[bed[0],bed[1],0]],'#93a8ac',1))
    style(fig,570,True)
    extent=np.maximum(np.array([bed[0],bed[1],28.]),mapped.max(axis=0))-np.array([0,0,-18.])
    ratio=extent/extent.max()*1.8
    fig.update_layout(scene_aspectmode='manual',scene_aspectratio=dict(zip(['x','y','z'],ratio)),
        scene_camera=dict(eye=dict(x=0,y=-.65,z=1.8),up=dict(x=0,y=1,z=0),projection=dict(type='orthographic')))
    return fig
