import csv,gzip,hashlib,json,re,unicodedata,zipfile,os
from pathlib import Path
from collections import defaultdict
R=Path(__file__).resolve().parent;T=R/'tecnico';O=R/'entrega';O.mkdir(exist_ok=True)
def norm(s):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(s).upper()) if not unicodedata.combining(c)).split())
def arr(s):
 if isinstance(s,list):return s
 if not s or s=='{}':return []
 return next(csv.reader([s[1:-1]],escapechar='\\'))
source_zip=Path(os.environ.get('EVAL_SOURCE_ZIP',R.parent/'upload/avaliacao_final_completa(1).zip'))
with zipfile.ZipFile(source_zip)as z:sheet_bytes=z.read('para_especialistas/ficha_revisao_comercial.html')
d=json.loads(re.search(r'<script[^>]*id="studyData"[^>]*>(.*?)</script>',sheet_bytes.decode(),re.S)[1]);key=json.load(open(T/'analyst_key.json'))
snapshot=T/'inputs/source_snapshot';m=json.load(open(snapshot/'manifest.json'))
aud={'source_manifest':m,'files':{},'counts':{},'worksheet_hash':hashlib.sha256(sheet_bytes).hexdigest()}
for name in ['candidates.csv.gz','applications.csv.gz']:
 h=hashlib.sha256((snapshot/name).read_bytes()).hexdigest();assert h==m['files'][name]['sha256'];aud['files'][name]={'sha256':h,'manifest_verified':True}
products=list(csv.DictReader(gzip.open(snapshot/'candidates.csv.gz','rt',encoding='utf-8-sig',newline='')));bp={p['cd_item']:p for p in products};ids={bp[p['code']]['id_item'] for c in d['cases'] for p in (([c['reference_product']] if c['reference_product'] else [])+c['A']['products']+c['B']['products']) if p['code'] in bp}
# Escolha adicional exclusivamente para futuros testes sintéticos, fora dos códigos já usados na ficha.
used={p['code'] for c in d['cases'] for p in (([c['reference_product']] if c['reference_product'] else [])+c['A']['products']+c['B']['products'])}
new_candidates=[]
for pattern in [r'^FILTRO AR ',r'^PALHETA ',r'^KIT EMBREAGEM ',r'^CORREIA ',r'^LIMPA CONTATO',r'^PASTILHA DE FREIO ',r'^AMORTECEDOR DIANTEIRO DIREITO ',r'^RETENTOR ',r'^FILTRO OLEO ']:
 p=next((p for p in products if p['cd_item'] not in used and re.search(pattern,norm(p['candidate_title']))),None)
 if p:new_candidates.append(p);ids.add(p['id_item']);used.add(p['cd_item'])
apps=defaultdict(list);n=0
for a in csv.DictReader(gzip.open(snapshot/'applications.csv.gz','rt',encoding='utf-8-sig',newline='')):
 n+=1
 if a['id_item'] in ids:apps[a['id_item']].append(a)
aud['counts']={'products':len(products),'applications':n};assert len(products)==m['files']['candidates.csv.gz']['rows'] and n==m['files']['applications.csv.gz']['rows']
targets={}
for c in d['cases']:
 msg=c['initial_message'];last=re.split(r' para ',msg,flags=re.I)[-1];model=year=eng=None
 mt=re.match(r'(.+?)\s+(\d{4})(?:\s+motor\s+([\d.,]+))?',last)
 if mt:model=mt[1];year=int(mt[2]);eng=mt[3].replace(',','.') if mt[3] else None
 else:
  mo=re.match(r'(.+?) motor ([\d.,]+)',last)
  if mo:model=mo[1];eng=mo[2].replace(',','.')
  elif len(re.split(r' para ',msg,flags=re.I))>1:model=re.sub(r'\s+(traseiro|dianteiro|esquerdo|direito)$','',last,flags=re.I)
 # Não confundir “para motos” com modelo; o último segmento preserva YS 250 FAZER.
 targets[c['id']]={'model':model,'year':year,'engine':eng}
(R/'cache.json').write_text(json.dumps({'study':d,'key':key,'products':products,'apps':apps,'targets':targets,'new_products':new_candidates},ensure_ascii=False))
(O/'auditoria_catalogo_correto.json').write_text(json.dumps(aud,ensure_ascii=False,indent=2))
print('catálogo',aud['counts'],'produtos auditáveis',len(apps),'aplicações auditáveis',sum(map(len,apps.values())))
