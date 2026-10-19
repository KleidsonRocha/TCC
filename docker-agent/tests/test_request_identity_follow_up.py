"""Regressions from the base-model category audit, independent of a live LLM."""
import json
import logging

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.core.domain.models import ConversationState, PartItem
from app.core.domain.pre_search import SearchCriteria
from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.infra.pre_search_dictionary_extractor import DictionaryPreSearchExtractor
from app.infra.pre_search_validator_llm import LLMPreSearchValidator
from app.main import create_app


@pytest.fixture
def catalog():
    return PreSearchCatalog(
        part_patterns=[(name, aliases) for name, aliases in [
            ('bomba de agua', ('bomba agua', 'bomba da agua', 'bomba de agua')),
            ('polia bomba de agua', ('polia bomba de agua', 'polia da bomba de agua')),
            ('rolamento de suspensao', ('rolamento de suspensao',)),
            ('amortecedores suspensao', ('amortecedor', 'amortecedores suspensao')),
            ('cilindro de roda', ('cilindro roda', 'cilindro de roda')),
            ('kit amortecedor', ('kit amortecedor',)),
            ('semi eixo', ('semi eixo',)), ('bujao', ('bujao',)),
            ('caixa de bateria', ('caixa de bateria',)), ('radiador', ('radiador',)),
            ('pastilhas de freio', ('pastilha', 'pastilhas')),
        ]],
        brand_aliases={'FIAT': ('fiat',), 'RENAULT': ('renault',)},
        model_aliases={name: (name.lower(),) for name in [
            'SAVEIRO', 'SANTANA', 'GOL', 'PARATI', 'PALIO', 'SIENA', 'STRADA',
            'TEMPRA', 'CLIO', 'TWINGO', 'S10', '4X4', 'FH 460', '460', 'IBIZA',
        ]},
        invalid_slot_tokens={'nao'}, generic_ambiguous_parts=set(),
        needs_side=set(), needs_position=set(), needs_axle=set(),
        needs_engine={'radiador', 'caixa de bateria'}, needs_variant={'semi eixo', 'bujao'},
        engine_by_model={'fh 460': ['12.8 L 24V SOHC L6 D 13 C 460']},
        engine_options_by_model={'fh 460': [('12.8 L 24V SOHC L6 D 13 C 460', 2010, 2020)]},
    )


@pytest.fixture
def validator(catalog):
    instance = LLMPreSearchValidator(
        settings=Settings(CATALOG_DB_ENABLED=False, LLM_WARMUP_ENABLED=False),
        catalog=catalog, logger=logging.getLogger('identity-test'),
    )
    instance._post_chat_or_generate = lambda **kwargs: pytest.fail('Unexpected LLM call')
    return instance


@pytest.mark.parametrize('message,part,model,year', [
    ('POLIA 6PK BOMBA DA AGUA VW GOL/PARATI/SAVEIRO/SANTANA 97/ para SAVEIRO 2005 motor 2.0', 'polia bomba de agua', 'SAVEIRO', 2005),
    ('TAPA-PO CILINDRO RODA VW GOL/GOLF/SAVEIRO para IBIZA 1999 motor 1.6 traseiro', 'tapa po cilindro de roda', 'IBIZA', 1999),
    ('ROLAMENTO AMORTECEDOR FIAT PALIO/SIENA/STRADA/TEMPRA para PALIO 2009 motor 1.0 dianteiro', 'rolamento de suspensao', 'PALIO', 2009),
    ('KIT AMORTECEDOR RENAULT CLIO 98/ TWINGO 2000/ DIANTEIRO para CLIO 2004 motor 1.6 dianteiro', 'kit amortecedor', 'CLIO', 2004),
    ('semi eixo para S10 2017 motor 2.5 LTZ FLEX 4X4 CD AT', 'semi eixo', 'S10', 2017),
])
def test_audited_product_titles_keep_component_and_requested_application(catalog, message, part, model, year):
    extractor = DictionaryPreSearchExtractor(catalog=catalog)
    criteria = extractor.extract(message)
    assert (criteria.part_query, criteria.vehicle_model, criteria.vehicle_year) == (part, model, year)
    assert len(extractor.extract_items(message)) == 1


def test_multi_item_components_do_not_become_inner_parts_or_share_local_vehicles(catalog):
    items = DictionaryPreSearchExtractor(catalog=catalog).extract_items(
        'polia 6PK bomba da agua para SAVEIRO 2005 motor 2.0 e '
        'rolamento amortecedor para PALIO 2009 motor 1.0 dianteiro'
    )
    assert [(i.part_query, i.vehicle_model, i.vehicle_year, i.engine) for i in items] == [
        ('polia bomba de agua', 'SAVEIRO', 2005, '2.0'),
        ('rolamento de suspensao', 'PALIO', 2009, '1.0'),
    ]


