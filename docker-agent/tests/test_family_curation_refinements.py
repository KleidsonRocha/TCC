"""Identity, scoped curation and typed constraints from the category audit."""
import csv
import json
import logging
import os
from pathlib import Path

import pytest

from app.config import Settings
from app.core.domain.pre_search import SearchCriteria
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.infra.erp_search_query import build_search_sql
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_family_curation import curate_catalog, source_identity_matches
from app.infra.pre_search_validator_llm import LLMPreSearchValidator


def seed_rows():
    root = Path('db/init/csv')
    concepts = list(csv.DictReader((root/'pre_search_family_concept.csv').open(encoding='utf-8'), delimiter=';'))
    for row in concepts:
        for key in ('aliases', 'source_families'):
            row[key] = row[key].split('|') if row[key] else []
        for key in ('generic_ambiguous_parts','needs_side','needs_position','needs_axle','needs_engine','needs_variant'):
            row[key] = row[key].lower() == 'true' if row[key] else None
    decisions = list(csv.DictReader((root/'pre_search_alias_decision.csv').open(encoding='utf-8')))
    return concepts, decisions


@pytest.fixture
def catalog():
    concepts, decisions = seed_rows()
    families = {row['family_key'] for row in concepts}
    families.update(row['family_key'] for row in decisions if row['family_key'])
    families.update(source for row in concepts for source in row['source_families'])
    families.update({'bomba de agua','bomba manual','semi eixo','cilindro de roda','amortecedores suspensao'})
    scopes = {}
    for row in csv.DictReader(Path('db/init/csv/pre_search_family_scope.csv').open(encoding='utf-8')):
        scopes.setdefault(row['family_key'], []).append((int(row['source_group_code']),int(row['source_subgroup_code'])))
    raw = PreSearchCatalog(part_patterns=[(family,(family,)) for family in families],
        part_family_ids=scopes, brand_aliases={}, model_aliases={'Gol':('gol',),'Clio':('clio',),'S10':('s10',)},
        invalid_slot_tokens=set(), generic_ambiguous_parts=set(), needs_side={'abracadeiras'},
        needs_position=set(), needs_axle={'arruelas'}, needs_engine=set(), needs_variant=set(), engine_by_model={})
    return curate_catalog(raw, concepts, decisions)


@pytest.mark.parametrize('message,expected', [
    ('trizeta para Gol 2010', 'trizetas'), ('trizetas para Gol 2010', 'trizetas'),
    ('eletro ventilador para Gol 2010','eletroventilador'),
    ('kit amortecedor para Clio 2004','kit amortecedor'),
    ('kit dobradica para S10 2017','kit dobradica'),
    ('tapa-po cilindro roda para Gol 2010','tapa po cilindro de roda'),
    ('pino de eixo para Gol 2010','pino de eixo'),
])
def test_curated_component_has_one_identity(catalog, message, expected):
    extractor = DictionaryPreSearchExtractor(catalog=catalog)
    assert extractor.extract(message).part_query == expected
    assert len(extractor.extract_items(message)) == 1


@pytest.mark.parametrize('alias', ['batente','bucha','pino','auxiliar','antichama','tampa'])
def test_physically_ambiguous_alias_asks_before_llm_or_search(catalog, alias):
    validator = LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    validator._post_chat_or_generate = lambda **kw: pytest.fail('ambiguous alias reached LLM')
    result = validator.validate(alias+' para Gol 2010')
    assert result.decision == 'ask' and result.next_question.key == 'part_query'


@pytest.mark.parametrize('message,abs_value,fuel,transmission', [
    ('semi eixo sem ABS para Gol 2010', False,None,None),
    ('semi eixo s/ABS para Gol 2010', False,None,None),
    ('semi eixo com ABS para Gol 2010', True,None,None),
    ('semi eixo para Gol 2010 flex cambio manual', None,'flex','manual'),
    ('semi eixo para Gol 2010 diesel transmissao automatica', None,'diesel','automatico'),
    ('bomba manual para Gol 2010', None,None,None),
])
def test_product_and_vehicle_attributes_are_not_versions(catalog, message, abs_value, fuel, transmission):
    criteria = DictionaryPreSearchExtractor(catalog=catalog).extract(message)
    assert criteria.variant is None
    assert (criteria.abs, criteria.fuel, criteria.transmission) == (abs_value,fuel,transmission)


