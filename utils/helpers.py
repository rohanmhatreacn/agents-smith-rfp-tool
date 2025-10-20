import mimetypes
import docling

def load_file(filepath: str) -> str:
    ext = mimetypes.guess_type(filepath)[0] or "text/plain"
    if ext.startswith("application/pdf") or ext.endswith("msword"):
        return docling.parse(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
