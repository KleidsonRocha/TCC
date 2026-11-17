import csv,hashlib,html,json,re,shutil,statistics,unicodedata,zipfile,os
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from criterios_371 import PRIOR,ASK,SEARCH,WRONG_REF,SUSPECT,BADQ,IDENTITY
R=Path(__file__).resolve().parent;O=R/'entrega';O.mkdir(exist_ok=True);X=json.load(open(R/'cache.json'));D=X['study'];C=D['cases'];KEY=X['key'];BP={p['cd_item']:p for p in X['products']};AP=X['apps'];NOW=datetime.now(timezone.utc).isoformat()
NOTICE='Revisão exploratória assistida por IA: três perspectivas do mesmo modelo/contexto, sem independência e sem revisão humana. O script aplica julgamentos semânticos explícitos e verificações cadastrais; não executa três modelos nem o chatbot.'
def dump(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2))
def norm(s):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',str(s).upper())if not unicodedata.combining(c)).split())
def arr(s):
 if isinstance(s,list):return s
 if s in ('','{}',None):return []
 return next(csv.reader([s[1:-1]],escapechar='\\'))
def variant(s):return norm(s).replace(' ','')
def first(o):
 s=o['turns'][0]['assistant'].lower()
 return 'handoff'if'encaminhar' in s else 'ask'if'?'in s or 'por favor, informe'in s or 'por favor, especifique'in s else 'search'if o['products']or'nao encontrei'in s or'encontrei'in s or'analisei'in s else 'unknown'
def final(o):
 s=o['turns'][-1]['assistant'].lower()
 return 'items'if o['products']else 'handoff'if'encaminhar'in s and'peca atendimento humano'not in s else 'ask'if'?'in s or'por favor, informe'in s or'por favor, especifique'in s else 'empty_search'if'nao encontrei'in s or'nenhum item'in s else 'unknown'

PATS_PRIOR={'AV-028':r'SAPATA.*FREIO','AV-093':r'ROLAMENTO.*AMORTECEDOR','AV-203':r'ROLAMENTO.*AMORTECEDOR','AV-218':r'KIT.*AMORTECEDOR','AV-296':r'LONA.*FREIO','AV-312':r'POLIA.*BOMBA.*AGUA'}
IDENTITY.update(PATS_PRIOR)
split_ids={'AV-028','AV-047','AV-069','AV-240','AV-298','AV-321'}
bad_prior={'AV-053','AV-063','AV-162','AV-184','AV-250','AV-261','AV-284','AV-328','AV-339','AV-359'}
BADQ.update({cid:'Pergunta não resolve a identidade/função ou especificação indicada no gabarito.'for cid in bad_prior})
explicit_wrong_outputs={
 'AV-123':r'GARFO.*EMBREAGEM','AV-150':r'MACANETA','AV-238':r'MACANETA','AV-171':r'RETENTOR.*CAMBIO','AV-236':r'RETENTOR.*CAMBIO','AV-179':r'BANDEJA','AV-187':r'CHAVE.*SETA','AV-193':r'BOBINA','AV-222':r'^CILINDRO.*MESTRE','AV-223':r'CABO.*VELOCIMETRO','AV-266':r'(AR QUENTE|RESPIRO|TAMPAO)','AV-272':r'ANEL.*SINCRONIZADOR','AV-293':r'ROLETE','AV-331':r'TENSOR.*CORREIA','AV-340':r'REGULADOR.*FREIO','AV-347':r'AMORTECEDOR.*DIANTEIRO',
 'AV-119':r'PINO','AV-348':r'SEMI.?EIXO','AV-358':r'POLIA'}
unresolved_identity={cid for cid in ASK if any(k in norm(ASK[cid])for k in ['DE QUAL','QUAL FUNCAO','QUAL COMPONENTE','DE QUE FUNCAO','IDENTIDADE GENERICA','IDENTIFICAR O COMPONENTE'])}
FN_CODES={'AV-069':'COR-741876','AV-073':'CBV144.525','AV-108':'KT-50072','AV-149':'YM612006','AV-298':'COR-400229','AV-101':'KT-20252','AV-243':'KT-20252','AV-361':'KT-20252'}

