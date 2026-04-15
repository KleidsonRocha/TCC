import sys

import pytest

from scripts.testing.run_mutation_tests import (
    CURATED_PROFILES,
    _build_mutmut_command,
    _build_results_command,
    _ensure_supported_runtime,
    _render_mutmut_config,
    main,
)


def test_build_mutmut_command() -> None:
    command = _build_mutmut_command()

    assert command == [sys.executable, "-m", "mutmut", "run"]


def test_build_results_command_supports_plain_results_and_browse() -> None:
    assert _build_results_command(browse=False) == [sys.executable, "-m", "mutmut", "results"]
    assert _build_results_command(browse=True) == [sys.executable, "-m", "mutmut", "browse"]


def test_curated_profiles_keep_expected_keys() -> None:
    assert set(CURATED_PROFILES) == {
        "review_queue",
        "export_dataset",
        "training_cycle",
        "format_payloads",
    }


def test_render_mutmut_config_uses_profile_specific_paths_and_tests() -> None:
    config = _render_mutmut_config(CURATED_PROFILES["review_queue"])

    assert "scripts/training/review_pre_search_queue.py" in config
    assert "tests/test_review_pre_search_queue.py" in config
    assert "scripts/training/run_pre_search_fine_tuning_cycle.py" not in config


def test_ensure_supported_runtime_rejects_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "win32")

    with pytest.raises(RuntimeError, match="nao roda diretamente no Windows"):
        _ensure_supported_runtime()


def test_main_lists_profiles_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["run_mutation_tests.py", "--list"])

    main()

    output = capsys.readouterr().out
    assert "review_queue" in output
    assert "training_cycle" in output


def test_main_dispatches_single_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], bool, bool, bool]] = []

    def _fake_run_profiles(*, project_root, profiles, show_results, browse, clean_between_profiles):
        _ = project_root
        calls.append(([profile.name for profile in profiles], show_results, browse, clean_between_profiles))

    monkeypatch.setattr("sys.argv", ["run_mutation_tests.py", "review_queue", "--results"])
    monkeypatch.setattr("scripts.testing.run_mutation_tests._ensure_supported_runtime", lambda: None)
    monkeypatch.setattr("scripts.testing.run_mutation_tests._run_profiles", _fake_run_profiles)

    main()

    assert calls == [(["review_queue"], True, False, False)]
