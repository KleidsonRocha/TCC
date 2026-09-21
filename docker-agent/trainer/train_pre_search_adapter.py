import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_TARGET_MODULES = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)


def _bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treina um adapter LoRA/QLoRA para o pre-search.")
    parser.add_argument("--train-file", required=True, help="Arquivo train.messages.jsonl.")
    parser.add_argument("--validation-file", default=None, help="Arquivo validation.messages.jsonl.")
    parser.add_argument(
        "--base-model",
        default=os.getenv("TRAINER_HF_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        help="Model ID do Hugging Face usado como base de treino.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Diretorio da run de treino. O adapter sera salvo em output-dir/adapter.",
    )
    parser.add_argument("--num-train-epochs", type=float, default=float(os.getenv("TRAINER_NUM_EPOCHS", "2")))
    parser.add_argument(
        "--per-device-train-batch-size",
        type=int,
        default=int(os.getenv("TRAINER_BATCH_SIZE", "1")),
    )
    parser.add_argument(
        "--per-device-eval-batch-size",
        type=int,
        default=int(os.getenv("TRAINER_EVAL_BATCH_SIZE", "1")),
    )
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=int(os.getenv("TRAINER_GRAD_ACCUM_STEPS", "8")),
    )
    parser.add_argument("--learning-rate", type=float, default=float(os.getenv("TRAINER_LEARNING_RATE", "0.0001")))
    parser.add_argument("--warmup-ratio", type=float, default=float(os.getenv("TRAINER_WARMUP_RATIO", "0.03")))
    parser.add_argument("--max-seq-length", type=int, default=int(os.getenv("TRAINER_MAX_SEQ_LENGTH", "2048")))
    parser.add_argument("--logging-steps", type=int, default=int(os.getenv("TRAINER_LOGGING_STEPS", "5")))
    parser.add_argument("--save-steps", type=int, default=int(os.getenv("TRAINER_SAVE_STEPS", "10")))
    parser.add_argument("--eval-steps", type=int, default=int(os.getenv("TRAINER_EVAL_STEPS", "10")))
    parser.add_argument("--save-total-limit", type=int, default=int(os.getenv("TRAINER_SAVE_TOTAL_LIMIT", "2")))
    parser.add_argument("--seed", type=int, default=int(os.getenv("TRAINER_SEED", "42")))
    parser.add_argument("--lora-r", type=int, default=int(os.getenv("TRAINER_LORA_R", "16")))
    parser.add_argument("--lora-alpha", type=int, default=int(os.getenv("TRAINER_LORA_ALPHA", "32")))
    parser.add_argument("--lora-dropout", type=float, default=float(os.getenv("TRAINER_LORA_DROPOUT", "0.05")))
    parser.add_argument(
        "--target-modules",
        default=os.getenv("TRAINER_TARGET_MODULES", ",".join(DEFAULT_TARGET_MODULES)),
        help="Lista CSV de modulos LoRA.",
    )
    parser.add_argument(
        "--load-in-4bit",
        dest="load_in_4bit",
        action="store_true",
        default=_bool_env("TRAINER_LOAD_IN_4BIT", True),
        help="Ativa QLoRA 4-bit quando houver CUDA disponivel.",
    )
    parser.add_argument(
        "--no-load-in-4bit",
        dest="load_in_4bit",
        action="store_false",
        help="Desativa quantizacao 4-bit.",
    )
    parser.add_argument(
        "--gradient-checkpointing",
        dest="gradient_checkpointing",
        action="store_true",
        default=_bool_env("TRAINER_GRADIENT_CHECKPOINTING", True),
        help="Ativa gradient checkpointing.",
    )
    parser.add_argument(
        "--no-gradient-checkpointing",
        dest="gradient_checkpointing",
        action="store_false",
        help="Desativa gradient checkpointing.",
    )
    parser.add_argument(
        "--trust-remote-code",
        dest="trust_remote_code",
        action="store_true",
        default=_bool_env("TRAINER_TRUST_REMOTE_CODE", False),
        help="Permite trust_remote_code ao carregar o modelo.",
    )
    parser.add_argument(
        "--report-to",
        default=os.getenv("TRAINER_REPORT_TO", "none"),
        help="Integracao de logs do transformers/trl. Ex.: none, tensorboard, wandb.",
    )
    parser.add_argument(
        "--hf-token",
        default=os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN"),
        help="Token do Hugging Face, se necessario.",
    )
    return parser.parse_args()


def _import_training_stack() -> dict[str, Any]:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
    from trl import SFTConfig, SFTTrainer

    return {
        "torch": torch,
        "load_dataset": load_dataset,
        "LoraConfig": LoraConfig,
        "TaskType": TaskType,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "set_seed": set_seed,
        "SFTConfig": SFTConfig,
        "SFTTrainer": SFTTrainer,
    }


def _resolve_dtype(torch_module: Any) -> Any:
    if not torch_module.cuda.is_available():
        return torch_module.float32
    if torch_module.cuda.is_bf16_supported():
        return torch_module.bfloat16
    return torch_module.float16


