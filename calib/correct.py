import numpy as np, json
from pathlib import Path
from shutil import copyfile
ROOT = Path(__file__).resolve().parents[1]
# Original capture (unchanged). Intermediate pre-scale PLY is gitignored.
SRC = str(ROOT / 'media' / 'Livingroom-in-Taipei.ply')
DST = str(ROOT / 'calib' / 'Livingroom-in-Taipei.corrected.ply')
raw=open(SRC,'rb').read(); hl=raw.index(b'end_header\n')+11; header=raw[:hl]
props=[l.split()[-1].decode() for l in header.splitlines() if l.startswith(b'property')]
assert all(b'property float' in l for l in header.splitlines() if l.startswith(b'property'))
d=np.frombuffer(raw[hl:],np.float32).reshape(-1,len(props)).astype(np.float64).copy()
I=lambda n: props.index(n)
def rot_a_to_b(a,b):
    a=a/np.linalg.norm(a); b=b/np.linalg.norm(b); v=np.cross(a,b); c=a@b; s=np.linalg.norm(v)
    if s<1e-12: return np.eye(3)
    K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]); return np.eye(3)+K+K@K*((1-c)/s**2)
def Ry(t): c,s=np.cos(t),np.sin(t); return np.array([[c,0,s],[0,1,0],[-s,0,c]])
# 1) 180deg about Z (file is y-down/x-left vs three.js y-up)
R0=np.diag([-1.,-1.,1.])
# 2) level: measured gravity 'up' in R0 frame (flat horizontal splats + vertical-surface normals)
up=np.array([-0.00246845,0.99986862,-0.01601998]); R1=rot_a_to_b(up,np.array([0,1.,0]))
# 3) yaw: dominant back (TV) wall normal in R0 frame -> +Z (wall faces viewer, viewer looks -Z)
wall_yaw=np.radians(-3.1)   # atan2(nx,nz) of fitted wall planes (inlier-weighted)
R2=Ry(-wall_yaw)
R=R2@R1@R0
# 4) translate: origin = floor point directly below the tuned viewing position
floor_h=-1.90   # floor level along 'up' in R0 frame (lowest horizontal splat cluster / 0.5th pct)
cam_raw=np.array([0.72,0.31,0.05]); look_raw=np.array([1.61,1.02,-2.87])
c=R@cam_raw; t=-np.array([c[0],0,c[2]]); 
# floor in new frame: y of floor plane = floor_h (since R1 maps up->Y, R2 is about Y)
t[1]=-floor_h
T=np.eye(4); T[:3,:3]=R; T[:3,3]=t
P=d[:,[I('x'),I('y'),I('z')]]; d[:,[I('x'),I('y'),I('z')]]=P@R.T+t
if 'nx' in props: d[:,[I('nx'),I('ny'),I('nz')]]=d[:,[I('nx'),I('ny'),I('nz')]]@R.T
# quaternions (w,x,y,z): q' = qR * q
def mat2quat(M):
    w=np.sqrt(max(0,1+M[0,0]+M[1,1]+M[2,2]))/2; x=np.sqrt(max(0,1+M[0,0]-M[1,1]-M[2,2]))/2
    y=np.sqrt(max(0,1-M[0,0]+M[1,1]-M[2,2]))/2; z=np.sqrt(max(0,1-M[0,0]-M[1,1]+M[2,2]))/2
    x=np.copysign(x,M[2,1]-M[1,2]); y=np.copysign(y,M[0,2]-M[2,0]); z=np.copysign(z,M[1,0]-M[0,1])
    if w<1e-6: # 180-ish: pick via largest
        i=np.argmax([x*x,y*y,z*z]); x,y,z=[abs(x),abs(y),abs(z)]
        v=np.array([x,y,z]); 
        if i==0: v[1]=np.copysign(v[1],M[0,1]+M[1,0]); v[2]=np.copysign(v[2],M[0,2]+M[2,0])
        if i==1: v[0]=np.copysign(v[0],M[0,1]+M[1,0]); v[2]=np.copysign(v[2],M[1,2]+M[2,1])
        if i==2: v[0]=np.copysign(v[0],M[0,2]+M[2,0]); v[1]=np.copysign(v[1],M[1,2]+M[2,1])
        x,y,z=v
    q=np.array([w,x,y,z]); return q/np.linalg.norm(q)
def qmul(a,b):
    w1,x1,y1,z1=a.T if a.ndim>1 else a; w2,x2,y2,z2=b.T
    return np.stack([w1*w2-x1*x2-y1*y2-z1*z2,w1*x2+x1*w2+y1*z2-z1*y2,w1*y2-x1*z2+y1*w2+z1*x2,w1*z2+x1*y2-y1*x2+z1*w2],1)
def q2m(q):
    w,x,y,z=q/np.linalg.norm(q,axis=-1,keepdims=True) if q.ndim>1 else q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y)],[2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x)],[2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)]])
