from app.core.domain.models import PartItem
from app.core.domain.result_disambiguation import (
    build_result_disambiguation_state,
    resolve_result_disambiguation,
)


def _item(
    item_id: str,
    title: str,
    score: float,
    **attributes: list[str],
) -> PartItem:
    return PartItem(
        item_id=item_id,
        title=title,
        score=score,
        attributes=attributes,
    )


def test_build_state_chooses_attribute_that_really_separates_candidates() -> None:
    state = build_result_disambiguation_state(
        [
            _item("A-1", "Radiador 1.0", 0.9, application=["Gol"], engine=["1.0"]),
            _item("A-2", "Radiador 1.6", 0.8, application=["Gol"], engine=["1.6"]),
        ]
    )

    assert state.question_key == "engine"
    assert [option.label for option in state.options] == ["1.0", "1.6"]
    assert state.attempt == 1


def test_attribute_answer_selects_single_candidate() -> None:
    state = build_result_disambiguation_state(
        [
            _item("A-1", "Radiador 1.0", 0.9, engine=["1.0"]),
            _item("A-2", "Radiador 1.6", 0.8, engine=["1.6"]),
        ]
    )

    resolution = resolve_result_disambiguation("motor 1.6", state)

    assert resolution.kind == "selected"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.item_id == "A-2"


def test_item_fallback_is_short_and_accepts_number() -> None:
    state = build_result_disambiguation_state(
        [
            _item(f"A-{index}", f"Item {index}", 0.9 - index / 100)
            for index in range(1, 13)
        ]
    )

    assert state.question_key == "item"
    assert len(state.options) == 10

    resolution = resolve_result_disambiguation("opcao 2", state)

    assert resolution.kind == "selected"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.item_id == "A-2"


def test_negating_item_page_advances_without_repeating_candidates() -> None:
    state = build_result_disambiguation_state(
        [
            _item(f"A-{index}", f"Item {index}", 0.9 - index / 100)
            for index in range(1, 13)
        ]
    )

    resolution = resolve_result_disambiguation("nenhuma dessas", state)

    assert resolution.kind == "listed"
    assert [candidate.item_id for candidate in resolution.listed_candidates] == ["A-11", "A-12"]


def test_ver_mais_advances_page_without_consuming_failed_attempt() -> None:
    state = build_result_disambiguation_state(
        [
            _item(f"A-{index}", f"Item {index}", 0.9 - index / 100)
            for index in range(1, 24)
        ]
    )

    resolution = resolve_result_disambiguation("ver mais", state)

    assert resolution.kind == "ask"
    assert resolution.state is not None
    assert resolution.state.attempt == 1
    assert resolution.state.visible_candidate_ids == [f"A-{index}" for index in range(11, 21)]


def test_negating_discriminator_offers_new_search_instead_of_inventing_filter() -> None:
    state = build_result_disambiguation_state(
        [
            _item("A-1", "Radiador 1.0", 0.9, engine=["1.0"]),
            _item("A-2", "Radiador 1.6", 0.8, engine=["1.6"]),
        ]
    )

    resolution = resolve_result_disambiguation("nao sei", state)

    assert resolution.kind == "rejected"


def test_unrecognized_answers_reach_handoff_only_after_limit() -> None:
    state = build_result_disambiguation_state(
        [_item("A-1", "Item 1", 0.9), _item("A-2", "Item 2", 0.8)]
    )

    second = resolve_result_disambiguation("talvez", state)
    assert second.kind == "unresolved"
    assert second.state is not None
    assert second.state.attempt == 2

    third = resolve_result_disambiguation("aquela", second.state)
    assert third.kind == "unresolved"
    assert third.state is not None
    assert third.state.attempt == 3

    handoff = resolve_result_disambiguation("indefinido", third.state)
    assert handoff.kind == "handoff"


def test_explicit_handoff_request_does_not_consume_attempts() -> None:
    state = build_result_disambiguation_state(
        [_item("A-1", "Item 1", 0.9), _item("A-2", "Item 2", 0.8)]
    )

    resolution = resolve_result_disambiguation("quero falar com um vendedor", state)

    assert resolution.kind == "handoff"
    assert resolution.handoff_reason == "result_disambiguation_requested"


def test_controlled_title_feature_can_be_used_as_other_discriminator() -> None:
    state = build_result_disambiguation_state(
        [
            _item("R-1", "Radiador com ar", 0.9, feature=["Com ar condicionado"]),
            _item("R-2", "Radiador sem ar", 0.8, feature=["Sem ar condicionado"]),
        ]
    )

    assert state.question_key == "feature"
    assert [option.label for option in state.options] == [
        "Com ar condicionado",
        "Sem ar condicionado",
    ]


