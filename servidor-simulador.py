#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor del Simulador MotoKaizen
=================================
Sirve el simulador (index.html), expone la consulta de productos reales
GET /api/producto?barcode=... (Odoo JSON-RPC) y el endpoint de validación
facial POST /api/validate-face usando OpenCV (detección de objetos con
Haar cascade).

Uso:
    python servidor-simulador.py [puerto] [host]
    (por defecto: 0.0.0.0:5000)

Si OpenCV no está instalado (pip install opencv-python), el servidor sigue
funcionando, pero la interfaz no confirma la identidad y permite reintentar
cuando el análisis esté disponible.
"""

import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import ssl
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np  # dependencia de OpenCV; requerida para el análisis de imágenes
from document_decisions import classify_document, is_openai_configured
from odoo_client import (
    OdooError,
    OdooNotConfigured,
    OdooProductNotFound,
    OdooRequestError,
    get_product_by_barcode,
    is_odoo_configured,
    odoo_status,
)

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    CERTIFICATE_AVAILABLE = True
except ImportError:
    CERTIFICATE_AVAILABLE = False

ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_BODY = 8 * 1024 * 1024  # 8 MB

# --- Carga opcional de OpenCV / clasificador ---
CV_AVAILABLE = False
CASCADE_AVAILABLE = False
_cascade = None
_face_message = ""

try:
    import cv2  # pip install opencv-python
    CV_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    _face_message = "OpenCV no está disponible: %s" % exc

if CV_AVAILABLE:
    try:
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        _cascade = cv2.CascadeClassifier(cascade_path)
        CASCADE_AVAILABLE = not _cascade.empty()
        if not CASCADE_AVAILABLE:
            _face_message = "No se pudo cargar el clasificador facial (haarcascade_frontalface_default.xml)."
    except Exception as exc:  # noqa: BLE001
        _face_message = "Error al cargar el clasificador facial: %s" % exc


def detect_faces_in_jpeg(jpeg_bytes):
    """Devuelve (num_faces, mensaje)."""
    import numpy as np
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return 0, "No se pudo decodificar la imagen capturada."
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=6,
        minSize=(90, 90),
    )
    if len(faces) == 0:
        return 0, "No se detectó un rostro en el cuadro actual."
    return len(faces), "Rostro detectado."


# --- Carga opcional de Tesseract / OCR (validación de documentos) ---
OCR_AVAILABLE = False
_ocr_message = ""
TESS_DATA_DIR = os.path.join(ROOT, "tessdata")


def _find_tesseract():
    for cand in (
        os.environ.get("TESSERACT_CMD"),
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ):
        if cand and os.path.isfile(cand):
            return cand
    return None


try:
    import pytesseract  # pip install pytesseract

    _tesseract_cmd = _find_tesseract()
    if _tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
        if os.path.isdir(TESS_DATA_DIR):
            os.environ.setdefault("TESSDATA_PREFIX", os.path.normpath(TESS_DATA_DIR))
        OCR_AVAILABLE = True
    else:
        _ocr_message = "No se encontró el binario de Tesseract (tesseract.exe)."
except Exception as exc:  # noqa: BLE001
    _ocr_message = "OCR no disponible: %s" % exc


def _ocr_lang_config():
    """Idioma(s) y config de Tesseract según los datos disponibles en ./tessdata."""
    lang = "eng"
    config = "--psm 6"
    if os.path.isdir(TESS_DATA_DIR):
        has_spa = os.path.isfile(os.path.join(TESS_DATA_DIR, "spa.traineddata"))
        has_eng = os.path.isfile(os.path.join(TESS_DATA_DIR, "eng.traineddata"))
        if has_spa and has_eng:
            lang = "spa+eng"
        elif has_spa:
            lang = "spa"
    return lang, config


DOC_KEYWORDS = {
    "cédula": ["cédula de ciudadanía", "cedula de ciudadania", "cédula", "cedula", "ciudadanía", "ciudadania"],
    "extranjeria": ["cédula de extranjería", "cedula de extranjeria", "extranjería", "extranjeria"],
    "tarjeta_identidad": ["tarjeta de identidad", "registro civil"],
    "pasaporte": ["pasaporte", "passport", "número de pasaporte", "numero de pasaporte"],
    "dni_generico": ["documento de identidad", "identity document", "documento", "identidad", "identity card", "identificación", "identificacion", "id. ", "no. de documento"],
    "campo_biografico": ["apellidos", "apellidos:", "nombres", "fecha de nacimiento", "lugar de nacimiento", "nacionalidad", "fecha de vencimiento", "sexo", "firma", "república de colombia", "republica de colombia"],
}

DOC_NUMBER_PATTERNS = [
    re.compile(r"\b\d{6,11}\b"),
    re.compile(r"\b\d{1,3}(?:[. \t]\d{3}){1,3}\b"),
    re.compile(r"\b[A-Z]{1,2}[-\s]?\d{5,9}\b"),
]


def _normalize(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").upper()


def _lookup_keywords(text):
    norm = _normalize(text)
    found = []
    for clave, variants in DOC_KEYWORDS.items():
        if any(_normalize(v) in norm for v in variants):
            found.append(clave)
    return found


def _document_region(img):
    """Devuelve (proporción del marco cubierta, aspect_ok, polígono o None)."""
    h, w = img.shape[:2]
    frame_area = float(h * w)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < frame_area * 0.08:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx) and area > best_area:
            best, best_area = approx, area
    ratio = best_area / frame_area if best is not None else 0.0
    aspect_ok = False
    if best is not None:
        _, (bw, bh), _ = cv2.minAreaRect(best)
        if bw < bh:
            bw, bh = bh, bw
        aspect_ok = bh > 0 and 1.05 <= bw / bh <= 2.6
    return ratio, aspect_ok, best


def _order_doc_points(pts):
    """Ordena las 4 esquinas: tl, tr, br, bl."""
    rect = pts.reshape(4, 2)
    s = rect.sum(axis=1)
    d = np.diff(rect, axis=1).reshape(-1)
    tl = rect[np.argmin(s)]
    br = rect[np.argmax(s)]
    tr = rect[np.argmin(d)]
    bl = rect[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype="float32")


def _warp_document(gray, quad):
    """Endereza el documento (vista frontal) para un OCR más fiable."""
    rect = _order_doc_points(quad)
    (tl, tr, br, bl) = rect
    wA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    wB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    hA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    hB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_w = max(int(wA), int(wB))
    max_h = max(int(hA), int(hB))
    dst = np.array([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(gray, m, (max_w, max_h))


def _ocr_text(img_gray, psm=6):
    """Devuelve el texto OCR de una imagen preprocesada."""
    # En móviles el documento suele ocupar una fracción de la foto. Ampliar
    # también las regiones medianas mejora mucho los dígitos pequeños.
    min_side = min(img_gray.shape)
    if min_side < 900:
        scale = 2.5 if min_side < 500 else 1.8
        img_gray = cv2.resize(img_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    lang, config = _ocr_lang_config()
    return pytesseract.image_to_string(img_gray, lang=lang, config="--psm %d" % psm)


def _ocr_document_text(img, quad=None, ratio=0.0):
    """Ejecuta OCR en varias versiones para soportar fotos móviles con reflejos."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants = [gray]
    variants.append(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray))
    variants.append(cv2.threshold(variants[1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    variants.append(cv2.adaptiveThreshold(
        variants[1], 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    ))
    if quad is not None and ratio >= 0.08:
        try:
            warped = _warp_document(gray, quad)
            variants.extend([warped, cv2.threshold(warped, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]])
        except Exception:
            pass

    texts = []
    for variant in variants:
        for psm in (3, 6, 11, 12):
            text = _ocr_text(variant, psm=psm).strip()
            if text:
                texts.append(text)
    return "\n".join(texts)


def _digits_for_comparison(text):
    """Normaliza confusiones frecuentes de OCR en números de documento."""
    normalized = _normalize(text).translate(str.maketrans({
        "O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8"
    }))
    return re.sub(r"\D+", "", normalized)


def _expected_number_matches(text, expected_digits):
    """Compara el número digitado con candidatos OCR, tolerando separadores y ruido."""
    if not expected_digits:
        return False
    normalized = _normalize(text).translate(str.maketrans({
        "O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8"
    }))
    compact = re.sub(r"\D+", "", normalized)
    if expected_digits in compact:
        return True
    # OCR suele insertar espacios o puntos dentro de la cédula; compara cada
    # fragmento numérico largo antes de descartar caracteres no numéricos.
    for candidate in re.findall(r"[0-9][0-9 .-]{5,20}[0-9]", normalized):
        if re.sub(r"\D+", "", candidate) == expected_digits:
            return True
    # Cuando Tesseract confunde un solo dígito (p. ej. 8/3), acepta una
    # coincidencia de la misma longitud con un único error. El número escrito
    # por el usuario sigue siendo obligatorio; esto no valida una imagen sin
    # un número de documento legible.
    runs = re.findall(r"\d{6,}", compact)
    for run in runs:
        if len(run) == len(expected_digits):
            differences = sum(a != b for a, b in zip(run, expected_digits))
            if differences <= 1:
                return True
    return False


def _expected_document_matches(text, expected_document):
    """Compara números y códigos alfanuméricos de pasaportes."""
    expected = re.sub(r"[^A-Z0-9]", "", _normalize(str(expected_document or "")))
    if not expected:
        return False
    if expected.isdigit():
        return _expected_number_matches(text, expected)
    compact = re.sub(r"[^A-Z0-9]", "", _normalize(text))
    return expected in compact


def _guess_document_type(keywords_found):
    k = set(keywords_found)
    if "pasaporte" in k:
        return "pasaporte"
    if "extranjeria" in k:
        return "cédula de extranjería"
    if "cédula" in k:
        return "cédula de ciudadanía"
    if "tarjeta_identidad" in k:
        return "tarjeta de identidad"
    if "dni_generico" in k:
        return "documento de identidad"
    if "campo_biografico" in k:
        return "documento de identidad"
    return None


def analyze_document_jpeg(jpeg_bytes, expected_document=""):
    """Analiza la imagen y devuelve el dict de resultado para /api/validate-document."""
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {
            "is_document": False, "document_type": None, "confidence": 0.0,
            "keywords": [], "number_found": False,
            "message": "No se pudo decodificar la imagen.",
        }
    ratio, aspect_ok, quad = _document_region(img)

    text = ""
    kw_found = []
    number_found = False
    expected_token = re.sub(r"[^A-Z0-9]", "", _normalize(str(expected_document or "")))
    expected_digits = re.sub(r"\D+", "", expected_token)
    if OCR_AVAILABLE:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        try:
            text = _ocr_document_text(img, quad=quad, ratio=ratio)
            kw_found = _lookup_keywords(text)
            normalized_text = _normalize(text)
            number_found = any(p.search(normalized_text) for p in DOC_NUMBER_PATTERNS)
            expected_match = _expected_document_matches(text, expected_token)
            if expected_digits:
                number_found = expected_match
            elif expected_token:
                number_found = expected_match
        except Exception as exc:  # noqa: BLE001
            return {
                "is_document": False, "document_type": None, "confidence": 0.0,
                "keywords": [], "number_found": False,
                "message": "Error del analizador OCR: %s" % exc,
            }

    edge_score = min(1.0, ratio / 0.32)
    if 0.45 <= ratio <= 0.95 and aspect_ok:
        edge_score = max(edge_score, 0.75)
    kw_score = min(1.0, len(kw_found) * 0.28 + (0.35 if number_found else 0.0))
    confidence = round(0.30 * edge_score + 0.70 * kw_score, 2)

    strong_hit = any(k in ("cédula", "pasaporte", "tarjeta_identidad", "extranjeria", "dni_generico") for k in kw_found)
    identity_fields = "campo_biografico" in kw_found
    # Una cédula fotografiada puede perder todas las palabras del OCR por
    # reflejos, pero conserva el número y la geometría rectangular del formato.
    # No todos los documentos producen un contorno cerrado (bordes blancos,
    # fundas transparentes o fondo claro). En esos casos el OCR debe aportar
    # también palabras de identidad o campos biográficos.
    number_with_document_shape = bool(number_found and (aspect_ok or ratio >= 0.12))
    is_document = bool(
        (confidence >= 0.42 and strong_hit and (number_found or identity_fields))
        or (number_with_document_shape and (identity_fields or strong_hit or expected_digits))
    )

    dtype = _guess_document_type(kw_found) if is_document else None
    if is_document:
        message = "Documento de identidad detectado." if not dtype else "Documento de identidad detectado (%s)." % dtype
    else:
        message = "No se reconoció un documento de identidad. Asegúrate de capturar el documento completo y con buena iluminación."
    return {
        "is_document": is_document,
        "document_type": dtype,
        "confidence": confidence,
        "keywords": kw_found,
        "number_found": number_found,
        "message": message,
    }


MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".md": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def _locate_static(rel_path):
    """Devuelve (ruta, extensión, error). error es 403, 404 o None."""
    root_real = os.path.realpath(ROOT)
    full = os.path.realpath(os.path.join(root_real, rel_path))
    if full != root_real and not full.startswith(root_real + os.sep):
        return None, None, 403
    if not os.path.isfile(full):
        return None, None, 404
    return full, os.path.splitext(full)[1].lower(), None


def _status_payload():
    return {
        "ok": True,
        "cv2": CV_AVAILABLE,
        "cascade": CASCADE_AVAILABLE,
        "message": _face_message or "Servicio disponible.",
        "document_classifier": "openai_decisions",
        "openai_configured": is_openai_configured(),
        "odoo": odoo_status(),
        "odoo_configured": is_odoo_configured(),
        "endpoints": [
            "/api/producto",
            "/api/validate-face",
            "/api/verificar-documento",
            "/api/status",
        ],
    }


def _product_response(barcode):
    """Respuesta de /api/producto?barcode=... Devuelve (payload, código HTTP)."""
    barcode = (barcode or "").strip()
    if not barcode:
        return {
            "ok": False,
            "found": False,
            "error": "Falta el parámetro barcode.",
        }, 400
    if len(barcode) > 128:
        return {
            "ok": False,
            "found": False,
            "barcode": barcode,
            "error": "El código de barras es demasiado largo.",
        }, 400

    try:
        product = get_product_by_barcode(barcode)
    except OdooNotConfigured as exc:
        return {
            "ok": False,
            "found": False,
            "configured": False,
            "status": "not_configured",
            "barcode": barcode,
            "error": str(exc),
            "hint": "Configura ODOO_URL, ODOO_DB, ODOO_USERNAME y ODOO_API_KEY en Vercel o en .env.",
        }, 200
    except OdooProductNotFound as exc:
        return {
            "ok": False,
            "found": False,
            "configured": True,
            "status": "not_found",
            "barcode": barcode,
            "error": str(exc),
        }, 200
    except OdooRequestError as exc:
        return {
            "ok": False,
            "found": False,
            "configured": True,
            "status": "odoo_error",
            "barcode": barcode,
            "error": str(exc),
        }, 200
    except OdooError as exc:
        return {
            "ok": False,
            "found": False,
            "configured": True,
            "status": "odoo_error",
            "barcode": barcode,
            "error": str(exc),
        }, 200

    return {
        "ok": True,
        "found": True,
        "source": "odoo",
        "barcode": barcode,
        "product": product,
    }, 200


def _decode_image_request(payload):
    """Extrae el JPEG en base64 del cuerpo JSON. Devuelve (jpeg, error)."""
    if not isinstance(payload, dict):
        return None, {"ok": False, "message": "JSON inválido."}
    img_b64 = payload.get("image") or ""
    if isinstance(img_b64, str) and img_b64.startswith("data:"):
        img_b64 = img_b64.split(",", 1)[-1]
    try:
        jpeg = base64.b64decode(img_b64, validate=False)
    except Exception:
        return None, {"ok": False, "message": "Base64 inválido."}
    if not jpeg:
        return None, {"ok": False, "message": "Imagen vacía."}
    return jpeg, None


def _validate_face_response(jpeg):
    """Respuesta de /api/validate-face. Devuelve (payload, código HTTP)."""
    if not CV_AVAILABLE or not CASCADE_AVAILABLE:
        return {
            "ok": False,
            "available": False,
            "face_detected": False,
            "message": _face_message or "El análisis facial no está disponible en este servidor.",
        }, 200
    try:
        faces, msg = detect_faces_in_jpeg(jpeg)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "face_detected": False, "message": str(exc)}, 500
    return {
        "ok": True,
        "available": True,
        "face_detected": faces > 0,
        "faces": faces,
        "person_detected": faces > 0,
        "message": msg + " La prueba solo detecta la presencia de un rostro.",
    }, 200


def _document_response(payload, jpeg):
    """Respuesta de /api/verificar-documento. Devuelve (payload, código HTTP)."""
    try:
        result = classify_document(
            base64.b64encode(jpeg).decode("ascii"),
            payload.get("mime_type", "image/jpeg"),
        )
    except ValueError as exc:
        return {"ok": False, "available": True, "is_document": False, "message": str(exc)}, 400
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "available": False,
            "is_document": False,
            "message": "No se pudo clasificar la imagen con Decisions API: %s" % exc,
        }, 502
    return {"ok": True, "available": True, **result}, 200


class SimuladorHandler(BaseHTTPRequestHandler):
    server_version = "MotoKaizenSim/1.0"

    def log_message(self, fmt, *args):
        sys.stdout.write("[sim] %s\n" % (fmt % args))

    # ---------- helpers ----------
    def _send_json(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel_path):
        full, ext, error = _locate_static(rel_path)
        if error == 403:
            self._send_json({"ok": False, "error": "Ruta no permitida"}, 403)
            return
        if error:
            self._send_json({"ok": False, "error": "No encontrado"}, 404)
            return
        ctype = MIME_TYPES.get(ext, "application/octet-stream")
        with open(full, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0 or length > MAX_BODY:
            return None
        return self.rfile.read(length)

    # ---------- rutas ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/status":
            self._send_json(_status_payload())
            return
        if path == "/api/producto":
            params = parse_qs(parsed.query)
            barcode = (params.get("barcode") or [""])[0]
            payload, code = _product_response(barcode)
            self._send_json(payload, code)
            return
        if path == "/":
            self._send_static("index.html")
            return
        if path.startswith("/api/"):
            self._send_json({"ok": False, "error": "Endpoint no existe"}, 404)
            return
        rel = path.lstrip("/")
        if not rel:
            self._send_static("index.html")
            return
        self._send_static(rel)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_body()
        if body is None:
            self._send_json({"ok": False, "message": "Cuerpo de solicitud inválido."}, 400)
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "message": "JSON inválido."}, 400)
            return
        jpeg, error = _decode_image_request(payload)
        if error:
            self._send_json(error, 400)
            return

        if parsed.path == "/api/validate-face":
            result, code = _validate_face_response(jpeg)
            self._send_json(result, code)
            return

        if parsed.path == "/api/verificar-documento":
            result, code = _document_response(payload, jpeg)
            self._send_json(result, code)
            return

        self._send_json({"ok": False, "error": "Endpoint no existe"}, 404)


