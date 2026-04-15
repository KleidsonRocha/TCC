import pytest

from scripts.training import run_pre_search_fine_tuning_cycle

from scripts.training.run_pre_search_fine_tuning_cycle import _project_path_to_container
from scripts.training.run_pre_search_fine_tuning_cycle import (
    _default_publish_command,
    _default_train_command,
    _render_command,
)


def test_project_path_to_container_with_relative_path(tmp_path) -> None:
    project_root = (tmp_path / "docker-agent").resolve()
    project_root.mkdir()
    (project_root / ".tmp" / "fine_tuning").mkdir(parents=True)
    (project_root / ".tmp" / "fine_tuning" / "train.messages.jsonl").write_text("", encoding="utf-8")

    result = _project_path_to_container(
        project_root=project_root,
        path_value=".tmp/fine_tuning/train.messages.jsonl",
    )

    assert result == "/workspace/.tmp/fine_tuning/train.messages.jsonl"


def test_project_path_to_container_with_empty_path(tmp_path) -> None:
    project_root = (tmp_path / "docker-agent").resolve()
    project_root.mkdir()

    result = _project_path_to_container(
        project_root=project_root,
        path_value="",
    )

    assert result == ""


def test_project_path_to_container_rejects_path_outside_workspace(tmp_path) -> None:
    project_root = (tmp_path / "docker-agent").resolve()
    project_root.mkdir()
    outside_path = tmp_path / "outside" / "train.messages.jsonl"
    outside_path.parent.mkdir(parents=True)
    outside_path.write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="fora do workspace"):
        _project_path_to_container(
            project_root=project_root,
            path_value=str(outside_path),
        )


def test_default_commands_and_rendering_include_expected_placeholders() -> None:
    train_command = _default_train_command()
    publish_command = _default_publish_command(ollama_base_model="qwen2.5:7b")
    rendered = _render_command(
        '--train-file "{train_messages_file_in_container}" --output-dir "{trainer_output_dir_in_container}"',
        {
            "train_messages_file_in_container": "/workspace/.tmp/fine_tuning/train.messages.jsonl",
            "trainer_output_dir_in_container": "/workspace/.tmp/trainer_runs/model",
        },
    )

    assert train_command == (
        "docker compose --profile trainer build trainer"
        " && "
        "docker compose --profile trainer run --rm trainer "
        "python trainer/train_pre_search_adapter.py "
        '--train-file "{train_messages_file_in_container}" '
        '--validation-file "{validation_messages_file_in_container}" '
        '--output-dir "{trainer_output_dir_in_container}"'
    )
    assert publish_command == (
        "python scripts/training/package_pre_search_ollama_model.py "
        '--model-name "{target_model}" '
        "--artifact-kind adapter "
        '--artifact-path "{adapter_dir}" '
        '--base-model "qwen2.5:7b" '
        "--create "
        "--create-via-docker"
    )
    assert rendered == (
        '--train-file "/workspace/.tmp/fine_tuning/train.messages.jsonl" '
        '--output-dir "/workspace/.tmp/trainer_runs/model"'
    )


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, sql, params=None) -> None:
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0

    def cursor(self):
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_update_run_record_persists_status_json_and_finish_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)

    class _FakePsycopg:
        @staticmethod
        def connect(*args, **kwargs):
            return connection

    monkeypatch.setattr(run_pre_search_fine_tuning_cycle, "psycopg", _FakePsycopg)

    run_pre_search_fine_tuning_cycle._update_run_record(
        settings=run_pre_search_fine_tuning_cycle.Settings(
            APP_ENV="test",
            LOG_LEVEL="INFO",
            AGENT_PORT=8001,
            DEFAULT_LOCALE="pt-BR",
            DEFAULT_TIMEZONE="America/Sao_Paulo",
            CATALOG_DB_HOST="presearch-db",
            CATALOG_DB_PORT=5432,
            CATALOG_DB_NAME="presearch",
            CATALOG_DB_USER="presearch",
            CATALOG_DB_PASSWORD="presearch",
        ),
        run_id=44,
        status="completed",
        notes="benchmark concluido",
        data_export_dir=".tmp/fine_tuning_runs/run-1",
        train_file_path=".tmp/fine_tuning/train.messages.jsonl",
        validation_file_path=".tmp/fine_tuning/validation.messages.jsonl",
        benchmark_summary={"candidate_better": True, "case_pass_pct": 91.2},
        promotion_status="promoted",
        promoted_env_file=".env",
        set_finished=True,
    )

    assert connection.commit_count == 1
    assert len(cursor.executed) == 1

    sql, params = cursor.executed[0]
    assert "UPDATE pre_search_fine_tuning_run" in sql
    assert params[0] == "completed"
    assert params[1] == "benchmark concluido"
    assert params[2] == ".tmp/fine_tuning_runs/run-1"
    assert params[3] == ".tmp/fine_tuning/train.messages.jsonl"
    assert params[4] == ".tmp/fine_tuning/validation.messages.jsonl"
    assert getattr(params[5], "obj", None) == {"candidate_better": True, "case_pass_pct": 91.2}
    assert params[6] == "promoted"
    assert params[7] == ".env"
    assert params[8] is True
    assert params[9] is True
    assert params[10] == 44
