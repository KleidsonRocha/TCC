"""Export the v2 contract from the ERP using one read-only consistent snapshot.

Run from the repository root: python -m scripts.erp.export_search_snapshot
No integration DDL is executed on the source database.
"""

import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from app.config import Settings
from app.infra.postgres_conninfo import build_erp_conninfo


DEFAULT_OUTPUT = Path("db/init/fallback/v2")
COLUMNS = {
    "candidates": (
        "id_item", "cd_item", "nm_item", "candidate_title", "cd_grupo", "cd_subgrupo",
        "part_family", "cd_original", "cd_fabricante", "search_text",
    ),
    "applications": (
        "application_id", "id_item", "vehicle_brand", "vehicle_model", "year_start",
        "year_end", "year_open_end", "engines", "variants", "injections",
        "transmissions", "application_text",
    ),
}


def source_select(name: str) -> str:
    # Explicit order is the CSV import contract, independent of view column order.
    return f"SELECT {', '.join(COLUMNS[name])} FROM soccol.item_search_{name}"


def export_snapshot(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"contract_version": 2, "encoding": "UTF8", "exported_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    # COPY yields bytes in client_encoding; the ERP currently uses WIN1252.
    with psycopg.connect(build_erp_conninfo(Settings()), client_encoding="UTF8") as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '10min'")
        for name in ("candidates", "applications"):
            filename = f"{name}.csv.gz"
            target = output_dir / filename
            temporary = output_dir / (filename + ".tmp")
            with conn.cursor() as cur, gzip.open(temporary, "wb") as output:
                with cur.copy(f"COPY ({source_select(name)}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)") as copy:
                    for chunk in copy:
                        output.write(chunk)
                count = cur.rowcount
            temporary.replace(target)
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest["files"][filename] = {"rows": count, "sha256": checksum}
            print(f"{name}: {count} rows", flush=True)
    # Publish the checksum pair last. A partial replacement cannot pass bootstrap validation.
    checksums = "".join(f"{value['sha256']}  {name}\n" for name, value in manifest["files"].items())
    temporary_manifest = output_dir / "manifest.sha256.tmp"
    temporary_manifest.write_text(checksums, encoding="utf-8")
    temporary_manifest.replace(output_dir / "manifest.sha256")
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(export_snapshot(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
