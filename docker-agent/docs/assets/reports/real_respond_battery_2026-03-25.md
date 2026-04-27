# Bateria Real De 50 Testes - 2026-03-25

## Escopo

Relatorio gerado por chamadas reais ao `POST /respond`, sem `StubPreSearchValidator`, `_FakeTools` ou `TestClient` sobrescrito.

- total de testes executados: `50`
- endpoint: `http://localhost:8001/respond`
- trace prefix: `real-battery-20260325`

## Resumo

- respostas HTTP 200: `48`
- respostas com `request_info`: `27`
- respostas com `show_items`: `17`
- respostas com `handoff.required=true`: `4`
- erros HTTP: `2`
- latencia minima observada: `3.46 ms`
- latencia maxima observada: `67884.72 ms`
- latencia media observada: `39279.70 ms`

## Resumo Por Categoria

- `complete`: casos=`5`, http_200=`5`, request_info=`2`, show_items=`3`, handoff=`0`, erros=`0`
- `complete_alias`: casos=`7`, http_200=`7`, request_info=`2`, show_items=`5`, handoff=`0`, erros=`0`
- `follow_up`: casos=`14`, http_200=`14`, request_info=`6`, show_items=`4`, handoff=`4`, erros=`0`
- `follow_up_text_engine`: casos=`1`, http_200=`1`, request_info=`1`, show_items=`0`, handoff=`0`, erros=`0`
- `partial`: casos=`13`, http_200=`13`, request_info=`10`, show_items=`3`, handoff=`0`, erros=`0`
- `partial_generic`: casos=`2`, http_200=`2`, request_info=`2`, show_items=`0`, handoff=`0`, erros=`0`
- `typo_complete`: casos=`4`, http_200=`4`, request_info=`2`, show_items=`2`, handoff=`0`, erros=`0`
- `typo_partial`: casos=`2`, http_200=`2`, request_info=`2`, show_items=`0`, handoff=`0`, erros=`0`
- `validation_error`: casos=`2`, http_200=`0`, request_info=`0`, show_items=`0`, handoff=`0`, erros=`2`

## Casos

### case_001 - complete

