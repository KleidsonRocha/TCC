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
    # Opcao, inicio e fim de vigencia vindos do mesmo catalogo que alimenta as
    # opcoes exibidas ao cliente.  A lista simples acima continua sendo usada
    # na apresentacao; estes dados permitem validar uma resposta textual.
    engine_options_by_model: dict[str, list[tuple[str, int | None, int | None]]] = field(
        default_factory=dict
    )
    needs_title_identity: set[str] = field(default_factory=set)
    # The source catalog is authoritative when it knows the manufacturer of a
    # model.  Older seeds can leave a model under SEM_MARCA_MAPEADA, therefore
    # this map is optional while the catalog is being enriched.
    model_brands: dict[str, tuple[str, ...]] = field(default_factory=dict)
    criteria_weights: dict[str, int] = field(default_factory=dict)
    min_score_to_search: int = 0
    min_score_to_search_by_part: dict[str, int] = field(default_factory=dict)
    part_code_patterns: tuple[str, ...] = field(default_factory=tuple)
    known_group_terms: set[str] = field(default_factory=set)
    part_family_ids: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
