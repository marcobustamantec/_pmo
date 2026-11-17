#!/usr/bin/env python3
"""
Genera un .md de seguimiento PMO a partir de un YAML de proyecto.

Uso (el .md se guarda en el directorio desde donde se ejecuta, no en el del YAML):
    python generar_seguimiento_pmo.py ruta/al/mejora_continua.yml
    python generar_seguimiento_pmo.py ruta/al/mejora_continua.yml -o otra/ruta/seguimiento.md

Requiere: pip install pyyaml
"""
import argparse
import sys
from collections import Counter
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML: pip install pyyaml")

CAMPOS = {"nombre", "tamaño", "dias", "puntos", "incertidumbre"}
ORDEN_INC = {"alta": 0, "media": 1, "baja": 2}
ICONO_INC = {"alta": "🔴 alta", "media": "🟡 media", "baja": "🟢 baja"}
ESTADOS = "⬜ Pendiente | 🔵 En curso | ✅ Listo | ⛔ Bloqueado"


def esc(txt) -> str:
    """Escapa pipes para no romper las tablas markdown."""
    return str(txt).replace("|", "\\|")


def num(v):
    """Devuelve int/float o None si viene vacío."""
    return v if isinstance(v, (int, float)) else None


def normalizar_item(raw: dict, aviso: list) -> dict:
    """
    Tolera un error típico del YAML: comas dentro del nombre en un mapa
    flow ({nombre: A, B, ...}) generan claves extra con valor nulo.
    Esas claves se reincorporan al nombre.
    """
    item = dict(raw)
    extras = [k for k in item if k not in CAMPOS and item[k] is None]
    if extras:
        item["nombre"] = ", ".join([str(item["nombre"])] + [str(k) for k in extras])
        for k in extras:
            del item[k]
        aviso.append(
            f"'{item['nombre']}': tenía comas sin comillas en el YAML; "
            f"se unió al nombre. Conviene encerrarlo entre comillas."
        )
    desconocidas = [k for k in item if k not in CAMPOS]
    for k in desconocidas:
        aviso.append(f"'{item.get('nombre')}': campo desconocido '{k}' ignorado.")
    return {
        "nombre": str(item.get("nombre", "(sin nombre)")).strip(),
        "tamaño": str(item.get("tamaño") or "—").strip(),
        "dias": num(item.get("dias")),
        "puntos": num(item.get("puntos")),
        "inc": str(item.get("incertidumbre") or "—").strip().lower(),
    }