def test_missing_attribute_does_not_exclude_unknown_candidates():
    state = build_result_disambiguation_state([
        _item("R-1", "Radiador Gol", .9, engine=["1.0"]),
        _item("R-2", "Radiador Gol", .8, engine=["1.6"]),
        _item("R-3", "Radiador Gol", .7),
    ])
    assert state.question_key == "item"


def test_free_refinement_invalidates_candidates_only_for_unoffered_filter():
    import logging
    from app.config import Settings
    from app.core.domain.models import ConversationState
    from app.core.domain.pre_search import SearchCriteria
    from app.core.usecases.process_agent_request import ProcessAgentRequestUseCase

    class Validator:
        def extract_dictionary_seed_criteria(self, *, message_text, last_messages):
            return SearchCriteria(engine=message_text)

    use_case = ProcessAgentRequestUseCase(
        tools=None, pre_search_validator=Validator(), settings=Settings(),
        logger=logging.getLogger('test'), review_recorder=None,
    )
    state = ConversationState(
        criteria=SearchCriteria(part_query='radiador', vehicle_model='Gol'),
        pending_slot='result_disambiguation',
        result_disambiguation=build_result_disambiguation_state([
            _item('R-1', 'Radiador', .9, engine=['1.0']),
            _item('R-2', 'Radiador', .8, engine=['1.6']),
        ]),
    )
    retained, changed = use_case._invalidate_result_disambiguation_for_criteria_correction(
        query='1.6', incoming_state=state,
    )
    assert not changed
    assert retained.result_disambiguation is not None
    cleared, changed = use_case._invalidate_result_disambiguation_for_criteria_correction(
        query='2.0', incoming_state=state,
    )
    assert changed
    assert cleared.result_disambiguation is None
    assert cleared.pending_slot == 'engine'


def test_shared_option_that_does_not_narrow_is_not_offered():
    state = build_result_disambiguation_state([
        _item("R-1", "Radiador", .9, application=["Gol", "Corsa"]),
        _item("R-2", "Radiador", .8, application=["Gol"]),
    ])
    assert state.question_key == "item"


def test_attribute_labels_are_normalized_across_candidates():
    state = build_result_disambiguation_state([
        _item("R-1", "Radiador", .9, variant=["Basico"]),
        _item("R-2", "Radiador", .8, variant=["BASICO"]),
        _item("R-3", "Radiador", .7, variant=["Sport"]),
    ])
    assert len(state.options) == 2
    assert state.options[0].candidate_ids == ["R-1", "R-2"]


def test_directional_disambiguation_normalizes_gender_and_keeps_axle_distinct():
    position_state = build_result_disambiguation_state([
        _item("R-1", "Pastilha", .9, position=["dianteira"]),
        _item("R-2", "Pastilha", .8, position=["traseiro"]),
    ])
    axle_state = build_result_disambiguation_state([
        _item("R-1", "Bucha", .9, axle=["eixo dianteiro"]),
        _item("R-2", "Bucha", .8, axle=["traseira"]),
    ])

    assert position_state.question_key == "position"
    assert [option.label for option in position_state.options] == ["Dianteiro", "Traseiro"]
    assert axle_state.question_key == "axle"
    assert [option.label for option in axle_state.options] == ["Eixo dianteiro", "Eixo traseiro"]


def test_negated_product_code_never_selects_product():
    state = build_result_disambiguation_state([
        _item("R-1", "Radiador Gol", .9),
        _item("R-2", "Radiador Gol", .8),
    ])
    assert resolve_result_disambiguation("nao quero R-1", state).kind == "rejected"


def test_unanswered_attribute_moves_to_list_and_preserves_serialized_state():
    from app.core.domain.models import ConversationState
    state = build_result_disambiguation_state([
        _item("R-1", "Radiador Gol", .9, engine=["1.0"]),
        _item("R-2", "Radiador Gol", .8, engine=["1.6"]),
    ])
    resolution = resolve_result_disambiguation("talvez", state)
    assert resolution.state.question_key == "item"
    assert "engine" in resolution.state.asked_fields
    restored = ConversationState.model_validate_json(ConversationState(
        pending_slot="result_disambiguation",
        result_disambiguation=resolution.state,
    ).model_dump_json())
    selected = resolve_result_disambiguation("2", restored.result_disambiguation)
    assert selected.selected_candidate.item_id == "R-2"
    assert resolution.state.visible_candidate_ids == ["R-1", "R-2"]
    assert "itens apresentados" in resolution.state.prompt
