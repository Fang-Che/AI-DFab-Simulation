"""Six-axis spherical-wrist surrogate; link dimensions are assumptions.

Not calibrated KR360 kinematics. Official axis ranges are only a provisional gate.
"""
import math
import numpy as np
LIMITS=np.array([[-185,185],[-130,20],[-100,144],[-350,350],[-120,120],[-350,350]],float)
def rx(a):
    c,s=math.cos(a),math.sin(a);return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def ry(a):
    c,s=math.cos(a),math.sin(a);return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def rz(a):
    c,s=math.cos(a),math.sin(a);return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def forward(q):
    q=np.radians(q);R=rz(q[0]);p=R@np.array([.25,0,1.045])
    R=R@ry(q[1]);p+=R@np.array([1.2,0,0])
    R=R@ry(q[2]);p+=R@np.array([1.16,0,0])
    R=R@rx(q[3])@ry(q[4])@rx(q[5]);p+=R@np.array([.216,0,0])
    return p,R
def inverse(p,R):
    p=np.asarray(p);R=np.asarray(R);w=p-R@np.array([.216,0,0]);q1=math.atan2(w[1],w[0])
    r=math.hypot(w[0],w[1])-.25;z=w[2]-1.045
    co=(r*r+z*z-1.2**2-1.16**2)/(2*1.2*1.16)
    if abs(co)>1+1e-8:return {'status':'unreachable','joints_deg':None}
    elbow=-math.acos(np.clip(co,-1,1));sh=math.atan2(z,r)-math.atan2(1.16*math.sin(elbow),1.2+1.16*math.cos(elbow))
    q2,q3=-sh,-elbow;W=(rz(q1)@ry(q2+q3)).T@R
    beta=math.acos(np.clip(W[0,0],-1,1))
    if abs(math.sin(beta))<1e-8:a=0.;c=math.atan2(W[2,1],W[1,1])
    else:a=math.atan2(W[1,0],-W[2,0]);c=math.atan2(W[0,1],W[0,2])
    q=np.degrees([q1,q2,q3,a,beta,c]);out,Rout=forward(q)
    return {'status':'within_surrogate_limits' if np.all((q>=LIMITS[:,0])&(q<=LIMITS[:,1])) else 'joint_limit',
        'joints_deg':q.tolist(),'position_error_mm':float(np.linalg.norm(out-p)*1000),
        'rotation_error':float(np.linalg.norm(Rout-R)),'calibrated_robot':False}
