#!/usr/bin/env python3
"""
Genera un .md de seguimiento PMO (con Gantt interactivo en Plotly) a partir
de un YAML de proyecto.

El .md y los HTML de los Gantt se guardan en el directorio desde donde se
ejecuta el script (no en el del YAML), salvo que uses -o.

Uso:
    python generar_seguimiento_pmo.py ruta/mejora_continua.yml
    python generar_seguimiento_pmo.py ruta/mejora_continua.yml --inicio 2026-12-01
    python generar_seguimiento_pmo.py ruta/mejora_continua.yml --modo paralelo
    python generar_seguimiento_pmo.py ruta/mejora_continua.yml -o otra/ruta/seguimiento.md
    python generar_seguimiento_pmo.py ruta/mejora_continua.yml --sin-gantt

Requiere: pip install pyyaml plotly
"""
import argparse
import math
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML: pip install pyyaml")

CAMPOS = {"nombre", "tamaño", "dias", "puntos", "incertidumbre"}
ORDEN_INC = {"alta": 0, "media": 1, "baja": 2}
ICONO_INC = {"alta": "🔴 alta", "media": "🟡 media", "baja": "🟢 baja"}
COLOR_INC = {"alta": "#e5484d", "media": "#f5a524", "baja": "#30a46c", "—": "#8b8d98"}
ESTADOS = "⬜ Pendiente | 🔵 En curso | ✅ Listo | ⛔ Bloqueado"


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------
def esc(txt) -> str:
    """Escapa pipes para no romper las tablas markdown."""
    return str(txt).replace("|", "\\|")


def num(v):
    """Devuelve int/float o None si viene vacío."""
    return v if isinstance(v, (int, float)) else None


def fmt(v):
    return "—" if v is None else str(v)


def fecha_txt(d) -> str:
    return "—" if d is None else f"{d:%d-%m-%Y}"


def slug(txt: str) -> str:
    """Ancla compatible con GitHub/GitLab/MkDocs (aprox.)."""
    import re
    s = txt.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s)


# --------------------------------------------------------------------------
# Lectura del YAML
# --------------------------------------------------------------------------
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
        "ini": None,   # se completan en agendar()
        "fin": None,
    }


