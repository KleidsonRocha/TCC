"""Exercise the search contract and CSV round-trip with automotive golden cases.

Only temporary tables are created in the local catalog database; never writes to ERP.
--integration-sql additionally audits SELECTs from a locally supplied ERP DDL file.
"""

import argparse
import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import Settings
from app.core.domain.pre_search import SearchCriteria
from app.infra.erp_search_tools_pg import PostgresErpSearchTools
from app.infra.postgres_conninfo import build_catalog_conninfo
from scripts.erp.export_search_snapshot import source_select


GOLDEN_PATH = Path("docs/assets/datasets/erp_search_golden_set.json")
SOURCE_TABLES = {
    "item": "id_item int, cd_item text, nm_item text, nm_reduzido text, cd_grupo int, cd_subgrupo int, fl_ativo text, cd_tipo text",
    "item_produto": "id_item int, cd_original text, cd_fabricante text",
    "subgrupo": "cd_grupo int, cd_subgrupo int, nm_subgrupo text",
    "produto_veiculos": "id_geral bigint, id_item int, cd_montadora int, cd_modelo int, ano_inicial int, ano_final int, cd_complemento int, complemento text, aplicacao text",
    "veiculo_modelo": "cd_modelo int, nm_modelo text, cd_montadora int",
    "veiculo_montadora": "cd_montadora int, nm_montadora text",
    "veiculo_complemento": "cd_complemento int, nm_complemento text",
    "veiculo_motor": "cd_motor int, nm_motor text",
    "veiculo_injecao": "cd_injecao int, nm_injecao text",
    "veiculo_transmissao": "cd_transmissao int, nm_transmissao text",
    "produto_veiculos_motor": "id_produto_veiculos bigint, cd_motor int",
    "produto_veiculos_injecao": "id_produto_veiculos bigint, cd_injecao int",
    "produto_veiculos_transmissao": "id_produto_veiculos bigint, cd_transmissao int",
    # Poisoned model-wide attributes must never be inherited by the item.
    "veiculo_modelo_motor": "cd_modelo int, cd_motor int",
    "veiculo_modelo_injecao": "cd_modelo int, cd_injecao int",
    "veiculo_modelo_transmissao": "cd_modelo int, cd_transmissao int",
    "veiculo_modelo_complemento": "cd_modelo int, cd_complemento int",
}


def install_source_fixture(conn, fixture: dict, integration_sql: Path) -> None:
    for name, columns in SOURCE_TABLES.items():
        conn.execute(f"CREATE TEMP TABLE {name} ({columns}) ON COMMIT DROP")
    brands = {}
    models = {}
    for item in fixture["candidates"]:
        conn.execute("INSERT INTO item VALUES (%s,%s,%s,%s,1,%s,'S','01')",
                     (item["id"], item["code"], item.get("name", item["title"]), item["title"], item["id"]))
        conn.execute("INSERT INTO subgrupo VALUES (1,%s,%s)", (item["id"], item["family"]))
    for application in fixture["applications"]:
        brand = application["brand"]
        model = (brand, application["model"])
        if brand not in brands:
            brands[brand] = len(brands) + 1
            conn.execute("INSERT INTO veiculo_montadora VALUES (%s,%s)", (brands[brand], brand))
        if model not in models:
            models[model] = len(models) + 1
            conn.execute("INSERT INTO veiculo_modelo VALUES (%s,%s,%s)", (models[model], model[1], brands[brand]))
        variants = application.get("variants", [])
        conn.execute("INSERT INTO produto_veiculos VALUES (%s,%s,%s,%s,%s,%s,NULL,%s,%s)", (
            application["id"], application["item"], brands[brand], models[model],
            application["start"], 0 if application.get("open") else application["end"],
            variants[0] if variants else None, "Texto livre 1.0 GLX nao comprova aplicacao",
        ))
        for key, singular in (("engines", "motor"), ("injections", "injecao"), ("transmissions", "transmissao")):
            for index, value in enumerate(application.get(key, [])):
                identifier = application["id"] * 100 + index
                conn.execute(f"INSERT INTO veiculo_{singular} VALUES (%s,%s)", (identifier, value))
                conn.execute(f"INSERT INTO produto_veiculos_{singular} VALUES (%s,%s)", (application["id"], identifier))
    for singular in ("motor", "injecao", "transmissao", "complemento"):
        conn.execute(f"INSERT INTO veiculo_{singular} VALUES (999999,'ATRIBUTO DE OUTRA PECA 1.0')")
        for model_id in models.values():
            conn.execute(f"INSERT INTO veiculo_modelo_{singular} VALUES (%s,999999)", (model_id,))
    # The external module is tested from its actual SELECTs, not a rewritten imitation.
    external_sql = integration_sql.read_text(encoding="utf-8")
    for name in ("candidates", "applications"):
        select = external_sql.split(f"-- BEGIN {name.upper()} SELECT\n", 1)[1].split(
            f"-- END {name.upper()} SELECT", 1
        )[0].strip().replace("public.", "pg_temp.")
        conn.execute(f"CREATE TEMP VIEW integration_{name} AS {select}")


