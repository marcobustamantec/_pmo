#!/usr/bin/env python3
"""
generar_informe.py — Genera el informe de estado (Marp) a partir de los YAML.

Uso:
    python generar_informe.py                       # lee ./ y escribe ./informe.md
    python generar_informe.py -d datos/ -o out.md   # carpeta de datos y salida
    python generar_informe.py --html                # además exporta con marp-cli (si está instalado)
    python generar_informe.py --tema elige-idiem --css elige-idiem.css --pdf

Archivos esperados en la carpeta:
    01_definicion.yml, 02_reporte_status.yml, 03_milestones.yml, 04_riesgos.yml
    marp.md (opcional: solo se reutiliza su cabecera/front matter)

Requiere: pip install pyyaml
"""
import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML: pip install pyyaml")

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------
SEMAFORO = {
    "verde": "🟢 Normal",
    "amarillo": "🟡 Atención",
    "rojo": "🔴 Crítico",
}
TENDENCIA = {"mejora": "↗ mejora",
             "estable": "→ estable", "empeora": "↘ empeora"}
NIVEL = {
    "critico": "🔴 Crítico",
    "alto": "🟠 Alto",
    "moderado": "🟡 Moderado",
    "bajo": "🟢 Bajo",
}
PROB = {"baja": 1, "media": 2, "alta": 3}
IMPACTO = {"bajo": 1, "medio": 2, "alto": 3}
ESTADO_DEP = {"pendiente": "Pendiente",
              "en_curso": "En curso", "resuelto": "Resuelto"}
ESTADO_DEC = {
    "pendiente": "Pendiente",
    "en_revision": "En revisión",
    "en_curso": "En curso",
    "resuelto": "Resuelto",
    "aprobado": "Aprobado",
}
FILAS_POR_SLIDE = 7

# Tamaño de tarea (talla) -> puntos. Ajustar a la convención del equipo.
# Una tarea puede traer "puntos" explícitos y eso prevalece sobre la talla.
PUNTOS_TAMANO = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}

# Opcional: rol por iniciales para la slide de capacidad. Ej: {"DG": "Senior", "OS": "Dev"}
ROLES = {}

FRONT_MATTER_DEFECTO = """---
marp: true
theme: elige-idiem
paginate: true
size: 16:9
---"""

