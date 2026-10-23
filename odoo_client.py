#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cliente mínimo para consultar productos reales en Odoo por JSON-RPC.

Variables de entorno (también se pueden definir en .env):
    ODOO_URL        URL base de la instancia, por ejemplo https://miempresa.odoo.com
    ODOO_DB         Nombre de la base de datos
    ODOO_USERNAME   Usuario con permisos de lectura sobre productos
    ODOO_API_KEY    API key de Odoo (o contraseña, si la instancia lo permite)
    ODOO_TIMEOUT    Opcional. Segundos de espera por petición (por defecto 12)
    ODOO_CACHE_TTL  Opcional. Segundos de caché por producto (por defecto 60)

No se envían credenciales al navegador: el simulador solo recibe los datos
públicos del producto que se muestran en la ficha.
"""

import base64
import json
import os
import re
import ssl
import time
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PRODUCT_FIELDS = [
    "id",
    "name",
    "display_name",
    "default_code",
    "barcode",
    "lst_price",
    "list_price",
    "standard_price",
    "currency_id",
    "uom_id",
    "categ_id",
    "description_sale",
    "description",
    "qty_available",
    "virtual_available",
    "type",
    "sale_ok",
    "active",
    "product_tmpl_id",
    "product_template_attribute_value_ids",
    "product_template_variant_value_ids",
    "image_512",
    "image_1024",
    "image_1920",
    "image_256",
    "image_128",
    "product_brand_id",
]

CORE_PRODUCT_FIELDS = [
    "id",
    "name",
    "display_name",
    "default_code",
    "barcode",
    "lst_price",
    "list_price",
    "currency_id",
    "uom_id",
    "categ_id",
    "description_sale",
    "description",
    "qty_available",
    "type",
    "product_tmpl_id",
    "image_512",
    "image_1024",
    "image_1920",
]

_FIELDS_CACHE = None
_UID_CACHE = {"uid": None, "at": 0.0}
_PRODUCT_CACHE = {}


class OdooError(RuntimeError):
    """Error controlado de la integración con Odoo."""


class OdooNotConfigured(OdooError):
    """Faltan variables de entorno para conectar con Odoo."""


class OdooProductNotFound(OdooError):
    """El código no corresponde a ningún producto de Odoo."""


class OdooRequestError(OdooError):
    """La instancia de Odoo respondió con un error o no fue posible contactarla."""


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
    except OSError:
        # La integración de productos es opcional; el resto del simulador
        # debe seguir funcionando aunque .env no se pueda leer.
        pass


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
    }


def _rpc_url():
    base = _setting("ODOO_URL").rstrip("/")
    if base.endswith("/jsonrpc"):
        return base
    return base + "/jsonrpc"


def _timeout():
    try:
        return max(2.0, float(_setting("ODOO_TIMEOUT", "8")))
    except ValueError:
        return 8.0


def _ssl_context():
    context = ssl.create_default_context()
    if _setting("ODOO_VERIFY_SSL", "1").lower() in ("0", "false", "no", "off"):
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _clean_error_message(message):
    """Evita devolver trazas o datos internos de Odoo al navegador."""
    text = str(message or "").strip()
    if not text:
        return "Odoo no completó la solicitud."
    # Odoo suele incluir el nombre del modelo y una explicación legible.
    text = re.sub(r"\s+", " ", text)
    if len(text) > 300:
        text = text[:297].rstrip() + "..."
    return text


def _rpc(service, method, args):
    if not is_odoo_configured():
        raise OdooNotConfigured(
            "Odoo no está configurado. Define ODOO_URL, ODOO_DB, "
            "ODOO_USERNAME y ODOO_API_KEY en el servidor."
        )

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
        "id": int(time.time() * 1000) % 2147483647,
    }
    request = Request(
        _rpc_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MotoKaizen-Simulador/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=_timeout(), context=_ssl_context()) as response:
            raw = response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        if detail:
            try:
                parsed = json.loads(detail)
                detail = (
                    (parsed.get("error") or {}).get("data", {}).get("message")
                    or (parsed.get("error") or {}).get("message")
                    or detail
                )
            except Exception:  # noqa: BLE001
                pass
        raise OdooRequestError(
            "Odoo respondió HTTP %s: %s" % (exc.code, _clean_error_message(detail))
        ) from exc
    except URLError as exc:
        raise OdooRequestError(
            "No se pudo conectar con Odoo. Revisa ODOO_URL y la salida a internet: %s"
            % _clean_error_message(getattr(exc, "reason", exc))
        ) from exc
    except TimeoutError as exc:
        raise OdooRequestError("Odoo tardó demasiado en responder.") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OdooRequestError("Odoo devolvió una respuesta que no es JSON válido.") from exc

    if data.get("error"):
        error = data["error"] or {}
        message = (error.get("data") or {}).get("message") or error.get("message")
        raise OdooRequestError(_clean_error_message(message))

    return data.get("result")


def _authenticate():
    uid = _UID_CACHE.get("uid")
    if uid and time.time() - float(_UID_CACHE.get("at") or 0) < 600:
        return uid

    result = _rpc(
        "common",
        "login",
        [_setting("ODOO_DB"), _setting("ODOO_USERNAME"), _odoo_password()],
    )
    try:
        uid = int(result)
    except (TypeError, ValueError):
        uid = 0
    if not uid:
        raise OdooRequestError(
            "Odoo rechazó las credenciales. Verifica ODOO_DB, ODOO_USERNAME y ODOO_API_KEY."
        )
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


def _available_product_fields():
    global _FIELDS_CACHE
    if _FIELDS_CACHE is not None:
        return _FIELDS_CACHE
    try:
        fields = _execute_kw(
            "product.product",
            "fields_get",
            [],
            {"attributes": ["type", "string"]},
        )
        _FIELDS_CACHE = set(fields.keys()) if isinstance(fields, dict) else set()
    except OdooError:
        _FIELDS_CACHE = set()
    return _FIELDS_CACHE


def _product_fields():
    available = _available_product_fields()
    if not available:
        return CORE_PRODUCT_FIELDS
    selected = [field for field in PRODUCT_FIELDS if field in available]
    # El precio y el nombre son imprescindibles; si fields_get no los reporta,
    # se conserva el conjunto base para que Odoo devuelva un error claro.
    return selected or CORE_PRODUCT_FIELDS


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


def _many2one_id(value):
    if isinstance(value, (list, tuple)) and value:
        try:
            return int(value[0])
        except (TypeError, ValueError):
            return None
    return None


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


def _attributes_from_record(record):
    ids = (
        record.get("product_template_variant_value_ids")
        or record.get("product_template_attribute_value_ids")
        or []
    )
    if not ids:
        return []
    try:
        attributes = _execute_kw(
            "product.template.attribute.value",
            "read",
            [ids],
            {"fields": ["name", "attribute_id", "price_extra"]},
        )
    except OdooError:
        return []

    specs = []
    for attribute in attributes or []:
        value = _plain_text(attribute.get("name"))
        label = _many2one_name(attribute.get("attribute_id")) or "Atributo"
        if value:
            specs.append({"label": label, "value": value})
    return specs


def _product_to_dict(record, requested_barcode):
    currency = (
        _many2one_name(record.get("currency_id"))
        or _setting("ODOO_CURRENCY")
        or "COP"
    )
    odoo_id = record.get("id")
    name = record.get("display_name") or record.get("name") or "Producto Odoo"

    price = record.get("lst_price")
    if price is None or price is False:
        price = record.get("list_price")
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = None

    qty = record.get("qty_available")
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        qty = None

    brand = _many2one_name(record.get("product_brand_id"))
    category = _many2one_name(record.get("categ_id"))
    uom = _many2one_name(record.get("uom_id"))

    image = ""
    for field in ("image_512", "image_1024", "image_256", "image_128", "image_1920"):
        if record.get(field):
            image = _image_data_uri(record.get(field))
            break

    template_id = _many2one_id(record.get("product_tmpl_id"))
    odoo_url = ""
    if _setting("ODOO_URL") and odoo_id:
        odoo_url = "%s/web#id=%s&model=product.product&view_type=form" % (
            _setting("ODOO_URL").rstrip("/"),
            odoo_id,
        )

    return {
        "source": "odoo",
        "odoo_id": odoo_id,
        "template_id": template_id,
        "name": _plain_text(record.get("name")) or name,
        "display_name": _plain_text(name),
        "default_code": _plain_text(record.get("default_code")),
        "barcode": _plain_text(record.get("barcode")) or requested_barcode,
        "price": price,
        "currency": currency,
        "brand": _plain_text(brand),
        "category": _plain_text(category),
        "uom": _plain_text(uom),
        "description": _plain_text(
            record.get("description_sale")
            or record.get("description")
            or ""
        ),
        "qty_available": qty,
        "type": record.get("type") or "",
        "image": image,
        "specs": _attributes_from_record(record),
        "odoo_url": odoo_url,
    }


def get_product_by_barcode(barcode):
    """Devuelve la ficha real del producto o lanza una excepción controlada."""
    code = str(barcode or "").strip()
    if not code:
        raise OdooProductNotFound("Falta el código de barras del producto.")
    if len(code) > 128:
        raise OdooProductNotFound("El código de barras es demasiado largo.")

    if not is_odoo_configured():
        raise OdooNotConfigured(
            "Odoo no está configurado en este despliegue. Define ODOO_URL, "
            "ODOO_DB, ODOO_USERNAME y ODOO_API_KEY."
        )

    try:
        ttl = max(0.0, float(_setting("ODOO_CACHE_TTL", "60")))
    except ValueError:
        ttl = 60.0
    cached = _PRODUCT_CACHE.get(code)
    if cached and ttl and time.time() - cached[0] < ttl:
        return cached[1]

    domain = ["|", ("barcode", "=", code), ("default_code", "=", code)]
    records = _execute_kw(
        "product.product",
        "search_read",
        [domain],
        {
            "fields": _product_fields(),
            "limit": 1,
            "order": "id asc",
        },
    )

    if not records:
        raise OdooProductNotFound(
            "No existe ningún producto con el código %s en Odoo." % code
        )

    product = _product_to_dict(records[0], code)
    if ttl:
        _PRODUCT_CACHE[code] = (time.time(), product)
    return product