def install_contract_fixture(conn, fixture: dict) -> None:
    conn.execute("""CREATE TEMP TABLE contract_candidates (
        id_item bigint PRIMARY KEY, cd_item text, nm_item text, candidate_title text,
        cd_grupo integer, cd_subgrupo integer, part_family text NOT NULL,
        cd_original text, cd_fabricante text, search_text text
    ) ON COMMIT DROP""")
    conn.execute("""CREATE TEMP TABLE contract_applications (
        application_id bigint PRIMARY KEY, id_item bigint REFERENCES contract_candidates(id_item),
        vehicle_brand text, vehicle_model text, year_start integer, year_end integer,
        year_open_end boolean, engines text[], variants text[], injections text[],
        transmissions text[], application_text text
    ) ON COMMIT DROP""")
    for item in fixture["candidates"]:
        conn.execute("INSERT INTO contract_candidates VALUES (%s,%s,%s,%s,1,%s,%s,NULL,NULL,%s)", (
            item["id"], item["code"], item.get("name", item["title"]), item["title"],
            item["id"], item["family"], item["title"],
        ))
    for app in fixture["applications"]:
        conn.execute("INSERT INTO contract_applications VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
            app["id"], app["item"], app["brand"], app["model"], app["start"],
            None if app.get("open") else app["end"], bool(app.get("open")),
            app.get("engines", []), app.get("variants", []), app.get("injections", []),
            app.get("transmissions", []), "Texto livre 1.0 GLX nao comprova aplicacao",
        ))


def install_fixture(conn, fixture: dict, integration_sql: Path | None = None) -> None:
    install_contract_fixture(conn, fixture)
    if integration_sql is not None:
        install_source_fixture(conn, fixture, integration_sql)
    for name in ("candidates", "applications"):
        # Use the exporter's exact column projection; array/NULL serialization matters.
        select = source_select(name).replace(f"soccol.item_search_{name}", f"pg_temp.contract_{name}")
        conn.execute(f"CREATE TEMP TABLE snapshot_{name} (LIKE contract_{name}) ON COMMIT DROP")
        with conn.cursor() as cur:
            with cur.copy(f"COPY ({select}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)") as copy:
                chunks = [bytes(chunk) for chunk in copy]
            with cur.copy(f"COPY snapshot_{name} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)") as copy:
                for chunk in chunks:
                    copy.write(chunk)


def run_case(conn, case: dict, backend: str) -> dict:
    sql, params = PostgresErpSearchTools._build_search_sql(
        criteria=SearchCriteria(**case["criteria"]), limit=case.get("limit", 10),
        family_ids=case.get("family_ids"),
    )
    for name in ("candidates", "applications"):
        sql = sql.replace(f"soccol.item_search_{name}", f"pg_temp.{backend}_{name}")
    rows = conn.execute(sql, params).fetchall()
    ids = [row["item_code"] for row in rows]
    attributes = {row["item_code"]: PostgresErpSearchTools._build_disambiguation_attributes(row) for row in rows}
    attributes_ok = all(
        attributes.get(code, {}).get(key) == expected
        for code, fields in case.get("expected_attributes", {}).items()
        for key, expected in fields.items()
    )
    return {"id": case["id"], "backend": backend, "passed": ids == case["expected_ids"] and attributes_ok,
            "expected_ids": case["expected_ids"], "actual_ids": ids, "attributes": attributes}


def evaluate(integration_sql: Path | None = None) -> list[dict]:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    results = []
    with psycopg.connect(build_catalog_conninfo(Settings()), row_factory=dict_row, autocommit=True) as conn:
        for fixture_name, fixture in golden["fixtures"].items():
            with conn.transaction(force_rollback=True):
                install_fixture(conn, fixture, integration_sql)
                for case in golden["cases"]:
                    if case["fixture"] == fixture_name:
                        backends = ("contract", "snapshot", "integration") if integration_sql else ("contract", "snapshot")
                        for backend in backends:
                            results.append(run_case(conn, case, backend))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".tmp/eval/erp_search_golden_report.json"))
    parser.add_argument("--integration-sql", type=Path, help="Optional local ERP DDL with marked CANDIDATES/APPLICATIONS SELECTs")
    args = parser.parse_args()
    results = evaluate(args.integration_sql)
    report = {"passed": sum(row["passed"] for row in results), "total": len(results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ERP golden: {report['passed']}/{report['total']} passed; {args.output}")
    for row in results:
        if not row["passed"]:
            print(json.dumps(row, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
