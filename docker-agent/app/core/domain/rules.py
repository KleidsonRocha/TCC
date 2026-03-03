from app.core.domain.errors import InvalidMessageError, UnsupportedSchemaVersionError

SUPPORTED_SCHEMA_VERSION = "1.0"


def validate_schema_version(schema_version: str) -> None:
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError("schema_version deve ser '1.0'.")


def validate_message_text(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        raise InvalidMessageError("message.text nao pode ser vazio.")
    return normalized