# Interpretação inicial: não usa qual braço é D/H; a chave é aplicada somente às métricas.
BASE={}
for c in C:
 cid=c['id'];msg=c['initial_message'];t=X['targets'][cid];rp=c['reference_product'];requested=re.sub(r'^Preciso de\s+','',msg,flags=re.I).split(' para ')[0]
 if cid in PRIOR:
  ac,comp,missing,rv,note=PRIOR[cid];origin='fundamento individual do lote prioritário, reconferido contra snapshot correto'
 else:
  ac='ask'if cid in ASK or not t.get('model')else'search';comp=requested;missing=ASK.get(cid,'Dados suficientes para iniciar pesquisa de candidatos; conferir composição e refinamentos antes de fornecer.');rv='invalid_component'if cid in WRONG_REF else 'no_reference'if not rp else 'unknown';note=WRONG_REF.get(cid,ASK.get(cid,SUSPECT.get(cid,'Pesquisar candidatos pela identidade solicitada e pelos dados explicitamente informados; não aprovar montagem somente por categoria ou vínculo.')));origin='anotação por caso/função e aplicação explícita de critérios de triagem'
 if cid in ['AV-209','AV-244']:ac='ask';note='Há conflito dianteiro/traseiro no próprio pedido. Confirmar posição antes da busca.'
 if cid in ASK:missing=ASK[cid];ac='ask'
 if cid in SEARCH:ac='search';note=SEARCH[cid]
 if cid in WRONG_REF:rv='invalid_component'
 if cid in SUSPECT:note+=' '+SUSPECT[cid];rv='unknown'if rv!='invalid_component'else rv
 BASE[cid]={'case_id':cid,'request':msg,'component':comp,'expected_action':ac,'indispensable_missing':missing,'reference_status':rv,'interpretation':note,'annotation_origin':origin,'target':t,'historical_reference':rp,'catalog_snapshot':'2026-10-19','physical_fit_certified':False}
dump('gabarito_exploratorio_371.json',{'notice':NOTICE,'prior_output_exposure':True,'cases':BASE})
GHASH=hashlib.sha256((O/'gabarito_exploratorio_371.json').read_bytes()).hexdigest()

def matching(c,code,var=None):
 p=BP.get(code);t=BASE[c['id']]['target'];rr=[]
 if not p:return []
 for a in AP.get(p['id_item'],[]):
  if not t.get('model')or norm(a['vehicle_model'])!=norm(t['model']):continue
  if t.get('year')is not None:
   ys=int(a['year_start'])if a['year_start']else None;ye=int(a['year_end'])if a['year_end']else None
   if ys is None or t['year']<ys or(a['year_open_end']not in ['t','true','True']and(ye is None or t['year']>ye)):continue
  if t.get('engine')and not any(re.search(r'(?<![\d.])'+re.escape(t['engine'])+r'(?![\d.])',en)for en in arr(a['engines'])):continue
  if var and variant(var)not in[variant(v)for v in arr(a['variants'])]:continue
  rr.append(a)
 return rr
def catalog_evidence(c,code,var=None):
 p=BP.get(code);rows=matching(c,code,var)
 return {'code':code,'found':bool(p),'id_item':p['id_item']if p else None,'nm_item':p['nm_item']if p else None,'title':p['candidate_title']if p else None,'part_family':p['part_family']if p else None,'same_tuple_matching_count':len(rows),'matching_applications':rows,'all_application_count':len(AP.get(p['id_item'],[]))if p else 0,'physical_fit_certified':False}

