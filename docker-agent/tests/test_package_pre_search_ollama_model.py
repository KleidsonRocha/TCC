from scripts.training.package_pre_search_ollama_model import _build_modelfile, _stage_artifact_for_docker


def test_build_modelfile_for_adapter() -> None:
    result = _build_modelfile(
        artifact_kind="adapter",
        artifact_path="C:\\model\\adapter",
        base_model="qwen2.5:7b",
    )
    assert result == "FROM qwen2.5:7b\nADAPTER C:\\model\\adapter\n"


def test_build_modelfile_for_model() -> None:
    result = _build_modelfile(
        artifact_kind="model",
        artifact_path="C:\\model\\weights",
        base_model="ignored",
    )
    assert result == "FROM C:\\model\\weights\n"


def test_stage_artifact_for_docker_directory(tmp_path) -> None:
    source_dir = tmp_path / "adapter_source"
    source_dir.mkdir()
    (source_dir / "adapter_model.safetensors").write_text("adapter", encoding="utf-8")

    output_path = tmp_path / "ollama_models" / "pre-search-test"
    output_path.mkdir(parents=True)

    container_artifact_path, staged_path = _stage_artifact_for_docker(
        artifact_kind="adapter",
        artifact_path=str(source_dir),
        output_path=output_path,
        container_modelfile_root="/ollama_models",
        model_name="pre-search-test",
    )

    assert container_artifact_path == "/ollama_models/pre-search-test/adapter"
    assert staged_path == output_path / "adapter"
    assert (staged_path / "adapter_model.safetensors").read_text(encoding="utf-8") == "adapter"