qR=mat2quat(R); assert np.allclose(q2m(qR),R,atol=1e-6)
qi=[I(f'rot_{k}') for k in range(4)]; q=d[:,qi]; d[:,qi]=qmul(np.broadcast_to(qR,q.shape),q)
# SH: exact 3DGS (eval_sh) real basis, bands 1 and 2, rotated per band via least squares
C1=0.4886025119029199; C2=[1.0925484305920792,-1.0925484305920792,0.31539156525252005,-1.0925484305920792,0.5462742152960396]
def basis(D):
    x,y,z=D.T
    b1=np.stack([-C1*y,C1*z,-C1*x],1)
    b2=np.stack([C2[0]*x*y,C2[1]*y*z,C2[2]*(2*z*z-x*x-y*y),C2[3]*x*z,C2[4]*(x*x-y*y)],1)
    return b1,b2
nrest=sum(p.startswith('f_rest_') for p in props); K=nrest//3; print("SH coeffs/channel",K)
rng=np.random.default_rng(0); D=rng.normal(size=(500,3)); D/=np.linalg.norm(D,axis=1,keepdims=True)
A1,A2=basis(D); B1,B2=basis(D@R)   # basis at R^T d  (rows d @ R == (R^T d)^T)
M1=np.linalg.lstsq(A1,B1,rcond=None)[0]; M2=np.linalg.lstsq(A2,B2,rcond=None)[0]
for ch in range(3):
    cols=[I(f'f_rest_{ch*K+k}') for k in range(K)]
    c=d[:,cols]
    c[:,0:3]=c[:,0:3]@M1.T
    if K>=8: c[:,3:8]=c[:,3:8]@M2.T
    assert K in (3,8)
    d[:,cols]=c
# verify SH rotation on random splats: f_new(R d) == f_old(d)
old=np.frombuffer(raw[hl:],np.float32).reshape(-1,len(props)).astype(np.float64)
idx=rng.choice(len(d),200,replace=False); err=0
for ch in range(3):
    cols=[I(f'f_rest_{ch*K+k}') for k in range(K)]
    b1,b2=basis(D); n1,n2=basis(D@R.T)
    fo=old[idx][:,cols][:,:3]@b1.T+old[idx][:,cols][:,3:]@b2.T
    fn=d[idx][:,cols][:,:3]@n1.T+d[idx][:,cols][:,3:]@n2.T
    err=max(err,np.abs(fo-fn).max())
print("SH rotation max err",err)
# verify covariance: Sigma' = R Sigma R^T
s=np.exp(old[idx][:,[I('scale_0'),I('scale_1'),I('scale_2')]])
e=0
for j,i in enumerate(idx):
    Mo=q2m(old[i,qi]); Mn=q2m(d[i,qi]); So=Mo@np.diag(s[j]**2)@Mo.T; Sn=Mn@np.diag(s[j]**2)@Mn.T
    e=max(e,np.abs(R@So@R.T-Sn).max())
print("cov max err",e)
open(DST,'wb').write(header+d.astype(np.float32).tobytes())
newcam=R@cam_raw+t; newlook=R@look_raw+t
eul=np.degrees([np.arctan2(R[2,1],R[2,2]),-np.arcsin(R[2,0]),np.arctan2(R[1,0],R[0,0])])
out=dict(T=T.round(6).tolist(),euler_xyz_deg=eul.round(3).tolist(),quat_wxyz=qR.round(6).tolist(),
 new_camera=newcam.round(3).tolist(),new_lookat=newlook.round(3).tolist(),
 bbox_p2_p98=[np.percentile(d[:,[I('x'),I('y'),I('z')]],2,0).round(2).tolist(),np.percentile(d[:,[I('x'),I('y'),I('z')]],98,0).round(2).tolist()])
# 5) METRIC SCALE from the 65" 16:9 TV (visible panel 1.439 x 0.809 m, diag 1.651 m).
# Measured in corrected units by calib/tv_measure.py (ortho front render calib/tv_front_ortho.png):
#   outer dark rectangle 2.155 x 1.215 (aspect 1.774), inner bright edge 2.040 x 1.165 (aspect 1.751).
# Outer edge matches 16:9 and is taken as panel + ~7 mm bezel/side -> s = (1.439+0.015)/2.155 = 0.675
# (cross-check: height (0.809+0.015)/1.215=0.678, diag (1.651+0.02)/2.474=0.675; inner-edge bound 0.705).
S=0.675
DSTM = str(ROOT / 'public' / 'Livingroom-in-Taipei.metric.ply')
dm=d.copy()
dm[:,[I('x'),I('y'),I('z')]]*=S
for k in range(3): dm[:,I(f'scale_{k}')]+=np.log(S)   # file stores log(sigma)
open(DSTM,'wb').write(header+dm.astype(np.float32).tobytes())
TM=np.diag([S,S,S,1.])@T
out.update(metric_scale=S, T_metric=TM.round(6).tolist(),
  metric_camera=(newcam*S).round(3).tolist(), metric_lookat=(newlook*S).round(3).tolist(),
  capture_camera_metric=(t*S).round(3).tolist(),
  tv_scale_estimates=dict(width_outer=0.6677,height_outer=0.6658,diag_outer=0.6674,width_inner=0.7054,height_inner=0.6944,diag_inner=0.7028))
print(json.dumps(out,indent=1)); json.dump(out,open(ROOT / 'calib' / 'transform.json','w'),indent=1)
copyfile(DSTM, ROOT / 'media' / 'Livingroom-in-Taipei.metric.ply')