FACTS={};reference_evidence={}
for c in C:
 cid=c['id'];b=BASE[cid];reference_evidence[cid]=catalog_evidence(c,c['reference_product']['code'])if c['reference_product']else None
 revid=reference_evidence[cid];pat=IDENTITY.get(cid)
 if b['reference_status']=='unknown'and b['expected_action']=='search'and cid not in SUSPECT and revid and revid['matching_applications']and pat and re.search(pat,norm((revid.get('title')or'')+' '+(revid.get('nm_item')or''))):b['reference_status']='valid'
 facts={}
 for label in ['A','B']:
  o=c[label];state=final(o);ini=first(o);texts=[t['assistant']for t in o['turns']];s=' '.join(texts);bugs=[];hasq=ini=='ask'or any('?'in tx for tx in texts)
  if cid in BADQ and hasq:bugs.append('pergunta_sem_pertinencia_ao_discriminante')
  repeated=len(texts)>1 and len({norm(t)for t in texts})<len(texts)
  if cid in ['AV-005','AV-025','AV-250','AV-298']and len(texts)>1:repeated=True
  if repeated:bugs.append('repeticao_ou_contexto_nao_aproveitado')
  if cid in split_ids and'analisei 2'in s.lower():bugs.append('composicao_desmembrada_incorretamente')
  if cid=='AV-298'and len(texts)>1:bugs.append('modelo_ano_motor_perguntados_novamente')
  if cid=='AV-279':bugs.append('volume_confundido_com_modelo');bugs+=['volume_confundido_com_quantidade']if o['criteria'].get('quantity')==500 else[]
  if cid=='AV-028'and o['criteria'].get('vehicle_year')==2009:bugs.append('ano_do_titulo_substituiu_ano_do_cliente')
  if cid in ['AV-271','AV-366']and hasq and'eixo'in texts[0].lower():bugs.append('posicao_informada_nao_aproveitada')
  prod=[]
  for pp in o['products']:
   code=pp['code'];ce=catalog_evidence(c,code,o['criteria'].get('variant'));tt=norm((ce.get('title')or'')+' '+(ce.get('nm_item')or''));pat=IDENTITY.get(cid)
   wrong=cid in explicit_wrong_outputs and bool(re.search(explicit_wrong_outputs[cid],tt));identity=bool(pat and re.search(pat,tt))
   # Posição/lado somente quando há oposição explícita no título e não há suporte aos dois lados.
   ct=norm(ce.get('title')or'');side=o['criteria'].get('side');pos=o['criteria'].get('position');opposite=False
   if side=='left'and re.search(r'\bDIREIT[OA]\b',ct)and not re.search(r'\bESQUERD[OA]\b|LD/LE|LD / LE',ct):opposite=True
   if side=='right'and re.search(r'\bESQUERD[OA]\b',ct)and not re.search(r'\bDIREIT[OA]\b|LD/LE|LD / LE',ct):opposite=True
   if pos=='front'and re.search(r'\bTRASEIR[OA]\b',ct)and not re.search(r'\bDIANTEIR[OA]\b|DIANT/TRAS|DIANTEIRA/TRASEIRA',ct):opposite=True
   if pos=='rear'and re.search(r'\bDIANTEIR[OA]\b',ct)and not re.search(r'\bTRASEIR[OA]\b|DIANT/TRAS|DIANTEIRA/TRASEIRA',ct):opposite=True
   # Posição interna, giro e função podem usar dianteiro/traseiro/esquerda sem descrever o eixo do veículo.
   if cid in ['AV-140','AV-196','AV-268','AV-353','AV-356']:opposite=False
   status='incompatible_identity'if wrong else'incompatible_position'if opposite and identity else'registry_supported_candidate'if identity and ce['matching_applications']and cid not in SUSPECT and cid not in unresolved_identity else'undetermined'
   if cid in ['AV-152','AV-194']:status='undetermined'
   if cid=='AV-296'and code=='CB/40':status='undetermined'
   if cid=='AV-028'and code=='CB/49-CPA'and ce['matching_applications']:status='registry_supported_candidate'
   if cid in explicit_wrong_outputs and wrong:bugs.append('produto_de_outra_identidade_ou_composicao')
   if status=='incompatible_position':bugs.append('produto_com_posicao_oposta_explicita')
   ce['judgment']=status;ce['identity_pattern']=pat;prod.append(ce)
  if o['products']and cid in unresolved_identity:bugs.append('componente_generico_selecionado_sem_confirmacao')
  gap=None
  if cid in FN_CODES and state=='empty_search':
   code=FN_CODES[cid];ee=catalog_evidence(c,code,o['criteria'].get('variant'))
   if ee['matching_applications']:
    gap={'code':code,'application_id':ee['matching_applications'][0]['application_id'],'evidence':ee,'scope':'Falso negativo cadastral do componente identificado no pedido. Não demonstra estoque ou encaixe físico; causa interna não adjudicada.'};bugs.append('lacuna_recuperacao_cadastral')
  # Lista vazia nunca confirma ausência comercial sem investigação apropriada.
  facts[label]={'configuration':KEY['cases'][cid]['arms'][label],'initial_action':ini,'final_state':state,'initial_action_match':ini==b['expected_action'],'questions_present':hasq,'bugs':sorted(set(bugs)),'products':prod,'top1':'no_items'if not prod else'compatible'if prod[0]['judgment']=='registry_supported_candidate'else'incompatible'if prod[0]['judgment'].startswith('incompatible')else'undetermined','top3':'no_items'if not prod else'yes'if any(p['judgment']=='registry_supported_candidate'for p in prod[:3])else'no'if all(p['judgment'].startswith('incompatible')for p in prod[:3])else'unknown','registry_retrieval_gap':gap}
 FACTS[cid]=facts
