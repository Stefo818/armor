import math
def arrow(pts, w, col, head=64, hw=40):
    """Polilinea con punta di freccia in fondo (la punta coincide con l'ultimo punto)."""
    (x0,y0),(x1,y1)=pts[-2],pts[-1]; dx,dy=x1-x0,y1-y0; L=math.hypot(dx,dy); dx/=L; dy/=L
    bx,by=x1-head*dx,y1-head*dy; px,py=-dy,dx
    line=pts[:-1]+[(bx+dx*2,by+dy*2)]
    return (f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in line)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<polygon points="{x1:.1f},{y1:.1f} {bx+hw*px:.1f},{by+hw*py:.1f} {bx-hw*px:.1f},{by-hw*py:.1f}" fill="{col}" stroke="{col}" stroke-width="10" stroke-linejoin="round"/>')
def logo1(bg=True):
    s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a1a44"/><stop offset=".55" stop-color="#1d4ed8"/><stop offset="1" stop-color="#38bdf8"/></linearGradient><linearGradient id="b" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#10b981"/><stop offset="1" stop-color="#a7f3d0"/></linearGradient></defs>'
    if bg: s+='<rect width="512" height="512" rx="112" fill="#0b1224"/>'
    sh='M256 52 L432 112 V252 C432 356 356 430 256 466 C156 430 80 356 80 252 V112 Z'
    s+=f'<path d="{sh}" fill="url(#a)"/><path d="{sh}" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="7" transform="translate(256 259) scale(.9) translate(-256 -259)"/>'
    s+=arrow([(142,326),(206,252),(250,292),(368,168)],34,'url(#b)',head=70,hw=46)+'</svg>'
    return s
def logo2(bg=True):
    s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e293b"/><stop offset="1" stop-color="#020617"/></linearGradient><linearGradient id="b" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#34d399"/></linearGradient></defs>'
    if bg: s+='<rect width="512" height="512" rx="112" fill="#0b1224"/>'
    s+='<circle cx="256" cy="256" r="206" fill="url(#a)" stroke="url(#b)" stroke-width="12"/>'
    s+='<path d="M150 380 L256 128 L362 380" fill="none" stroke="#f8fafc" stroke-width="46" stroke-linecap="round" stroke-linejoin="round"/>'
    s+=arrow([(190,312),(230,296),(262,320),(334,226)],26,'url(#b)',head=52,hw=34)+'</svg>'
    return s
def logo3(bg=True):
    s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#0891b2"/></linearGradient></defs>'
    if bg: s+='<rect width="512" height="512" rx="112" fill="#0b1224"/>'
    hexa='M256 44 L450 150 V362 L256 468 L62 362 V150 Z'
    s+=f'<path d="{hexa}" fill="url(#a)"/>'
    for i,(y,o,c) in enumerate([(300,.45,'#fff'),(238,.7,'#fff'),(176,1,'#6ee7b7')]):
        s+=f'<path d="M142 {y+54} L256 {y-30} L370 {y+54}" fill="none" stroke="{c}" stroke-opacity="{o}" stroke-width="40" stroke-linecap="round" stroke-linejoin="round"/>'
    return s+'</svg>'
# --- lettere (altezza 0-100)
def word(variant, col='currentColor', h=44):
    if variant==1: w,j,cap,sk=10,'miter','butt',-12
    elif variant==2: w,j,cap,sk=3.6,'round','round',0
    else: w,j,cap,sk=15,'round','round',0
    gap={1:14,2:34,3:12}[variant]
    L={}
    L['A']=('M4 100 L30 6 L56 100' + ('' if variant==3 else ' M14 66 H46'),60)
    L['R']=('M6 100 V6 H34 Q58 6 58 32 Q58 58 34 58 H6',64)
    L['M']=('M6 100 V6 L36 62 L66 6 V100',72)
    L['O']=({1:'M18 6 H46 L62 22 V84 L46 100 H18 L2 84 V22 Z',2:'M32 6 A26 47 0 1 0 32.01 6 Z',3:'M32 6 A30 47 0 1 0 32.01 6 Z'}[variant],64)
    s=''; x=0; paths=''
    for i,ch in enumerate('ARMOR'):
        d,wd=L[ch]
        if ch=='R' and i==4:
            paths+=f'<g transform="translate({x} 0)"><path d="M6 100 V6 H34 Q58 6 58 32 Q58 58 34 58 H6"/><g>{arrow([(30,58),(48,94),(104,28)],w,"currentColor",head=30 if variant!=2 else 24,hw=19 if variant!=2 else 15)}</g></g>'
            x+=wd+gap+48
        elif ch=='R':
            paths+=f'<g transform="translate({x} 0)"><path d="{d} M30 58 L58 100"/></g>'; x+=wd+gap
        else:
            paths+=f'<g transform="translate({x} 0)"><path d="{d}"/></g>'; x+=wd+gap
    W=x
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-8 -14 {W+22} 130" style="height:{h}px" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="{j}" stroke-linecap="{cap}">'
            f'<g transform="skewX({sk}) translate({8 if sk else 0} 0)">{paths}</g></svg>')
if __name__=='__main__':
    open('/tmp/brand/l1.svg','w').write(logo1()); open('/tmp/brand/l2.svg','w').write(logo2()); open('/tmp/brand/l3.svg','w').write(logo3())
    html='<html><body style="margin:0;padding:24px;background:#0b1224;color:#e8edf5;font-family:system-ui;width:900px"><h2>Loghi</h2><div style="display:flex;gap:28px">'
    for n,f in enumerate((logo1,logo2,logo3),1):
        html+=f'<div><div style="width:200px">{f()}</div><div style="display:flex;gap:10px;margin-top:10px;align-items:center"><div style="width:48px">{f()}</div><div style="width:32px">{f()}</div><div style="width:20px">{f()}</div></div><b>Logo {n}</b></div>'
    html+='</div><h2>Font ARMOR</h2>'
    for v in (1,2,3):
        html+=f'<div style="margin:18px 0;padding:18px;background:#161d28;border-radius:14px;color:#fff"><div style="color:#6ea4ff">{word(v,"#e8edf5",64)}</div><div style="background:#f4f6f9;color:#0b1f4d;margin-top:12px;padding:12px;border-radius:10px">{word(v,"#0b1f4d",40)}</div><b>Font {v}</b></div>'
    open('/tmp/brand/prop.html','w').write(html+'</body></html>')