- `trace_id`: `real-battery-20260325-case_001`
- `conversation_id`: `conv-radiador-gol-direct-001`
- pergunta: `radiador gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `67884.72 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}, {'item_id': '20405', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - SUPERIOR RADIADOR', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `RV-12528` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/` | `score=0.64`
  - `IR48108` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `IR48109` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T` | `score=0.64`
  - `RV-12527` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `TRC0017` | `RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6` | `score=0.64`

### case_002 - complete

- `trace_id`: `real-battery-20260325-case_002`
- `conversation_id`: `conv-radiador-ecosport-direct-001`
- pergunta: `radiador ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `33998.06 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MV-312', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `IR48524` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733*A` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS` | `score=0.64`
  - `JAM-7555` | `MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0` | `score=0.56`
  - `JAM-7553` | `MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR` | `score=0.56`

### case_003 - typo_complete

- `trace_id`: `real-battery-20260325-case_003`
- `conversation_id`: `conv-radiador-ecosport-typo-001`
- pergunta: `rdiador ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `35228.44 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MV-312', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `IR48524` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733*A` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS` | `score=0.64`
  - `JAM-7555` | `MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0` | `score=0.56`
  - `JAM-7553` | `MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR` | `score=0.56`

### case_004 - complete_alias

- `trace_id`: `real-battery-20260325-case_004`
- `conversation_id`: `conv-radiador-gol-alias-001`
- pergunta: `radiador motor gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `37129.42 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}, {'item_id': '20405', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - SUPERIOR RADIADOR', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `RV-12528` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/` | `score=0.64`
  - `IR48108` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `IR48109` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T` | `score=0.64`
  - `RV-12527` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `TRC0017` | `RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6` | `score=0.64`

### case_005 - complete

- `trace_id`: `real-battery-20260325-case_005`
- `conversation_id`: `conv-coxim-ecosport-direct-001`
- pergunta: `coxim amortecedor ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `41861.94 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `022.1505` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `022.1553` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.` | `score=0.64`
  - `SP-2722` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `043.1688` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO` | `score=0.64`
  - `SP-2722A` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA` | `score=0.64`

### case_006 - typo_complete

- `trace_id`: `real-battery-20260325-case_006`
- `conversation_id`: `conv-coxim-ecosport-typo-001`
- pergunta: `coxin amortecedor ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `39918.42 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `022.1505` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `022.1553` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.` | `score=0.64`
  - `SP-2722` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `043.1688` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO` | `score=0.64`
  - `SP-2722A` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA` | `score=0.64`

### case_007 - complete_alias

- `trace_id`: `real-battery-20260325-case_007`
- `conversation_id`: `conv-coxim-ecosport-alias-001`
- pergunta: `coxim amort ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `38390.16 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `022.1505` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `022.1553` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.` | `score=0.64`
  - `SP-2722` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `043.1688` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO` | `score=0.64`
  - `SP-2722A` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA` | `score=0.64`

### case_008 - complete_alias

- `trace_id`: `real-battery-20260325-case_008`
- `conversation_id`: `conv-coxim-ecosport-plural-001`
- pergunta: `coxins amortecedor ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `41674.62 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `022.1505` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `022.1553` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.` | `score=0.64`
  - `SP-2722` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `043.1688` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO` | `score=0.64`
  - `SP-2722A` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA` | `score=0.64`

### case_009 - complete

- `trace_id`: `real-battery-20260325-case_009`
- `conversation_id`: `conv-pastilha-gol-direct-001`
- pergunta: `pastilha de freio gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `41645.29 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_010 - typo_complete

- `trace_id`: `real-battery-20260325-case_010`
- `conversation_id`: `conv-pastilha-gol-typo-001`
- pergunta: `pstilhas de freio gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `41964.87 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_011 - complete_alias

- `trace_id`: `real-battery-20260325-case_011`
- `conversation_id`: `conv-pastilha-gol-alias-001`
- pergunta: `pastilhas freio gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `38414.99 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_012 - complete_alias

- `trace_id`: `real-battery-20260325-case_012`
- `conversation_id`: `conv-pastilha-gol-short-001`
- pergunta: `pastilha gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `40736.51 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_013 - complete

- `trace_id`: `real-battery-20260325-case_013`
- `conversation_id`: `conv-disco-gol-direct-001`
- pergunta: `disco de freio gol 2010 dianteiro`
- status HTTP: `200`
- latencia total observada: `35521.02 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'discos de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_014 - complete_alias

- `trace_id`: `real-battery-20260325-case_014`
- `conversation_id`: `conv-radiador-ecosport-plural-001`
- pergunta: `radiadores motor ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `37568.67 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MV-312', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `IR48524` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733*A` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS` | `score=0.64`
  - `JAM-7555` | `MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0` | `score=0.56`
  - `JAM-7553` | `MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR` | `score=0.56`

### case_015 - complete_alias

- `trace_id`: `real-battery-20260325-case_015`
- `conversation_id`: `conv-radiador-gol-plural-001`
- pergunta: `radiadores arrefecimento gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `42977.5 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}, {'item_id': '20405', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - SUPERIOR RADIADOR', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `RV-12528` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/` | `score=0.64`
  - `IR48108` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `IR48109` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T` | `score=0.64`
  - `RV-12527` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `TRC0017` | `RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6` | `score=0.64`

### case_016 - partial

- `trace_id`: `real-battery-20260325-case_016`
- `conversation_id`: `conv-radiador-gol-follow-001`
- pergunta: `radiador gol 2010`
- status HTTP: `200`
- latencia total observada: `32754.46 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_017 - partial

- `trace_id`: `real-battery-20260325-case_017`
- `conversation_id`: `conv-radiador-ecosport-follow-001`
- pergunta: `radiador ecosport 2008`
- status HTTP: `200`
- latencia total observada: `44492.85 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_018 - partial

- `trace_id`: `real-battery-20260325-case_018`
- `conversation_id`: `conv-coxim-ecosport-follow-num-001`
- pergunta: `coxim amortecedor ecosport 2008`
- status HTTP: `200`
- latencia total observada: `45300.0 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_019 - partial

- `trace_id`: `real-battery-20260325-case_019`
- `conversation_id`: `conv-pastilha-gol-follow-001`
- pergunta: `pastilha de freio gol 2010`
- status HTTP: `200`
- latencia total observada: `33070.62 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_020 - partial

- `trace_id`: `real-battery-20260325-case_020`
- `conversation_id`: `conv-filtro-oleo-gol-follow-001`
- pergunta: `filtro de oleo gol 2010`
- status HTTP: `200`
- latencia total observada: `34365.6 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'LBM1', 'title': 'MAXI FILTRO DE OLEO FIAT 147/UNO/TEMPRA - FORD/VW CHT TODOS - KA/', 'score': 0.48}, {'item_id': 'LBM1*A', 'title': 'MAXI FILTRO DE OLEO FIAT 147/UNO/TEMPRA - FORD/VW CHT TODOS - KA/', 'score': 0.48}, {'item_id': 'W712/8', 'title': 'FILTRO OLEO PEUGEOT 106/206/306/405/504/605', 'score': 0.4}, {'item_id': 'W712/53', 'title': 'FILTRO OLEO VW GOL/PARATI 1.0 MI 8/16V - TODOS', 'score': 0.4}, {'item_id': 'W7125', 'title': 'FILTRO OLEO VW GOL/PARATI 1.0 MI 8/16V - TODOS', 'score': 0.4}, {'item_id': 'W7143', 'title': 'FILTRO OLEO FORD FIESTA/COURIER 96/99 ENDURA - KA TODOS', 'score': 0.4}, {'item_id': 'W7MULTI3/4-S', 'title': 'FILTRO OLEO MULTI VW AE TODOS - FIESTA/ECOSPORT/KA/FOCUS', 'score': 0.4}, {'item_id': 'W7MULTI3/4-S*A', 'title': 'FILTRO OLEO MULTI VW AE TODOS - FIESTA/ECOSPORT/KA/FOCUS', 'score': 0.4}, {'item_id': 'LBM2', 'title': 'MAXI FILTRO OLEO FORD C/MOTOR AP TODOS - VW TODOS C/MOTOR AP/AT', 'score': 0.4}, {'item_id': 'LBM2*A', 'title': 'MAXI FILTRO OLEO FORD C/MOTOR AP TODOS - VW TODOS C/MOTOR AP/AT', 'score': 0.4}]}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de oleo', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `LBM1` | `MAXI FILTRO DE OLEO FIAT 147/UNO/TEMPRA - FORD/VW CHT TODOS - KA/` | `score=0.48`
  - `LBM1*A` | `MAXI FILTRO DE OLEO FIAT 147/UNO/TEMPRA - FORD/VW CHT TODOS - KA/` | `score=0.48`
  - `W712/8` | `FILTRO OLEO PEUGEOT 106/206/306/405/504/605` | `score=0.4`
  - `W712/53` | `FILTRO OLEO VW GOL/PARATI 1.0 MI 8/16V - TODOS` | `score=0.4`
  - `W7125` | `FILTRO OLEO VW GOL/PARATI 1.0 MI 8/16V - TODOS` | `score=0.4`

