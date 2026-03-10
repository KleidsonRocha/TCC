from dataclasses import dataclass


@dataclass(frozen=True)
class PreSearchCatalog:
    part_patterns: list[tuple[str, tuple[str, ...]]]
    brand_aliases: dict[str, tuple[str, ...]]
    model_aliases: dict[str, tuple[str, ...]]
    invalid_slot_tokens: set[str]
    generic_ambiguous_parts: set[str]
    needs_side: set[str]
    needs_position: set[str]
    needs_engine: set[str]
    engine_by_model: dict[str, list[str]]
