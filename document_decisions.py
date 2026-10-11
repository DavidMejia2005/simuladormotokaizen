"""Clasificación visual de documentos mediante OpenAI Decisions API."""

import base64
import binascii
import os
import re


ALLOWED_DOCUMENT_CLASSES = {
    "cedula_colombiana",
    "pasaporte",
    "otro_documento",
    "imagen_no_documental",
    "ilegible_o_ambiguo",
}
ACCEPTED_DOCUMENT_CLASSES = {"cedula_colombiana", "pasaporte"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_MIN_CONFIDENCE = 0.80


def _load_local_env():
    """Carga pares simples de .env sin sobrescribir variables ya exportadas."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"').strip("'")
                if name and value and name not in os.environ:
                    os.environ[name] = value
    except OSError as exc:
        raise RuntimeError("No se pudo leer el archivo .env: %s" % exc) from exc


_load_local_env()


def is_openai_configured():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Falta el SDK oficial de OpenAI. Instala las dependencias de requirements.txt."
        ) from exc
    return OpenAI(api_key=api_key)


def _parse_image(image_data, mime_type):
    if not isinstance(image_data, str) or not image_data:
        raise ValueError("La imagen es obligatoria.")
    if image_data.startswith("data:"):
        match = re.fullmatch(r"data:(image/[^;]+);base64,(.+)", image_data, re.DOTALL)
        if not match:
            raise ValueError("La imagen debe ser una data URL base64 válida.")
        mime_type, image_data = match.groups()
    mime_type = (mime_type or "").lower().strip()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Formato de imagen no admitido.")
    try:
        decoded = base64.b64decode(image_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("La imagen base64 no es válida.") from exc
    if not decoded:
        raise ValueError("La imagen está vacía.")
    if len(decoded) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el límite de 5 MB.")
    signatures = {
        "image/jpeg": decoded.startswith(b"\xff\xd8\xff"),
        "image/png": decoded.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP",
        "image/gif": decoded.startswith((b"GIF87a", b"GIF89a")),
    }
    if not signatures[mime_type]:
        raise ValueError("El contenido no coincide con el formato de imagen declarado.")
    return mime_type, decoded


def classify_document(image_data, mime_type="image/jpeg"):
    """Clasifica una imagen y nunca aprueba si la API falla o responde ambiguo."""
    mime_type, decoded = _parse_image(image_data, mime_type)
    image_base64 = base64.b64encode(decoded).decode("ascii")
    decision = _client().decisions.create(
        model="gpt-6-luna",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Clasifica visualmente esta imagen como documento de identidad. "
                            "Solo clasifica el tipo visible; no afirmes autenticidad, vigencia "
                            "ni pertenencia a una persona."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}",
                    },
                ],
            }
        ],
        questions=[
            {
                "type": "choice",
                "name": "document_class",
                "instructions": (
                    "Elige exactamente la categoría que mejor describa la imagen. "
                    "Usa ilegible_o_ambiguo si el texto o el tipo no se puede distinguir "
                    "con suficiente claridad."
                ),
                "choices": [
                    {
                        "value": "cedula_colombiana",
                        "description": "Cédula de ciudadanía colombiana visible y reconocible.",
                    },
                    {
                        "value": "pasaporte",
                        "description": "Pasaporte visible y reconocible, de cualquier país.",
                    },
                    {
                        "value": "otro_documento",
                        "description": "Documento distinto de cédula colombiana o pasaporte.",
                    },
                    {
                        "value": "imagen_no_documental",
                        "description": "No es una imagen de un documento de identidad.",
                    },
                    {
                        "value": "ilegible_o_ambiguo",
                        "description": "La imagen está borrosa, incompleta, reflejada o es ambigua.",
                    },
                ],
            }
        ],
    )
    answers = getattr(decision, "answers", None) or []
    if not answers:
        raise RuntimeError("Decisions API no devolvió respuestas.")
    answer = answers[0]
    if getattr(answer, "type", None) == "refusal":
        raise RuntimeError("Decisions API rechazó clasificar la imagen.")
    if getattr(answer, "type", None) != "choice":
        raise RuntimeError("Decisions API devolvió un tipo de respuesta inesperado.")
    document_class = getattr(answer, "choice", None)
    confidence = getattr(answer, "confidence", None)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        raise RuntimeError("Decisions API no devolvió una confianza válida.")
    if not 0.0 <= confidence <= 1.0:
        raise RuntimeError("Decisions API devolvió una confianza fuera de rango.")
    if document_class not in ALLOWED_DOCUMENT_CLASSES:
        raise RuntimeError("Decisions API devolvió una categoría no permitida.")
    minimum = float(os.environ.get("DOCUMENT_DECISION_MIN_CONFIDENCE", DEFAULT_MIN_CONFIDENCE))
    accepted = document_class in ACCEPTED_DOCUMENT_CLASSES and confidence >= minimum
    return {
        "is_document": accepted,
        "document_class": document_class,
        "confidence": confidence,
        "minimum_confidence": minimum,
        "message": (
            "Tipo de documento aceptado para pruebas: %s."
            % ("cédula colombiana" if document_class == "cedula_colombiana" else "pasaporte")
            if accepted
            else (
                "La imagen es ambigua o ilegible. Toma otra foto."
                if document_class == "ilegible_o_ambiguo"
                else "Solo se aceptan cédula colombiana o pasaporte."
            )
        ),
    }
