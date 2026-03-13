from pathlib import Path

from scripts.training.run_pre_search_fine_tuning_cycle import _project_path_to_container


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
