# Bateria Real De 50 Testes - 2026-03-25

## Escopo

Relatorio gerado por chamadas reais ao `POST /respond`, sem `StubPreSearchValidator`, `_FakeTools` ou `TestClient` sobrescrito.

- total de testes executados: `50`
- endpoint: `http://localhost:8001/respond`
- trace prefix: `real-battery-20260325`

## Resumo

- respostas HTTP 200: `48`
- respostas com `request_info`: `18`
- respostas com `show_items`: `23`
- respostas com `handoff.required=true`: `7`
- erros HTTP: `2`
- latencia minima observada: `3.26 ms`
- latencia maxima observada: `93893.93 ms`
- latencia media observada: `39398.82 ms`

## Resumo Por Categoria

- `complete`: casos=`5`, http_200=`5`, request_info=`0`, show_items=`5`, handoff=`0`, erros=`0`
- `complete_alias`: casos=`7`, http_200=`7`, request_info=`0`, show_items=`7`, handoff=`0`, erros=`0`
- `follow_up`: casos=`14`, http_200=`14`, request_info=`3`, show_items=`6`, handoff=`5`, erros=`0`
- `follow_up_text_engine`: casos=`1`, http_200=`1`, request_info=`1`, show_items=`0`, handoff=`0`, erros=`0`
- `partial`: casos=`13`, http_200=`13`, request_info=`11`, show_items=`2`, handoff=`0`, erros=`0`
- `partial_generic`: casos=`2`, http_200=`2`, request_info=`2`, show_items=`0`, handoff=`0`, erros=`0`
- `typo_complete`: casos=`4`, http_200=`4`, request_info=`0`, show_items=`3`, handoff=`1`, erros=`0`
- `typo_partial`: casos=`2`, http_200=`2`, request_info=`1`, show_items=`0`, handoff=`1`, erros=`0`
- `validation_error`: casos=`2`, http_200=`0`, request_info=`0`, show_items=`0`, handoff=`0`, erros=`2`

## Casos

### case_001 - complete

- `trace_id`: `real-battery-20260325-case_001`
- `conversation_id`: `conv-radiador-gol-direct-001`
- pergunta: `radiador gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `93893.93 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'MF-11', 'title': 'TAMPA RADIADOR VW PASSAT/GOL/VOYAGE/PARATI /86', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}]}]`
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
- latencia total observada: `35429.19 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
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
- latencia total observada: `36662.89 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
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
- latencia total observada: `35341.28 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'MF-11', 'title': 'TAMPA RADIADOR VW PASSAT/GOL/VOYAGE/PARATI /86', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}]}]`
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
- latencia total observada: `35431.88 ms`
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
- latencia total observada: `35343.26 ms`
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
- latencia total observada: `35285.25 ms`
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
- latencia total observada: `35600.51 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': '022.1505', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '022.1553', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL.', 'score': 0.64}, {'item_id': 'SP-2722', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - S/ROL.', 'score': 0.64}, {'item_id': '043.1688', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - TRASEIRO', 'score': 0.64}, {'item_id': 'SP-2722A', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. INA', 'score': 0.64}, {'item_id': 'SP-2722B', 'title': 'COXIM AMORTECEDOR FORD NOVO FIESTA/ECOSPORT 2002/ - C/ROL. BSB', 'score': 0.64}, {'item_id': 'NK0237', 'title': 'KIT AMORTECEDOR TRASEIRO FORD E COSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}, {'item_id': 'NK0237*A', 'title': 'KIT AMORTECEDOR TRASEIRO FORD ECOSPORT 2003/2012 - FIESTA 2003/2014', 'score': 0.32}]}]`
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
- latencia total observada: `36039.35 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-44-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES', 'score': 0.48}, {'item_id': 'P-45-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA', 'score': 0.48}, {'item_id': 'PD/45-NA', 'title': 'PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/', 'score': 0.48}, {'item_id': 'PD/44-B-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES', 'score': 0.48}, {'item_id': 'P-368-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES', 'score': 0.48}, {'item_id': 'P-54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'PD/54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'P-367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'PD/367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'P-51-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VW GOL/PARATI/SAVEIRO 1.0/1.6/1.8 2000/ - SISTEMA ATE/TEVES', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-44-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES` | `score=0.48`
  - `P-45-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA` | `score=0.48`
  - `PD/45-NA` | `PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/` | `score=0.48`
  - `PD/44-B-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES` | `score=0.48`
  - `P-368-NA` | `PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES` | `score=0.48`