### case_021 - partial

- `trace_id`: `real-battery-20260325-case_021`
- `conversation_id`: `conv-bandeja-ecosport-follow-001`
- pergunta: `bandeja ecosport 2008`
- status HTTP: `200`
- latencia total observada: `32677.08 ms`
- resposta: `Qual lado da peca?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'side', 'prompt': 'Qual lado da peca?', 'options': ['Esquerdo', 'Direito', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_022 - partial

- `trace_id`: `real-battery-20260325-case_022`
- `conversation_id`: `conv-filtro-comb-gol-follow-001`
- pergunta: `filtro de combustivel gol 2010`
- status HTTP: `200`
- latencia total observada: `34322.48 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'WK58/3', 'title': 'FILTRO DE COMBUSTIVEL RENAULT LOGAN/SANDERO/FLUENCE/DUSTER/MEGANE - VW NOVO GOL/VOYAGE/SAVEIRO 2008/', 'score': 0.56}, {'item_id': 'WK730/4', 'title': 'FILTRO COMBUSTIVEL VW GOL/SAVEIRO TOTALFLEX', 'score': 0.4}, {'item_id': 'WK830/7*A', 'title': 'FILTRO COMBUSTIVEL VW PASSAT ALEMAO 1.8/2.0/2.8 - 96/', 'score': 0.4}, {'item_id': 'WK613/4', 'title': 'FILTRO COMBUSTIVEL VW GOL/PARATI/SANTANA/QUANTUM /96 TODOS', 'score': 0.4}, {'item_id': 'UN68', 'title': 'FILTRO COMBUSTIVEL UNIVERSAL GRANDE 6/8 MM - P/VEICULOS CARBURADOS', 'score': 0.4}, {'item_id': 'UN86', 'title': 'FILTRO COMBUSTIVEL UNIVERSAL PEQUENO 6/8 MM - P/VEICULOS CARBURADOS', 'score': 0.4}, {'item_id': 'FS07/1', 'title': 'FILTRO COMBUSTIVEL VW GOL/PARATI/SANTANA/QUANTUM /96 TODOS - BICO FINO/GROSSO', 'score': 0.4}, {'item_id': 'FS12/7', 'title': 'FILTRO COMBUSTIVEL VW GOL/PARATI/SAVEIRO 2003/ FLEX - FOX/CROSSFOX/SPACEFOX 2003/ FLEX', 'score': 0.4}, {'item_id': 'WK613/3', 'title': 'FILTRO COMBUSTIVEL VW GOL/PARATI/SAVEIRO/KOMBI MI 97/ TODOS - FOX 1.6 - NOVO POLO 1.0/1.6', 'score': 0.4}, {'item_id': 'FS50/7', 'title': 'FILTRO COMBUSTÍVEL RENAULT DUSTER OROCH 15/ CHERY QQ 10/15 CITROEN AIR CROSS 10/ HYUNDAI CRETA', 'score': 0.4}]}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de combustivel', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `WK58/3` | `FILTRO DE COMBUSTIVEL RENAULT LOGAN/SANDERO/FLUENCE/DUSTER/MEGANE - VW NOVO GOL/VOYAGE/SAVEIRO 2008/` | `score=0.56`
  - `WK730/4` | `FILTRO COMBUSTIVEL VW GOL/SAVEIRO TOTALFLEX` | `score=0.4`
  - `WK830/7*A` | `FILTRO COMBUSTIVEL VW PASSAT ALEMAO 1.8/2.0/2.8 - 96/` | `score=0.4`
  - `WK613/4` | `FILTRO COMBUSTIVEL VW GOL/PARATI/SANTANA/QUANTUM /96 TODOS` | `score=0.4`
  - `UN68` | `FILTRO COMBUSTIVEL UNIVERSAL GRANDE 6/8 MM - P/VEICULOS CARBURADOS` | `score=0.4`