dump('evidencias_referencias_371.json',reference_evidence);dump('verificacoes_742_saidas.json',{'notice':NOTICE,'cases':FACTS})
dump('gabarito_exploratorio_371.json',{'notice':NOTICE,'prior_output_exposure':True,'cases':BASE})
GHASH=hashlib.sha256((O/'gabarito_exploratorio_371.json').read_bytes()).hexdigest()

PERSONAS=[('IA_BALCAO_V3','Carlos — balcão','Compreensão, perguntas úteis, continuidade e confirmação da necessidade.'),('IA_APLICACAO_V3','Márcia — aplicação','Identidade/composição e evidência de aplicação; encaminhamento seguro quando faltam dados.'),('IA_AUDITORIA_V3','Renato — auditoria','Rastreabilidade, fidelidade dos critérios e falhas comprovadas de busca e integração.')]
def grade(cid,label,pid):
 f=FACTS[cid][label];b=BASE[cid];bugs=set(f['bugs']);state=f['final_state'];has=bool(f['products']);expected=b['expected_action'];g='partly'
 severe=bool(bugs&{'produto_de_outra_identidade_ou_composicao','produto_com_posicao_oposta_explicita','composicao_desmembrada_incorretamente','modelo_ano_motor_perguntados_novamente','volume_confundido_com_modelo','ano_do_titulo_substituiu_ano_do_cliente','lacuna_recuperacao_cadastral'})
 wrongq='pergunta_sem_pertinencia_ao_discriminante'in bugs;repeat='repeticao_ou_contexto_nao_aproveitado'in bugs
 if severe:g='inadequate'
 elif pid=='IA_APLICACAO_V3':
  if has:g='inadequate'if f['top1']=='incompatible'else'adequate'if f['top1']=='compatible'and expected!='ask'else'unknown'
  elif state=='handoff':g='adequate'if expected in ['ask','handoff']and not wrongq else'partly'
  elif expected=='ask'and state=='ask':g='partly'if wrongq or repeat else'adequate'
 elif pid=='IA_BALCAO_V3':
  if wrongq or repeat:g='inadequate'if cid not in ['AV-005','AV-025']else'partly'
  elif has:g='inadequate'if'componente_generico_selecionado_sem_confirmacao'in bugs else'adequate'if f['top1']=='compatible'and expected!='ask'else'partly'
  elif state=='handoff':g='adequate'if expected=='handoff'or(expected=='ask'and f['initial_action']=='ask')else'partly'
  elif state=='ask'and expected=='ask':g='adequate'
 else:
  if wrongq or repeat:g='inadequate'
  elif has:g='inadequate'if'componente_generico_selecionado_sem_confirmacao'in bugs else'adequate'if f['top1']=='compatible'and expected!='ask'else'partly'
  elif state=='handoff':g='adequate'if expected=='handoff'or(expected=='ask'and f['initial_action']=='ask')else'partly'
  elif state=='ask'and expected=='ask':g='adequate'
 if cid in ['AV-209','AV-244','AV-306']and state=='ask'and not severe:g='adequate'
 if g=='adequate'and has and any(p['judgment']!='registry_supported_candidate'for p in f['products']):g='partly'
 reasons=[b['interpretation'],b['indispensable_missing']]
 if cid in BADQ and f['questions_present']:reasons.append(BADQ[cid])
 if severe:reasons.append('Falha comprovada neste escopo: '+', '.join(sorted(bugs))+'.')
 if has and f['top1']=='undetermined':reasons.append('Top-1 não aprovado: vínculo cadastral e identidade/variante/refinamentos não bastam para conclusão técnica.')
 if has and any(p['judgment']!='registry_supported_candidate'for p in f['products']):reasons.append('Nem todos os candidatos apresentados foram aprovados; Top-1 sustentado não certifica a lista inteira.')
 if state=='handoff':reasons.append('Encaminhamento evita indicação sem suporte; não confirma ausência no catálogo. Pode ser parcial em autonomia/compreensão e adequado em contenção de risco.')
 return g,' '.join(reasons)