@pytest.mark.parametrize('message,part,model,year', [
    ('POLIA 6PK BOMBA DA AGUA VW GOL/PARATI/SAVEIRO/SANTANA 97/ para SAVEIRO 2005 motor 2.0', 'polia bomba de agua', 'SAVEIRO', 2005),
    ('ROLAMENTO AMORTECEDOR FIAT PALIO/SIENA/STRADA/TEMPRA para PALIO 2009 motor 1.0 dianteiro', 'rolamento de suspensao', 'PALIO', 2009),
    ('KIT AMORTECEDOR RENAULT CLIO 98/ TWINGO 2000/ DIANTEIRO para CLIO 2004 motor 1.6 dianteiro', 'kit amortecedor', 'CLIO', 2004),
])
def test_current_component_and_application_survive_incorrect_llm_output(validator, message, part, model, year):
    calls = []
    def wrong_response(**kwargs):
        calls.append(kwargs)
        return ({'message': {'content': json.dumps({
            'decision': 'search', 'criteria': {'part_query': 'bomba de agua',
                'vehicle_model': 'STRADA', 'vehicle_year': 2000},
            'missing_fields': [], 'confidence': 0.9,
        })}}, '/api/chat')
    validator._post_chat_or_generate = wrong_response
    result = validator.validate(message)
    assert calls
    assert (result.criteria.part_query, result.criteria.vehicle_model, result.criteria.vehicle_year) == (part, model, year)


@pytest.mark.parametrize('message', [
    'kit amortecedor traseiro para TEMPRA 1998 motor 2.0 dianteiro',
    'semi eixo direito para S10 2017 motor 2.5 esquerdo',
    'pastilha dianteira e traseira para PALIO 2009',
])
def test_conflicting_directions_stop_before_search_and_llm(validator, message):
    assert validator.try_validate_deterministically(message) is None
    for method in [validator.try_validate_deterministic_ask, validator.validate]:
        result = method(message)
        assert result.decision == 'ask'
        assert result.next_question.key == 'intent_resolution'


def test_different_items_can_have_different_positions(catalog):
    extractor = DictionaryPreSearchExtractor(catalog=catalog)
    message = 'pastilha dianteira para GOL 2010 e amortecedor traseiro para PALIO 2009'
    assert extractor.resolve_request_intent(message).unresolved_reason is None
    assert [i.position for i in extractor.extract_items(message)] == ['front', 'rear']


def test_negation_and_explicit_replacement_preserve_only_affirmative_component(validator):
    result = validator.try_validate_deterministically(
        'nao quero bomba de agua, quero polia da bomba de agua para SAVEIRO 2005 motor 2.0'
    )
    assert result.criteria.part_query == 'polia bomba de agua'
    assert result.criteria.vehicle_model == 'SAVEIRO'
    assert validator.try_validate_deterministic_ask('nao quero polia da bomba de agua').decision == 'ask'
    assert validator.try_validate_deterministically('pastilha dianteira nao traseira GOL 2010').criteria.position == 'front'


def test_unknown_component_is_not_released_as_its_known_main_part(validator):
    message = 'tapa-po cilindro roda para IBIZA 1999 motor 1.6'
    assert validator.try_validate_deterministically(message) is None
    result = validator.validate(message)
    assert result.decision == 'ask'
    assert result.criteria.part_query == 'tapa po cilindro de roda'


def state(part='semi eixo', model='S10', year=2017, engine='2.5', slot='variant'):
    return ConversationState(criteria=SearchCriteria(
        part_query=part, vehicle_model=model, vehicle_year=year, engine=engine,
    ), pending_slot=slot, last_decision='ask')


@pytest.mark.parametrize('answer,previous,expected', [
    ('LTZ 2.5 FLEX 4X4 CD AT', state(), 'LTZ 2.5 FLEX 4X4 CD AT'),
    ('ELX RST III', state('bujao', 'PALIO', 2010, '1.0'), 'ELX RST III'),
])
def test_proven_variant_answer_preserves_vehicle_and_full_value(validator, answer, previous, expected):
    calls=[]
    def prove(**kw):
        calls.append(kw)
        assert kw['criteria'] == previous.criteria
        return answer if kw['field']=='variant' and kw['value']==answer else None
    validator.set_follow_up_resolver(prove)
    result=validator.try_validate_deterministically(answer, conversation_state=previous)
    assert result.decision=='search'
    assert result.criteria.variant==expected
    assert result.criteria.vehicle_model==previous.criteria.vehicle_model
    assert result.criteria.engine==previous.criteria.engine
    assert result.criteria.vehicle_year==previous.criteria.vehicle_year
    assert result.criteria.part_code is None and calls