### case_023 - partial

- `trace_id`: `real-battery-20260325-case_023`
- `conversation_id`: `conv-filtro-ar-gol-follow-001`
- pergunta: `filtro ar motor gol 2010`
- status HTTP: `200`
- latencia total observada: `37739.44 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'HLP6093', 'title': 'FILTRO AR VW GOLF IV 1.6/1.8/2.0 98/ - BORA TODOS', 'score': 0.4}, {'item_id': 'HLP6093*A', 'title': 'FILTRO AR VW GOLF IV 1.6/1.8/2.0 98/ - BORA TODOS', 'score': 0.4}, {'item_id': 'C2990', 'title': 'FILTRO AR VW GOL/PARATI 1.0 MI 16V/POWER 01.01/ - GOLF 1.6 8V', 'score': 0.4}, {'item_id': 'C29108', 'title': 'FILTRO AR VW GOL 1.0 95/96 1.0 16V 97/ - GOL 2.0 EFI 95/ - GOL', 'score': 0.4}, {'item_id': 'CU3162', 'title': 'FILTRO AR CONDICIONADO VW GOL/PARATI/SAVEIRO 99/ - GERACAO III', 'score': 0.4}, {'item_id': 'CU3162*A', 'title': 'FILTRO AR CONDICIONADO VW GOL/PARATI/SAVEIRO 99/ - GERACAO III', 'score': 0.4}, {'item_id': 'HLP6091', 'title': 'FILTRO AR VW GOL 1.0 95/96 1.0 16V 97/ - GOL 2.0 EFI 95/ - GOL', 'score': 0.4}, {'item_id': 'HLP6091*A', 'title': 'FILTRO AR VW GOL 1.0 95/96 1.0 16V 97/ - GOL 2.0 EFI 95/ - GOL', 'score': 0.4}, {'item_id': 'HLP6096', 'title': 'FILTRO AR VW GOL/PARATI 1.0 8V/POWER 08.2001/ - FOX 1.0 2003/ - BAIXO', 'score': 0.4}, {'item_id': 'HLP6096*A', 'title': 'FILTRO AR VW GOL/PARATI 1.0 8V/POWER 08.2001/ - FOX 1.0 2003/ - BAIXO', 'score': 0.4}]}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de ar do motor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `HLP6093` | `FILTRO AR VW GOLF IV 1.6/1.8/2.0 98/ - BORA TODOS` | `score=0.4`
  - `HLP6093*A` | `FILTRO AR VW GOLF IV 1.6/1.8/2.0 98/ - BORA TODOS` | `score=0.4`
  - `C2990` | `FILTRO AR VW GOL/PARATI 1.0 MI 16V/POWER 01.01/ - GOLF 1.6 8V` | `score=0.4`
  - `C29108` | `FILTRO AR VW GOL 1.0 95/96 1.0 16V 97/ - GOL 2.0 EFI 95/ - GOL` | `score=0.4`
  - `CU3162` | `FILTRO AR CONDICIONADO VW GOL/PARATI/SAVEIRO 99/ - GERACAO III` | `score=0.4`

### case_024 - partial

- `trace_id`: `real-battery-20260325-case_024`
- `conversation_id`: `conv-disco-gol-follow-001`
- pergunta: `disco de freio gol 2010`
- status HTTP: `200`
- latencia total observada: `35470.19 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'discos de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_025 - partial