ANS=[];table=[]
for pid,name,focus in PERSONAS:
 a={'schema_version':'1.0','study_id':D['study_id'],'reviewer_id':pid,'experience':'PERSONA FICTÍCIA POR IA — '+name+'. '+focus,'simulation':True,'methodology':{'notice':NOTICE,'snapshot':'2026-10-19','ground_truth_hash':GHASH,'independent':False,'human_review':False,'prior_output_exposure':True,'configuration_key_used_for_aggregation':True},'assessments':{},'audit':[{'event':'retrospective_explicit_rubric_application','at':NOW}]}
 for c in C:
  cid=c['id'];b=BASE[cid];ref=reference_evidence[cid];allowed=ref['code']if ref and ref['matching_applications']and b['reference_status']=='valid'else'indeterminado'
  e={'reference':{'coherence':'contradictory'if cid in ['AV-009','AV-209','AV-244','AV-306']else'missing_information'if b['expected_action']=='ask'else'coherent','correct_component':b['component'],'correct_application':json.dumps(b['target'],ensure_ascii=False)+'; demais dados: '+b['request'],'missing_fields':b['indispensable_missing'],'correct_action':b['expected_action'],'reference_valid':b['reference_status'],'compatible_codes':allowed,'no_match_truth':'exists'if allowed!='indeterminado'else'insufficient_information','evidence':b['interpretation']+' Snapshot 19/10/2026. Ver evidencias_referencias_371.json e verificacoes_742_saidas.json.','evidence_strength':'partial'},'reference_locked_at':NOW,'reference_edited_after_outputs':True,'simulation':True}
  for label in ['A','B']:
   f=FACTS[cid][label];g,reason=grade(cid,label,pid);has=bool(f['products']);badq='pergunta_sem_pertinencia_ao_discriminante'in f['bugs'];repeat='repeticao_ou_contexto_nao_aproveitado'in f['bugs']
   e[label]={'intent':'no'if any(x in f['bugs']for x in ['produto_de_outra_identidade_ou_composicao','composicao_desmembrada_incorretamente','volume_confundido_com_modelo'])else'partly'if f['bugs']else'yes','questions':'no'if badq else'partly'if repeat else'unknown'if f['questions_present']and b['expected_action']=='search'else'yes'if f['questions_present']else'not_applicable','repetition':'yes'if repeat else'no','handoff':'yes'if f['final_state']=='handoff'and b['expected_action']in['ask','handoff']else'partly'if f['final_state']=='handoff'else'not_applicable','top1':f['top1'],'top3':f['top3'],'absence':'not_applicable'if has else'false_negative'if f['registry_retrieval_gap']else'missing_information'if b['expected_action']=='ask'else'unknown','error_reason':reason,'overall':g,'risk':'high'if has and(g in ['inadequate','unknown']or f['top1']!='compatible')else'medium'if g=='inadequate'else'low'}
   for p in f['products'][:10]:e[label]['code_'+p['code']]='compatible'if p['judgment']=='registry_supported_candidate'else'incompatible'if p['judgment'].startswith('incompatible')else'unknown'
  va=e['A']['overall'];vb=e['B']['overall'];rank={'adequate':3,'partly':2,'inadequate':0};choice='unknown'if'unknown'in[va,vb]else'A'if rank[va]>rank[vb]else'B'if rank[vb]>rank[va]else'neither'if va=='inadequate'else'tie';e['preference']={'choice':choice,'reason':'Comparação pela rubrica da perspectiva; discordância e indeterminação preservadas. Não é adjudicação humana.'};a['assessments'][cid]=e
 ANS.append(a);dump('avaliacao_'+pid+'.json',a)
 for scope in ['all_371','priority_60','additional_311']:
  cc=[c for c in C if scope=='all_371'or(scope=='priority_60'and c['priority'])or(scope=='additional_311'and not c['priority'])]
  for arm in ['D','H']:
   vv=[a['assessments'][c['id']][next(l for l,v in KEY['cases'][c['id']]['arms'].items()if v==arm)]['overall']for c in cc];co=Counter(vv);table.append({'persona':pid,'scope':scope,'arm':arm,'n':len(vv),**{k:co[k]for k in ['adequate','partly','inadequate','unknown']},'strict_adequate_percent':round(co['adequate']/len(vv)*100,2)})