def parse_fecha(v):
    """Acepta date, datetime o 'YYYY-MM-DD'. Devuelve date o None."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v).strip(), "%Y-%m-%d").date()


def cargar(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    proyecto = data["proyecto"]
    avisos: list = []
    milestones = []
    for m in proyecto.get("milestone") or []:
        items = [normalizar_item(i, avisos) for i in (m.get("wb") or [])]
        milestones.append({"nombre": m["nombre"], "items": items})
    return (
        proyecto.get("nombre", "Proyecto"),
        milestones,
        avisos,
        parse_fecha(proyecto.get("inicio")),   # campo opcional proyecto.inicio
    )


def totales(items):
    return {
        "n": len(items),
        "dias": sum(i["dias"] or 0 for i in items),
        "puntos": sum(i["puntos"] or 0 for i in items),
        "sin_est": sum(1 for i in items if i["dias"] is None),
    }


# --------------------------------------------------------------------------
# Calendarización (días hábiles lun-vie, sin feriados)
# --------------------------------------------------------------------------
def proximo_habil(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def sumar_habiles(d: date, n: int) -> date:
    """Fecha en que termina un trabajo de n días hábiles iniciado en d.
    (fin exclusivo: es el día hábil en que parte lo siguiente)."""
    d = proximo_habil(d)
    restantes = n
    while restantes > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            restantes -= 1
    return d


def agendar(milestones, inicio: date, modo: str):
    """
    Asigna ini/fin a cada work item estimado.
      - secuencial: un solo equipo; todo se hace uno tras otro, en el orden del YAML.
      - paralelo:   cada milestone parte en la fecha de inicio; dentro de cada
                    milestone los items van uno tras otro.
    Los items sin estimar no se calendarizan.
    """
    base = proximo_habil(inicio)
    cursor = base
    for m in milestones:
        if modo == "paralelo":
            cursor = base
        for i in m["items"]:
            if i["dias"] is None:
                continue
            i["ini"] = cursor
            i["fin"] = sumar_habiles(cursor, math.ceil(i["dias"]))
            cursor = i["fin"]
        agendados = [i for i in m["items"] if i["ini"]]
        m["ini"] = min((i["ini"] for i in agendados), default=None)
        m["fin"] = max((i["fin"] for i in agendados), default=None)
    fines = [m["fin"] for m in milestones if m["fin"]]
    return base, (max(fines) if fines else None)


# --------------------------------------------------------------------------
# Gantt con Plotly
# --------------------------------------------------------------------------
def _ms(d1: date, d2: date) -> float:
    return (d2 - d1).days * 86_400_000


def generar_gantt(nombre, milestones, carpeta: Path, stem: str, hoy: date):
    """
    Escribe dos HTML interactivos en `carpeta` y devuelve una lista de dicts
    {archivo, titulo, alto}. plotly.min.js se guarda una sola vez en la carpeta
    (funciona offline / detrás de un proxy, sin CDN).
    Devuelve (lista, error). Si Plotly no está instalado -> ([], mensaje).
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return [], "Plotly no está instalado (pip install plotly); se omitieron los Gantt."

    config = {"displaylogo": False, "responsive": True}
    salida = []

    todos = [i for m in milestones for i in m["items"] if i["ini"]]
    if not todos:
        return [], "No hay work items con estimación; no se generó Gantt."
    ini_proy = min(i["ini"] for i in todos)
    fin_proy = max(i["fin"] for i in todos)

    def linea_hoy(fig):
        if ini_proy <= hoy <= fin_proy:
            x = datetime.combine(hoy, datetime.min.time())
            fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper",
                          line=dict(color="#6e56cf", width=2, dash="dot"))
            fig.add_annotation(x=x, y=1, yref="paper", text="Hoy", showarrow=False,
                               yanchor="bottom", font=dict(color="#6e56cf"))

    def layout(fig, titulo, alto, etiquetas):
        fig.update_layout(
            title=dict(text=titulo, x=0.01),
            template="plotly_white",
            height=alto,
            margin=dict(l=10, r=20, t=70, b=40),
            barmode="overlay",
            legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
            hoverlabel=dict(align="left"),
        )
        fig.update_xaxes(type="date", showgrid=True, gridcolor="#e6e8ef",
                         tickformat="%d %b\n%Y", side="top")
        fig.update_yaxes(autorange="reversed", automargin=True,
                         categoryorder="array", categoryarray=etiquetas)

    # ---- Gantt 1: resumen por milestone
    filas = [(n, m) for n, m in enumerate(milestones, 1) if m["ini"]]
    etiquetas = [f"M{n} · {m['nombre']}" for n, m in filas]
    fig = go.Figure(go.Bar(
        y=etiquetas,
        x=[_ms(m["ini"], m["fin"]) for _, m in filas],
        base=[datetime.combine(m["ini"], datetime.min.time()) for _, m in filas],
        orientation="h",
        marker=dict(color="#3e63dd"),
        text=[f"{totales(m['items'])['dias']} d" for _, m in filas],
        textposition="inside", insidetextanchor="middle",
        textfont=dict(color="white"),
        customdata=[[fecha_txt(m["ini"]), fecha_txt(m["fin"]),
                     totales(m["items"])["dias"], totales(m["items"])["puntos"],
                     totales(m["items"])["n"]] for _, m in filas],
        hovertemplate=("<b>%{y}</b><br>Inicio: %{customdata[0]}<br>"
                       "Fin: %{customdata[1]}<br>Días est.: %{customdata[2]}<br>"
                       "Pts: %{customdata[3]} · Items: %{customdata[4]}<extra></extra>"),
        showlegend=False,
    ))
    alto = max(260, 46 * len(filas) + 140)
    layout(fig, f"{nombre} — Gantt por milestone", alto, etiquetas)
    linea_hoy(fig)
    archivo = f"gantt_{stem}_resumen.html"
    fig.write_html(carpeta / archivo, include_plotlyjs="directory",
                   full_html=True, config=config)
    salida.append({"archivo": archivo, "titulo": "Gantt por milestone", "alto": alto})

    # ---- Gantt 2: detalle por work item, coloreado por incertidumbre
    etiquetas, ranking = [], []
    for n, m in enumerate(milestones, 1):
        for i in m["items"]:
            if i["ini"]:
                etiq = f"M{n} · {i['nombre']}"
                etiquetas.append(etiq)
                ranking.append((n, etiq, i))

    fig = go.Figure()
    for inc in ["alta", "media", "baja", "—"]:
        sel = [(n, e, i) for n, e, i in ranking if i["inc"] == inc or
               (inc == "—" and i["inc"] not in ORDEN_INC)]
        if not sel:
            continue
        fig.add_trace(go.Bar(
            name=f"incertidumbre {inc}" if inc != "—" else "sin clasificar",
            y=[e for _, e, _ in sel],
            x=[_ms(i["ini"], i["fin"]) for _, _, i in sel],
            base=[datetime.combine(i["ini"], datetime.min.time()) for _, _, i in sel],
            orientation="h",
            marker=dict(color=COLOR_INC[inc], line=dict(color="white", width=1)),
            text=[f"{fmt(i['dias'])} d" for _, _, i in sel],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white"),
            customdata=[[fecha_txt(i["ini"]), fecha_txt(i["fin"]), fmt(i["dias"]),
                         fmt(i["puntos"]), i["tamaño"]] for _, _, i in sel],
            hovertemplate=("<b>%{y}</b><br>Inicio: %{customdata[0]}<br>"
                           "Fin: %{customdata[1]}<br>Días: %{customdata[2]} · "
                           "Pts: %{customdata[3]} · Tamaño: %{customdata[4]}"
                           "<extra></extra>"),
        ))

    # Bandas alternadas para distinguir milestones
    pos, ultima, banda = 0, None, False
    inicios = {}
    for idx, (n, _, _) in enumerate(ranking):
        inicios.setdefault(n, [idx, idx])[1] = idx
    for n, (a, b) in inicios.items():
        if n % 2 == 0:
            fig.add_shape(type="rect", xref="paper", x0=0, x1=1, yref="y",
                          y0=a - 0.5, y1=b + 0.5, fillcolor="#f4f5fb",
                          line_width=0, layer="below")

    alto = max(320, 30 * len(ranking) + 150)
    layout(fig, f"{nombre} — Gantt por work item", alto, [e for _, e, _ in ranking])
    linea_hoy(fig)
    archivo = f"gantt_{stem}_detalle.html"
    fig.write_html(carpeta / archivo, include_plotlyjs="directory",
                   full_html=True, config=config)
    salida.append({"archivo": archivo, "titulo": "Gantt por work item", "alto": alto})

    return salida, None