ESTILO = """<style>
section { font-size: 24px; }
section table { font-size: 0.72em; }
section h1 { font-size: 1.5em; }
section h2 { font-size: 1.3em; }
section h3 { font-size: 1.0em; }
section.portada { text-align: center; justify-content: center; }
section.portada h1 { font-size: 2em; }
</style>"""


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def cargar(path: Path):
    if not path.exists():
        sys.exit(f"No se encontró {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fecha(v) -> str:
    if v in (None, "", "--"):
        return "—"
    if isinstance(v, (dt.date, dt.datetime)):
        return v.strftime("%d-%m-%Y")
    s = str(v)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    return f"{m[3]}-{m[2]}-{m[1]}" if m else s


def txt(v, vacio="—") -> str:
    """Texto seguro para celdas de tabla Markdown."""
    if v is None or str(v).strip() == "":
        return vacio
    return " ".join(str(v).split()).replace("|", "\\|")


def num(v):
    """Convierte a float o None (maneja '--', vacío, etc.)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct(parte, total) -> float:
    return (parte / total * 100) if total else 0.0


def tabla(headers, filas, alinear=None):
    alinear = alinear or ["l"] * len(headers)
    sep = {"l": "---", "r": "---:", "c": ":---:"}
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(sep[a] for a in alinear) + " |"]
    for f in filas:
        out.append("| " + " | ".join(txt(c) for c in f) + " |")
    return "\n".join(out)


def slides_tabla(titulo, subtitulo, headers, filas, alinear=None,
                 extra="", por_slide=FILAS_POR_SLIDE, nivel=2):
    """Genera 1..n slides; si la tabla es larga la parte en '(cont)'."""
    if not filas:
        filas = [["—"] + ["—"] * (len(headers) - 1)]
    bloques = [filas[i:i + por_slide] for i in range(0, len(filas), por_slide)]
    out = []
    for i, bloque in enumerate(bloques):
        t = titulo if i == 0 else f"{titulo} (cont)"
        s = f"{'#' * nivel} {t}\n\n"
        if subtitulo:
            s += f"{'#' * (nivel + 1)} {subtitulo}\n\n"
        s += tabla(headers, bloque, alinear) + "\n"
        if extra and i == len(bloques) - 1:
            s += "\n" + extra + "\n"
        out.append(s)
    return out


# ----------------------------------------------------------------------------
# Cálculos sobre milestones
# ----------------------------------------------------------------------------
def fmt_pts(v) -> str:
    """Puntos sin decimales si son enteros (3.0 -> 3, 2.5 -> 2.5)."""
    return f"{v:.1f}".rstrip("0").rstrip(".") if v else "0"


def normalizar_tarea(t):
    """Convierte una tarea del YAML nuevo a la forma que usa el informe."""
    tam = str(t.get("tamaño", "")).strip().upper()
    puntos = t.get("puntos")
    if puntos is None:
        if tam not in PUNTOS_TAMANO:
            print(
                f"⚠ Tamaño desconocido '{tam}' en tarea '{t.get('wb')}' (se cuenta 0 pts)")
        puntos = PUNTOS_TAMANO.get(tam, 0)
    estado = t.get("estado")
    avance = num(t.get("avance"))
    if estado == "finalizado":
        avance = 1.0
    avance = min(max(avance or 0.0, 0.0), 1.0)
    asignado = t.get("asignado") or []
    if isinstance(asignado, str):
        asignado = [asignado]
    return {
        "nombre": t.get("wb", "—"),
        "detalle": t.get("detalle"),
        "tamano": tam,
        "puntos": puntos,
        "asignado": list(asignado),
        "incertidumbre": t.get("incertidumbre"),
        "estado": estado,
        "avance": avance,
        "inicio": t.get("inicio"),
        "fin": t.get("fin"),
    }


def analizar_milestones(ms_yaml):
    proyecto = ms_yaml.get("proyecto", {})
    hitos = []
    for m in proyecto.get("entregas", []) or []:
        wbs = [normalizar_tarea(t) for t in (m.get("tareas") or [])]
        pts_tot = sum(w["puntos"] for w in wbs)
        # puntos ganados: puntos * avance (una tarea al 50% aporta la mitad)
        pts_ok = sum(w["puntos"] * w["avance"] for w in wbs)
        n_ok = sum(1 for w in wbs if w["estado"] == "finalizado")
        estados = {w["estado"] for w in wbs}
        if wbs and n_ok == len(wbs):
            estado = "Completado"
        elif "wip" in estados or n_ok > 0 or any(w["avance"] > 0 for w in wbs):
            estado = "En curso"
        elif estados == {"pausado"}:
            estado = "Pausado"
        else:
            estado = "Pendiente"
        hitos.append({
            "nombre": m.get("hito", "—"),
            "descripcion": m.get("descripcion"),
            "wbs": wbs,
            "pts_tot": pts_tot,
            "pts_ok": pts_ok,
            "n_tot": len(wbs),
            "n_ok": n_ok,
            "estado": estado,
            "completo": bool(wbs) and n_ok == len(wbs),
        })
    return hitos


def capacidad(hitos):
    """Puntos por persona (iniciales en 'asignado') a partir de las tareas."""
    personas = {}
    for h in hitos:
        for w in h["wbs"]:
            for nombre in w["asignado"]:
                k = (nombre, ROLES.get(nombre, ""))
                d = personas.setdefault(
                    k, {"asig": 0, "ok": 0, "tareas_abiertas": 0})
                d["asig"] += w["puntos"]
                d["ok"] += w["puntos"] * w["avance"]
                if w["estado"] != "finalizado":
                    d["tareas_abiertas"] += 1
    return personas


# ----------------------------------------------------------------------------
# Riesgos
# ----------------------------------------------------------------------------
def nivel_riesgo(item, es_problema=False):
    forzado = str(item.get("nivel", "")).lower().replace("í", "i")
    if forzado in NIVEL:
        return forzado
    imp = IMPACTO.get(str(item.get("impacto", "")).lower(), 1)
    if es_problema:  # ya ocurrió: probabilidad máxima
        score = 3 * imp
    else:
        score = PROB.get(str(item.get("prob", "")).lower(), 1) * imp
    if score >= 9:
        return "critico"
    if score >= 6:
        return "alto"
    if score >= 3:
        return "moderado"
    return "bajo"


# ----------------------------------------------------------------------------
# Construcción del informe
# ----------------------------------------------------------------------------
def construir(d1, d2, d3, d4, front_matter, inyectar_estilo=False):
    hitos = analizar_milestones(d3)
    todos_wb = [w for h in hitos for w in h["wbs"]]
    pts_tot = sum(h["pts_tot"] for h in hitos)
    pts_ok = sum(h["pts_ok"] for h in hitos)
    n_tot, n_ok = len(todos_wb), sum(
        1 for w in todos_wb if w["estado"] == "finalizado")
    hitos_ok = sum(1 for h in hitos if h["completo"])

    # Riesgos / problemas
    riesgos = [r for r in d4.get("riesgos", [])
               or [] if r.get("estado") != "cerrado"]
    riesgos += [r for r in d4.get("emergentes", [])
                or [] if r.get("estado") != "cerrado"]
    problemas = [p for p in d4.get(
        "problemas", []) or [] if p.get("estado") != "cerrado"]
    bloqueos = [p for p in problemas if p.get("estado") == "materializado"]
    for r in riesgos:
        r["_nivel"] = nivel_riesgo(r)
    for p in problemas:
        p["_nivel"] = nivel_riesgo(p, es_problema=True)
    n_criticos = sum(1 for x in riesgos if x["_nivel"] == "critico")

    # Avance
    av = d2.get("avance", {}) or {}
    real = num(av.get("real"))
    if real is None:
        real = pct(pts_ok, pts_tot)
    plan = num(av.get("planificado"))

    # Semáforo
    sem = d2.get("semaforo")
    if sem not in SEMAFORO:
        if plan is not None:
            desv = plan - real
            sem = "verde" if desv <= 5 else "amarillo" if desv <= 15 else "rojo"
        else:
            sem = "amarillo" if bloqueos else "verde"
    tend = TENDENCIA.get(d2.get("tendencia"), "")
    estado_general = SEMAFORO[sem] + (f" ({tend})" if tend else "")

    f = d2.get("fechas", {}) or {}
    periodo = d1.get("periodo", {}) or {}
    celula = d1.get("responsable", "—")

    S = []  # slides

    # --- Portada --------------------------------------------------------
    S.append(
        "<!-- _class: portada -->\n\n"
        f"# {d1.get('nombre', '[Proyecto]')}\n\n"
        f"## Informe de estado y seguimiento\n\n"
        + (f"*{d1['subtitulo']}*\n\n" if d1.get("subtitulo") else "")
        + "**Project Status Report**\n\n"
        f"Período reportado: {fecha(periodo.get('desde'))} – {fecha(periodo.get('hasta'))}\n\n"
        f"Fecha de actualización: {fecha(d1.get('fecha_reporte'))}\n"
    )

    # --- 1. Resumen -----------------------------------------------------
    plan_txt = f"{plan:.0f}%" if plan is not None else "no definido"
    filas = [
        ["Estado general", estado_general],
        ["Fase actual", d2.get("fase")],
        ["Avance real",
            f"{fmt_pts(pts_ok)} : {fmt_pts(pts_tot)} puntos — **{real:.0f}%** (planificado: {plan_txt})"],
        ["Célula", celula],
        ["Cierre de tareas", f"{n_ok} de {n_tot}"],
        ["Cumplimiento de hitos", f"{hitos_ok} de {len(hitos)}"],
        ["Riesgos identificados", f"{len(riesgos)} (críticos: {n_criticos})"],
        ["Bloqueos activos", len(bloqueos)],
    ]
    S.append("## Resumen del proyecto\n\n"
             + tabla(["Dimensión", "Situación"], filas)
             + f"\n\n### Resumen ejecutivo\n\n{txt(d2.get('situacion'), '')}\n")

    desv = d2.get("desviacion", {}) or {}
    s = "## Resumen del proyecto (cont)\n\n"
    s += (f"**Término plan:** {fecha(f.get('termino_plan'))} · "
          f"**Término estimado:** {fecha(f.get('termino_estimado'))}\n\n")
    if desv.get("causa") or desv.get("accion"):
        s += "### Desviación\n\n"
        if desv.get("causa"):
            s += f"- **Causa:** {txt(desv['causa'])}\n"
        if desv.get("accion"):
            s += f"- **Acción:** {txt(desv['accion'])}\n"
        s += "\n"
    if d2.get("avances"):
        s += "### Avances del período\n\n" + \
            "".join(f"- {txt(a)}\n" for a in d2["avances"]) + "\n"
    if d2.get("alertas"):
        s += "### Alertas\n\n" + \
            "".join(f"- {txt(a)}\n" for a in d2["alertas"])
    S.append(s)

    # --- 2. Alcance y objetivos -----------------------------------------
    s = f"## Alcance y objetivos\n\n### Objetivo general\n\n{txt(d1.get('objetivo'), '')}\n\n### Alcance\n\n"
    s += "".join(f"{i}. {txt(a)}\n" for i,
                 a in enumerate(d1.get("alcance", []) or [], 1))
    if d1.get("resultados_esperados"):
        s += "\n### Resultados esperados\n\n" + \
            "".join(f"- {txt(r)}\n" for r in d1["resultados_esperados"])
    if d1.get("cambios_alcance"):
        s += f"\n**Cambios de alcance:** {txt(d1['cambios_alcance'])}\n"
    S.append(s)

    # --- 3. Fases / hitos -----------------------------------------------
    filas = [[h["nombre"], h["descripcion"], fmt_pts(h["pts_ok"]), fmt_pts(h["pts_tot"]),
              f"{pct(h['pts_ok'], h['pts_tot']):.0f}%"] for h in hitos]
    filas.append([f"**Total**", "", f"**{fmt_pts(pts_ok)}**",
                 f"**{fmt_pts(pts_tot)}**", f"**{pct(pts_ok, pts_tot):.0f}%**"])
    S += slides_tabla(
        "Fases del proyecto", "Avance por hitos",
        ["Componente / Entregable", "Descripción",
            "Puntos cerrados", "Puntos totales", "Avance"],
        filas, ["l", "l", "r", "r", "r"], por_slide=8,
    )

    # --- 4. Riesgos y problemas -----------------------------------------
    def prob_txt(r):
        return str(r.get("prob", "—")).capitalize()

    filas = [[r["id"], r["titulo"], prob_txt(r), str(r.get("impacto", "—")).capitalize(),
              NIVEL[r["_nivel"]]] for r in riesgos]
    filas += [[p["id"], p["titulo"], "—", str(p.get("impacto", "—")).capitalize(),
               NIVEL[p["_nivel"]]] for p in problemas]
    S += slides_tabla(
        "Riesgos y problemas",
        "Situaciones que pueden afectar o están afectando el proyecto",
        ["ID", "Riesgo / Problema", "Probabilidad", "Impacto", "Nivel"], filas,
    )

    filas = [[x["id"], x.get("accion"), x.get("resp"), fecha(x.get("fecha"))]
             for x in riesgos + problemas]
    S += slides_tabla(
        "Riesgos y problemas (cont)", "Plan de respuesta",
        ["ID", "Acción preventiva / correctiva", "Responsable", "Fecha"], filas,
    )

    filas = [[x["id"], x.get("contingencia")]
             for x in riesgos if x.get("contingencia")]
    if filas:
        S += slides_tabla("Riesgos y problemas (cont)", "Planes de contingencia",
                          ["ID", "Contingencia si el riesgo se materializa"], filas)

    # --- 5. Decisiones --------------------------------------------------
    filas = [[x.get("decision"), x.get("quien"), fecha(x.get("fecha")),
              ESTADO_DEC.get(x.get("estado"), txt(x.get("estado")).capitalize())]
             for x in d2.get("decisiones", []) or []]
    S += slides_tabla(
        "Decisiones y acuerdos",
        "Definiciones necesarias para mantener la ejecución del proyecto",
        ["Decisión / Acuerdo", "Responsable de decidir",
            "Fecha requerida", "Estado"], filas,
    )

    # --- 6. Capacidad ---------------------------------------------------
    pers = capacidad(hitos)
    pend_total = sum(v["asig"] - v["ok"] for v in pers.values()) or 1
    filas = []
    ordenadas = sorted(pers.items(), key=lambda kv: -
                       (kv[1]["asig"] - kv[1]["ok"]))
    for (nombre, rol), v in ordenadas:
        pend = v["asig"] - v["ok"]
        share = pct(pend, pend_total)
        obs = f"Concentra {share:.0f}% de los puntos pendientes" if share >= 35 else (
            "Sin carga pendiente" if pend == 0 else "")
        filas.append([f"{nombre} ({rol})" if rol else nombre, fmt_pts(v["asig"]),
                      fmt_pts(v["ok"]), fmt_pts(pend), v["tareas_abiertas"], obs])
    extra = ""
    if d2.get("alertas_capacidad"):
        extra += "".join(f"- ⚠ {txt(a)}\n" for a in d2["alertas_capacidad"])
    if d2.get("impacto_capacidad"):
        extra += f"\n**Impacto:** {txt(d2['impacto_capacidad'])}\n"
    extra += ("\n<small>Los puntos de una tarea con más de un desarrollador se cuentan completos "
              "para cada uno.</small>")
    S += slides_tabla(
        "Capacidad", "Puntos asignados por desarrollador",
        ["Recurso / Perfil", "Puntos asignados", "Cerrados",
            "Pendientes", "Tareas abiertas", "Observación"],
        filas, ["l", "r", "r", "r", "r", "l"], extra=extra, por_slide=9,
    )

    # --- 7. Dependencias y bloqueos -------------------------------------
    filas = [[x.get("dep"), x.get("contraparte"), x.get("req"), fecha(x.get("fecha")),
              ESTADO_DEP.get(x.get("estado"), txt(x.get("estado")).capitalize())]
             for x in d2.get("dependencias", []) or []]
    bl = "### Bloqueos actuales\n\n"
    if bloqueos:
        for b in bloqueos:
            bl += (f"- **Bloqueo:** {txt(b['titulo'])}.\n"
                   f"  - **Impacto:** {txt(b.get('efecto'))}.\n"
                   f"  - **Responsable de resolver:** {txt(b.get('resp'))}.\n"
                   f"  - **Fecha comprometida:** {fecha(b.get('fecha'))}.\n")
    else:
        bl += "Sin bloqueos activos.\n"
    if d2.get("apoyo"):
        bl += f"\n**Apoyo requerido:** {txt(d2['apoyo'])}\n"
    S += slides_tabla(
        "Dependencias y bloqueos",
        "Condiciones externas necesarias para continuar la ejecución",
        ["Dependencia", "Contraparte", "Requerimiento", "Fecha requerida", "Estado"],
        filas, extra=bl, por_slide=4,
    )

    # --- 8. Plan de trabajo pendiente -----------------------------------
    PRIORIDAD = {"En curso": "Alta", "Pendiente": "Media", "Pausado": "Baja"}
    filas = []
    for h in hitos:
        if h["completo"]:
            continue
        abiertos = [w for w in h["wbs"] if w["estado"] != "finalizado"]
        resp = sorted({p for w in abiertos for p in w["asignado"]})
        pend = h["pts_tot"] - h["pts_ok"]
        # inicio / fin: opcionales en el YAML (campos 'inicio' y 'fin' del WB)
        ini = [w["inicio"] for w in abiertos if w["inicio"]]
        fin = [w["fin"] for w in abiertos if w["fin"]]
        filas.append([f"{h['nombre']} ({fmt_pts(pend)} pts)", ", ".join(resp),
                      fecha(min(ini)) if ini else "Por definir",
                      fecha(max(fin)) if fin else "Por definir",
                      PRIORIDAD.get(h["estado"], "Media"), h["estado"]])
    sh = d2.get("siguiente_hito", {}) or {}
    extra = ""
    if sh:
        resp_h = sh.get("responsable") or celula
        extra = (f"**Siguiente hito:** {txt(sh.get('nombre'))} — {fecha(sh.get('fecha'))} "
                 f"(resp.: {txt(resp_h)}). Criterio: {txt(sh.get('criterio'))}.")
    S += slides_tabla(
        "Plan de trabajo pendiente",
        "Actividades necesarias para completar el proyecto",
        ["Actividad", "Responsable", "Inicio", "Término", "Prioridad", "Estado"],
        filas, extra=extra, por_slide=9,
    )

    # --- 9. Próximos pasos ----------------------------------------------
    pasos = d2.get("proximos_pasos", []) or []
    filas = [[i, x.get("accion"), x.get("resp"), fecha(x.get("fecha")), x.get("resultado")]
             for i, x in enumerate(pasos, 1)]
    foco = d2.get("foco") or [x.get("accion") for x in pasos[:3]]
    extra = "### Foco del siguiente período\n\n" + "".join(
        f"{i}. {txt(x)}.\n" for i, x in enumerate(foco, 1))
    S += slides_tabla(
        "Próximos pasos", "Compromisos concretos para el siguiente período",
        ["N°", "Acción", "Responsable", "Fecha compromiso", "Resultado esperado"],
        filas, extra=extra, por_slide=5,
    )

    if d2.get("conclusion"):
        S.append(f"## Conclusión\n\n{txt(d2['conclusion'], '')}\n")

    estilo = ESTILO + "\n\n" if inyectar_estilo else ""
    return front_matter + "\n\n" + estilo + "\n---\n\n".join(S)


def fijar_tema(front_matter: str, tema: str) -> str:
    """Reemplaza (o agrega) la línea 'theme:' del front matter."""
    if re.search(r"^theme:.*$", front_matter, re.M):
        return re.sub(r"^theme:.*$", f"theme: {tema}", front_matter, flags=re.M)
    return front_matter.replace("marp: true", f"marp: true\ntheme: {tema}", 1)


def tema_de(front_matter: str) -> str:
    m = re.search(r"^theme:\s*(\S+)", front_matter, re.M)
    return m.group(1) if m else "default"


def fijar_footer_fecha(front_matter: str, f) -> str:
    """Actualiza la fecha (dd.mmm.aaaa) del footer con fecha_reporte."""
    meses = "ene feb mar abr may jun jul ago sep oct nov dic".split()
    if isinstance(f, str):
        try:
            f = dt.date.fromisoformat(f)
        except ValueError:
            return front_matter
    if not isinstance(f, (dt.date, dt.datetime)):
        return front_matter
    nueva = f"{f.day:02d}.{meses[f.month - 1]}.{f.year}"
    return re.sub(r"(?m)^(footer:.*?)\d{2}\.[a-z]{3}\.\d{4}", lambda m: m[1] + nueva, front_matter)


def leer_front_matter(path: Path) -> str:
    if path.exists():
        m = re.match(r"\A---\n.*?\n---",
                     path.read_text(encoding="utf-8"), re.S)
        if m:
            return m.group(0)
    return FRONT_MATTER_DEFECTO


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Genera el informe Marp desde los YAML.")
    ap.add_argument("-d", "--dir", default=".",
                    help="Carpeta con los YAML (default: .)")
    ap.add_argument("-o", "--salida", default="informe.md",
                    help="Archivo Markdown de salida")
    ap.add_argument(
        "--tema", help="Nombre del tema Marp (ej: elige-idiem); pisa el de marp.md")
    ap.add_argument("--css", help="Archivo .css (o carpeta) del tema, para marp --theme-set. "
                                  "Si se omite, se busca un .css junto a los YAML o en ./themes")
    ap.add_argument("--ajustar-fuente", action="store_true",
                    help="Inyectar tamaños de fuente propios (por defecto solo con theme: default)")
    ap.add_argument("--html", action="store_true",
                    help="Exportar también a HTML con marp-cli")
    ap.add_argument("--pdf", action="store_true",
                    help="Exportar también a PDF con marp-cli")
    a = ap.parse_args()

    base = Path(a.dir)
    fm = leer_front_matter(base / "marp.md")
    if a.tema:
        fm = fijar_tema(fm, a.tema)
    inyectar = a.ajustar_fuente

    css = Path(a.css) if a.css else None
    if css is None:
        for cand in (sorted(base.glob("*.css")), sorted((base / "themes").glob("*.css"))):
            if cand:
                css = cand[0] if len(cand) == 1 else cand[0].parent
                break

    d1 = cargar(base / "01_definicion.yml")
    fm = fijar_footer_fecha(fm, d1.get("fecha_reporte"))
    md = construir(
        d1,
        cargar(base / "02_reporte_status.yml"),
        cargar(base / "03_milestones.yml"),
        cargar(base / "04_riesgos.yml"),
        fm,
        inyectar_estilo=inyectar,
    )
    out = Path(a.salida)
    out.write_text(md, encoding="utf-8")
    print(f"✔ Informe generado: {out}")

    for flag, ext in ((a.html, "--html"), (a.pdf, "--pdf")):
        if flag:
            exe = shutil.which("marp")
            if not exe:
                print("⚠ marp-cli no está instalado (npm i -g @marp-team/marp-cli)")
                break
            cmd = [exe, str(out), ext, "--allow-local-files"]
            if css:
                cmd += ["--theme-set", str(css)]
            print("→", " ".join(cmd))
            subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
