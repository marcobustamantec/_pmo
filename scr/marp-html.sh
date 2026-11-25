
#!/usr/bin/env bash

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Generar tema con recursos incorporados
python3 "$ROOT/scr/embed_theme.py"

THEME="/tmp/elige-idiem-embedded.css"

# Ejecutar Marp con el tema generado
exec marp "$@" \
    --theme-set "$THEME" \
    --allow-local-files