def _local_ipv4():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def ensure_local_certificate():
    """Crea un certificado local con SAN para la IP LAN, si aún no existe."""
    cert_path = os.path.join(ROOT, ".motokaizen-local.crt")
    key_path = os.path.join(ROOT, ".motokaizen-local.key")
    if os.path.isfile(cert_path) and os.path.isfile(key_path):
        return cert_path, key_path

    ip_address = _local_ipv4()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MotoKaizen Local"),
        x509.NameAttribute(NameOID.COMMON_NAME, ip_address),
    ])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.ip_address(ip_address)),
            x509.DNSName("localhost"),
        ]), critical=False)
        .sign(key, hashes.SHA256())
    )
    with open(key_path, "wb") as key_file:
        key_file.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as cert_file:
        cert_file.write(certificate.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    httpd = ThreadingHTTPServer((host, port), SimuladorHandler)
    https_enabled = "--https" in sys.argv[3:]
    if https_enabled:
        if not CERTIFICATE_AVAILABLE:
            raise RuntimeError("HTTPS requiere cryptography. Instala: python -m pip install cryptography")
        cert_path, key_path = ensure_local_certificate()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print("HTTPS activo. En iPhone abre https://<IP-LOCAL>:%d y acepta el certificado local." % port)
    print("Servidor del Simulador MotoKaizen -> http://%s:%d" % (host, port))
    if not CV_AVAILABLE:
        print("AVISO: OpenCV no instalado; la validación facial no estará disponible.")
    elif not CASCADE_AVAILABLE:
        print("AVISO: clasificador facial no cargado; la validación facial no estará disponible.")
    else:
        print("OK: detección de rostro por OpenCV disponible (Haar cascade).")
    print("Clasificación documental: OpenAI Decisions API (requiere OPENAI_API_KEY).")
    if is_odoo_configured():
        print("Productos reales: Odoo configurado para /api/producto.")
    else:
        print("AVISO: Odoo no configurado; /api/producto responderá 503 hasta definir ODOO_URL, ODOO_DB, ODOO_USERNAME y ODOO_API_KEY.")
    print("Presiona Ctrl+C para detener el servidor.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
        httpd.server_close()


# ---------------------------------------------------------------------------
# Punto de entrada WSGI (Vercel y otros servidores compatibles)
# ---------------------------------------------------------------------------
def _wsgi_json(start_response, payload, code=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(
        "%d %s" % (code, HTTPStatus(code).phrase),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def _wsgi_static(start_response, rel_path):
    full, ext, error = _locate_static(rel_path)
    if error == 403:
        return _wsgi_json(start_response, {"ok": False, "error": "Ruta no permitida"}, 403)
    if error:
        return None  # el llamador decide si aplica el fallback a index.html
    with open(full, "rb") as fh:
        data = fh.read()
    headers = [
        ("Content-Type", MIME_TYPES.get(ext, "application/octet-stream")),
        ("Content-Length", str(len(data))),
    ]
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"):
        headers.append(("Cache-Control", "no-store"))
    start_response("200 OK", headers)
    return [data]


def app(environ, start_response):
    """Aplicación WSGI con las mismas rutas que el servidor local.

    Se declara a nivel de módulo (fuera de main) para que Vercel u otro
    servidor WSGI pueda cargarla como la app del módulo.
    """
    method = (environ.get("REQUEST_METHOD") or "GET").upper()
    path = unquote(environ.get("PATH_INFO") or "/")

    if method in ("GET", "HEAD"):
        if path == "/api/status":
            return _wsgi_json(start_response, _status_payload())
        if path == "/api/producto":
            params = parse_qs(environ.get("QUERY_STRING") or "")
            barcode = (params.get("barcode") or [""])[0]
            payload, code = _product_response(barcode)
            return _wsgi_json(start_response, payload, code)
        if path.startswith("/api/"):
            return _wsgi_json(start_response, {"ok": False, "error": "Endpoint no existe"}, 404)
        rel = path.lstrip("/")
        if not rel or rel.endswith("/"):
            rel = rel + "index.html"
        response = _wsgi_static(start_response, rel)
        if response is None and not os.path.splitext(rel)[1]:
            response = _wsgi_static(start_response, "index.html")
        if response is None:
            response = _wsgi_json(start_response, {"ok": False, "error": "No encontrado"}, 404)
        return response

    if method == "POST":
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0 or length > MAX_BODY:
            return _wsgi_json(start_response, {"ok": False, "message": "Cuerpo de solicitud inválido."}, 400)
        try:
            payload = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
        except Exception:
            return _wsgi_json(start_response, {"ok": False, "message": "JSON inválido."}, 400)
        jpeg, error = _decode_image_request(payload)
        if error:
            return _wsgi_json(start_response, error, 400)
        if path == "/api/validate-face":
            result, code = _validate_face_response(jpeg)
            return _wsgi_json(start_response, result, code)
        if path == "/api/verificar-documento":
            result, code = _document_response(payload, jpeg)
            return _wsgi_json(start_response, result, code)
        return _wsgi_json(start_response, {"ok": False, "error": "Endpoint no existe"}, 404)

    return _wsgi_json(start_response, {"ok": False, "error": "Método no permitido"}, 405)


if __name__ == "__main__":
    main()