def test_false_abs_survives_history_and_incorrect_llm(catalog):
    validator = LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    validator._post_chat_or_generate = lambda **kw: ({'message':{'content':json.dumps({
        'decision':'search','criteria':{'part_query':'semi eixo','abs':True,'variant':'ABS','fuel':'diesel'},
        'missing_fields':[],'confidence':0.9})}},'/api/chat')
    result = validator.validate('semi eixo sem ABS para Gol 2010',last_messages=[
        {'role':'user','text':'semi eixo com ABS para Gol 2010'}])
    assert result.criteria.abs is False and result.criteria.variant is None
    assert result.criteria.fuel is None


@pytest.mark.parametrize('message,field,value', [('sem ABS','abs',False),('flex','fuel','flex')])
def test_typed_follow_up_does_not_fabricate_a_version(catalog,message,field,value):
    from app.core.domain.models import ConversationState
    validator = LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    validator._post_chat_or_generate=lambda **kw: pytest.fail('typed reply reached LLM')
    previous=ConversationState(criteria=SearchCriteria(part_query='semi eixo',vehicle_model='S10',vehicle_year=2017),
        pending_slot='variant',last_decision='ask')
    result=validator.validate(message,conversation_state=previous)
    assert result.decision=='ask' and result.next_question.key=='variant'
    assert getattr(result.criteria,field)==value
    assert result.criteria.variant is None and result.criteria.vehicle_model=='S10'


def test_new_vehicle_does_not_inherit_old_fuel_or_transmission(catalog):
    result=DictionaryPreSearchExtractor(catalog=catalog).extract('bomba manual para Clio 2004',
        last_messages=[{'role':'user','text':'semi eixo para Gol 2010 diesel cambio automatico com ABS'}])
    assert result.fuel is None and result.transmission is None and result.abs is None


@pytest.mark.parametrize('message,field,value', [
    ('semi eixo para Gol 2010 tras nao diant','position','rear'),
    ('semi eixo para Gol 2010 diant nao tras','position','front'),
    ('semi eixo para Gol 2010 dir nao esq','side','right'),
    ('semi eixo para Gol 2010 esq nao dir','side','left'),
])
def test_abbreviated_negative_direction_does_not_become_positive(catalog,message,field,value):
    assert getattr(DictionaryPreSearchExtractor(catalog=catalog).extract(message),field)==value


def test_abbreviated_direction_conflict_stops_before_llm(catalog):
    validator=LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    validator._post_chat_or_generate=lambda **kw: pytest.fail('direction conflict reached LLM')
    result=validator.validate('semi eixo diant e tras para Gol 2010')
    assert result.decision=='ask' and result.next_question.key=='intent_resolution'


@pytest.mark.parametrize('message', ['kit reparo amortecedor para Gol 2010','conjunto amortecedor para Gol 2010',
    'conjunto bomba de agua para Gol 2010'])
def test_uncurated_composition_is_not_reduced_to_known_kit(catalog, message):
    validator = LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    validator._post_chat_or_generate = lambda **kw: pytest.fail('composition reached LLM')
    result = validator.validate(message)
    assert result.decision=='ask' and result.next_question.key=='part_query'
    assert result.criteria.part_query not in {'kit amortecedor','amortecedores suspensao'}


def test_curated_scopes_do_not_accept_another_component(catalog):
    source = {'cd_grupo':9,'cd_subgrupo':27,'candidate_title':'ELETRO VENTILADOR GOL'}
    assert source_identity_matches(source,'eletroventilador',catalog)
    assert not source_identity_matches({**source,'candidate_title':'SUPORTE ELETROVENTILADOR'},'eletroventilador',catalog)
    assert not source_identity_matches({**source,'cd_subgrupo':28},'eletroventilador',catalog)
    assert source_identity_matches({'cd_grupo':10,'cd_subgrupo':21,'candidate_title':'TRIZETA GOL'},'trizetas',catalog)
    assert not source_identity_matches({'cd_grupo':10,'cd_subgrupo':21,'candidate_title':'CILINDRO EMBREAGEM'},'trizetas',catalog)


