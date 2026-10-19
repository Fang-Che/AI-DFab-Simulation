"""ABB IRB6400 kinematics from the Manis IBOIS DH data (millimetres).

Mesh zero pose is registered using FK(q) @ inverse(FK(0)). This is a
geometric model, not a calibrated controller or dynamics simulation.
"""
import math
import numpy as np
from .core import ROOT, read_json

A = [240,1050,225,0,0,0]
D = [800,0,0,1520,0,200]
ALPHA = [math.pi/2,0,math.pi/2,-math.pi/2,math.pi/2,0]
LIMITS = [[-180,180],[-70,85],[-28,110],[-300,300],[-120,120],[-300,300]]

def forward(joints):
    q=np.radians(joints)*[1,-1,-1,1,-1,1]+[0,math.pi/2,0,0,0,0]
    t=np.eye(4); out=[t.copy()]
    for a,d,alpha,theta in zip(A,D,ALPHA,q):
        c,s=math.cos(theta),math.sin(theta);ca,sa=math.cos(alpha),math.sin(alpha)
        t=t@np.array([[c,-s*ca,s*sa,a*c],[s,c*ca,-c*sa,a*s],[0,sa,ca,d],[0,0,0,1]])
        out.append(t.copy())
    return out

def inverse(target,previous=None):
    previous=np.array(previous if previous is not None else [0,25,25,0,45,0],float)
    target=np.array(target); w=target[:3,3]-200*target[:3,2]
    L=math.hypot(225,1520);phi=math.atan2(1520,225); candidates=[]
    for flip in [False,True]:
        yaw=math.atan2(w[1],w[0])+(math.pi if flip else 0)
        r=math.hypot(w[0],w[1])*(-1 if flip else 1)-240;z=w[2]-800
        cosine=(r*r+z*z-1050**2-L**2)/(2*1050*L)
        if abs(cosine)>1+1e-8:continue
        for sign in [-1,1]:
            e=sign*math.acos(np.clip(cosine,-1,1))
            theta2=math.atan2(z,r)-math.atan2(L*math.sin(e),1050+L*math.cos(e))
            first=np.degrees([yaw,math.pi/2-theta2,-e-phi])
            R=forward([*first,0,0,0])[3][:3,:3].T@target[:3,:3]
            beta=math.acos(np.clip(R[2,2],-1,1))
            for ws in [1,-1]:
                b=beta*ws
                if abs(math.sin(b))<1e-7:
                    a=math.radians(previous[3]);c=math.atan2(R[1,0],R[0,0])-a
                else:
                    a=math.atan2(R[1,2]/math.sin(b),R[0,2]/math.sin(b))
                    c=math.atan2(R[2,1]/math.sin(b),-R[2,0]/math.sin(b))
                q=np.r_[first,np.degrees([a,-b,c])]
                for i in range(6):
                    options=[q[i]+360*k for k in range(-2,3) if LIMITS[i][0]-1e-6<=q[i]+360*k<=LIMITS[i][1]+1e-6]
                    if not options:break
                    q[i]=min(options,key=lambda x:abs(x-previous[i]))
                else:
                    err=np.max(np.abs(forward(q)[-1]-target))
                    if err<1e-5:candidates.append(q)
    return None if not candidates else min(candidates,key=lambda q:np.linalg.norm(q-previous)).tolist()

def model():
    return read_json(ROOT/'robotics/assets/abb_irb6400.json')

def extract_model(path):
    import rhino3dm as rh
    import hashlib,json
    source=rh.File3dm.Read(str(path));links=[]
    for obj in source.Objects:
        mesh=obj.Geometry
        if not isinstance(mesh,rh.Mesh):continue
        layer=source.Layers[obj.Attributes.LayerIndex].Name
        if layer not in [str(i) for i in range(7)]:continue
        faces=[]
        for a,b,c,d in mesh.Faces:
            faces.append([a,b,c])
            if d!=c:faces.append([a,c,d])
        links.append({'index':int(layer),'v':[[v.X,v.Y,v.Z] for v in mesh.Vertices],'f':faces})
    links.sort(key=lambda x:x['index'])
    if [x['index'] for x in links]!=list(range(7)):raise ValueError('Expected base and six ABB links')
    data={'name':'ABB IRB6400','source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'parameter_source':'Manis/Robots/IBOIS.xml','a':A,'d':D,'alpha':ALPHA,'joint_limits_deg':LIMITS,
          'payload_kg':100,'links':links,'home_flange_mm':forward([0]*6)[-1].tolist()}
    (ROOT/'robotics/assets/abb_irb6400.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
    return data
