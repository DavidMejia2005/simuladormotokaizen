#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consulta de productos reales en Odoo mediante JSON-RPC HTTP puro.

Se usa `requests` (no `xmlrpc.client`) para que el endpoint funcione igual en
local y en el runtime Serverless de Vercel.

Variables de entorno (también se pueden definir en .env):
    ODOO_URL        URL base, por ejemplo https://miempresa.odoo.com
    ODOO_DB         Nombre de la base de datos
    ODOO_USERNAME   Usuario con permisos de lectura sobre productos
    ODOO_API_KEY    API key de Odoo (o contraseña, si la instancia lo permite)
    ODOO_TIMEOUT    Opcional. Segundos de espera de lectura (por defecto 8)
    ODOO_CURRENCY   Opcional. Moneda por defecto si Odoo no la devuelve (COP)
    ODOO_VERIFY_SSL Opcional. 0 para desactivar verificación TLS en pruebas
"""

import base64
import os
import re
import time
from html import unescape

import requests


# Campos solicitados explícitamente a Odoo. Mantener esta lista corta evita
# fallos por campos que no existen en algunas versiones/módulos de Odoo.
PRODUCT_FIELDS = [
    "id",
    "name",
    "display_name",
    "default_code",
    "barcode",
    "lst_price",
    "image_512",
    "categ_id",
    "description_sale",
]

_JSONRPC_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "MotoKaizen-Simulador/1.0",
}

_UID_CACHE = {"uid": None, "at": 0.0}


class OdooError(RuntimeError):
    """Error controlado de la integración con Odoo."""


class OdooNotConfigured(OdooError):
    """Faltan variables de entorno para conectar con Odoo."""


class OdooProductNotFound(OdooError):
    """El código no corresponde a ningún producto de Odoo."""


class OdooRequestError(OdooError):
    """Odoo respondió con un error o no fue posible contactarlo."""


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
        print("[ODOO] No se pudo leer .env: %s" % exc, flush=True)


_load_local_env()


def _setting(name, default=""):
    return (os.environ.get(name) or default).strip()


def _is_placeholder(value):
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized.startswith("tu_")
        or "tuempresa" in normalized
        or "reemplazar" in normalized
        or normalized == "usuario@empresa.com"
    )


def _odoo_password():
    return _setting("ODOO_API_KEY") or _setting("ODOO_PASSWORD")


def is_odoo_configured():
    values = [
        _setting("ODOO_URL"),
        _setting("ODOO_DB"),
        _setting("ODOO_USERNAME"),
        _odoo_password(),
    ]
    return all(value and not _is_placeholder(value) for value in values)


def odoo_status():
    """Resumen sin credenciales para /api/status."""
    return {
        "configured": is_odoo_configured(),
        "product_endpoint": "/api/producto?barcode=...",
        "transport": "requests/json-rpc",
    }


def _jsonrpc_url():
    base = _setting("ODOO_URL").rstrip("/")
    if base and not base.startswith(("http://", "https://")):
        base = "https://" + base
    if base.endswith("/jsonrpc"):
        return base
    return base + "/jsonrpc"


def _timeout():
    try:
        return max(2.0, float(_setting("ODOO_TIMEOUT", "8")))
    except ValueError:
        return 8.0


def _verify_ssl():
    return _setting("ODOO_VERIFY_SSL", "1").lower() not in ("0", "false", "no", "off")


def _clean_error_message(message):
    """Evita devolver trazas o datos internos extensos al navegador."""
    text = str(message or "").strip()
    if not text:
        return "Odoo no completó la solicitud."
    text = re.sub(r"\s+", " ", text)
    if len(text) > 300:
        text = text[:297].rstrip() + "..."
    return text


def _response_error_message(response):
    """Extrae el mensaje legible de un error HTTP/JSON-RPC de Odoo."""
    try:
        payload = response.json()
    except ValueError:
        return _clean_error_message(response.text)

    error = payload.get("error") or {}
    return _clean_error_message(
        (error.get("data") or {}).get("message")
        or error.get("message")
        or response.text
    )


def _rpc(service, method, args):
    """Ejecuta una llamada JSON-RPC 2.0 contra {ODOO_URL}/jsonrpc."""
    if not is_odoo_configured():
        print(
            "[ODOO] Configuración incompleta: faltan ODOO_URL, ODOO_DB, "
            "ODOO_USERNAME u ODOO_API_KEY.",
            flush=True,
        )
        raise OdooNotConfigured(
            "Odoo no está configurado. Define ODOO_URL, ODOO_DB, "
            "ODOO_USERNAME y ODOO_API_KEY en el servidor."
        )

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": args,
        },
        "id": 1,
    }
    url = _jsonrpc_url()

    try:
        response = requests.post(
            url,
            json=payload,
            headers=_JSONRPC_HEADERS,
            timeout=(4.0, _timeout()),
            verify=_verify_ssl(),
        )
    except requests.exceptions.Timeout as exc:
        print("[ODOO] Timeout al conectar con %s: %s" % (url, exc), flush=True)
        raise OdooRequestError("Odoo tardó demasiado en responder.") from exc
    except requests.exceptions.SSLError as exc:
        print("[ODOO] Error SSL con %s: %s" % (url, exc), flush=True)
        raise OdooRequestError(
            "No se pudo establecer la conexión segura con Odoo: %s"
            % _clean_error_message(exc)
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        print("[ODOO] Error de conexión con %s: %s" % (url, exc), flush=True)
        raise OdooRequestError(
            "No se pudo conectar con Odoo. Revisa ODOO_URL y la salida a "
            "internet del servidor: %s" % _clean_error_message(exc)
        ) from exc
    except requests.exceptions.RequestException as exc:
        print("[ODOO] Error HTTP inesperado con %s: %s" % (url, exc), flush=True)
        raise OdooRequestError(
            "No fue posible comunicarse con Odoo: %s" % _clean_error_message(exc)
        ) from exc

    print(
        "[ODOO] POST %s service=%s method=%s -> HTTP %s"
        % (url, service, method, response.status_code),
        flush=True,
    )

    if response.status_code >= 400:
        detail = _response_error_message(response)
        print(
            "[ODOO] Odoo respondió HTTP %s para service=%s method=%s: %s"
            % (response.status_code, service, method, detail),
            flush=True,
        )
        raise OdooRequestError(
            "Odoo respondió HTTP %s: %s" % (response.status_code, detail)
        )

    try:
        data = response.json()
    except ValueError as exc:
        snippet = _clean_error_message(response.text[:500])
        print("[ODOO] Respuesta no JSON: %s" % snippet, flush=True)
        raise OdooRequestError(
            "Odoo devolvió una respuesta que no es JSON válido."
        ) from exc

    if data.get("error"):
        error = data.get("error") or {}
        message = _clean_error_message(
            (error.get("data") or {}).get("message") or error.get("message")
        )
        print("[ODOO] Error JSON-RPC: %s" % message, flush=True)
        raise OdooRequestError(message)

    return data.get("result")


def _authenticate():
    """Hace login JSON-RPC y reutiliza el uid durante diez minutos."""
    uid = _UID_CACHE.get("uid")
    if uid and time.time() - float(_UID_CACHE.get("at") or 0) < 600:
        return uid

    db = _setting("ODOO_DB")
    username = _setting("ODOO_USERNAME")
    print("[ODOO] Autenticando db=%s user=%s" % (db, username), flush=True)

    result = _rpc(
        "common",
        "login",
        [db, username, _odoo_password()],
    )
    try:
        uid = int(result)
    except (TypeError, ValueError):
        uid = 0

    if not uid:
        print(
            "[ODOO] Login rechazado por Odoo para db=%s user=%s."
            % (db, username),
            flush=True,
        )
        raise OdooRequestError(
            "Odoo rechazó las credenciales. Verifica ODOO_DB, "
            "ODOO_USERNAME y ODOO_API_KEY."
        )

    print("[ODOO] Login correcto. uid=%s db=%s" % (uid, db), flush=True)
    _UID_CACHE["uid"] = uid
    _UID_CACHE["at"] = time.time()
    return uid


def _execute_kw(model, method, args, kwargs=None):
    return _rpc(
        "object",
        "execute_kw",
        [
            _setting("ODOO_DB"),
            _authenticate(),
            _odoo_password(),
            model,
            method,
            args,
            kwargs or {},
        ],
    )


def _plain_text(value):
    if value is None or value is False:
        return ""
    text = str(value)
    if "<" in text and ">" in text:
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _many2one_name(value):
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return str(value[1])
    return ""


def _image_data_uri(value):
    if not value:
        return ""
    if isinstance(value, bytes):
        encoded = base64.b64encode(value).decode("ascii")
    else:
        encoded = str(value).strip()
    if not encoded:
        return ""
    if encoded.startswith("data:"):
        return encoded
    return "data:image/png;base64," + encoded


def _product_to_dict(record, requested_barcode):
    odoo_id = record.get("id")
    display_name = _plain_text(
        record.get("display_name") or record.get("name") or "Producto Odoo"
    )
    name = _plain_text(record.get("name")) or display_name

    price = record.get("lst_price")
    if price is None or price is False:
        price = None
    else:
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = None

    odoo_url = ""
    if _setting("ODOO_URL") and odoo_id:
        odoo_url = "%s/web#id=%s&model=product.product&view_type=form" % (
            _setting("ODOO_URL").rstrip("/"),
            odoo_id,
        )

    return {
        "source": "odoo",
        "odoo_id": odoo_id,
        "template_id": None,
        "name": name,
        "display_name": display_name,
        "default_code": _plain_text(record.get("default_code")),
        "barcode": _plain_text(record.get("barcode")) or requested_barcode,
        "price": price,
        "currency": _setting("ODOO_CURRENCY", "COP") or "COP",
        "brand": "",
        "category": _plain_text(_many2one_name(record.get("categ_id"))),
        "uom": "",
        "description": _plain_text(record.get("description_sale")),
        "qty_available": None,
        "type": "",
        "image": _image_data_uri(record.get("image_512")),
        "specs": [],
        "odoo_url": odoo_url,
    }


def get_product_by_barcode(barcode):
    """Devuelve la ficha real del producto o lanza una excepción controlada."""
    code = str(barcode or "").strip()
    if not code:
        raise OdooProductNotFound("Producto no encontrado en Odoo")
    if len(code) > 128:
        raise OdooProductNotFound("Producto no encontrado en Odoo")

    if not is_odoo_configured():
        print(
            "[ODOO] No se puede buscar %r: integración sin configurar." % code,
            flush=True,
        )
        raise OdooNotConfigured(
            "Odoo no está configurado en este despliegue. Define ODOO_URL, "
            "ODOO_DB, ODOO_USERNAME y ODOO_API_KEY."
        )

    print("[ODOO] Buscando product.product por barcode/default_code=%r" % code, flush=True)
    domain = ["|", ("barcode", "=", code), ("default_code", "=", code)]
    try:
        records = _execute_kw(
            "product.product",
            "search_read",
            [domain],
            {
                "fields": PRODUCT_FIELDS,
                "limit": 1,
            },
        )
    except OdooError:
        print("[ODOO] Falló la consulta search_read para %r." % code, flush=True)
        raise

    if not records:
        print("[ODOO] Producto no encontrado para barcode=%r" % code, flush=True)
        raise OdooProductNotFound("Producto no encontrado en Odoo")

    product = _product_to_dict(records[0], code)
    print(
        "[ODOO] Producto encontrado id=%s barcode=%r display_name=%r"
        % (product.get("odoo_id"), product.get("barcode"), product.get("display_name")),
        flush=True,
    )
    return product