def test_direction_requirements_are_changed_by_family_only(catalog):
    assert 'abracadeiras' in catalog.needs_side
    assert 'arruelas' not in catalog.needs_axle
    assert 'kit dobradica' in catalog.needs_side
    assert 'kit amortecedor' in catalog.needs_position
    assert 'pino de eixo' in catalog.needs_axle


def test_explicit_alias_decisions_override_old_ambiguity_and_are_repeatable(catalog):
    from dataclasses import replace
    concepts, decisions = seed_rows()
    stale = replace(catalog, ambiguous_part_aliases=catalog.ambiguous_part_aliases | {'trizeta','bomba agua'})
    updated = curate_catalog(stale, concepts, decisions)
    assert 'trizeta' not in updated.ambiguous_part_aliases
    assert 'bomba agua' not in updated.ambiguous_part_aliases
    assert DictionaryPreSearchExtractor(catalog=updated).extract('trizeta Gol 2010').part_query=='trizetas'


@pytest.fixture
def postgres():
    if os.environ.get('ERP_SEARCH_TEST_POSTGRES') != '1':
        pytest.skip('Requires local test PostgreSQL')
    import psycopg
    from psycopg.rows import dict_row
    from app.infra.postgres_conninfo import build_catalog_conninfo
    with psycopg.connect(build_catalog_conninfo(Settings()),row_factory=dict_row,autocommit=True) as conn:
        with conn.transaction(force_rollback=True):
            yield conn


def execute_fixture(conn, fixture, criteria, **kwargs):
    from scripts.eval.evaluate_erp_search import install_contract_fixture
    install_contract_fixture(conn, fixture)
    query, params = build_search_sql(criteria=criteria,limit=10,**kwargs)
    for name in ('candidates','applications'):
        query=query.replace('soccol.item_search_'+name,'pg_temp.contract_'+name)
    return {row['item_code'] for row in conn.execute(query,params).fetchall() if row['item_code']}


@pytest.mark.parametrize('fields,expected', [
    ({'abs':False,'side':'left'}, {'WITHOUT','CROSS'}),
    ({'abs':True},{'WITH'}),
    ({'fuel':'flex','transmission':'manual'},{'WITHOUT','UNKNOWN'}),
    ({'fuel':'flex','transmission':'automatico'},set()),
    ({'axle':'front'},{'WITHOUT'}),
    ({'position':'front'},{'WITHOUT','UNKNOWN'}),
])
def test_sql_typed_refinements_and_abbreviations_share_one_application(postgres, fields, expected):
    items=[('WITHOUT','SEMI EIXO LE EIXO DIANT SEM ABS'),('WITH','SEMI EIXO LD COM ABS'),
           ('UNKNOWN','SEMI EIXO LE DIANT'),('CROSS','SEMI EIXO LE EIXO TRAS SEM ABS')]
    fixture={'candidates':[{'id':i,'code':code,'title':title,'family':'semi eixo'}
        for i,(code,title) in enumerate(items,1)],'applications':[
        {'id':i,'item':i,'brand':'VW','model':'Gol','start':2008,'end':2012,
         'engines':['1.0 FLEX' if i in (1,3) else '1.0 DIESEL'],
         'transmissions':['Manual' if i!=2 else 'Automatica']} for i in range(1,5)]}
    fixture['applications'].append({'id':5,'item':4,'brand':'VW','model':'Golf','start':2008,
        'end':2012,'engines':['1.0 FLEX'],'transmissions':['Automatica']})
    criteria=SearchCriteria(part_query='semi eixo',vehicle_model='Gol',vehicle_year=2010,engine='1.0',**fields)
    assert execute_fixture(postgres,fixture,criteria)==expected


def test_sql_broad_scope_requires_complete_kit_identity(postgres, catalog):
    fixture={'candidates':[
        {'id':1,'code':'KIT','title':'KIT AMORTECEDOR DIANTEIRO','family':'DIVERSOS'},
        {'id':2,'code':'REPAIR','title':'KIT REPARO AMORTECEDOR','family':'DIVERSOS'},
        {'id':3,'code':'OTHER','title':'KIT EMBREAGEM','family':'DIVERSOS'},
    ],'applications':[]}
    assert execute_fixture(postgres,fixture,SearchCriteria(part_query='kit amortecedor'),
        family_ids=[(1,1),(1,2),(1,3)],family_title_pattern=catalog.family_title_patterns['kit amortecedor'])=={'KIT'}


