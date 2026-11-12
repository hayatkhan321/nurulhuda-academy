"""Checking files that teachers upload with their application.

Only PDF, common photo formats and Word files are accepted, recognised by their first bytes rather than by
their name, and at most 2 MB per box. Files are only ever downloaded by the founders from the admin area.
"""
import re

MAX_BYTES = 2 * 1024 * 1024

# first bytes -> (content type, extension)
_SIGNATURES = [
    (b"%PDF-", ("application/pdf", "pdf")),
    (b"\xff\xd8\xff", ("image/jpeg", "jpg")),
    (b"\x89PNG\r\n\x1a\n", ("image/png", "png")),
    (b"GIF8", ("image/gif", "gif")),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", ("application/msword", "doc")),
]


def sniff(head: bytes, allow_word: bool):
    for sig, kind in _SIGNATURES:
        if head.startswith(sig):
            if kind[1] == "doc" and not allow_word:
                return None
            return kind
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ("image/webp", "webp")
    if head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"heif", b"mif1", b"msf1"):
        return ("image/heic", "heic")
    if allow_word and head.startswith(b"PK\x03\x04"):
        return ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx")
    return None


def safe_name(name: str, ext: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._ -]+", "", (name or "").rsplit(".", 1)[0]).strip()[:80] or "file"
    return f"{base}.{ext}"


def read_files(files, kind: str, allow_word: bool):
    """Returns (list of dicts, error message or None). Empty file boxes are simply skipped."""
    out, total = [], 0
    for f in files:
        if not f or not f.filename:
            continue
        data = f.read(MAX_BYTES + 1)
        total += len(data)
        if len(data) > MAX_BYTES or total > MAX_BYTES:
            return [], "This is larger than 2 MB. Please choose a smaller file, or take a photo at a lower size."
        if not data:
            continue
        found = sniff(data[:16], allow_word)
        if not found:
            return [], ("Please upload a PDF, a Word file or a photo (JPG or PNG)." if allow_word
                        else "Please upload a PDF or a photo (JPG or PNG).")
        ctype, ext = found
        out.append({"kind": kind, "filename": safe_name(f.filename, ext), "content_type": ctype,
                    "size": len(data), "data": data})
    return out, None
