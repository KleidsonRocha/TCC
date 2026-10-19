"""Apply database-backed concept and alias decisions without changing ERP taxonomy."""
from collections import defaultdict
from dataclasses import replace
import re

from app.core.domain.pre_search_catalog import PreSearchCatalog
from app.infra.pre_search_text import normalize_pre_search_text


def source_identity_matches(source: dict, family: str, catalog: PreSearchCatalog) -> bool:
    """Independent evaluator check: scope plus component, never title alone."""
    if (source['cd_grupo'], source['cd_subgrupo']) not in catalog.part_family_ids.get(family, []):
        return False
    title = normalize_pre_search_text(source.get('candidate_title'))
    pattern = catalog.family_title_patterns.get(family)
    if pattern and not re.search(pattern.replace(r'\m', r'\b').replace(r'\M', r'\b'), title):
        return False
    head = title.split()[0] if title else ''
    if head.rstrip('s') in {'kit','tampa','mangueira','suporte','reparo','conjunto'}:
        if head.rstrip('s') not in {word.rstrip('s') for word in family.split()}:
            return False
    return True


def curate_catalog(catalog: PreSearchCatalog, concepts: list[dict], decisions: list[dict]) -> PreSearchCatalog:
    patterns = {key: set(aliases) for key, aliases in catalog.part_patterns}
    scopes = {key: set(map(tuple, pairs)) for key, pairs in catalog.part_family_ids.items()}
    rule_fields = ('generic_ambiguous_parts', 'needs_side', 'needs_position', 'needs_axle',
                   'needs_engine', 'needs_variant', 'needs_title_identity')
    rules = {field: set(getattr(catalog, field)) for field in rule_fields}
    title_patterns = dict(catalog.family_title_patterns)
    for row in concepts:
        family = row['family_key']
        if family not in patterns and not row['aliases'] and not row['source_families']:
            continue
        patterns.setdefault(family, set()).update(row['aliases'])
        patterns[family].add(family)
        for source in row['source_families']:
            if source == family:
                continue
            patterns[family].update(patterns.pop(source, set()))
            scopes.setdefault(family, set()).update(scopes.pop(source, set()))
            for field in rule_fields:
                if source in rules[field]:
                    rules[field].add(family)
                    rules[field].discard(source)
        if row['title_pattern']:
            title_patterns[family] = row['title_pattern']
        for field in rule_fields[:-1]:
            value = row.get(field)
            if value is True:
                rules[field].add(family)
            elif value is False:
                rules[field].discard(family)
    ambiguous = set(catalog.ambiguous_part_aliases)
    for row in decisions:
        alias, family = row['alias_normalized'], row['family_key']
        for aliases in patterns.values():
            aliases.discard(alias)
        if family:
            if family not in patterns:
                raise ValueError(f'Unknown curated alias family: {family}')
            patterns[family].add(alias)
            ambiguous.discard(alias)
        else:
            ambiguous.add(alias)
    # Unreviewed collisions also fail closed; never choose dictionary order.
    targets = defaultdict(set)
    for family, aliases in patterns.items():
        for alias in aliases:
            targets[alias].add(family)
    ambiguous.update(alias for alias, families in targets.items() if len(families) > 1)
    for aliases in patterns.values():
        aliases.difference_update(ambiguous)
    return replace(catalog, part_patterns=[(key, tuple(sorted(aliases))) for key, aliases in sorted(patterns.items()) if aliases],
        part_family_ids={key: sorted(pairs) for key, pairs in scopes.items()},
        family_title_patterns=title_patterns, ambiguous_part_aliases=ambiguous, **rules)