- `trace_id`: `real-battery-20260325-case_025`
- `conversation_id`: `conv-farol-gol-follow-001`
- pergunta: `farol gol 2010`
- status HTTP: `200`
- latencia total observada: `46661.87 ms`
- resposta: `Qual peca voce precisa?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Qual peca voce precisa?'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_026 - partial

- `trace_id`: `real-battery-20260325-case_026`
- `conversation_id`: `conv-radiador-focus-follow-001`
- pergunta: `radiador focus 2010`
- status HTTP: `200`
- latencia total observada: `34223.0 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['DURATEC', 'DURATEC HE', 'SIGMA', 'ZETEC ROCAM', 'ZETEC-S']}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Focus', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_027 - partial

- `trace_id`: `real-battery-20260325-case_027`
- `conversation_id`: `conv-coxim-ecosport-follow-text-001`
- pergunta: `coxim amortecedor ecosport 2008`
- status HTTP: `200`
- latencia total observada: `41302.02 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_028 - partial

- `trace_id`: `real-battery-20260325-case_028`
- `conversation_id`: `conv-pastilha-ecosport-follow-001`
- pergunta: `pastilha de freio ecosport 2008`
- status HTTP: `200`
- latencia total observada: `35450.67 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['DRAGON', 'DURATEC', 'DURATEC HE', 'SIGMA', 'ZETEC ROCAM']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_029 - partial_generic

- `trace_id`: `real-battery-20260325-case_029`
- `conversation_id`: `conv-generic-part-follow-001`
- pergunta: `quero uma peca`
- status HTTP: `200`
- latencia total observada: `32400.67 ms`
- resposta: `Poderia me informar qual peça você precisa?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Poderia me informar qual peça você precisa?'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': None, 'vehicle_year': None, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_030 - partial_generic

- `trace_id`: `real-battery-20260325-case_030`
- `conversation_id`: `conv-generic-gol-follow-001`
- pergunta: `preciso de ajuda com uma peca do gol`
- status HTTP: `200`
- latencia total observada: `35363.85 ms`
- resposta: `Qual a família da peça que você precisa?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Qual a família da peça que você precisa?'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': None, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_031 - follow_up

- `trace_id`: `real-battery-20260325-case_031`
- `conversation_id`: `conv-radiador-gol-follow-001`
- `parent_case_id`: `case_016`
- pergunta: `1.0`
- status HTTP: `200`
- latencia total observada: `42153.78 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}, {'item_id': '20405', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - SUPERIOR RADIADOR', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `RV-12528` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/` | `score=0.64`
  - `IR48108` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `IR48109` | `RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T` | `score=0.64`
  - `RV-12527` | `RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M` | `score=0.64`
  - `TRC0017` | `RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6` | `score=0.64`

### case_032 - follow_up

- `trace_id`: `real-battery-20260325-case_032`
- `conversation_id`: `conv-radiador-ecosport-follow-001`
- `parent_case_id`: `case_017`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `42989.59 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MV-312', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `IR48524` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS` | `score=0.64`
  - `RV-12733*A` | `RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS` | `score=0.64`
  - `JAM-7555` | `MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0` | `score=0.56`
  - `JAM-7553` | `MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR` | `score=0.56`

### case_033 - follow_up

