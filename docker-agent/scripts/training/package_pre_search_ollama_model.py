import argparse
import json
import shutil
import subprocess
from pathlib import Path

from app.config import Settings


def _build_modelfile(
    *,
    artifact_kind: str,
    artifact_path: str,
    base_model: str,
) -> str:
    if artifact_kind == "adapter":
        return f"FROM {base_model}\nADAPTER {artifact_path}\n"
    if artifact_kind == "model":
        return f"FROM {artifact_path}\n"
    raise ValueError(f"artifact_kind invalido: {artifact_kind}")


def _resolve_command(*, template: str, model_name: str, modelfile_path: Path) -> str:
    return template.format(
        model_name=model_name,
        modelfile=str(modelfile_path),
    )


def _replace_staged_path(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


def _stage_artifact_for_docker(
    *,
    artifact_kind: str,
    artifact_path: str,
    output_path: Path,
    container_modelfile_root: str,
    model_name: str,
) -> tuple[str, Path]:
    source_path = Path(artifact_path).expanduser().resolve()
    if not source_path.exists():
        raise RuntimeError(f"Artefato nao encontrado para empacotar no Ollama: {source_path}")

    staged_name = artifact_kind if source_path.is_dir() else source_path.name
    staged_path = output_path / staged_name
    _replace_staged_path(staged_path)

    if source_path.is_dir():
        shutil.copytree(source_path, staged_path)
    else:
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, staged_path)

    container_artifact_path = (Path(container_modelfile_root) / model_name / staged_name).as_posix()
    return container_artifact_path, staged_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Monta um Modelfile e opcionalmente cria um modelo no Ollama.")
    parser.add_argument("--model-name", required=True, help="Nome do modelo final no Ollama.")
    parser.add_argument("--artifact-kind", choices=["adapter", "model"], default=None, help="Tipo do artefato treinado.")
    parser.add_argument("--artifact-path", default=None, help="Caminho para adapter ou pesos finais.")
    parser.add_argument("--base-model", default=None, help="Modelo base no Ollama para casos com adapter.")
    parser.add_argument("--output-dir", default=None, help="Diretorio para escrever o Modelfile.")
    parser.add_argument("--create", action="store_true", help="Executa o comando de criacao no Ollama.")
    parser.add_argument("--create-via-docker", action="store_true", help="Executa a criacao via docker exec no container do Ollama.")
    parser.add_argument(
        "--create-command",
        default="ollama create {model_name} -f {modelfile}",
        help="Template do comando de criacao. Placeholders: {model_name}, {modelfile}.",
    )
    parser.add_argument("--docker-container-name", default="ollama", help="Nome do container do Ollama.")
    parser.add_argument(
        "--container-modelfile-root",
        default="/ollama_models",
        help="Diretorio montado dentro do container do Ollama para os Modelfiles.",
    )
    args = parser.parse_args()

    settings = Settings()
    artifact_kind = args.artifact_kind or settings.ft_ollama_artifact_kind
    artifact_path = args.artifact_path or settings.ft_ollama_artifact_path
    base_model = args.base_model or settings.ft_ollama_base_model or settings.llm_model
    output_dir = Path(args.output_dir or settings.ft_ollama_output_dir)

    if not artifact_path:
        raise RuntimeError("Informe --artifact-path ou configure FT_OLLAMA_ARTIFACT_PATH.")

    output_path = output_dir / args.model_name
    output_path.mkdir(parents=True, exist_ok=True)
    modelfile_path = output_path / "Modelfile"
    modelfile_artifact_path = artifact_path
    staged_artifact_path: str | None = None
    if args.create_via_docker:
        modelfile_artifact_path, staged_path = _stage_artifact_for_docker(
            artifact_kind=artifact_kind,
            artifact_path=artifact_path,
            output_path=output_path,
            container_modelfile_root=args.container_modelfile_root,
            model_name=args.model_name,
        )
        staged_artifact_path = str(staged_path)
    modelfile_content = _build_modelfile(
        artifact_kind=artifact_kind,
        artifact_path=modelfile_artifact_path,
        base_model=base_model,
    )
    modelfile_path.write_text(modelfile_content, encoding="utf-8")

    create_command = _resolve_command(
        template=args.create_command,
        model_name=args.model_name,
        modelfile_path=modelfile_path,
    )
    container_modelfile_path = (
        Path(args.container_modelfile_root) / args.model_name / "Modelfile"
    ).as_posix()
    docker_create_command = (
        f"docker exec {args.docker_container_name} "
        f"ollama create {args.model_name} -f {container_modelfile_path}"
    )

    if args.create:
        create_target = docker_create_command if args.create_via_docker else create_command
        result = subprocess.run(
            create_target,
            shell=True,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Falha ao criar modelo no Ollama.\n"
                f"Comando: {create_target}\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )

    print(
        json.dumps(
            {
                "model_name": args.model_name,
                "artifact_kind": artifact_kind,
                "artifact_path": artifact_path,
                "modelfile_artifact_path": modelfile_artifact_path,
                "staged_artifact_path": staged_artifact_path,
                "base_model": base_model,
                "modelfile_path": str(modelfile_path),
                "container_modelfile_path": container_modelfile_path,
                "modelfile_preview": modelfile_content,
                "create_command": create_command,
                "docker_create_command": docker_create_command,
                "create_executed": args.create,
                "create_via_docker": args.create_via_docker,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