def test_sql_assembly_cannot_masquerade_as_single_component(postgres):
    fixture={'candidates':[{'id':i,'code':str(i),'family':'radiador','title':title}
        for i,title in enumerate(['RADIADOR','KIT RADIADOR','REPARO RADIADOR','CONJUNTO RADIADOR'],1)],
        'applications':[]}
    assert execute_fixture(postgres,fixture,SearchCriteria(part_query='radiador'))=={'1'}


@pytest.mark.parametrize('engine,expected',[('1.0',set()),('2.0',{'MIXED'})])
def test_fuel_cannot_be_taken_from_another_engine_in_the_same_array(postgres,engine,expected):
    fixture={'candidates':[{'id':1,'code':'MIXED','family':'radiador','title':'RADIADOR'}],
        'applications':[{'id':1,'item':1,'brand':'VW','model':'Gol','start':2008,'end':2012,
                         'engines':['1.0 GASOLINA','2.0 FLEX']}]}
    assert execute_fixture(postgres,fixture,SearchCriteria(part_query='radiador',
        vehicle_model='Gol',vehicle_year=2010,engine=engine,fuel='flex'))==expected


def test_battery_box_identity_rejects_misclassified_clip(postgres,catalog):
    fixture={'candidates':[
        {'id':1,'code':'CLIP','family':'caixa de bateria','title':'PRESILHA CAPO/TAMPA BATERIA'},
        {'id':2,'code':'BOX','family':'caixa de bateria','title':'CAIXA DE BATERIA'},
    ],'applications':[]}
    assert execute_fixture(postgres,fixture,SearchCriteria(part_query='caixa de bateria'),
        family_ids=[(1,1),(1,2)],family_title_pattern=catalog.family_title_patterns['caixa de bateria'])=={'BOX'}


def test_known_vehicle_option_does_not_depend_on_a_matching_product(postgres):
    from app.infra.erp_search_query import build_follow_up_option_sql
    from scripts.eval.evaluate_erp_search import install_contract_fixture
    fixture={'candidates':[{'id':1,'code':'CLIP','family':'caixa de bateria','title':'PRESILHA'}],
        'applications':[{'id':1,'item':1,'brand':'VOLVO','model':'FH 460','start':2016,'end':2020,
                         'engines':['12.8 L 24V SOHC L6 D 13 C 460']}]}
    install_contract_fixture(postgres,fixture)
    criteria=SearchCriteria(part_query='caixa de bateria',vehicle_model='FH 460',vehicle_year=2016,
        engine='12.8 L 24V SOHC L6 D 13 C 460')
    sql,params=build_follow_up_option_sql(criteria)
    sql=sql.replace('soccol.item_search_applications','pg_temp.contract_applications')
    assert postgres.execute(sql,params).fetchone()['option_exists'] is True
    params['vehicle_model_norm']='460'
    assert postgres.execute(sql,params).fetchone() is None
    params['vehicle_model_norm']='fh 460'
    params['vehicle_year']=2000
    assert postgres.execute(sql,params).fetchone() is None


def test_new_ambiguous_request_keeps_its_explicit_vehicle_instead_of_old_pending_slot(catalog):
    from app.core.domain.models import ConversationState
    validator=LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    previous=ConversationState(criteria=SearchCriteria(part_query='semi eixo',vehicle_model='S10',vehicle_year=2017),
        pending_slot='variant',last_decision='ask')
    result=validator.validate('batente para Gol 2010',conversation_state=previous)
    assert result.decision=='ask' and result.next_question.key=='part_query'
    assert result.criteria.vehicle_model=='Gol' and result.criteria.vehicle_year==2010


def test_legacy_variant_abs_is_not_reinterpreted_as_positive_abs(catalog):
    validator=LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        logger=logging.getLogger('curation'),catalog=catalog)
    old=SearchCriteria(part_query='semi eixo',vehicle_model='S10',variant='ABS',abs=False)
    clean=validator._canonicalize_criteria_part_query(old)
    assert clean.variant is None and clean.abs is False
    assert old.variant=='ABS'