@pytest.mark.parametrize('answer', ['LTZ 2.5 FLEX 4X4 CD AT', 'versao desconhecida', 'nao sei'])
def test_unproved_variant_does_not_promote_incidental_model_or_fuel(validator, answer):
    validator.set_follow_up_resolver(lambda **kw: None)
    previous=state()
    result=validator.try_validate_deterministically(answer, conversation_state=previous)
    if result is not None:assert result.decision!='search'
    current=validator._normalize_pending_follow_up_current_criteria(
        message_text=answer,criteria=validator.extract_dictionary_seed_criteria(message_text=answer),
        conversation_state=previous,
    )
    assert current.vehicle_model=='S10'
    assert current.variant is None


def test_unknown_variant_is_asked_without_letting_llm_invent_a_value(validator):
    validator.set_follow_up_resolver(lambda **kw: None)
    result=validator.validate('versao desconhecida',conversation_state=state())
    assert result.decision=='ask'
    assert result.next_question.key=='variant'
    assert result.criteria.vehicle_model=='S10' and result.criteria.variant is None


def test_unavailable_contextual_source_is_handoff_not_invalid_option(validator):
    def fail(**kwargs):raise RuntimeError('simulated unavailable source')
    validator.set_follow_up_resolver(fail)
    result=validator.validate('LTZ 2.5 FLEX 4X4 CD AT',conversation_state=state())
    assert result.decision=='handoff'
    assert 'verificar' in result.next_question.prompt


def test_contextual_proof_is_reused_only_within_one_request(validator):
    calls=[]
    validator.set_follow_up_resolver(lambda **kw: calls.append(kw) or kw['value'])
    previous=state()
    for _ in range(2):
        validator.begin_validation_request()
        validator.prepare_follow_up('LTZ 2.5 FLEX 4X4 CD AT',conversation_state=previous)
        validator.try_validate_deterministically('LTZ 2.5 FLEX 4X4 CD AT',conversation_state=previous)
    assert len(calls)==2


@pytest.mark.parametrize('message', [
    'semi eixo direito para S10 2017 motor 2.5 esquerdo',
    'tapa-po cilindro roda para IBIZA 1999 motor 1.6',
])
def test_http_unresolved_identity_never_reaches_search(validator, message):
    tools=RecordingTools()
    app=create_app(settings_override=Settings(CATALOG_DB_ENABLED=False,PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,LLM_WARMUP_ENABLED=False),pre_search_validator_override=validator,tools_override=tools)
    with TestClient(app)as client:
        response=client.post('/respond',json={
            'schema_version':'1.0','trace_id':'identity-confirm','conversation_id':'identity-confirm',
            'channel':{'name':'test'},'business':{'branch_id':1},'message':{'text':message},
        })
    assert response.status_code==200
    assert tools.calls==[]
    assert response.json()['conversation_state']['last_decision']=='ask'


def test_textual_truck_engine_is_governed_by_previous_model_and_year(validator):
    previous=state('radiador','FH 460',2016,None,'engine')
    result=validator.try_validate_deterministically('12.8 L 24V SOHC L6 D 13 C 460',conversation_state=previous)
    assert result.decision=='search'
    assert result.criteria.vehicle_model=='FH 460'
    assert result.criteria.engine=='12.8 L 24V SOHC L6 D 13 C 460'
    # Same text outside the catalog interval is not an accepted engine option.
    previous.criteria.vehicle_year=2000
    result=validator.try_validate_deterministically('12.8 L 24V SOHC L6 D 13 C 460',conversation_state=previous)
    assert result is None


def test_initial_explicit_truck_displacement_is_not_read_as_a_dimension(catalog):
    extractor=DictionaryPreSearchExtractor(catalog=catalog)
    assert extractor.extract('radiador para FH 460 2016 motor 12.8').engine=='12.8'
    assert extractor.extract('radiador FH 460 com largura 12.8 mm').engine is None


def test_full_engine_answer_requires_proof_when_catalog_only_knows_engine_code(catalog):
    catalog.engine_by_model['fh 460'] = ['D 13 C 460']
    catalog.engine_options_by_model['fh 460'] = [('D 13 C 460', 2010, 2020)]
    instance = LLMPreSearchValidator(settings=Settings(CATALOG_DB_ENABLED=False),
        catalog=catalog, logger=logging.getLogger('identity-test'))
    previous = state('radiador', 'FH 460', 2016, None, 'engine')
    answer = '12.8 L 24V SOHC L6 D 13 C 460'
    instance.set_follow_up_resolver(lambda **kw: kw['value'])
    result = instance.try_validate_deterministically(answer, conversation_state=previous)
    assert result.criteria.engine == answer
    instance.begin_validation_request()
    instance.set_follow_up_resolver(lambda **kw: None)
    result = instance.validate(answer, conversation_state=previous)
    assert result.decision == 'ask' and result.next_question.key == 'engine'
    assert result.criteria.engine is None


