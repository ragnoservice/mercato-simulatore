#!/usr/bin/env python3
"""Aggiorna mercato.json con PUN orario (pun-oggi.it) e PSV giornaliero (quifinanza.it).
Solo libreria standard. Se una fonte non risponde o i dati non sono plausibili, quel dato viene saltato."""
import json,re,sys,html,datetime,urllib.request
from zoneinfo import ZoneInfo
UA='Mozilla/5.0 (compatible; mercato-simulatore/1.0)'
def get(url):
    r=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'it-IT,it;q=0.9'})
    return urllib.request.urlopen(r,timeout=40).read().decode('utf8','replace')
def num(x,lo,hi): return isinstance(x,(int,float)) and lo<=x<=hi
oggi=datetime.datetime.now(ZoneInfo('Europe/Rome')).date()
MESI=['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre']
m=json.load(open('mercato.json',encoding='utf8'))
G=m.setdefault('mercato_giornaliero',{})
log=[]
# --- PUN orario di oggi
try:
    h=get('https://pun-oggi.it/')
    t=re.search(r'<title>PUN oggi,\s*(\d{1,2})\s+([a-zà]+)',h,re.I)
    ok_data=bool(t) and int(t.group(1))==oggi.day and MESI[oggi.month-1]==t.group(2).lower()
    vals={int(a):float(b.replace('.','').replace(',','.'))/1000 for a,b in re.findall(r'data-strip="(\d+)"\s+title="[^"]*·\s*([\d.]+,\d+)\s*€/MWh"',h)}
    po=[round(vals[i],5) for i in range(24)] if len(vals)==24 else None
    if ok_data and po and all(num(x,0,1.5) for x in po):
        d=G.setdefault(oggi.isoformat(),{}); d['punOrario']=po; log.append('PUN orario '+oggi.isoformat())
    else: log.append('PUN saltato (data/valori non validi)')
except Exception as e: log.append('PUN errore: %s'%e)
# --- PSV giornaliero (tabella ultimi giorni)
try:
    h=get('https://quifinanza.it/osservatorio-prezzi/prezzo-psv-gas-oggi/919996/amp/')
    t=html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S)))
    righe=re.findall(r'(\d{2})/(\d{2})/(\d{4})\s+(\d+,\d+)\s*euro/Smc',t)
    n=0
    for gg,mm,aa,v in righe[:12]:
        try: k=datetime.date(int(aa),int(mm),int(gg))
        except ValueError: continue
        v=float(v.replace(',','.'))
        if not num(v,0.1,5) or k>oggi: continue
        d=G.setdefault(k.isoformat(),{})
        if 'psv' not in d or (oggi-k).days<=3: d['psv']=v; n+=1
    log.append('PSV: %d giorni'%n)
except Exception as e: log.append('PSV errore: %s'%e)
for k,v in G.items():
    if v: v['fonte']='pun-oggi.it (GME MGP) / quifinanza.it'
G={k:v for k,v in G.items() if v}
lim=(oggi-datetime.timedelta(days=60)).isoformat()
m['mercato_giornaliero']={k:v for k,v in G.items() if k>=lim}
m['aggiornato']=max(m['mercato_giornaliero']) if m['mercato_giornaliero'] else m.get('aggiornato','')
json.dump(m,open('mercato.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
print(' | '.join(log))
