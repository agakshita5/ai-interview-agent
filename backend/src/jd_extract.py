import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_text_from_bytes(filename: str, content: bytes) -> str:
    if not content:
        return ""
    ext = Path(filename or "").suffix.lower()
    if ext == ".txt":
        return content.decode("utf-8", errors="replace")

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()

    if ext == ".docx":
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()

    if ext == ".doc":
        if sys.platform == "darwin":
            path = None
            try:
                fd, path = tempfile.mkstemp(suffix=".doc")
                os.write(fd, content)
                os.close(fd)
                out = subprocess.run(
                    ["textutil", "-convert", "txt", "-stdout", path],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if out.returncode != 0:
                    raise ValueError(out.stderr or "Could not read .doc file")
                return (out.stdout or "").strip()
            finally:
                if path and os.path.isfile(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
        raise ValueError(
            "Legacy .doc is only supported on macOS here. Upload DOCX or PDF instead."
        )

    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