def cargar(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    proyecto = data["proyecto"]
    avisos: list = []
    milestones = []
    for m in proyecto.get("milestone") or []:
        items = [normalizar_item(i, avisos) for i in (m.get("wb") or [])]
        milestones.append({"nombre": m["nombre"], "items": items})
    return proyecto.get("nombre", "Proyecto"), milestones, avisos


def totales(items):
    return {
        "n": len(items),
        "dias": sum(i["dias"] or 0 for i in items),
        "puntos": sum(i["puntos"] or 0 for i in items),
        "sin_est": sum(1 for i in items if i["dias"] is None),
    }


def fmt(v):
    return "—" if v is None else str(v)


def generar_md(nombre, milestones, avisos) -> str:
    todos = [i for m in milestones for i in m["items"]]
    t = totales(todos)
    inc = Counter(i["inc"] for i in todos)
    L = []

    L += [f"# Seguimiento PMO — {nombre}", ""]
    L += [
        f"- **Fecha de corte:** {date.today():%d-%m-%Y}",
        "- **PM / Responsable:** _por definir_",
        f"- **Leyenda de estado:** {ESTADOS}",
        "",
    ]

    # ---- Resumen ejecutivo
    L += ["## 1. Resumen ejecutivo", ""]
    L += [
        "| Indicador | Valor |",
        "|---|---:|",
        f"| Milestones | {len(milestones)} |",
        f"| Work items | {t['n']} |",
        f"| Días estimados totales | {t['dias']} |",
        f"| Story points totales | {t['puntos']} |",
        f"| Items sin estimar | {t['sin_est']} |",
        f"| Incertidumbre alta / media / baja | "
        f"{inc.get('alta', 0)} / {inc.get('media', 0)} / {inc.get('baja', 0)} |",
        "| % avance global | 0% |",
        "",
    ]

    # ---- Tablero por milestone
    L += ["## 2. Tablero por milestone", ""]
    L += [
        "| # | Milestone | Items | Días | Pts | Sin estimar | Estado | % Avance |",
        "|--:|---|--:|--:|--:|--:|---|--:|",
    ]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        estado = "⬜ Pendiente" if mt["n"] else "⚪ Sin work items"
        L.append(
            f"| {n} | [{esc(m['nombre'])}](#{n}-{slug(m['nombre'])}) | {mt['n']} | "
            f"{mt['dias']} | {mt['puntos']} | {mt['sin_est']} | {estado} | 0% |"
        )
    L.append("")

    # ---- Detalle
    L += ["## 3. Detalle de work items", ""]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        L += [f"### {n}. {m['nombre']}", ""]
        if not m["items"]:
            L += ["_Sin work items definidos (pendiente de levantamiento)._", ""]
            continue
        L += [
            f"**Total:** {mt['dias']} días · {mt['puntos']} pts · {mt['n']} items",
            "",
            "| Work item | Tamaño | Días | Pts | Incertidumbre | Estado | Responsable | Inicio | Fin | % | Notas |",
            "|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|",
        ]
        for i in m["items"]:
            estado = "⚠️ Sin estimar" if i["dias"] is None else "⬜ Pendiente"
            L.append(
                f"| {esc(i['nombre'])} | {i['tamaño']} | {fmt(i['dias'])} | "
                f"{fmt(i['puntos'])} | {ICONO_INC.get(i['inc'], i['inc'])} | "
                f"{estado} |  |  |  | 0 |  |"
            )
        L.append("")

    # ---- Riesgos iniciales derivados
    L += ["## 4. Riesgos y alertas iniciales (derivados de la estimación)", ""]
    riesgos = []
    for m in milestones:
        for i in m["items"]:
            motivos = []
            if i["dias"] is None:
                motivos.append("sin estimar")
            if i["inc"] in ("alta", "media"):
                motivos.append(f"incertidumbre {i['inc']}")
            if motivos:
                riesgos.append((ORDEN_INC.get(i["inc"], 3), m["nombre"], i, motivos))
    riesgos.sort(key=lambda r: (r[0], r[1]))
    if riesgos:
        L += [
            "| Milestone | Work item | Motivo | Días | Mitigación / Acción | Dueño | Estado |",
            "|---|---|---|--:|---|---|---|",
        ]
        for _, mn, i, motivos in riesgos:
            L.append(
                f"| {esc(mn)} | {esc(i['nombre'])} | {', '.join(motivos)} | "
                f"{fmt(i['dias'])} |  |  | ⬜ Abierto |"
            )
    else:
        L.append("_Sin alertas._")
    L.append("")

    # ---- Secciones de gestión vacías
    L += [
        "## 5. Registro de riesgos adicionales",
        "",
        "| ID | Riesgo | Probabilidad | Impacto | Mitigación | Dueño | Estado |",
        "|---|---|---|---|---|---|---|",
        "| R-01 |  |  |  |  |  | ⬜ Abierto |",
        "",
        "## 6. Bloqueos y dependencias",
        "",
        "| Fecha | Descripción | Afecta a | Responsable | Fecha compromiso | Estado |",
        "|---|---|---|---|---|---|",
        "|  |  |  |  |  |  |",
        "",
        "## 7. Decisiones y acuerdos",
        "",
        "| Fecha | Decisión / acuerdo | Participantes |",
        "|---|---|---|",
        "|  |  |  |",
        "",
        "## 8. Control de cambios de alcance",
        "",
        "| Fecha | Cambio | Impacto (días/pts) | Aprobado por |",
        "|---|---|---|---|",
        "|  |  |  |  |",
        "",
    ]

    if avisos:
        L += ["## Notas de generación", ""]
        L += [f"- {a}" for a in avisos]
        L.append("")

    return "\n".join(L)


def slug(txt: str) -> str:
    """Ancla compatible con GitHub/GitLab (aprox.)."""
    import re
    s = txt.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml", type=Path, help="Archivo YAML de entrada")
    ap.add_argument("-o", "--output", type=Path, help="Archivo .md de salida")
    args = ap.parse_args()

    # Por defecto, el .md se guarda en el directorio desde donde se ejecuta
    # el script (cwd), no junto al YAML ni junto al script.
    salida = args.output or Path.cwd() / f"seguimiento_pmo_{args.yaml.stem}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    nombre, milestones, avisos = cargar(args.yaml)
    salida.write_text(generar_md(nombre, milestones, avisos), encoding="utf-8")

    for a in avisos:
        print(f"⚠️  {a}", file=sys.stderr)
    print(f"✅ Generado: {salida}")


if __name__ == "__main__":
    main()
