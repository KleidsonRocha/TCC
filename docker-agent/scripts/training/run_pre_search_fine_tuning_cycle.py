import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.infra.pre_search_benchmark import benchmark_model, load_dataset
from app.infra.pre_search_model_cycle import (
    candidate_is_better,
    generate_target_model_name,
    update_env_llm_model,
)
from app.infra.postgres_conninfo import build_catalog_conninfo


def _run_command(*, command: str, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        shell=True,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Comando falhou ({result.returncode}): {command}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def _render_command(template: str, values: dict[str, str]) -> str:
    return template.format(**values)


def _project_path_to_container(*, project_root: Path, path_value: str) -> str:
    if not path_value:
        return ""
    resolved_path = Path(path_value)
    if not resolved_path.is_absolute():
        resolved_path = (project_root / resolved_path).resolve()
    else:
        resolved_path = resolved_path.resolve()
    try:
        relative_path = resolved_path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise RuntimeError(
            f"Caminho fora do workspace do projeto nao pode ser montado na trainer: {resolved_path}"
        ) from exc
    return f"/workspace/{relative_path.as_posix()}"


def _default_train_command() -> str:
    return (
        "docker compose --profile trainer build trainer"
        " && "
        "docker compose --profile trainer run --rm trainer "
        "python trainer/train_pre_search_adapter.py "
        '--train-file "{train_messages_file_in_container}" '
        '--validation-file "{validation_messages_file_in_container}" '
        '--output-dir "{trainer_output_dir_in_container}"'
    )


def _default_publish_command(*, ollama_base_model: str) -> str:
    return (
        "python scripts/training/package_pre_search_ollama_model.py "
        '--model-name "{target_model}" '
        "--artifact-kind adapter "
        '--artifact-path "{adapter_dir}" '
        f'--base-model "{ollama_base_model}" '
        "--create "
        "--create-via-docker"
    )


def _create_run_record(
    *,
    settings: Settings,
    dataset_slug: str,
    provider: str,
    base_model: str,
    target_model_name: str,
) -> int:
    with psycopg.connect(build_catalog_conninfo(settings), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM pre_search_fine_tuning_dataset_header WHERE slug = %s",
                (dataset_slug,),
            )
            dataset_row = cur.fetchone()
            if not dataset_row:
                raise RuntimeError(f"Dataset de fine-tuning nao encontrado: {dataset_slug}")

            cur.execute(
                """
                INSERT INTO pre_search_fine_tuning_run (
                    dataset_id,
                    provider,
                    base_model,
                    target_model_name,
                    status,
                    started_at,
                    updated_by
                )
                VALUES (%s, %s, %s, %s, 'draft', NOW(), 'automation')
                RETURNING id
                """,
                (
                    int(dataset_row["id"]),
                    provider,
                    base_model,
                    target_model_name,
                ),
            )
            run_id = int(cur.fetchone()["id"])
        conn.commit()
    return run_id


def _update_run_record(
    *,
    settings: Settings,
    run_id: int,
    status: str,
    notes: str | None = None,
    data_export_dir: str | None = None,
    train_file_path: str | None = None,
    validation_file_path: str | None = None,
    benchmark_summary: dict[str, Any] | None = None,
    promotion_status: str | None = None,
    promoted_env_file: str | None = None,
    set_finished: bool = False,
) -> None:
    with psycopg.connect(build_catalog_conninfo(settings)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pre_search_fine_tuning_run
                SET
                    status = %s,
                    notes = COALESCE(%s, notes),
                    data_export_dir = COALESCE(%s, data_export_dir),
                    train_file_path = COALESCE(%s, train_file_path),
                    validation_file_path = COALESCE(%s, validation_file_path),
                    benchmark_summary = COALESCE(%s, benchmark_summary),
                    promotion_status = COALESCE(%s, promotion_status),
                    promoted_env_file = COALESCE(%s, promoted_env_file),
                    promotion_applied_at = CASE WHEN %s THEN NOW() ELSE promotion_applied_at END,
                    finished_at = CASE WHEN %s THEN NOW() ELSE finished_at END,
                    updated_at = NOW(),
                    updated_by = 'automation'
                WHERE id = %s
                """,
                (
                    status,
                    notes,
                    data_export_dir,
                    train_file_path,
                    validation_file_path,
                    Jsonb(benchmark_summary) if benchmark_summary is not None else None,
                    promotion_status,
                    promoted_env_file,
                    bool(promoted_env_file),
                    set_finished,
                    run_id,
                ),
            )
        conn.commit()


def _export_dataset(*, project_root: Path, dataset_slug: str, output_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/training/export_pre_search_fine_tuning_dataset.py",
        "--dataset-slug",
        dataset_slug,
        "--output-dir",
        str(output_dir),
    ]
    result = subprocess.run(
        command,
        cwd=str(project_root),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Falha ao exportar dataset.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestra o ciclo de fine-tuning e promocao de modelo do pre-search.")
    parser.add_argument("--dataset-slug", default=None, help="Dataset de fine-tuning a exportar.")
    parser.add_argument("--candidate-model", default=None, help="Nome de modelo ja existente para comparar/promover.")
    parser.add_argument("--target-model-name", default=None, help="Nome do modelo candidato a gerar.")
    parser.add_argument("--train-command", default=None, help="Comando externo de treino.")
    parser.add_argument("--publish-command", default=None, help="Comando externo para publicar o modelo candidato.")
    parser.add_argument("--provider", default="external", help="Nome do provider de treino.")
    parser.add_argument("--run-dir", default=".tmp/fine_tuning_runs", help="Diretorio base das runs.")
    parser.add_argument("--golden-set", default=None, help="Dataset de benchmark.")
    parser.add_argument("--promote-if-better", action="store_true", help="Atualiza o LLM_MODEL no .env se o candidato vencer.")
    parser.add_argument("--restart-agent", action="store_true", help="Reinicia o docker-agent apos promocao.")
    parser.add_argument("--restart-command", default="docker compose up -d docker-agent", help="Comando para reiniciar o agente apos promocao.")
    args = parser.parse_args()

    settings = Settings()
    project_root = Path(__file__).resolve().parents[1]
    dataset_slug = args.dataset_slug or settings.ft_dataset_slug
    base_model = settings.llm_model
    target_model_name = (
        args.candidate_model
        or args.target_model_name
        or generate_target_model_name(prefix=settings.ft_target_model_prefix)
    )
    train_command_template = args.train_command or settings.ft_train_command
    publish_command_template = args.publish_command or settings.ft_publish_command
    using_default_docker_trainer = False
    if not args.candidate_model and not train_command_template:
        train_command_template = _default_train_command()
        publish_command_template = publish_command_template or _default_publish_command(
            ollama_base_model=settings.ft_ollama_base_model,
        )
        using_default_docker_trainer = True
    golden_set_path = Path(args.golden_set or settings.ft_golden_set_file)

    if not args.candidate_model and train_command_template and not publish_command_template:
        raise RuntimeError(
            "Ha treino configurado, mas nenhum publish-command. "
            "Informe --publish-command/FT_PUBLISH_COMMAND ou use o fluxo default."
        )

    run_id = _create_run_record(
        settings=settings,
        dataset_slug=dataset_slug,
        provider="docker_trainer" if using_default_docker_trainer else args.provider,
        base_model=base_model,
        target_model_name=target_model_name,
    )

    try:
        export_output = _export_dataset(
            project_root=project_root,
            dataset_slug=dataset_slug,
            output_dir=project_root / args.run_dir,
        )
        run_output_dir = project_root / export_output["output_dir"]
        _update_run_record(
            settings=settings,
            run_id=run_id,
            status="exported",
            data_export_dir=str(run_output_dir),
            train_file_path=export_output["splits"]["train"]["messages_file"],
            validation_file_path=export_output["splits"]["validation"]["messages_file"],
        )

        command_values = {
            "dataset_slug": dataset_slug,
            "base_model": base_model,
            "target_model": target_model_name,
            "run_dir": str(run_output_dir),
            "trainer_output_dir": str(run_output_dir / "trainer" / target_model_name),
            "adapter_dir": str(run_output_dir / "trainer" / target_model_name / "adapter"),
            "trainer_summary_file": str(run_output_dir / "trainer" / target_model_name / "training_summary.json"),
            "train_messages_file": export_output["splits"]["train"]["messages_file"] or "",
            "validation_messages_file": export_output["splits"]["validation"]["messages_file"] or "",
            "train_records_file": export_output["splits"]["train"]["records_file"] or "",
            "validation_records_file": export_output["splits"]["validation"]["records_file"] or "",
            "system_prompt_file": export_output["system_prompt_file"],
            "manifest_file": export_output["manifest_file"],
        }
        command_values["train_messages_file_in_container"] = _project_path_to_container(
            project_root=project_root,
            path_value=command_values["train_messages_file"],
        )
        command_values["validation_messages_file_in_container"] = _project_path_to_container(
            project_root=project_root,
            path_value=command_values["validation_messages_file"],
        )
        command_values["trainer_output_dir_in_container"] = _project_path_to_container(
            project_root=project_root,
            path_value=command_values["trainer_output_dir"],
        )

        shell_env = dict(os.environ)
        shell_env.update(command_values)

        if train_command_template:
            _run_command(
                command=_render_command(train_command_template, command_values),
                cwd=project_root,
                env=shell_env,
            )
            _update_run_record(settings=settings, run_id=run_id, status="submitted")

        if publish_command_template:
            _run_command(
                command=_render_command(publish_command_template, command_values),
                cwd=project_root,
                env=shell_env,
            )

        dataset = load_dataset(project_root / golden_set_path)
        baseline_metrics = benchmark_model(dataset=dataset, settings=settings, model_name=base_model)
        candidate_metrics = benchmark_model(dataset=dataset, settings=settings, model_name=target_model_name)
        promoted_env_file = None
        promotion_status = "rejected"
        candidate_better = (
            target_model_name != base_model
            and candidate_is_better(baseline=baseline_metrics, candidate=candidate_metrics)
        )

        if candidate_better:
            if args.promote_if_better:
                env_path = project_root / settings.ft_active_env_file
                update_env_llm_model(env_path=env_path, new_model_name=target_model_name)
                promoted_env_file = str(env_path)
                promotion_status = "promoted"
                if args.restart_agent:
                    _run_command(
                        command=args.restart_command,
                        cwd=project_root,
                        env=dict(os.environ),
                    )
            else:
                promotion_status = "pending"

        benchmark_summary = {
            "dataset": str(project_root / golden_set_path),
            "baseline": baseline_metrics,
            "candidate": candidate_metrics,
            "candidate_better": candidate_better,
        }
        _update_run_record(
            settings=settings,
            run_id=run_id,
            status="completed",
            benchmark_summary=benchmark_summary,
            promotion_status=promotion_status,
            promoted_env_file=promoted_env_file,
            set_finished=True,
        )

        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "base_model": base_model,
                    "target_model_name": target_model_name,
                    "train_command": train_command_template,
                    "publish_command": publish_command_template,
                    "benchmark": benchmark_summary,
                    "promotion_status": promotion_status,
                    "promoted_env_file": promoted_env_file,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception as exc:
        _update_run_record(
            settings=settings,
            run_id=run_id,
            status="failed",
            notes=str(exc),
            set_finished=True,
        )
        raise


if __name__ == "__main__":
    main()
