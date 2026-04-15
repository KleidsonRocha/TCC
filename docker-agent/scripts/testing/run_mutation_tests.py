import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MutationProfile:
    name: str
    paths_to_mutate: tuple[str, ...]
    test_selection: tuple[str, ...]
    also_copy: tuple[str, ...]
    description: str


CURATED_PROFILES: dict[str, MutationProfile] = {
    "review_queue": MutationProfile(
        name="review_queue",
        paths_to_mutate=("scripts/training/review_pre_search_queue.py",),
        test_selection=("tests/test_review_pre_search_queue.py",),
        also_copy=("app/", "scripts/__init__.py", "scripts/training/__init__.py"),
        description="Fila de revisao, revisao humana e promocao para dataset de fine-tuning.",
    ),
    "export_dataset": MutationProfile(
        name="export_dataset",
        paths_to_mutate=("scripts/training/export_pre_search_fine_tuning_dataset.py",),
        test_selection=("tests/test_export_pre_search_fine_tuning_dataset.py",),
        also_copy=("app/", "scripts/__init__.py", "scripts/training/__init__.py"),
        description="Exportacao do dataset curado para JSONL e manifest.",
    ),
    "training_cycle": MutationProfile(
        name="training_cycle",
        paths_to_mutate=("scripts/training/run_pre_search_fine_tuning_cycle.py",),
        test_selection=("tests/test_run_pre_search_fine_tuning_cycle.py",),
        also_copy=("app/", "scripts/__init__.py", "scripts/training/__init__.py"),
        description="Renderizacao de comandos e mapeamento de paths do ciclo de treino.",
    ),
    "format_payloads": MutationProfile(
        name="format_payloads",
        paths_to_mutate=("app/infra/pre_search_fine_tuning_format.py",),
        test_selection=(
            "tests/test_pre_search_fine_tuning_format.py",
            "tests/test_export_pre_search_fine_tuning_dataset.py",
        ),
        also_copy=("app/", "scripts/", "docs/assets/datasets/"),
        description="Serializacao dos payloads de treino e contrato de mensagens.",
    ),
}


def _build_mutmut_command() -> list[str]:
    return [sys.executable, "-m", "mutmut", "run"]


def _build_results_command(*, browse: bool) -> list[str]:
    return [sys.executable, "-m", "mutmut", "browse" if browse else "results"]


def _ensure_supported_runtime() -> None:
    if sys.platform.startswith("win"):
        raise RuntimeError(
            "mutmut exige fork e nao roda diretamente no Windows. "
            "Use WSL ou execute este script dentro do container docker-agent."
        )


def _remove_mutants_dir(project_root: Path) -> None:
    mutants_dir = project_root / "mutants"
    if mutants_dir.exists():
        shutil.rmtree(mutants_dir)


def _print_profiles() -> None:
    for profile in CURATED_PROFILES.values():
        print(f"{profile.name}: {profile.description}")


def _render_mutmut_config(profile: MutationProfile) -> str:
    lines = [
        "[mutmut]",
        "paths_to_mutate =",
        *[f"    {item}" for item in profile.paths_to_mutate],
        "also_copy =",
        *[f"    {item}" for item in profile.also_copy],
        "pytest_add_cli_args_test_selection =",
        *[f"    {item}" for item in profile.test_selection],
        "mutate_only_covered_lines = true",
        "max_stack_depth = 8",
        "do_not_mutate =",
        "    */__init__.py",
        "",
    ]
    return "\n".join(lines)


def _render_sitecustomize_patch() -> str:
    return """import multiprocessing as _mp

_original_set_start_method = _mp.set_start_method


def _safe_set_start_method(method=None, force=False):
    try:
        return _original_set_start_method(method, force=force)
    except RuntimeError as exc:
        if "context has already been set" not in str(exc):
            raise
        current = _mp.get_start_method(allow_none=True)
        if current == method:
            return None
        raise


_mp.set_start_method = _safe_set_start_method
"""


@contextmanager
def _temporary_mutmut_config(project_root: Path, profile: MutationProfile):
    config_path = project_root / "setup.cfg"
    original_text = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    config_path.write_text(_render_mutmut_config(profile), encoding="utf-8")
    try:
        yield
    finally:
        if original_text is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(original_text, encoding="utf-8")


@contextmanager
def _mutation_python_env():
    with tempfile.TemporaryDirectory(prefix="mutmut-sitecustomize-") as temp_dir:
        shim_dir = Path(temp_dir)
        (shim_dir / "sitecustomize.py").write_text(_render_sitecustomize_patch(), encoding="utf-8")
        env = dict(os.environ)
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{shim_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(shim_dir)
        )
        yield env


def _run_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def _run_profiles(
    *,
    project_root: Path,
    profiles: list[MutationProfile],
    show_results: bool,
    browse: bool,
    clean_between_profiles: bool,
) -> None:
    for profile in profiles:
        if clean_between_profiles:
            _remove_mutants_dir(project_root)
        print(f"[mutmut] executando perfil: {profile.name}")
        with _temporary_mutmut_config(project_root, profile):
            with _mutation_python_env() as env:
                _run_command(_build_mutmut_command(), env=env)
                if show_results or browse:
                    _run_command(_build_results_command(browse=browse), env=env)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Roda mutation testing curado para os modulos mais criticos do projeto."
    )
    parser.add_argument(
        "profile",
        nargs="?",
        default="all_curated",
        choices=["all_curated", *CURATED_PROFILES.keys()],
        help="Perfil de mutation testing a executar.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lista os perfis disponiveis e encerra.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Apaga o diretorio mutants/ antes de iniciar uma nova rodada.",
    )
    parser.add_argument(
        "--results",
        action="store_true",
        help="Exibe o resumo de resultados apos a execucao.",
    )
    parser.add_argument(
        "--browse",
        action="store_true",
        help="Abre o navegador TUI do mutmut apos a execucao.",
    )
    args = parser.parse_args()

    if args.list:
        _print_profiles()
        return

    _ensure_supported_runtime()
    project_root = Path(__file__).resolve().parents[2]
    if args.clean:
        _remove_mutants_dir(project_root)

    if args.profile == "all_curated":
        profiles = list(CURATED_PROFILES.values())
    else:
        profiles = [CURATED_PROFILES[args.profile]]

    _run_profiles(
        project_root=project_root,
        profiles=profiles,
        show_results=args.results,
        browse=args.browse,
        clean_between_profiles=args.profile == "all_curated",
    )


if __name__ == "__main__":
    main()