# --------------------------------------------------------------------------
# Generación del markdown
# --------------------------------------------------------------------------
def generar_md(nombre, milestones, avisos, cron) -> str:
    """
    cron = dict(inicio, fin, modo, gantts, error_gantt)
    """
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

    # ---- 1. Resumen ejecutivo
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
        f"| Inicio planificado | {fecha_txt(cron['inicio'])} |",
        f"| Término estimado ({cron['modo']}) | {fecha_txt(cron['fin'])} |",
        "| % avance global | 0% |",
        "",
    ]

    # ---- 2. Tablero por milestone
    L += ["## 2. Tablero por milestone", ""]
    L += [
        "| # | Milestone | Items | Días | Pts | Inicio | Fin | Sin estimar | Estado | % Avance |",
        "|--:|---|--:|--:|--:|---|---|--:|---|--:|",
    ]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        estado = "⬜ Pendiente" if mt["n"] else "⚪ Sin work items"
        L.append(
            f"| {n} | [{esc(m['nombre'])}](#{n}-{slug(m['nombre'])}) | {mt['n']} | "
            f"{mt['dias']} | {mt['puntos']} | {fecha_txt(m['ini'])} | "
            f"{fecha_txt(m['fin'])} | {mt['sin_est']} | {estado} | 0% |"
        )
    L.append("")

    # ---- 3. Cronograma (Gantt)
    L += ["## 3. Cronograma (Gantt)", ""]
    if cron["gantts"]:
        for g in cron["gantts"]:
            L += [
                f"**{g['titulo']}** · [abrir en pestaña nueva]({g['archivo']})",
                "",
                f'<iframe src="{g["archivo"]}" width="100%" height="{g["alto"] + 10}" '
                f'style="border:0" loading="lazy"></iframe>',
                "",
            ]
    elif cron["error_gantt"]:
        L += [f"_{cron['error_gantt']}_", ""]
    sin_est = [i["nombre"] for i in todos if i["dias"] is None]
    L += [
        "> **Supuestos del cronograma:** "
        f"inicio {fecha_txt(cron['inicio'])}; días hábiles (lun-vie) sin feriados; "
        + ("un solo equipo, todo en secuencia según el orden del YAML."
           if cron["modo"] == "secuencial" else
           "cada milestone parte en la fecha de inicio y sus items van en secuencia.")
        + (f" Sin calendarizar por no tener estimación: {', '.join(sin_est)}."
           if sin_est else ""),
        "",
    ]

    # ---- 4. Detalle
    L += ["## 4. Detalle de work items", ""]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        L += [f"### {n}. {m['nombre']}", ""]
        if not m["items"]:
            L += ["_Sin work items definidos (pendiente de levantamiento)._", ""]
            continue
        L += [
            f"**Total:** {mt['dias']} días · {mt['puntos']} pts · {mt['n']} items",
            "",
            "| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |",
            "|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|",
        ]
        for i in m["items"]:
            estado = "⚠️ Sin estimar" if i["dias"] is None else "⬜ Pendiente"
            L.append(
                f"| {esc(i['nombre'])} | {i['tamaño']} | {fmt(i['dias'])} | "
                f"{fmt(i['puntos'])} | {ICONO_INC.get(i['inc'], i['inc'])} | "
                f"{fecha_txt(i['ini'])} | {fecha_txt(i['fin'])} | "
                f"{estado} |  | 0 |  |"
            )
        L.append("")

    # ---- 5. Riesgos iniciales derivados
    L += ["## 5. Riesgos y alertas iniciales (derivados de la estimación)", ""]
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

    # ---- 6-9. Secciones de gestión vacías
    L += [
        "## 6. Registro de riesgos adicionales",
        "",
        "| ID | Riesgo | Probabilidad | Impacto | Mitigación | Dueño | Estado |",
        "|---|---|---|---|---|---|---|",
        "| R-01 |  |  |  |  |  | ⬜ Abierto |",
        "",
        "## 7. Bloqueos y dependencias",
        "",
        "| Fecha | Descripción | Afecta a | Responsable | Fecha compromiso | Estado |",
        "|---|---|---|---|---|---|",
        "|  |  |  |  |  |  |",
        "",
        "## 8. Decisiones y acuerdos",
        "",
        "| Fecha | Decisión / acuerdo | Participantes |",
        "|---|---|---|",
        "|  |  |  |",
        "",
        "## 9. Control de cambios de alcance",
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


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml", type=Path, help="Archivo YAML de entrada")
    ap.add_argument("-o", "--output", type=Path, help="Archivo .md de salida")
    ap.add_argument("--inicio", type=parse_fecha, metavar="YYYY-MM-DD",
                    help="Fecha de inicio del cronograma "
                         "(por defecto: proyecto.inicio del YAML o hoy)")
    ap.add_argument("--modo", choices=["secuencial", "paralelo"], default="secuencial",
                    help="secuencial: un equipo, todo en fila (defecto). "
                         "paralelo: cada milestone parte en la fecha de inicio")
    ap.add_argument("--sin-gantt", action="store_true",
                    help="No generar los gráficos Gantt")
    args = ap.parse_args()

    # Por defecto el .md se guarda en el directorio de ejecución (cwd)
    salida = args.output or Path.cwd() / f"seguimiento_pmo_{args.yaml.stem}.md"
    salida.parent.mkdir(parents=True, exist_ok=True)

    nombre, milestones, avisos, inicio_yaml = cargar(args.yaml)
    inicio = args.inicio or inicio_yaml or date.today()
    inicio, fin = agendar(milestones, inicio, args.modo)

    gantts, error_gantt = [], None
    if not args.sin_gantt:
        gantts, error_gantt = generar_gantt(
            nombre, milestones, salida.parent, args.yaml.stem, date.today())
        if error_gantt:
            avisos.append(error_gantt)

    cron = {"inicio": inicio, "fin": fin, "modo": args.modo,
            "gantts": gantts, "error_gantt": error_gantt}
    salida.write_text(generar_md(nombre, milestones, avisos, cron), encoding="utf-8")

    for a in avisos:
        print(f"⚠️  {a}", file=sys.stderr)
    print(f"✅ Generado: {salida}")
    for g in gantts:
        print(f"📊 Gantt: {salida.parent / g['archivo']}")


if __name__ == "__main__":
    main()