dis=[];synth=[];tax=defaultdict(lambda:Counter());pairedprefs=[]
for c in C:
 cid=c['id'];group=KEY['cases'][cid]['group_code']
 for label in ['A','B']:
  vv={a['reviewer_id']:a['assessments'][cid][label]['overall']for a in ANS};vals=set(vv.values());status=next(iter(vals))if len(vals)==1 else'unknown'if'unknown'in vals else'partly';arm=FACTS[cid][label]['configuration'];synth.append({'case_id':cid,'configuration':arm,'label':label,'synthesis':status,'perspectives':vv});tax[(group,arm)][status]+=1
  if len(vals)>1:dis.append({'case_id':cid,'label':label,'configuration':arm,'judgments':vv,'human_adjudication':'pendente'})
 for a in ANS:
  ee=a['assessments'][cid];vD=ee[next(l for l,arm in KEY['cases'][cid]['arms'].items()if arm=='D')]['overall'];vH=ee[next(l for l,arm in KEY['cases'][cid]['arms'].items()if arm=='H')]['overall'];rank={'adequate':3,'partly':2,'inadequate':0};pref='indeterminado'if'unknown'in[vD,vH]else'H'if rank[vH]>rank[vD]else'D'if rank[vD]>rank[vH]else'empate';pairedprefs.append({'case_id':cid,'persona':a['reviewer_id'],'preference':pref})
