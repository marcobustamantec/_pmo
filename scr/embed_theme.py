
from pathlib import Path
import re
import base64
import mimetypes
from urllib.parse import unquote

# Raíz del repositorio: directorio padre de scripts/
ROOT = Path(__file__).resolve().parent.parent

# Tema original
CSS_FILE = ROOT / "styles" / "elige-idiem.css"

# Tema generado
OUTPUT_FILE = Path("/tmp/elige-idiem-embedded.css")

css = CSS_FILE.read_text(encoding="utf-8")

# Detectar recursos url(...) del CSS
pattern = re.compile(
    r"""url\(\s*(?P<quote>["']?)(?P<path>.*?)(?P=quote)\s*\)""",
    re.IGNORECASE
)

def embed_resource(match):
    path = match.group("path").strip()

    # No modificar recursos que no sean archivos locales
    if (
        not path
        or path.startswith(("data:", "http:", "https:", "//", "#", "file:"))
    ):
        return match.group(0)

    # Resolver la ruta respecto del CSS original
    resource = (CSS_FILE.parent / unquote(path)).resolve()

    if not resource.is_file():
        raise FileNotFoundError(
            f"Recurso no encontrado: {path}\n"
            f"Ruta buscada: {resource}"
        )

    mime = mimetypes.guess_type(resource.name)[0]

    if not mime:
        mime = "application/octet-stream"

    encoded = base64.b64encode(resource.read_bytes()).decode("ascii")

    return f'url("data:{mime};base64,{encoded}")'


css_embedded = pattern.sub(embed_resource, css)

OUTPUT_FILE.write_text(css_embedded, encoding="utf-8")

print(f"Tema generado correctamente: {OUTPUT_FILE}")
