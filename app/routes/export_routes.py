from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.services.export_service import (
    _build_docx,
    _build_pdf,
    _normalize_export_payload,
)

export_bp = Blueprint("export", __name__)


@export_bp.post("/api/export/docx")
def export_docx():
    try:
        req_json = request.get_json(silent=True) or {}
        payload = _normalize_export_payload(req_json.get("payload", req_json))
        buffer: BytesIO = _build_docx(payload)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name="storyboard.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


@export_bp.post("/api/export/pdf")
def export_pdf():
    try:
        req_json = request.get_json(silent=True) or {}
        payload = _normalize_export_payload(req_json.get("payload", req_json))
        buffer: BytesIO = _build_pdf(payload)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name="storyboard.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500