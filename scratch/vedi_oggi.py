import re,html
s=open('/home/claude/armor/site/index.html',encoding='utf-8').read()
t=re.sub(r"<style.*?</style>|<script.*?</script>","",s,flags=re.S)
t=re.sub(r"<[^>]+>"," ",t); t=html.unescape(re.sub(r"\s+"," ",t))
for k in ("Quadro di oggi","Indice Armor 5","Salute del mercato","Indice Armor e Super Armor","Zone di rischio"):
    for m in list(re.finditer(k,t))[:2]: print(k,'|',t[m.start():m.start()+230]); print()
print(len(re.findall(r"data-gi=",s)))