### case_010 - typo_complete

- `trace_id`: `real-battery-20260325-case_010`
- `conversation_id`: `conv-pastilha-gol-typo-001`
- pergunta: `pstilhas de freio gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `37496.79 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-44-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES', 'score': 0.48}, {'item_id': 'P-45-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA', 'score': 0.48}, {'item_id': 'PD/45-NA', 'title': 'PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/', 'score': 0.48}, {'item_id': 'PD/44-B-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES', 'score': 0.48}, {'item_id': 'P-368-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES', 'score': 0.48}, {'item_id': 'P-54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'PD/54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'P-367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'PD/367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'P-51-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VW GOL/PARATI/SAVEIRO 1.0/1.6/1.8 2000/ - SISTEMA ATE/TEVES', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-44-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES` | `score=0.48`
  - `P-45-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA` | `score=0.48`
  - `PD/45-NA` | `PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/` | `score=0.48`
  - `PD/44-B-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES` | `score=0.48`
  - `P-368-NA` | `PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES` | `score=0.48`

### case_011 - complete_alias

- `trace_id`: `real-battery-20260325-case_011`
- `conversation_id`: `conv-pastilha-gol-alias-001`
- pergunta: `pastilhas freio gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `37343.66 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-44-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES', 'score': 0.48}, {'item_id': 'P-45-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA', 'score': 0.48}, {'item_id': 'PD/45-NA', 'title': 'PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/', 'score': 0.48}, {'item_id': 'PD/44-B-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES', 'score': 0.48}, {'item_id': 'P-368-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES', 'score': 0.48}, {'item_id': 'P-54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'PD/54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'P-367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'PD/367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'P-51-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VW GOL/PARATI/SAVEIRO 1.0/1.6/1.8 2000/ - SISTEMA ATE/TEVES', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-44-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES` | `score=0.48`
  - `P-45-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA` | `score=0.48`
  - `PD/45-NA` | `PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/` | `score=0.48`
  - `PD/44-B-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES` | `score=0.48`
  - `P-368-NA` | `PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES` | `score=0.48`

### case_012 - complete_alias

- `trace_id`: `real-battery-20260325-case_012`
- `conversation_id`: `conv-pastilha-gol-short-001`
- pergunta: `pastilha gol 2010 1.0`
- status HTTP: `200`
- latencia total observada: `37134.62 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-44-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES', 'score': 0.48}, {'item_id': 'P-45-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA', 'score': 0.48}, {'item_id': 'PD/45-NA', 'title': 'PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/', 'score': 0.48}, {'item_id': 'PD/44-B-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES', 'score': 0.48}, {'item_id': 'P-368-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES', 'score': 0.48}, {'item_id': 'P-54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'PD/54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'P-367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'PD/367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'P-51-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VW GOL/PARATI/SAVEIRO 1.0/1.6/1.8 2000/ - SISTEMA ATE/TEVES', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-44-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES` | `score=0.48`
  - `P-45-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA` | `score=0.48`
  - `PD/45-NA` | `PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/` | `score=0.48`
  - `PD/44-B-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES` | `score=0.48`
  - `P-368-NA` | `PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES` | `score=0.48`

### case_013 - complete

