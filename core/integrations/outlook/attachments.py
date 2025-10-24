import base64
from typing import Any, Dict, List, Optional
from core.utils.log_manager.log_manager import (
    log_error,
    log_attachments_process_start,
    log_attachments_completed,
)


SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _get_extension(filename: str) -> str:
    if not filename:
        return ""
    lower = filename.lower()
    for ext in SUPPORTED_IMAGE_EXTENSIONS:
        if lower.endswith(ext):
            return ext
    if lower.endswith(".msg"):
        return ".msg"
    return ""


def _normalize_graph_attachment(attachment: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": attachment.get("id"),
        "name": attachment.get("name"),
        "content_type": attachment.get("contentType"),
        "is_inline": attachment.get("isInline", False),
        # Graph returns base64 string in contentBytes for FileAttachment
        "base64_data": attachment.get("contentBytes"),
        "size": attachment.get("size"),
        # ItemAttachment expanded content (if requested via $expand)
        "item": attachment.get("item"),
        # For safety, allow caller to see raw
        "_raw": attachment,
    }


def handle_image_attachment(filename: str, mime_type: str, base64_data: str) -> Optional[Dict[str, Any]]:
    if not base64_data:
        return None
    if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
        # Some senders mislabel; allow by extension
        ext = _get_extension(filename)
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            return None
        # Normalize mime from extension
        if ext == ".png":
            mime_type = "image/png"
        else:
            mime_type = "image/jpeg"

    # Ensure the string is valid base64; if not, try to re-encode
    try:
        # Validate by decoding once
        base64.b64decode(base64_data, validate=True)
        normalized_b64 = base64_data
    except Exception as e:
        # If Graph provided bytes, caller should pass base64. As a fallback, try encoding bytes
        try:
            normalized_b64 = base64.b64encode(base64_data).decode("utf-8")  # type: ignore[arg-type]
        except Exception as enc_e:
            log_error(f"ATTACHMENTS: Failed to normalize image attachment {filename}", enc_e)
            return None

    data_url = f"data:{mime_type};base64,{normalized_b64}"

    return {
        "type": "image",
        "filename": filename,
        "mime_type": mime_type,
        "base64_data": normalized_b64,
        "data_url": data_url,
        # Convenience block for Agents SDK
        "input_block": {"type": "input_image", "detail": "auto", "image_url": data_url},
    }


def handle_msg_attachment(filename: str, base64_data: str) -> Optional[Dict[str, Any]]:
    if not base64_data:
        return None
    try:
        raw_bytes = base64.b64decode(base64_data)
    except Exception:
        return None

    sender = None
    subject = None
    body = None

    # Best-effort parse using extract_msg if available; keep lightweight and optional
    try:
        import io
        try:
            import extract_msg  # type: ignore
        except Exception:
            extract_msg = None  # type: ignore

        if extract_msg is not None:
            with io.BytesIO(raw_bytes) as buffer:
                msg = extract_msg.Message(buffer)  # type: ignore[attr-defined]
                try:
                    sender = msg.sender or msg.sender_email
                except Exception:
                    sender = None
                try:
                    subject = msg.subject
                except Exception:
                    subject = None
                try:
                    # Prefer plain body; fall back to HTML stripped by caller later
                    body = msg.body or msg.bodyHTML
                except Exception:
                    body = None
                try:
                    msg.close()
                except Exception:
                    pass
    except Exception as e:
        # Parsing failure is non-fatal; return raw base64 with minimal metadata
        pass

    return {
        "type": "msg",
        "filename": filename,
        "mime_type": "application/vnd.ms-outlook",
        "base64_data": base64_data,
        "parsed": {
            "sender": sender,
            "subject": subject,
            "body": body,
        },
    }


def handle_item_attachment(filename: str, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not item:
        return None
    try:
        sender_email = None
        try:
            sender_email = (item.get("sender") or {}).get("emailAddress", {}).get("address")
        except Exception:
            sender_email = None
        subject = item.get("subject")
        body_content = None
        try:
            body_content = (item.get("body") or {}).get("content")
        except Exception:
            body_content = None
        return {
            "type": "msg",
            "filename": filename,
            "mime_type": "message/rfc822",
            "base64_data": None,
            "parsed": {
                "sender": sender_email,
                "subject": subject,
                "body": body_content,
            },
        }
    except Exception:
        return None


def process_attachments(graph_attachments: List[Dict[str, Any]]) -> Dict[str, Any]:
    log_attachments_process_start(len(graph_attachments or []))
    processed: List[Dict[str, Any]] = []
    image_blocks: List[Dict[str, Any]] = []
    msg_summaries: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    pdfs: List[Dict[str, Any]] = []
    other_files: List[Dict[str, Any]] = []

    for att in graph_attachments or []:
        a = _normalize_graph_attachment(att)
        name = a.get("name") or "attachment"
        mime = a.get("content_type") or ""
        base64_data = a.get("base64_data")
        item = a.get("item")
        ext = _get_extension(name)

        # Images
        if mime in SUPPORTED_IMAGE_MIME_TYPES or ext in SUPPORTED_IMAGE_EXTENSIONS:
            img = handle_image_attachment(name, mime, base64_data)
            if img:
                processed.append(img)
                images.append(img)
                image_blocks.append(img["input_block"])
                # minimal logging only
                continue

        # Outlook .msg (file attachment)
        if ext == ".msg" or mime in {"application/vnd.ms-outlook", "application/vnd.ms-outlook-item"}:
            msg_obj = handle_msg_attachment(name, base64_data)
            if msg_obj:
                processed.append(msg_obj)
                other_files.append(msg_obj)
                summary = {
                    "filename": name,
                    "sender": (msg_obj.get("parsed") or {}).get("sender"),
                    "subject": (msg_obj.get("parsed") or {}).get("subject"),
                }
                # For prompt safety, include only first 2000 chars of body if present
                body_text = (msg_obj.get("parsed") or {}).get("body")
                if body_text:
                    summary["body_preview"] = str(body_text)[:2000]
                msg_summaries.append(summary)
                # minimal logging only
                continue

        # Outlook item attachment (expanded message)
        if item:
            msg_obj = handle_item_attachment(name, item)
            if msg_obj:
                processed.append(msg_obj)
                other_files.append(msg_obj)
                summary = {
                    "filename": name,
                    "sender": (msg_obj.get("parsed") or {}).get("sender"),
                    "subject": (msg_obj.get("parsed") or {}).get("subject"),
                }
                body_text = (msg_obj.get("parsed") or {}).get("body")
                if body_text:
                    summary["body_preview"] = str(body_text)[:2000]
                msg_summaries.append(summary)
                # minimal logging only
                continue

        # All other file types (PDFs, Excel, Word, etc.)
        if base64_data:
            other_file = {
                "type": "file",
                "filename": name,
                "mime_type": mime,
                "base64_data": base64_data,
            }
            processed.append(other_file)
            
            # Track PDFs separately for logging
            if name.lower().endswith('.pdf') or mime == 'application/pdf':
                pdfs.append(other_file)
            
            other_files.append(other_file)
            continue

        # Only skip if no data at all
        skipped.append({
            "filename": name,
            "mime_type": mime,
            "error": "no_data"
        })

    log_attachments_completed(len(image_blocks), len(pdfs), len(msg_summaries), len(skipped))
    return {
        "processed": processed,
        "image_blocks": image_blocks,
        "msg_summaries": msg_summaries,
        "skipped": skipped,
        "images": images,
        "pdfs": pdfs,
        "other_files": other_files,
    }


