from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreSearchCatalog:
    part_patterns: list[tuple[str, tuple[str, ...]]]
    brand_aliases: dict[str, tuple[str, ...]]
    model_aliases: dict[str, tuple[str, ...]]
    invalid_slot_tokens: set[str]
    generic_ambiguous_parts: set[str]
    needs_side: set[str]
    needs_position: set[str]
    needs_axle: set[str]
    needs_engine: set[str]
    needs_variant: set[str]
    engine_by_model: dict[str, list[str]]
    criteria_weights: dict[str, int] = field(default_factory=dict)
    min_score_to_search: int = 0
    min_score_to_search_by_part: dict[str, int] = field(default_factory=dict)
    part_code_patterns: tuple[str, ...] = field(default_factory=tuple)
    known_group_terms: set[str] = field(default_factory=set)