- `trace_id`: `real-battery-20260325-case_033`
- `conversation_id`: `conv-coxim-ecosport-follow-num-001`
- `parent_case_id`: `case_018`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `44286.65 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `022.1505` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `022.1553` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.` | `score=0.64`
  - `SP-2722` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.` | `score=0.64`
  - `043.1688` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO` | `score=0.64`
  - `SP-2722A` | `COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA` | `score=0.64`

### case_034 - follow_up

- `trace_id`: `real-battery-20260325-case_034`
- `conversation_id`: `conv-pastilha-gol-follow-001`
- `parent_case_id`: `case_019`
- pergunta: `1.0`
- status HTTP: `200`
- latencia total observada: `44716.57 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_035 - follow_up

- `trace_id`: `real-battery-20260325-case_035`
- `conversation_id`: `conv-filtro-oleo-gol-follow-001`
- `parent_case_id`: `case_020`
- pergunta: `dianteiro`
- status HTTP: `200`
- latencia total observada: `40893.31 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'filtro de oleo', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_036 - follow_up

- `trace_id`: `real-battery-20260325-case_036`
- `conversation_id`: `conv-bandeja-ecosport-follow-001`
- `parent_case_id`: `case_021`
- pergunta: `dianteiro`
- status HTTP: `200`
- latencia total observada: `44080.41 ms`
- resposta: `Qual lado da peça?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'side', 'prompt': 'Qual lado da peça?'}]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_037 - follow_up

- `trace_id`: `real-battery-20260325-case_037`
- `conversation_id`: `conv-filtro-comb-gol-follow-001`
- `parent_case_id`: `case_022`
- pergunta: `esquerdo`
- status HTTP: `200`
- latencia total observada: `43565.37 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'filtro de combustivel', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': 'left', 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_038 - follow_up

- `trace_id`: `real-battery-20260325-case_038`
- `conversation_id`: `conv-filtro-ar-gol-follow-001`
- `parent_case_id`: `case_023`
- pergunta: `dianteiro`
- status HTTP: `200`
- latencia total observada: `47331.2 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'filtro de ar do motor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_039 - follow_up

- `trace_id`: `real-battery-20260325-case_039`
- `conversation_id`: `conv-disco-gol-follow-001`
- `parent_case_id`: `case_024`
- pergunta: `dianteiro`
- status HTTP: `200`
- latencia total observada: `47008.16 ms`
- resposta: `Qual a motorização do veículo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorização do veículo?'}]`
- criteria em `conversation_state`: `{'part_query': 'discos de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_040 - follow_up

- `trace_id`: `real-battery-20260325-case_040`
- `conversation_id`: `conv-farol-gol-follow-001`
- `parent_case_id`: `case_025`
- pergunta: `esquerdo`
- status HTTP: `200`
- latencia total observada: `44160.3 ms`
- resposta: `Qual peça do farol você precisa?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Qual peça do farol você precisa?'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': 'left', 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_041 - follow_up

- `trace_id`: `real-battery-20260325-case_041`
- `conversation_id`: `conv-radiador-focus-follow-001`
- `parent_case_id`: `case_026`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `44692.75 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12734', 'title': 'RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM AR CONDICIONADO - AUTOMÁTICO/MANUAL', 'score': 0.64}, {'item_id': 'RV-12734*A', 'title': 'RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM AR CONDICIONADO - AUTOMÁTICO/MANUAL', 'score': 0.64}, {'item_id': 'VCT-7006', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR FORD NOVA ECOSPORT/NEW FIESTA/FOCUS 1.6 10/ - KA 1.5 SIGMA', 'score': 0.64}, {'item_id': 'IR48507', 'title': 'RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM OU SEM AR CONDICIONADO - AUTOMÁTICO/MANUAL', 'score': 0.64}, {'item_id': 'G-1117', 'title': 'RESERVATORIO AGUA FORD FOCUS 2000/2008 - RADIADOR', 'score': 0.56}, {'item_id': 'JAM-7579', 'title': 'MANGUEIRA RADIADOR FORD FOCUS 1.8/2.0 2000/ - INFERIOR', 'score': 0.56}, {'item_id': '05-2084', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD FOCUS 2.0 16V 2004/2013', 'score': 0.56}, {'item_id': '05-2086', 'title': 'MANGUEIRA INFERIOR DO RADIADOR FORD FOCUS 2.0 16V 2004/2013', 'score': 0.56}, {'item_id': '05-4043', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD FOCUS 1.6 16V 2010/2013', 'score': 0.56}, {'item_id': '05-4145', 'title': 'MANGUEIRA INFERIOR DO RADIADOR FORD FOCUS 1.6 16V 2010/2013', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Focus', 'vehicle_year': 2010, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `RV-12734` | `RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM AR CONDICIONADO - AUTOMÁTICO/MANUAL` | `score=0.64`
  - `RV-12734*A` | `RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM AR CONDICIONADO - AUTOMÁTICO/MANUAL` | `score=0.64`
  - `VCT-7006` | `RADIADOR/RESFRIADOR DE ÓLEO MOTOR FORD NOVA ECOSPORT/NEW FIESTA/FOCUS 1.6 10/ - KA 1.5 SIGMA` | `score=0.64`
  - `IR48507` | `RADIADOR FORD FOCUS 1.6/1.8/2.0 16V 09/13 - FLEX - COM OU SEM AR CONDICIONADO - AUTOMÁTICO/MANUAL` | `score=0.64`
  - `G-1117` | `RESERVATORIO AGUA FORD FOCUS 2000/2008 - RADIADOR` | `score=0.56`

### case_042 - follow_up_text_engine

- `trace_id`: `real-battery-20260325-case_042`
- `conversation_id`: `conv-coxim-ecosport-follow-text-001`
- `parent_case_id`: `case_027`
- pergunta: `zetec rocam`
- status HTTP: `200`
- latencia total observada: `50865.62 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_043 - follow_up