- `trace_id`: `real-battery-20260325-case_013`
- `conversation_id`: `conv-disco-gol-direct-001`
- pergunta: `disco de freio gol 2010 dianteiro`
- status HTTP: `200`
- latencia total observada: `34720.57 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'BD-5298', 'title': 'DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS', 'score': 0.6}, {'item_id': 'HF-87', 'title': 'DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS', 'score': 0.6}, {'item_id': 'FLDI00126', 'title': 'DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS', 'score': 0.6}, {'item_id': 'RPDI00480', 'title': 'DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS', 'score': 0.6}, {'item_id': 'BD-3790', 'title': 'DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M', 'score': 0.6}, {'item_id': 'RCDI01030', 'title': 'DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M', 'score': 0.6}, {'item_id': 'BD-5297', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.6}, {'item_id': 'HF-87A', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.6}, {'item_id': 'MR005', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.6}, {'item_id': 'BD-9614', 'title': 'DISCO DE FREIO DIANTEIRO VW UP! TSI 14/ - NOVO GOL/VOYAGE/SAVEIRO 13/ VENTILADO 256M ESPESSURA 22MM', 'score': 0.6}]}]`
- criteria em `conversation_state`: `{'part_query': 'disco de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `BD-5298` | `DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS` | `score=0.6`
  - `HF-87` | `DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS` | `score=0.6`
  - `FLDI00126` | `DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS` | `score=0.6`
  - `RPDI00480` | `DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS` | `score=0.6`
  - `BD-3790` | `DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M` | `score=0.6`

### case_014 - complete_alias

- `trace_id`: `real-battery-20260325-case_014`
- `conversation_id`: `conv-radiador-ecosport-plural-001`
- pergunta: `radiadores motor ecosport 2008 1.6`
- status HTTP: `200`
- latencia total observada: `37706.01 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
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
- latencia total observada: `36919.39 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'MF-11', 'title': 'TAMPA RADIADOR VW PASSAT/GOL/VOYAGE/PARATI /86', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}]}]`
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
- latencia total observada: `31609.46 ms`
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
- latencia total observada: `41223.35 ms`
- resposta: `Por favor, informe o tipo do motor do seu Ford EcoSport de 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o tipo do motor do seu Ford EcoSport de 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_018 - partial

- `trace_id`: `real-battery-20260325-case_018`
- `conversation_id`: `conv-coxim-ecosport-follow-num-001`
- pergunta: `coxim amortecedor ecosport 2008`
- status HTTP: `200`
- latencia total observada: `42024.84 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport de 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport de 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_019 - partial

- `trace_id`: `real-battery-20260325-case_019`
- `conversation_id`: `conv-pastilha-gol-follow-001`
- pergunta: `pastilha de freio gol 2010`
- status HTTP: `200`
- latencia total observada: `41876.07 ms`
- resposta: `Por favor, informe o motor do seu veículo GOL de 2010.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu veículo GOL de 2010.'}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_020 - partial

- `trace_id`: `real-battery-20260325-case_020`
- `conversation_id`: `conv-filtro-oleo-gol-follow-001`
- pergunta: `filtro de oleo gol 2010`
- status HTTP: `200`
- latencia total observada: `41009.84 ms`
- resposta: `Qual eixo do seu carro (dianteiro ou traseiro)?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'axle', 'prompt': 'Qual eixo do seu carro (dianteiro ou traseiro)?'}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de oleo', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_021 - partial

- `trace_id`: `real-battery-20260325-case_021`
- `conversation_id`: `conv-bandeja-ecosport-follow-001`
- pergunta: `bandeja ecosport 2008`
- status HTTP: `200`
- latencia total observada: `43887.53 ms`
- resposta: `Qual eixo (dianteiro ou traseiro) você precisa da bandeja do Ecosport 2008?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'axle', 'prompt': 'Qual eixo (dianteiro ou traseiro) você precisa da bandeja do Ecosport 2008?'}]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_022 - partial

- `trace_id`: `real-battery-20260325-case_022`
- `conversation_id`: `conv-filtro-comb-gol-follow-001`
- pergunta: `filtro de combustivel gol 2010`
- status HTTP: `200`
- latencia total observada: `39730.43 ms`
- resposta: `Qual lado do veículo você precisa do filtro de combustível?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'side', 'prompt': 'Qual lado do veículo você precisa do filtro de combustível?'}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de combustivel', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_023 - partial

