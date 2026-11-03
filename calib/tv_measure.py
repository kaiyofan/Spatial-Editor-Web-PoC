# Measure the TV in an orthographic front render of corrected.ply (0.005 units/px, center three(-2.2,1.2))
import numpy as np, json
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
# Render is not checked in; see calib/README.md.
a=np.asarray(Image.open(ROOT / 'calib' / 'tv_front_ortho.png').convert('RGB')).astype(float)/255
L=a@[0.2126,0.7152,0.0722]; PX=4.0/800; cx,cy=-2.2,1.2
def edges(profile,lo,hi,inward):
    seg=profile[lo:hi]; i=np.argmin(seg)+lo; mn=profile[i]
    out_ref=np.median(profile[lo-12:lo]) if inward>0 else np.median(profile[hi:hi+12])
    in_ref=np.median(profile[hi:hi+15]) if inward>0 else np.median(profile[lo-15:lo])
    def cross(ref,dirn):
        thr=(mn+ref)/2; j=i
        while 0<j<len(profile)-1 and profile[j]<thr: j+=dirn
        return j-dirn*0.5
    outer=cross(out_ref,-inward); inner=cross(in_ref,inward); return outer,inner
res={'L':[],'R':[],'T':[],'B':[]}
for r0 in range(140,340,20):
    col=np.median(L[r0:r0+20,:],0)
    res['L'].append(edges(col,298,328,+1)); res['R'].append(edges(col,724,742,-1))
for c0 in range(340,720,20):
    row=np.median(L[:,c0:c0+20],1)
    res['T'].append(edges(row,120,134,+1))
    # bottom: outer edge only (screen content near bottom is dark)
    j=372; 
    while row[j]>(row[366]+row[374])/2 and j>355: j-=1
    res['B'].append((j+0.5,np.nan))
med={k:np.nanmedian(np.array(v),0) for k,v in res.items()}
for k,v in res.items(): print(k,'outer/inner px median',np.round(med[k],1),'spread(outer p25-p75)',np.round(np.percentile(np.array(v)[:,0],[25,75]),1))
top_bezel=med['T'][1]-med['T'][0]
ox0,ox1=med['L'][0],med['R'][0]; ix0,ix1=med['L'][1],med['R'][1]
oy0,oy1=med['T'][0],med['B'][0]; iy0,iy1=med['T'][1],med['B'][0]-top_bezel
m=lambda px: px*PX
outer=dict(w=m(ox1-ox0),h=m(oy1-oy0)); inner=dict(w=m(ix1-ix0),h=m(iy1-iy0))
for n,dd in [('outer(bezel incl.)',outer),('inner(screen)',inner)]:
    dd['diag']=float(np.hypot(dd['w'],dd['h'])); dd['aspect']=dd['w']/dd['h']
    print(n,{k:round(v,4) for k,v in dd.items()})
W,H,D=1.439,0.809,1.651
s=dict(width=W/inner['w'],height=H/inner['h'],diag=D/inner['diag'],width_outer=W/outer['w'],height_outer=H/outer['h'],diag_outer=D/outer['diag'])
print({k:round(v,4) for k,v in s.items()})
tv_center=(cx+m((ix0+ix1)/2-400), cy-m((iy0+iy1)/2-300))
print("TV screen center (corrected units) x,y:",np.round(tv_center,3))
json.dump(dict(inner=inner,outer=outer,s=s,tv_center_xy=tv_center),open(ROOT / 'calib' / 'tv_measure.json','w'),indent=1)