- `trace_id`: `real-battery-20260325-case_043`
- `conversation_id`: `conv-pastilha-ecosport-follow-001`
- `parent_case_id`: `case_028`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `48040.29 ms`
- resposta: `Em qual posicao a peca fica?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'position', 'prompt': 'Em qual posicao a peca fica?', 'options': ['Dianteiro', 'Traseiro', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_044 - follow_up

- `trace_id`: `real-battery-20260325-case_044`
- `conversation_id`: `conv-generic-part-follow-001`
- `parent_case_id`: `case_029`
- pergunta: `radiador gol 2010`
- status HTTP: `200`
- latencia total observada: `35412.15 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_045 - follow_up

- `trace_id`: `real-battery-20260325-case_045`
- `conversation_id`: `conv-generic-gol-follow-001`
- `parent_case_id`: `case_030`
- pergunta: `pastilha de freio 2010 1.0`
- status HTTP: `200`
- latencia total observada: `47034.32 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': 'FREIO-2010', 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`

### case_046 - validation_error

- `trace_id`: `real-battery-20260325-case_046`
- `conversation_id`: `conv-invalid-empty-001`
- pergunta: `   `
- status HTTP: `400`
- latencia total observada: `5.64 ms`
- erro: `{"detail": "message.text nao pode ser vazio."}`

### case_047 - validation_error

- `trace_id`: `real-battery-20260325-case_047`
- `conversation_id`: `conv-invalid-schema-001`
- pergunta: `Oi`
- status HTTP: `400`
- latencia total observada: `3.46 ms`
- erro: `{"detail": "schema_version deve ser '1.0'."}`

### case_048 - typo_partial

- `trace_id`: `real-battery-20260325-case_048`
- `conversation_id`: `conv-radiador-typo-partial-001`
- pergunta: `rdiador gol 2010`
- status HTTP: `200`
- latencia total observada: `40872.38 ms`
- resposta: `Por favor, informe o motor do seu Gol 2010.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Gol 2010.'}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_049 - typo_partial

- `trace_id`: `real-battery-20260325-case_049`
- `conversation_id`: `conv-pastilha-typo-partial-001`
- pergunta: `pstilhas gol 2010`
- status HTTP: `200`
- latencia total observada: `42759.74 ms`
- resposta: `Qual o motor do seu Gol de 2010?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual o motor do seu Gol de 2010?'}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_050 - typo_complete

- `trace_id`: `real-battery-20260325-case_050`
- `conversation_id`: `conv-bandeja-typo-direct-001`
- pergunta: `bndejas ecosport 2008 eixo dianteiro`
- status HTTP: `200`
- latencia total observada: `42604.0 ms`
- resposta: `Qual lado da peca?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'side', 'prompt': 'Qual lado da peca?', 'options': ['Esquerdo', 'Direito', 'Nao sei']}]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': 'front', 'axle': 'front', 'variant': None, 'quantity': None}`

