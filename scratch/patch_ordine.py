p='src/armor/report.py'
b=open(p,'rb').read().decode('utf-8')
lines=b.split('\n')
ip=[i for i,l in enumerate(lines) if "F('Paura, protezioni e prezzi'" in l]
ib=[i for i,l in enumerate(lines) if "F('La bussola di oggi'" in l]
assert len(ip)==1 and len(ib)==1, (ip,ib)
l=lines.pop(ip[0]); ib=[i for i,x in enumerate(lines) if "F('La bussola di oggi'" in x][0]
lines.insert(ib,l)
open(p,'wb').write('\n'.join(lines).encode('utf-8'))