- `trace_id`: `real-battery-20260325-case_023`
- `conversation_id`: `conv-filtro-ar-gol-follow-001`
- pergunta: `filtro ar motor gol 2010`
- status HTTP: `200`
- latencia total observada: `40031.68 ms`
- resposta: `Qual eixo do veículo você está procurando?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'axle', 'prompt': 'Qual eixo do veículo você está procurando?'}]`
- criteria em `conversation_state`: `{'part_query': 'filtro de ar do motor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_024 - partial

- `trace_id`: `real-battery-20260325-case_024`
- `conversation_id`: `conv-disco-gol-follow-001`
- pergunta: `disco de freio gol 2010`
- status HTTP: `200`
- latencia total observada: `40251.51 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'BD-5298', 'title': 'DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS', 'score': 0.56}, {'item_id': 'HF-87', 'title': 'DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS', 'score': 0.56}, {'item_id': 'FLDI00126', 'title': 'DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS', 'score': 0.56}, {'item_id': 'RPDI00480', 'title': 'DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS', 'score': 0.56}, {'item_id': 'BD-3790', 'title': 'DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M', 'score': 0.56}, {'item_id': 'RCDI01030', 'title': 'DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M', 'score': 0.56}, {'item_id': 'BD-5297', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.56}, {'item_id': 'HF-87A', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.56}, {'item_id': 'MR005', 'title': 'DISCO DE FREIO DIANTEIRO NOVO GOL/VOYAGE/SAVEIRO 1.6 08/ ARO 14 - VENTILADO 256MM - ESPESSURA 19MM', 'score': 0.56}, {'item_id': 'BD-9614', 'title': 'DISCO DE FREIO DIANTEIRO VW UP! TSI 14/ - NOVO GOL/VOYAGE/SAVEIRO 13/ VENTILADO 256M ESPESSURA 22MM', 'score': 0.56}]}]`
- criteria em `conversation_state`: `{'part_query': 'disco de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `BD-5298` | `DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS` | `score=0.56`
  - `HF-87` | `DISCO DE FREIO DIANTEIRO VW NOVO GOL/VOYAGE 1.0 2008/ ARO 13 - VENTILADO 239MM 4 FUROS` | `score=0.56`
  - `FLDI00126` | `DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS` | `score=0.56`
  - `RPDI00480` | `DISCO DE FREIO DIANTEIRO VW GOL/VOYAGE/SAVEIRO/PASSAT - SANTANA /89 - SÓLIDO 239MM 4 FUROS` | `score=0.56`
  - `BD-3790` | `DISCO DE FREIO DIANTEIRO VW SANTANA 94/ GOL GTI 95/ POLO 97/ GOLF 1.8 GTI 93/98 - VENTILADO 256M` | `score=0.56`

### case_025 - partial

- `trace_id`: `real-battery-20260325-case_025`
- `conversation_id`: `conv-farol-gol-follow-001`
- pergunta: `farol gol 2010`
- status HTTP: `200`
- latencia total observada: `31433.3 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'PF37', 'title': 'PARAFUSO DO FAROL', 'score': 0.48}, {'item_id': 'AV-12253', 'title': 'LAMPADA FAROL H4 12V 3200K 60/55 WATTS', 'score': 0.48}, {'item_id': '64150', 'title': 'LAMPADA FAROL/AUXILIAR - 3200K H1 - 55 WATTS', 'score': 0.48}, {'item_id': 'AV-12248', 'title': 'LÂMPADA FAROL/AUXILIAR - 3200K H1 - 12V 55 WATTS', 'score': 0.48}, {'item_id': 'AV-12250', 'title': 'LAMPADA FAROL AUXILIAR - 3200K H3 - 12V 55 WATTS', 'score': 0.48}, {'item_id': 'PF39', 'title': 'PARAFUSO DO FAROL-PARACHOQUE - MOLDURAS EXTERNAS', 'score': 0.48}, {'item_id': 'PF50', 'title': 'PARAFUSO DO SUPORTE DO FILTRO DO AR-FAROL E PARACHOQUE', 'score': 0.48}, {'item_id': 'PF35', 'title': 'PARAFUSO DO FAROL-COLUNAS/MOLDURAS INTERNAS-PORTA MALAS E PARACHOQUE', 'score': 0.48}, {'item_id': '64210CBL', 'title': 'LAMPADA FAROL ALTO/BAIXO - 4200K LUZ BRANCA H7 - 55 WATTS - ATE 30 + LUZ - VALOR JOGOC/2', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'farol', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`
- top items:
  - `PF37` | `PARAFUSO DO FAROL` | `score=0.48`
  - `AV-12253` | `LAMPADA FAROL H4 12V 3200K 60/55 WATTS` | `score=0.48`
  - `64150` | `LAMPADA FAROL/AUXILIAR - 3200K H1 - 55 WATTS` | `score=0.48`
  - `AV-12248` | `LÂMPADA FAROL/AUXILIAR - 3200K H1 - 12V 55 WATTS` | `score=0.48`
  - `AV-12250` | `LAMPADA FAROL AUXILIAR - 3200K H3 - 12V 55 WATTS` | `score=0.48`

### case_026 - partial

- `trace_id`: `real-battery-20260325-case_026`
- `conversation_id`: `conv-radiador-focus-follow-001`
- pergunta: `radiador focus 2010`
- status HTTP: `200`
- latencia total observada: `39940.01 ms`
- resposta: `Por favor, informe o motor do seu Ford Focus de 2010.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford Focus de 2010.'}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Focus', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_027 - partial

- `trace_id`: `real-battery-20260325-case_027`
- `conversation_id`: `conv-coxim-ecosport-follow-text-001`
- pergunta: `coxim amortecedor ecosport 2008`
- status HTTP: `200`
- latencia total observada: `41796.66 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport de 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport de 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_028 - partial

- `trace_id`: `real-battery-20260325-case_028`
- `conversation_id`: `conv-pastilha-ecosport-follow-001`
- pergunta: `pastilha de freio ecosport 2008`
- status HTTP: `200`
- latencia total observada: `42191.23 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_029 - partial_generic

- `trace_id`: `real-battery-20260325-case_029`
- `conversation_id`: `conv-generic-part-follow-001`
- pergunta: `quero uma peca`
- status HTTP: `200`
- latencia total observada: `31306.23 ms`
- resposta: `Por favor, informe qual peça você precisa.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Por favor, informe qual peça você precisa.'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': None, 'vehicle_year': None, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_030 - partial_generic

- `trace_id`: `real-battery-20260325-case_030`
- `conversation_id`: `conv-generic-gol-follow-001`
- pergunta: `preciso de ajuda com uma peca do gol`
- status HTTP: `200`
- latencia total observada: `30671.7 ms`
- resposta: `Qual peça do Gol você precisa?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'part_query', 'prompt': 'Qual peça do Gol você precisa?'}]`
- criteria em `conversation_state`: `{'part_query': None, 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'GOL', 'vehicle_year': None, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_031 - follow_up

- `trace_id`: `real-battery-20260325-case_031`
- `conversation_id`: `conv-radiador-gol-follow-001`
- `parent_case_id`: `case_016`
- pergunta: `1.0`
- status HTTP: `200`
- latencia total observada: `43953.14 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'RV-12528', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - GOL 1.0 12V - SAVEIRO 10/ - FOX/ 1.0/1.6 06/', 'score': 0.64}, {'item_id': 'IR48108', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'IR48109', 'title': 'RADIADOR COM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - F.T', 'score': 0.64}, {'item_id': 'RV-12527', 'title': 'RADIADOR SEM AR CONDICIONADO VW NOVO GOL/VOYAGE 08/ - NOVA SAVEIRO 10/ - FOX/POLO 1.0/1.6 06/ - A/M', 'score': 0.64}, {'item_id': 'TRC0017', 'title': 'RADIADOR/RESFRIADOR DE ÓLEO MOTOR VW TIGUAN/UP!/POLO/VIRTUS/GOLF/JETTA MSI/MPI/TSI/TSFI 1.0/1.4/1.6', 'score': 0.64}, {'item_id': 'KT-40023', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE GRANDE', 'score': 0.56}, {'item_id': 'MF-11', 'title': 'TAMPA RADIADOR VW PASSAT/GOL/VOYAGE/PARATI /86', 'score': 0.56}, {'item_id': 'KT-40028', 'title': 'KIT COXIM RADIADOR VW PASSAT/GOL/VOYAGE PEQUENO', 'score': 0.56}, {'item_id': '20434', 'title': 'MANGUEIRA VW GOL 1.0 II 95/96 - SUPERIOR RADIADOR', 'score': 0.56}, {'item_id': '20403', 'title': 'MANGUEIRA VW GOL/PARATI AP 95/ - INFERIOR RADIADOR', 'score': 0.56}]}]`
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
- latencia total observada: `46176.15 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'IR48524', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODOS', 'score': 0.64}, {'item_id': 'RV-12733*A', 'title': 'RADIADOR FORD NOVO FIESTA 1.0 SUPERCHARGER - 1.6 03/10 - ECOSPORT 1.0/1.6 8V - 2.0 16V 03/10  TODDOS', 'score': 0.64}, {'item_id': 'JAM-7555', 'title': 'MANGUEIRA SUPERIOR DO RADIADOR FORD ECOSPORT 2.0', 'score': 0.56}, {'item_id': 'JAM-7553', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - SUPERIOR', 'score': 0.56}, {'item_id': 'JAM-7554', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 1.6 2003/ - INFERIOR', 'score': 0.56}, {'item_id': 'JAM-7556', 'title': 'MANGUEIRA RADIADOR FORD ECOSPORT 2.0 2004/ - INFERIOR', 'score': 0.56}, {'item_id': 'G-1114', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-12462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}, {'item_id': 'MF-462', 'title': 'RESERVATÓRIO ÁGUA DO RADIADOR 2 SAÍDAS FORD NOVO FIESTA/ECOSPORT 2002/', 'score': 0.56}]}]`
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
- latencia total observada: `45241.65 ms`
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
- latencia total observada: `46635.96 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-44-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES', 'score': 0.48}, {'item_id': 'P-45-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA', 'score': 0.48}, {'item_id': 'PD/45-NA', 'title': 'PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/', 'score': 0.48}, {'item_id': 'PD/44-B-NA', 'title': 'PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES', 'score': 0.48}, {'item_id': 'P-368-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES', 'score': 0.48}, {'item_id': 'P-54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'PD/54-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VARGA VW GOL/PARATI 1.0/1.6/1.8 96/ - GM CORSA 96/', 'score': 0.48}, {'item_id': 'P-367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'PD/367-NA', 'title': 'PASTILHA DE FREIO VW NOVO GOL/SAVEIRO 08/ BOSCH - GOLF 94/ 94/95 - POLO CLASSIC 97/', 'score': 0.48}, {'item_id': 'P-51-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA VW GOL/PARATI/SAVEIRO 1.0/1.6/1.8 2000/ - SISTEMA ATE/TEVES', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': '1.0', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-44-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ TEVES` | `score=0.48`
  - `P-45-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 - 94/ VARGA` | `score=0.48`
  - `PD/45-NA` | `PASTILHA DE FREIO VW GOL/PARATI/QUANTUM/SANTANA/SAVEIRO 1995/` | `score=0.48`
  - `PD/44-B-NA` | `PASTILHA DE FREIO VW SANTANA/QUANTUM 1.8/2.0 94/ - C/ALARME TEVES` | `score=0.48`
  - `P-368-NA` | `PASTILHA DE FREIO VW NOVO GOL/VOYAGE 08/ - FOX 1.0 2003/ ARO 13 - TEVES` | `score=0.48`

### case_035 - follow_up

- `trace_id`: `real-battery-20260325-case_035`
- `conversation_id`: `conv-filtro-oleo-gol-follow-001`
- `parent_case_id`: `case_020`
- pergunta: `dianteiro`
- status HTTP: `200`
- latencia total observada: `42676.82 ms`
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
- latencia total observada: `54457.47 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['DRAGON', 'DURATEC', 'DURATEC HE', 'SIGMA', 'ZETEC ROCAM']}]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_037 - follow_up

- `trace_id`: `real-battery-20260325-case_037`
- `conversation_id`: `conv-filtro-comb-gol-follow-001`
- `parent_case_id`: `case_022`
- pergunta: `esquerdo`
- status HTTP: `200`
- latencia total observada: `42614.53 ms`
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
- latencia total observada: `43459.73 ms`
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
- latencia total observada: `49335.51 ms`
- resposta: `Por favor, informe o motor do seu veículo.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu veículo.'}]`
- criteria em `conversation_state`: `{'part_query': 'disco de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': 'front', 'axle': None, 'variant': None, 'quantity': None}`

### case_040 - follow_up

- `trace_id`: `real-battery-20260325-case_040`
- `conversation_id`: `conv-farol-gol-follow-001`
- `parent_case_id`: `case_025`
- pergunta: `esquerdo`
- status HTTP: `200`
- latencia total observada: `43765.53 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'farol', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': 'left', 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_041 - follow_up

- `trace_id`: `real-battery-20260325-case_041`
- `conversation_id`: `conv-radiador-focus-follow-001`
- `parent_case_id`: `case_026`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `45873.01 ms`
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
- latencia total observada: `51882.29 ms`
- resposta: `Por favor, informe o motor do seu Ford EcoSport de 2008.`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Por favor, informe o motor do seu Ford EcoSport de 2008.'}]`
- criteria em `conversation_state`: `{'part_query': 'coxim amortecedor', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_043 - follow_up

- `trace_id`: `real-battery-20260325-case_043`
- `conversation_id`: `conv-pastilha-ecosport-follow-001`
- `parent_case_id`: `case_028`
- pergunta: `1.6`
- status HTTP: `200`
- latencia total observada: `47587.94 ms`
- resposta: `Encontrei mais de uma opcao. Seguem os itens encontrados para refinar a busca.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `False`
- actions: `[{'type': 'show_items', 'items': [{'item_id': 'P-497-NA', 'title': 'PASTILHA DE FREIO FORD NOVO FIESTA 1.0/1.6 SUPER CHARGER C/ABS - ECOSPORT TODOS', 'score': 0.48}, {'item_id': 'PD/497-NA', 'title': 'PASTILHA DE FREIO FORD NOVO FIESTA 1.0/1.6 SUPER CHARGER C/ABS - ECOSPORT TODOS', 'score': 0.48}, {'item_id': 'P-767-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 09/ AUTOMATICO - NOVA ECOSPORT 13/ - FOCUS 09.2009/', 'score': 0.48}, {'item_id': 'PD/767-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 09/ AUTOMATICO - NOVA ECOSPORT 13/ - FOCUS 09.2009/', 'score': 0.48}, {'item_id': 'BF1082-00', 'title': 'PASTILHA DE FREIO DIANTEIRA ECOSPORT 09/ AUTOMATICO -NOVA ECOSPORT 13/ - FOCUS 09.2009/ - VOLVO', 'score': 0.48}, {'item_id': 'P-80-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 4X2 03/ - NOVO FIESTA COM ABS 1.0/1.4 09/ - 1.6 09/10', 'score': 0.48}, {'item_id': 'PD/767-CMAXX', 'title': 'PASTILHA DE FREIO DIANTEIRA ECOSPORT 09/ AUTOMATICO -NOVA ECOSPORT 13/ - FOCUS 09.2009/ - VOLVO', 'score': 0.48}, {'item_id': 'PD/80-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 4X2 03/ - NOVO FIESTA COM ABS 1.0/1.4 09/ - 1.6 09/10', 'score': 0.48}, {'item_id': 'P-1103-NA', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD NOVO FOCUS 1.6/20 08/009 - ECOSPORT 2.0 4X2 2005/08.2009 AUTOMATICA', 'score': 0.48}, {'item_id': 'PD/1103-CMAXX', 'title': 'PASTILHA DE FREIO DIANTEIRA FORD NOVO FOCUS 1.6/20 08/009 - ECOSPORT 2.0 4X2 2005/08.2009 AUTOMATICA', 'score': 0.48}]}]`
- criteria em `conversation_state`: `{'part_query': 'pastilhas de freio', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': '1.6', 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': 1}`
- top items:
  - `P-497-NA` | `PASTILHA DE FREIO FORD NOVO FIESTA 1.0/1.6 SUPER CHARGER C/ABS - ECOSPORT TODOS` | `score=0.48`
  - `PD/497-NA` | `PASTILHA DE FREIO FORD NOVO FIESTA 1.0/1.6 SUPER CHARGER C/ABS - ECOSPORT TODOS` | `score=0.48`
  - `P-767-NA` | `PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 09/ AUTOMATICO - NOVA ECOSPORT 13/ - FOCUS 09.2009/` | `score=0.48`
  - `PD/767-NA` | `PASTILHA DE FREIO DIANTEIRA FORD ECOSPORT 09/ AUTOMATICO - NOVA ECOSPORT 13/ - FOCUS 09.2009/` | `score=0.48`
  - `BF1082-00` | `PASTILHA DE FREIO DIANTEIRA ECOSPORT 09/ AUTOMATICO -NOVA ECOSPORT 13/ - FOCUS 09.2009/ - VOLVO` | `score=0.48`

### case_044 - follow_up

- `trace_id`: `real-battery-20260325-case_044`
- `conversation_id`: `conv-generic-part-follow-001`
- `parent_case_id`: `case_029`
- pergunta: `radiador gol 2010`
- status HTTP: `200`
- latencia total observada: `36751.62 ms`
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
- latencia total observada: `48834.21 ms`
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
- latencia total observada: `4.29 ms`
- erro: `{"detail": "message.text nao pode ser vazio."}`

### case_047 - validation_error

- `trace_id`: `real-battery-20260325-case_047`
- `conversation_id`: `conv-invalid-schema-001`
- pergunta: `Oi`
- status HTTP: `400`
- latencia total observada: `3.26 ms`
- erro: `{"detail": "schema_version deve ser '1.0'."}`

### case_048 - typo_partial

- `trace_id`: `real-battery-20260325-case_048`
- `conversation_id`: `conv-radiador-typo-partial-001`
- pergunta: `rdiador gol 2010`
- status HTTP: `200`
- latencia total observada: `32331.68 ms`
- resposta: `Qual a motorizacao do veiculo?`
- ferramentas usadas: `['pre_search_validator']`
- handoff: `False`
- actions: `[{'type': 'request_info', 'key': 'engine', 'prompt': 'Qual a motorizacao do veiculo?', 'options': ['1.6 L 8V SOHC L4', '1300 AR', '1600 AR', 'AP 1600', 'AP 1800', 'AP 2000', 'CHT', 'EA111', 'EA111 AT', 'EA111 TEC', 'EA111 VHT', 'EA211']}]`
- criteria em `conversation_state`: `{'part_query': 'radiador', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_049 - typo_partial

- `trace_id`: `real-battery-20260325-case_049`
- `conversation_id`: `conv-pastilha-typo-partial-001`
- pergunta: `pstilhas gol 2010`
- status HTTP: `200`
- latencia total observada: `31639.51 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'pstilhas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Gol', 'vehicle_year': 2010, 'engine': None, 'side': None, 'position': None, 'axle': None, 'variant': None, 'quantity': None}`

### case_050 - typo_complete

- `trace_id`: `real-battery-20260325-case_050`
- `conversation_id`: `conv-bandeja-typo-direct-001`
- pergunta: `bndejas ecosport 2008 eixo dianteiro`
- status HTTP: `200`
- latencia total observada: `37384.11 ms`
- resposta: `Nao encontrei a peca com esses dados. Me informe modelo, ano e motorizacao para tentar novamente. Se preferir, posso transferir para atendimento humano.`
- ferramentas usadas: `['pre_search_validator', 'search_parts']`
- handoff: `True`
- handoff_reason: `no_match`
- actions: `[]`
- criteria em `conversation_state`: `{'part_query': 'bandejas', 'part_code': None, 'vehicle_brand': None, 'vehicle_model': 'Ecosport', 'vehicle_year': 2008, 'engine': None, 'side': None, 'position': 'front', 'axle': 'front', 'variant': None, 'quantity': None}`

