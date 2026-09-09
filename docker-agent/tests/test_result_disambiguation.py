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
            for index in range(1, 7)
        ]
    )

    assert state.question_key == "item"
    assert len(state.options) == 4

    resolution = resolve_result_disambiguation("opcao 2", state)

    assert resolution.kind == "selected"
    assert resolution.selected_candidate is not None
    assert resolution.selected_candidate.item_id == "A-2"


def test_negating_item_page_advances_without_repeating_candidates() -> None:
    state = build_result_disambiguation_state(
        [
            _item(f"A-{index}", f"Item {index}", 0.9 - index / 100)
            for index in range(1, 7)
        ]
    )

    resolution = resolve_result_disambiguation("nenhuma dessas", state)

    assert resolution.kind == "ask"
    assert resolution.state is not None
    assert resolution.state.attempt == 2
    assert [candidate.item_id for candidate in resolution.state.candidates] == ["A-5", "A-6"]


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