def _load_datasets(*, load_dataset_fn: Any, train_file: str, validation_file: str | None) -> Any:
    data_files: dict[str, str] = {"train": train_file}
    if validation_file:
        data_files["validation"] = validation_file
    return load_dataset_fn("json", data_files=data_files)


def _build_model_and_tokenizer(*, stack: dict[str, Any], args: argparse.Namespace) -> tuple[Any, Any, dict[str, Any]]:
    torch_module = stack["torch"]
    quantization_config = None
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": args.trust_remote_code,
        "token": args.hf_token,
    }

    if args.load_in_4bit and torch_module.cuda.is_available():
        quantization_config = stack["BitsAndBytesConfig"](
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=_resolve_dtype(torch_module),
        )
        model_kwargs["quantization_config"] = quantization_config
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = _resolve_dtype(torch_module)
        if torch_module.cuda.is_available():
            model_kwargs["device_map"] = "auto"

    tokenizer = stack["AutoTokenizer"].from_pretrained(
        args.base_model,
        trust_remote_code=args.trust_remote_code,
        token=args.hf_token,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = stack["AutoModelForCausalLM"].from_pretrained(
        args.base_model,
        **model_kwargs,
    )

    if args.load_in_4bit and torch_module.cuda.is_available():
        model = stack["prepare_model_for_kbit_training"](model)

    return model, tokenizer, model_kwargs


def _build_trainer(*, stack: dict[str, Any], args: argparse.Namespace, dataset: Any, model: Any, tokenizer: Any) -> Any:
    torch_module = stack["torch"]
    target_modules = [item.strip() for item in args.target_modules.split(",") if item.strip()]
    lora_config = stack["LoraConfig"](
        task_type=stack["TaskType"].CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules=target_modules,
    )

    bf16_enabled = torch_module.cuda.is_available() and torch_module.cuda.is_bf16_supported()
    fp16_enabled = torch_module.cuda.is_available() and not bf16_enabled
    evaluation_enabled = "validation" in dataset
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = stack["SFTConfig"](
        output_dir=str(output_dir),
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps if evaluation_enabled else None,
        save_strategy="steps",
        eval_strategy="steps" if evaluation_enabled else "no",
        save_total_limit=args.save_total_limit,
        load_best_model_at_end=evaluation_enabled,
        metric_for_best_model="eval_loss" if evaluation_enabled else None,
        greater_is_better=False if evaluation_enabled else None,
        max_length=args.max_seq_length,
        dataset_text_field=None,
        packing=False,
        seed=args.seed,
        report_to=[] if args.report_to == "none" else [args.report_to],
        fp16=fp16_enabled,
        bf16=bf16_enabled,
        gradient_checkpointing=args.gradient_checkpointing,
        optim="paged_adamw_8bit" if args.load_in_4bit and torch_module.cuda.is_available() else "adamw_torch",
    )

    return stack["SFTTrainer"](
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"] if evaluation_enabled else None,
        processing_class=tokenizer,
        peft_config=lora_config,
    )


def _write_summary(
    *,
    output_dir: Path,
    adapter_dir: Path,
    args: argparse.Namespace,
    train_result: Any,
    eval_metrics: dict[str, Any] | None,
    model_kwargs: dict[str, Any],
) -> Path:
    summary = {
        "base_model": args.base_model,
        "train_file": args.train_file,
        "validation_file": args.validation_file,
        "output_dir": str(output_dir),
        "adapter_dir": str(adapter_dir),
        "load_in_4bit": args.load_in_4bit,
        "gradient_checkpointing": args.gradient_checkpointing,
        "target_modules": [item.strip() for item in args.target_modules.split(",") if item.strip()],
        "train_metrics": dict(train_result.metrics),
        "eval_metrics": eval_metrics,
        "model_load_kwargs": {
            key: str(value)
            for key, value in model_kwargs.items()
            if key != "token"
        },
    }
    summary_path = output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path


def main() -> None:
    args = _parse_args()
    stack = _import_training_stack()
    stack["set_seed"](args.seed)

    dataset = _load_datasets(
        load_dataset_fn=stack["load_dataset"],
        train_file=args.train_file,
        validation_file=args.validation_file,
    )
    model, tokenizer, model_kwargs = _build_model_and_tokenizer(stack=stack, args=args)
    trainer = _build_trainer(
        stack=stack,
        args=args,
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
    )

    train_result = trainer.train()
    eval_metrics = trainer.evaluate() if "validation" in dataset else None

    output_dir = Path(args.output_dir)
    adapter_dir = output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    summary_path = _write_summary(
        output_dir=output_dir,
        adapter_dir=adapter_dir,
        args=args,
        train_result=train_result,
        eval_metrics=eval_metrics,
        model_kwargs=model_kwargs,
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "base_model": args.base_model,
                "train_file": args.train_file,
                "validation_file": args.validation_file,
                "output_dir": str(output_dir),
                "adapter_dir": str(adapter_dir),
                "training_summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
