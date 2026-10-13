"""Upload validation by actual file content (magic bytes and structure), not by name or browser MIME type."""

import io
import re
import unicodedata
import zipfile

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def detect_cv_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return PDF_MIME
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" in names and "word/document.xml" in names:
                    # Macro-enabled documents are not accepted.
                    if any(name.endswith("vbaProject.bin") for name in names):
                        return None
                    # Zip bomb guard: the uncompressed size must stay reasonable.
                    if sum(info.file_size for info in archive.infolist()) > 100 * 1024 * 1024:
                        return None
                    return DOCX_MIME
        except zipfile.BadZipFile:
            return None
    return None


def detect_image_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def safe_filename(*parts: str, extension: str) -> str:
    """ASCII-only, filesystem- and header-safe download names, e.g. CV_Semih_Altintas_Data_Engineer.pdf"""
    text = "_".join(part for part in parts if part)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:80] or "document"
    return f"{text}.{extension}"