def test_explicit_vehicle_correction_is_not_hidden_by_pending_variant(validator):
    validator._post_chat_or_generate=lambda **kw: ({'message':{'content':json.dumps({
        'decision':'search','criteria':{'part_query':'semi eixo','vehicle_model':'S10','vehicle_year':2017,'variant':'flex'},
        'missing_fields':[],'confidence':0.9})}},'/api/chat')
    result=validator.validate('corrigindo, para PALIO 2010 motor 1.0',conversation_state=state())
    assert result.criteria.vehicle_model=='PALIO'
    assert result.criteria.vehicle_year==2010


def test_llm_cannot_replace_proven_version_or_component(validator):
    validator.set_follow_up_resolver(lambda **kw: 'LTZ 2.5 FLEX 4X4 CD AT')
    validator._post_chat_or_generate=lambda **kw: ({'message':{'content':json.dumps({
        'decision':'ask','criteria':{'part_query':'bomba de agua','vehicle_model':'4X4','variant':'flex'},
        'missing_fields':['variant'],'confidence':0.8})}},'/api/chat')
    result=validator.validate('LTZ 2.5 FLEX 4X4 CD AT',conversation_state=state())
    assert result.decision=='search'
    assert result.criteria.part_query=='semi eixo'
    assert result.criteria.vehicle_model=='S10'
    assert result.criteria.variant=='LTZ 2.5 FLEX 4X4 CD AT'


@pytest.mark.parametrize('message', [
    'nao e 1.6', 'nao e duratec',
])
def test_unrepresentable_negated_attribute_requires_confirmation(validator, message):
    previous=state('radiador','FH 460',2016,None,'engine')
    result=validator.validate(message,conversation_state=previous)
    assert result.decision=='ask'
    assert result.next_question.key=='intent_resolution'


def test_active_multi_item_version_answer_only_changes_the_selected_item(validator):
    previous=state()
    previous.items=[SearchCriteria(part_query='bujao',vehicle_model='PALIO',vehicle_year=2010,engine='1.0',variant='ELX RST III'),previous.criteria]
    previous.active_item_index=1
    validator.set_follow_up_resolver(lambda **kw:'LTZ 2.5 FLEX 4X4 CD AT')
    result=validator.try_validate_deterministically(
        'LTZ 2.5 FLEX 4X4 CD AT',conversation_state=previous,
        last_messages=[{'role':'user','text':'bujao para PALIO 2010 motor 1.0 e semi eixo para S10 2017 motor 2.5'}],
    )
    assert result.criteria.vehicle_model=='S10'
    assert result.criteria.part_query=='semi eixo'
    assert previous.items[0].variant=='ELX RST III'


class RecordingTools:
    def __init__(self):self.calls=[]
    def resolve_follow_up_value(self, **kw):
        assert kw['criteria'].vehicle_model=='S10'
        return kw['value'] if kw['value']=='LTZ 2.5 FLEX 4X4 CD AT' else None
    def search_parts(self,query,branch_id,criteria=None):
        self.calls.append(criteria)
        return [PartItem(item_id='KJH0309',title='SEMIEIXO S10',score=0.8)]


def test_http_follow_up_uses_proof_and_preserves_search_filters(validator):
    tools=RecordingTools()
    app=create_app(settings_override=Settings(CATALOG_DB_ENABLED=False,PRE_SEARCH_REVIEW_CAPTURE_ENABLED=False,LLM_WARMUP_ENABLED=False),
                   pre_search_validator_override=validator,tools_override=tools)
    with TestClient(app)as client:
        response=client.post('/respond',json={
            'schema_version':'1.0','trace_id':'identity-s10','conversation_id':'identity-s10',
            'channel':{'name':'test'},'business':{'branch_id':1},
            'message':{'text':'LTZ 2.5 FLEX 4X4 CD AT'},
            'context':{'last_messages':[],'conversation_state':state().model_dump()},
        })
    assert response.status_code==200
    assert len(tools.calls)==1
    assert tools.calls[0].vehicle_model=='S10'
    assert tools.calls[0].variant=='LTZ 2.5 FLEX 4X4 CD AT'
    assert response.json()['conversation_state']['criteria']['variant']=='LTZ 2.5 FLEX 4X4 CD AT'