metrics={'notice':NOTICE,'configuration_names':{'D':'Arquitetura determinística; handoff conservador no ponto residual','H':'Mesma arquitetura com Qwen2.5:7b residual e validações existentes'},'fine_tuned_comparison':False,'counts':table,'unique_initial_requests':len({norm(c['initial_message'])for c in C}),'scope':'371 duplas da primeira repetição; 3 perspectivas por saída = 2226 julgamentos. Outras repetições verificadas tecnicamente, não contadas como novos clientes.','synthesis_counts':{arm:dict(Counter(x['synthesis']for x in synth if x['configuration']==arm))for arm in['D','H']},'paired_preferences':{pid:dict(Counter(p['preference']for p in pairedprefs if p['persona']==pid))for pid,_,_ in PERSONAS},'do_not_pool_partial_with_adequate':True,'not_human_accuracy':True}
dump('metricas_por_configuracao.json',metrics);dump('discordancias_e_sintese.json',{'notice':NOTICE,'disagreements':dis,'synthesis':synth,'rule':'Somente concordância unânime mantém classe; divergência com indeterminado fica indeterminada, demais divergências parciais. Não cria verdade técnica.'})
dump('metricas_por_grupo.json',[{'group_code':g,'arm':a,**dict(co)}for(g,a),co in sorted(tax.items())])
with(O/'avaliacoes_371.csv').open('w',newline='',encoding='utf-8-sig')as file:
 w=csv.writer(file);w.writerow(['caso','prioritario','grupo','persona','saida','configuracao','pedido','acao_esperada','acao_observada','conducao','top1_cadastral','top3_cadastral','falhas','justificativa'])
 for a in ANS:
  for c in C:
   cid=c['id']
   for l in['A','B']:
    f=FACTS[cid][l];e=a['assessments'][cid][l];w.writerow([cid,c['priority'],KEY['cases'][cid]['group_code'],a['reviewer_id'],l,f['configuration'],c['initial_message'],BASE[cid]['expected_action'],f['initial_action'],e['overall'],e['top1'],e['top3'],';'.join(f['bugs']),e['error_reason']])
gaps=[{'case_id':cid,'label':l,'arm':f['configuration'],**f['registry_retrieval_gap']}for cid,ff in FACTS.items()for l,f in ff.items()if f['registry_retrieval_gap']];dump('lacunas_recuperacao.json',gaps)
dump('protocolo_avaliacao_371.json',{'notice':NOTICE,'created_at':NOW,'source_snapshot':'2026-10-19','catalog_counts':{'products':52798,'applications':1779443},'previous_snapshot_superseded':'Snapshot de 14/09/2026 usado na versão 2; substituído nesta extensão pela fonte efetiva do ensaio. Não comparar percentuais como se apenas a amostra tivesse mudado.','ground_truth_hash':GHASH,'prior_output_exposure':True,'independent_reviewers':False,'human_reviewer_count':0,'prospective_registration':False,'review_depth':'Anotações semânticas explícitas por caso/função e verificações de todo o vínculo cadastral para referências/candidatos. Aplicação programática de rubricas, não 3 chamadas de LLM independentes.','cases':371,'outputs':742,'judgments':2226,'configuration_key_used_after_semantic_baseline':True,'rubrics':{pid:focus for pid,name,focus in PERSONAS},'limits':['Ausência não confirmada sem critério fechado.','Compatibilidade cadastral não é ensaio de montagem.','Perguntas, encaminhamentos e resultados têm denominadores distintos.','Três repetições não são três amostras independentes.','Fonte e rubrica da extensão são registradas como versão 3.','Adjudicação humana e dez pedidos reais novos permanecem pendentes.']})

dump('personas.json',{'notice':NOTICE,'profiles':[{'id':pid,'name':name,'focus':focus}for pid,name,focus in PERSONAS]})
with zipfile.ZipFile(Path(os.environ.get('EVAL_SOURCE_ZIP',R.parent/'upload/avaliacao_final_completa(1).zip')))as z:(O/'ficha_original_para_importar.html').write_bytes(z.read('para_especialistas/ficha_revisao_comercial.html'))
dump('chave_configuracoes.json',KEY)
print(json.dumps({'metrics':[r for r in table if r['scope']=='all_371'],'synthesis':metrics['synthesis_counts'],'gaps':[(g['case_id'],g['arm'],g['code'])for g in gaps],'disagreements':len(dis),'unique_requests':metrics['unique_initial_requests']},ensure_ascii=False,indent=2))
