#!/usr/bin/env python3
"""
Genera un .md de seguimiento PMO de portafolio (varios YAML de proyectos),
con recursos compartidos, disponibilidad individual y ausencias.

El .md y los HTML de los Gantt se guardan en el directorio desde donde se
ejecuta el script (no en el del YAML), salvo que uses -o.

Uso:
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --inicio 2026-12-01
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --modo prioridad
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --modo secuencial
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml -o otra/ruta/seguimiento.md
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --sin-gantt

Requiere: pip install pyyaml plotly
"""
import argparse
import math
import random
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Falta PyYAML: pip install pyyaml")

CAMPOS = {"nombre", "tamaño", "dias", "puntos", "incertidumbre",
          "junior", "senior", "dedicacion_sr", "estado", "avance"}
ORDEN_INC = {"alta": 0, "media": 1, "baja": 2}
ICONO_INC = {"alta": "🔴 alta", "media": "🟡 media", "baja": "🟢 baja"}
COLOR_INC = {"alta": "#e5484d", "media": "#f5a524", "baja": "#30a46c", "—": "#8b8d98"}
# estado (YAML) -> etiqueta en el informe
ESTADOS_MAP = {
    "backlog": "⬜ Pendiente",
    "wip": "🔵 En curso",
    "finalizado": "✅ Listo",
    "pausado": "⏸️ Pausado",
}
ESTADOS = " | ".join(ESTADOS_MAP.values())

DESC_MODO = {
    "optimizado": ("por desarrollador: cada junior hace una tarea a la vez, ninguna "
                   "senior supera el 100% de carga (suma de dedicacion_sr de sus "
                   "tareas simultáneas) y el orden se optimiza para terminar lo antes "
                   "posible."),
    "prioridad": ("por desarrollador (cada junior una tarea a la vez, senior ≤ 100%), "
                  "respetando el orden de milestones del YAML."),
    "secuencial": "un solo equipo, todo en secuencia según el orden del YAML.",
    "paralelo": "cada milestone parte en la fecha de inicio y sus items van en secuencia.",
}
PALETA = ["#3e63dd", "#e5484d", "#30a46c", "#f5a524", "#6e56cf",
          "#0090ff", "#d6409f", "#12a594", "#ab6400", "#8b8d98"]
EPS = 1e-9


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
    nombre = str(item.get("nombre", "(sin nombre)")).strip()
    desconocidas = [k for k in item if k not in CAMPOS]
    for k in desconocidas:
        aviso.append(f"'{nombre}': campo desconocido '{k}' ignorado.")

    # ---- responsables
    ded_sr = num(item.get("dedicacion_sr"))
    senior_raw = item.get("senior")
    if isinstance(senior_raw, (int, float)) and not isinstance(senior_raw, bool):
        # Formato antiguo: senior: 0.2 era una dedicación, no una persona
        if ded_sr is None:
            ded_sr = senior_raw
        aviso.append(f"'{nombre}': 'senior' trae un número ({senior_raw}); "
                     f"se tomó como dedicacion_sr y queda sin senior asignado.")
        senior_raw = None
    jr = _personas(item.get("junior"), nombre, "junior", aviso)
    sr = _personas(senior_raw, nombre, "senior", aviso)
    if sr and ded_sr is None:
        aviso.append(f"'{nombre}': tiene senior pero no dedicacion_sr; "
                     f"no se contabiliza su carga.")

    # ---- estado y avance
    est = str(item.get("estado") or "").strip().lower()
    if not est:
        aviso.append(f"'{nombre}': sin 'estado'; se asumió backlog.")
        est = "backlog"
    elif est not in ESTADOS_MAP:
        aviso.append(f"'{nombre}': estado '{est}' no reconocido "
                     f"({', '.join(ESTADOS_MAP)}); se asumió backlog.")
        est = "backlog"
    avance = num(item.get("avance"))
    if avance is None:
        avance = 1.0 if est == "finalizado" else 0.0
    avance = min(max(float(avance), 0.0), 1.0)
    if est == "finalizado" and avance < 1:
        aviso.append(f"'{nombre}': finalizado pero avance {avance:.0%}.")
    if est == "backlog" and avance > 0:
        aviso.append(f"'{nombre}': en backlog pero con avance {avance:.0%}.")
    if est in ("wip", "pausado") and avance >= 1:
        aviso.append(f"'{nombre}': estado {est} pero avance 100%.")

    return {
        "nombre": nombre,
        "tamaño": str(item.get("tamaño") or "—").strip(),
        "dias": num(item.get("dias")),
        "puntos": num(item.get("puntos")),
        "inc": str(item.get("incertidumbre") or "—").strip().lower(),
        "jr": jr,
        "sr": sr,
        "ded_sr": ded_sr,
        "estado": est,
        "avance": avance,
        "ini": None,   # se completan en agendar()
        "fin": None,
        "rest": None,  # días hábiles pendientes calendarizados
    }


def _personas(v, nombre, campo, aviso) -> list:
    """junior/senior pueden venir vacíos, como texto o como lista."""
    if v is None:
        return []
    out = []
    for p in (v if isinstance(v, list) else [v]):
        if p is None:
            continue
        if isinstance(p, (int, float)) and not isinstance(p, bool):
            aviso.append(f"'{nombre}': {campo} = {p} no es una persona; se ignoró.")
            continue
        out.append(str(p).strip())
    return out


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
        milestones.append({
            "nombre": m["nombre"],
            "proyecto": proyecto.get("nombre", path.stem),
            "items": items
        })
    return (
        proyecto.get("nombre", "Proyecto"),
        milestones,
        avisos,
        parse_fecha(proyecto.get("inicio")),   # campo opcional proyecto.inicio
    )



def cargar_recursos(path: Path | None):
    """
    Lee el catálogo transversal de funcionarios.
    disponibilidad: fracción de jornada disponible para el portafolio (0..1).
    ausencias: intervalos inclusivos que bloquean completamente al funcionario.
    """
    if path is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    funcionarios = data.get("funcionarios") or {}
    recursos = {}
    for codigo, cfg in funcionarios.items():
        cfg = cfg or {}
        disponibilidad = float(cfg.get("disponibilidad", 1.0))
        if not 0 <= disponibilidad <= 1:
            raise ValueError(
                f"Disponibilidad de {codigo} debe estar entre 0 y 1; "
                f"se recibió {disponibilidad}."
            )
        ausencias = []
        for a in cfg.get("ausencias") or []:
            desde, hasta = parse_fecha(a["desde"]), parse_fecha(a["hasta"])
            if hasta < desde:
                raise ValueError(f"Ausencia de {codigo}: 'hasta' anterior a 'desde'.")
            ausencias.append((desde, hasta))
        recursos[str(codigo)] = {
            "disponibilidad": disponibilidad,
            "ausencias": ausencias,
            "nombre": cfg.get("nombre", str(codigo)),
            "rol": cfg.get("rol", ""),
        }
    return recursos


def disponibilidad_persona(persona, dia, recursos):
    """Capacidad efectiva del funcionario en una fecha determinada."""
    cfg = recursos.get(persona, {})
    if any(desde <= dia <= hasta for desde, hasta in cfg.get("ausencias", [])):
        return 0.0
    return cfg.get("disponibilidad", 1.0)


def _capacidad_persona(persona, indice, fechas, recursos):
    if indice >= len(fechas):
        return recursos.get(persona, {}).get("disponibilidad", 1.0)
    return disponibilidad_persona(persona, fechas[indice], recursos)


def totales(items):
    dias = sum(i["dias"] or 0 for i in items)
    hechos = sum((i["dias"] or 0) * i["avance"] for i in items)
    return {
        "n": len(items),
        "dias": dias,
        "dias_rest": round(dias - hechos, 1),
        "avance": (hechos / dias) if dias else 0.0,   # ponderado por días
        "puntos": sum(i["puntos"] or 0 for i in items),
        "sin_est": sum(1 for i in items if i["dias"] is None),
        "por_estado": Counter(i["estado"] for i in items),
    }


def estado_milestone(items) -> str:
    if not items:
        return "⚪ Sin work items"
    es = {i["estado"] for i in items}
    if es == {"finalizado"}:
        return ESTADOS_MAP["finalizado"]
    if "wip" in es or any(i["avance"] > 0 for i in items):
        return ESTADOS_MAP["wip"]
    if "pausado" in es:
        return ESTADOS_MAP["pausado"]
    return ESTADOS_MAP["backlog"]


def responsables_txt(i) -> str:
    partes = []
    if i["jr"]:
        partes.append("Jr: " + ", ".join(i["jr"]))
    if i["sr"]:
        ded = f" ({i['ded_sr']:.0%})" if i["ded_sr"] is not None else ""
        partes.append("Sr: " + ", ".join(i["sr"]) + ded)
    return " · ".join(partes) or "—"


def carga_por_persona(milestones):
    """
    Días-persona pendientes por responsable (items no finalizados).
    Supuestos: cada junior asignado dedica los días pendientes completos del
    item; el senior aporta días_pendientes × dedicacion_sr.
    """
    c = {}
    def reg(persona, rol, dias, item):
        e = c.setdefault((persona, rol), {"dias": 0.0, "items": 0})
        e["dias"] += dias
        e["items"] += 1
    for m in milestones:
        for i in m["items"]:
            if i["estado"] == "finalizado" or i["dias"] is None:
                continue
            rest = i["dias"] * (1 - i["avance"])
            for p in i["jr"]:
                reg(p, "Junior", rest, i)
            if i["ded_sr"] is not None:
                for p in i["sr"]:
                    reg(p, "Senior", rest * i["ded_sr"] / len(i["sr"]), i)
            else:
                for p in i["sr"]:
                    reg(p, "Senior", 0.0, i)
    return sorted(((p, r, e["items"], e["dias"]) for (p, r), e in c.items()),
                  key=lambda x: (-x[3], x[0]))


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


def agendar_simple(milestones, inicio: date, modo: str):
    """
    Asigna ini/fin a cada work item estimado y no finalizado, usando solo
    los días pendientes: ceil(dias × (1 − avance)).
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
            if i["dias"] is None or i["estado"] == "finalizado":
                continue
            rest = math.ceil(i["dias"] * (1 - i["avance"]))
            if rest <= 0:
                continue
            i["rest"] = rest
            i["ini"] = cursor
            i["fin"] = sumar_habiles(cursor, rest)
            cursor = i["fin"]
        agendados = [i for i in m["items"] if i["ini"]]
        m["ini"] = min((i["ini"] for i in agendados), default=None)
        m["fin"] = max((i["fin"] for i in agendados), default=None)
    fines = [m["fin"] for m in milestones if m["fin"]]
    return base, (max(fines) if fines else None)


def _calendario(base: date, n: int) -> list:
    """Lista de n+1 días hábiles consecutivos desde base (índice 0 = base)."""
    fechas = [base]
    while len(fechas) < n + 1:
        d = fechas[-1] + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        fechas.append(d)
    return fechas


def _tareas(milestones, avisos, recursos=None):
    """Work items pendientes; ajusta duración de juniors según disponibilidad."""
    recursos = recursos or {}
    tareas = []
    for mi, m in enumerate(milestones):
        for i in m["items"]:
            if i["dias"] is None or i["estado"] == "finalizado":
                continue
            dur_base = math.ceil(i["dias"] * (1 - i["avance"]))
            if dur_base <= 0:
                continue

            jr = list(dict.fromkeys(i["jr"]))
            sr = {}
            if i["sr"] and i["ded_sr"]:
                ded = i["ded_sr"]
                if ded > 1:
                    avisos.append(f"'{i['nombre']}': dedicacion_sr {ded} > 1; se limitó a 1 (100%).")
                    ded = 1.0
                sr = {p: ded / len(i["sr"]) for p in i["sr"]}

            # Un junior sigue dedicado a una tarea a la vez. Si su disponibilidad
            # general es parcial, el esfuerzo calendario se alarga proporcionalmente.
            factor = 1.0
            jr_load = {}
            for p in jr:
                disp = recursos.get(p, {}).get("disponibilidad", 1.0)
                if disp <= 0:
                    raise ValueError(
                        f"'{i['nombre']}' está asignado a {p}, cuya disponibilidad "
                        "base es 0%. Corrige el recurso o la asignación."
                    )
                factor = max(factor, 1.0 / disp)
                jr_load[p] = disp

            dur = math.ceil(dur_base * factor) if math.isfinite(factor) else dur_base
            tareas.append({
                "item": i, "mi": mi, "idx": len(tareas), "dur": dur,
                "dur_base": dur_base, "jr": jr, "jr_load": jr_load, "sr": sr
            })
    return tareas


def _programar(tareas, orden, fechas, recursos):
    """
    Generación serial de cronograma con capacidad diaria por funcionario.
    Juniors: una tarea a la vez; disponibilidad parcial alarga su duración.
    Seniors: su dedicación simultánea no puede superar su disponibilidad diaria.
    Ausencias: capacidad cero durante todo el intervalo.
    """
    uso = {}
    inicios, fin_ms = {}, {}
    for t in orden:
        s = 0
        while True:
            choque = None
            for d in range(s, s + t["dur"]):
                dia = fechas[d] if d < len(fechas) else fechas[-1] + timedelta(days=1)
                for p in t["jr"]:
                    demanda = t["jr_load"].get(p, 0.0)
                    capacidad = disponibilidad_persona(p, dia, recursos)
                    if capacidad <= 0 or uso.get(("J", p, d), 0.0) + demanda > capacidad + EPS:
                        choque = d
                        break
                if choque is not None:
                    break
                for p, demanda in t["sr"].items():
                    capacidad = disponibilidad_persona(p, dia, recursos)
                    capacidad_base = recursos.get(p, {}).get("disponibilidad", 1.0)
                    if demanda > capacidad_base + EPS:
                        raise ValueError(
                            f"El work item '{t['item']['nombre']}' requiere "
                            f"{demanda:.0%} de {p}, pero su disponibilidad base es "
                            f"{capacidad_base:.0%}. Ajusta dedicacion_sr o la disponibilidad."
                        )
                    if capacidad <= 0 or uso.get(("S", p, d), 0.0) + demanda > capacidad + EPS:
                        choque = d
                        break
                if choque is not None:
                    break
            if choque is None:
                break
            s = choque + 1

        for d in range(s, s + t["dur"]):
            for p in t["jr"]:
                demanda = t["jr_load"].get(p, 0.0)
                uso[("J", p, d)] = uso.get(("J", p, d), 0.0) + demanda
            for p, demanda in t["sr"].items():
                uso[("S", p, d)] = uso.get(("S", p, d), 0.0) + demanda
        inicios[t["idx"]] = s
        fin_ms[t["mi"]] = max(fin_ms.get(t["mi"], 0), s + t["dur"])

    makespan = max((inicios[t["idx"]] + t["dur"] for t in tareas), default=0)
    return {
        "inicios": inicios, "uso": uso, "makespan": makespan,
        "score": (makespan, sum(fin_ms.values()))
    }


def agendar_recursos(milestones, inicio: date, modo: str, avisos: list, recursos=None):
    """Planifica conjuntamente todos los proyectos con disponibilidad compartida."""
    recursos = recursos or {}
    base = proximo_habil(inicio)
    tareas = _tareas(milestones, avisos, recursos)
    for m in milestones:
        m["ini"] = m["fin"] = None
    if not tareas:
        return base, None, None

    # Horizonte de fechas suficientemente amplio para absorber ausencias.
    dur_total = sum(t["dur"] for t in tareas)
    fechas = _calendario(base, max(dur_total * 3 + 30, 365))

    def en_curso(t):
        return t["item"]["estado"] != "wip"

    base_orden = sorted(tareas, key=lambda t: (en_curso(t), t["idx"]))
    res0 = _programar(tareas, base_orden, fechas, recursos)
    mejor, ensayos = res0, 1

    if modo == "optimizado":
        carga_j = Counter()
        for t in tareas:
            for p in t["jr"]:
                carga_j[p] += t["dur"]
        candidatos = [
            sorted(tareas, key=lambda t: (en_curso(t),
                   -max([carga_j[p] for p in t["jr"]] or [0]), -t["dur"], t["idx"])),
            sorted(tareas, key=lambda t: (en_curso(t), -t["dur"], t["idx"])),
        ]
        rng = random.Random(7)
        for _ in range(600):
            spread = rng.choice([3, 8, 20, 60])
            candidatos.append(sorted(
                tareas, key=lambda t: (en_curso(t), t["idx"] + rng.uniform(0, spread))))
        for orden in candidatos:
            r = _programar(tareas, orden, fechas, recursos)
            ensayos += 1
            if r["score"] < mejor["score"]:
                mejor = r

    # Asegurar calendario real hasta el último día programado.
    fechas = _calendario(base, mejor["makespan"])
    for t in tareas:
        i, s = t["item"], mejor["inicios"][t["idx"]]
        i["rest"] = t["dur"]
        i["ini"] = fechas[s]
        i["fin"] = fechas[s + t["dur"]]
        i["dias_calendario"] = t["dur"]

    for m in milestones:
        ag = [i for i in m["items"] if i["ini"]]
        m["ini"] = min((i["ini"] for i in ag), default=None)
        m["fin"] = max((i["fin"] for i in ag), default=None)

    seniors = sorted({p for t in tareas for p in t["sr"]})
    juniors = sorted({p for t in tareas for p in t["jr"]})
    carga_sr = {p: [round(mejor["uso"].get(("S", p, d), 0.0), 4)
                    for d in range(mejor["makespan"])] for p in seniors}
    carga_jr = {p: [round(mejor["uso"].get(("J", p, d), 0.0), 4)
                    for d in range(mejor["makespan"])] for p in juniors}
    carga_j = Counter()
    for t in tareas:
        for p in t["jr"]:
            carga_j[p] += t["dur"]
    cuello = carga_j.most_common(1)[0] if carga_j else None
    plan = {
        "fechas": fechas, "makespan": mejor["makespan"], "cuello": cuello,
        "fin_prioridad": fechas[res0["makespan"]],
        "carga_sr": carga_sr, "carga_jr": carga_jr, "ensayos": ensayos,
        "recursos": recursos
    }
    return base, fechas[mejor["makespan"]], plan


def agendar(milestones, inicio: date, modo: str, avisos: list, recursos=None):
    """Devuelve (inicio, fin, plan)."""
    if modo in ("secuencial", "paralelo"):
        base, fin = agendar_simple(milestones, inicio, modo)
        if recursos:
            avisos.append("El modo secuencial/paralelo no aplica disponibilidad individual; usa optimizado o prioridad.")
        return base, fin, None
    return agendar_recursos(milestones, inicio, modo, avisos, recursos)


# --------------------------------------------------------------------------
# Gantt con Plotly
# --------------------------------------------------------------------------
def _ms(d1: date, d2: date) -> float:
    return (d2 - d1).days * 86_400_000


def generar_gantt(nombre, milestones, carpeta: Path, stem: str, hoy: date,
                  plan=None):
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
    etiquetas = [f"{m.get('proyecto', nombre)} · M{n} · {m['nombre']}" for n, m in filas]
    fig = go.Figure(go.Bar(
        y=etiquetas,
        x=[_ms(m["ini"], m["fin"]) for _, m in filas],
        base=[datetime.combine(m["ini"], datetime.min.time()) for _, m in filas],
        orientation="h",
        marker=dict(color="#3e63dd"),
        text=[f"{totales(m['items'])['dias_rest']:g} d" for _, m in filas],
        textposition="inside", insidetextanchor="middle",
        textfont=dict(color="white"),
        customdata=[[fecha_txt(m["ini"]), fecha_txt(m["fin"]),
                     totales(m["items"])["dias_rest"], totales(m["items"])["puntos"],
                     totales(m["items"])["n"]] for _, m in filas],
        hovertemplate=("<b>%{y}</b><br>Inicio: %{customdata[0]}<br>"
                       "Fin: %{customdata[1]}<br>Días pendientes: %{customdata[2]}<br>"
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
                etiq = f"{m.get('proyecto', nombre)} · M{n} · {i['nombre']}"
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
            text=[f"{i['rest']} d" for _, _, i in sel],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white"),
            customdata=[[fecha_txt(i["ini"]), fecha_txt(i["fin"]),
                         f"{i['rest']} de {fmt(i['dias'])}",
                         fmt(i["puntos"]), i["tamaño"],
                         responsables_txt(i)] for _, _, i in sel],
            hovertemplate=("<b>%{y}</b><br>Inicio: %{customdata[0]}<br>"
                           "Fin: %{customdata[1]}<br>Días pend.: %{customdata[2]} · "
                           "Pts: %{customdata[3]} · Tamaño: %{customdata[4]}<br>"
                           "%{customdata[5]}<extra></extra>"),
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

    # ---- Gantt 3: por desarrollador (una fila por junior)
    filas_dev = {}
    for n, m in enumerate(milestones, 1):
        for i in m["items"]:
            if not i["ini"]:
                continue
            for p in (i["jr"] or ["__solo_sr__"]):
                filas_dev.setdefault(p, []).append((n, i))
    # Items sin junior: se reparten en carriles para que no se pisen
    if "__solo_sr__" in filas_dev:
        carriles = []   # fin del último item de cada carril
        for n, i in sorted(filas_dev.pop("__solo_sr__"), key=lambda x: x[1]["ini"]):
            for k, fin_c in enumerate(carriles):
                if fin_c <= i["ini"]:
                    carriles[k] = i["fin"]
                    break
            else:
                carriles.append(i["fin"])
                k = len(carriles) - 1
            filas_dev.setdefault(f"Solo senior · carril {k + 1}", []).append((n, i))
    juniors = sorted(p for p in filas_dev if not p.startswith("Solo senior"))
    orden_filas = juniors + sorted(p for p in filas_dev if p.startswith("Solo senior"))

    fig = go.Figure()
    for n, m in enumerate(milestones, 1):
        sel = [(p, i) for p in orden_filas for (nn, i) in filas_dev[p] if nn == n]
        if not sel:
            continue
        fig.add_trace(go.Bar(
            name=f"M{n} · {m['nombre']}",
            y=[p for p, _ in sel],
            x=[_ms(i["ini"], i["fin"]) for _, i in sel],
            base=[datetime.combine(i["ini"], datetime.min.time()) for _, i in sel],
            orientation="h",
            marker=dict(color=PALETA[(n - 1) % len(PALETA)],
                        line=dict(color="white", width=1.5)),
            text=[i["nombre"][:38] + ("…" if len(i["nombre"]) > 38 else "")
                  for _, i in sel],
            textposition="inside", insidetextanchor="start",
            textfont=dict(color="white", size=10),
            customdata=[[i["nombre"], fecha_txt(i["ini"]), fecha_txt(i["fin"]),
                         f"{i['rest']} de {fmt(i['dias'])}",
                         ICONO_INC.get(i["inc"], i["inc"]),
                         responsables_txt(i)] for _, i in sel],
            hovertemplate=("<b>%{customdata[0]}</b><br>Inicio: %{customdata[1]}<br>"
                           "Fin: %{customdata[2]}<br>Días pend.: %{customdata[3]}<br>"
                           "Incertidumbre: %{customdata[4]}<br>%{customdata[5]}"
                           "<extra></extra>"),
        ))
    alto = max(300, 62 * len(orden_filas) + 170)
    layout(fig, f"{nombre} — Gantt por desarrollador", alto, orden_filas)
    fig.update_layout(legend=dict(orientation="h", y=-0.08, x=0, xanchor="left"),
                      margin=dict(l=10, r=20, t=70, b=90))
    fig.update_yaxes(categoryarray=orden_filas)
    linea_hoy(fig)
    archivo = f"gantt_{stem}_desarrolladores.html"
    fig.write_html(carpeta / archivo, include_plotlyjs="directory",
                   full_html=True, config=config)
    salida.append({"archivo": archivo, "titulo": "Gantt por desarrollador",
                   "alto": alto})

    # ---- Gantt 4: carga de cada senior en el tiempo (límite 100%)
    if plan and plan.get("carga_sr"):
        fechas, ms = plan["fechas"], plan["makespan"]
        fig = go.Figure()
        for k, (p, carga) in enumerate(sorted(plan["carga_sr"].items())):
            xs = [datetime.combine(d, datetime.min.time()) for d in fechas[:ms + 1]]
            ys = [c * 100 for c in carga] + [carga[-1] * 100 if carga else 0]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, name=f"Senior {p}", mode="lines", line_shape="hv",
                line=dict(color=PALETA[k % len(PALETA)], width=2.5),
                hovertemplate=f"<b>{p}</b><br>%{{x|%d-%m-%Y}}: %{{y:.0f}}%<extra></extra>"))
        fig.add_hline(y=100, line=dict(color="#e5484d", dash="dash"),
                      annotation_text="Límite 100%", annotation_position="top left")
        layout(fig, f"{nombre} — Carga de seniors (límite 100%)", 400, [])
        fig.update_yaxes(autorange=True, range=[0, 115], ticksuffix="%",
                         categoryorder="trace", categoryarray=None)
        fig.update_xaxes(side="bottom")
        archivo = f"gantt_{stem}_carga_seniors.html"
        fig.write_html(carpeta / archivo, include_plotlyjs="directory",
                       full_html=True, config=config)
        salida.append({"archivo": archivo, "titulo": "Carga de seniors",
                       "alto": 400})

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
    pe = t["por_estado"]
    plan = cron.get("plan")
    extra_plan = []
    if plan:
        if cron["modo"] == "optimizado":
            extra_plan.append(f"| Término con orden del YAML (sin optimizar) | "
                              f"{fecha_txt(plan['fin_prioridad'])} |")
        if plan.get("cuello"):
            extra_plan.append(f"| Cuello de botella (junior) | {plan['cuello'][0]} "
                              f"({plan['cuello'][1]} días hábiles pendientes) |")
        picos = [max(c) for c in plan["carga_sr"].values() if c]
        if picos:
            extra_plan.append(f"| Pico de carga senior (límite 100%) | "
                              f"{max(picos):.0%} |")
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
        f"| Días pendientes | {t['dias_rest']:g} |",
        f"| Story points totales | {t['puntos']} |",
        f"| Items sin estimar | {t['sin_est']} |",
        f"| Incertidumbre alta / media / baja | "
        f"{inc.get('alta', 0)} / {inc.get('media', 0)} / {inc.get('baja', 0)} |",
        f"| Inicio planificado | {fecha_txt(cron['inicio'])} |",
        f"| Término estimado ({cron['modo']}) | {fecha_txt(cron['fin'])} |",
        *extra_plan,
        f"| Finalizados / en curso / pausados / backlog | "
        f"{pe.get('finalizado', 0)} / {pe.get('wip', 0)} / "
        f"{pe.get('pausado', 0)} / {pe.get('backlog', 0)} |",
        f"| % avance global (ponderado por días) | {t['avance']:.0%} |",
        "",
    ]

    # ---- 2. Resumen por proyecto
    L += ["## 2. Resumen por proyecto", "",
          "| Proyecto | Milestones | Items | Días pendientes | Inicio | Término | Avance |",
          "|---|--:|--:|--:|---|---|--:|"]
    proyectos = {}
    for m in milestones:
        p = m.get("proyecto", nombre)
        proyectos.setdefault(p, []).extend(m["items"])
    for p, items_p in proyectos.items():
        mp = [m for m in milestones if m.get("proyecto", nombre) == p]
        ag = [i for i in items_p if i["ini"]]
        tp = totales(items_p)
        L.append(
            f"| {esc(p)} | {len(mp)} | {tp['n']} | {tp['dias_rest']:g} | "
            f"{fecha_txt(min((i['ini'] for i in ag), default=None))} | "
            f"{fecha_txt(max((i['fin'] for i in ag), default=None))} | "
            f"{tp['avance']:.0%} |"
        )
    L.append("")

    # ---- 3. Tablero por milestone
    L += ["## 3. Tablero por milestone", ""]
    L += [
        "| # | Milestone | Items | Días | Pend. | Pts | Inicio | Fin | Sin estimar | Estado | % Avance |",
        "|--:|---|--:|--:|--:|--:|---|---|--:|---|--:|",
    ]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        estado = estado_milestone(m["items"])
        L.append(
            f"| {n} | [{esc(m['nombre'])}](#{n}-{slug(m['nombre'])}) | {mt['n']} | "
            f"{mt['dias']} | {mt['dias_rest']:g} | {mt['puntos']} | "
            f"{fecha_txt(m['ini'])} | {fecha_txt(m['fin'])} | "
            f"{mt['sin_est']} | {estado} | {mt['avance']:.0%} |"
        )
    L.append("")

    # ---- 3. Cronograma (Gantt)
    L += ["## 4. Cronograma (Gantt)", ""]
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
        "solo se agenda el trabajo pendiente (los finalizados no aparecen y los "
        "avanzados cuentan solo sus días restantes); "
        + DESC_MODO[cron["modo"]]
        + (f" Sin calendarizar por no tener estimación: {', '.join(sin_est)}."
           if sin_est else ""),
        "",
    ]

    # ---- 4. Detalle
    L += ["## 5. Detalle de work items", ""]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        L += [f"### {n}. {m['nombre']}", ""]
        if not m["items"]:
            L += ["_Sin work items definidos (pendiente de levantamiento)._", ""]
            continue
        L += [
            f"**Total:** {mt['dias']} días ({mt['dias_rest']:g} pendientes) · "
            f"{mt['puntos']} pts · {mt['n']} items · {mt['avance']:.0%} avance",
            "",
            "| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |",
            "|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|",
        ]
        for i in m["items"]:
            estado = ESTADOS_MAP[i["estado"]]
            if i["dias"] is None and i["estado"] != "finalizado":
                estado = "⚠️ Sin estimar"
            L.append(
                f"| {esc(i['nombre'])} | {i['tamaño']} | {fmt(i['dias'])} | "
                f"{fmt(i['puntos'])} | {ICONO_INC.get(i['inc'], i['inc'])} | "
                f"{fecha_txt(i['ini'])} | {fecha_txt(i['fin'])} | "
                f"{estado} | {esc(responsables_txt(i))} | {i['avance']:.0%} |  |"
            )
        L.append("")

    # ---- 5. Carga por responsable
    L += ["## 6. Carga por responsable (trabajo pendiente)", ""]
    carga = carga_por_persona(milestones)
    if carga:
        L += [
            "| Persona | Rol | Items abiertos | Días-persona pendientes | Carga pico |",
            "|---|---|--:|--:|--:|",
        ]
        carga_plan = (plan or {}).get("carga_sr", {})
        for p, r, n, d in carga:
            pico = (f"{max(carga_plan[p]):.0%}"
                    if r == "Senior" and carga_plan.get(p) else "—")
            L.append(f"| {esc(p)} | {r} | {n} | {d:.1f} | {pico} |")
        L += ["",
              "> Supuestos: cada junior asignado dedica los días pendientes completos "
              "del item; el senior aporta días pendientes × dedicacion_sr. "
              "Carga pico = máximo simultáneo de la senior en el cronograma.", ""]
    else:
        L += ["_Sin trabajo pendiente asignado._", ""]

    # ---- 6. Riesgos iniciales derivados
    L += ["## 7. Riesgos y alertas (derivados de la estimación y el estado)", ""]
    riesgos = []
    for m in milestones:
        for i in m["items"]:
            if i["estado"] == "finalizado":
                continue
            motivos = []
            if i["estado"] == "pausado":
                motivos.append("pausado")
            if not i["jr"] and not i["sr"]:
                motivos.append("sin responsable")
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

    # ---- 7-10. Secciones de gestión vacías
    L += [
        "## 8. Registro de riesgos adicionales",
        "",
        "| ID | Riesgo | Probabilidad | Impacto | Mitigación | Dueño | Estado |",
        "|---|---|---|---|---|---|---|",
        "| R-01 |  |  |  |  |  | ⬜ Abierto |",
        "",
        "## 9. Bloqueos y dependencias",
        "",
        "| Fecha | Descripción | Afecta a | Responsable | Fecha compromiso | Estado |",
        "|---|---|---|---|---|---|",
        "|  |  |  |  |  |  |",
        "",
        "## 10. Decisiones y acuerdos",
        "",
        "| Fecha | Decisión / acuerdo | Participantes |",
        "|---|---|---|",
        "|  |  |  |",
        "",
        "## 11. Control de cambios de alcance",
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
    ap = argparse.ArgumentParser(
        description="Genera planificación combinada de portafolio desde varios YAML.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("yaml", type=Path, nargs="+", help="Uno o más YAML de proyectos")
    ap.add_argument("-r", "--recursos", type=Path,
                    help="YAML transversal con disponibilidad y ausencias")
    ap.add_argument("-o", "--output", type=Path,
                    help="Archivo Markdown de salida")
    ap.add_argument("--inicio", type=parse_fecha, metavar="YYYY-MM-DD",
                    help="Fecha de inicio común del portafolio")
    ap.add_argument("--modo", choices=list(DESC_MODO), default="optimizado",
                    help="optimizado o prioridad consideran recursos compartidos")
    ap.add_argument("--sin-gantt", action="store_true",
                    help="No generar los gráficos Gantt")
    args = ap.parse_args()

    salida = args.output or Path.cwd() / "seguimiento_portafolio.md"
    salida.parent.mkdir(parents=True, exist_ok=True)

    milestones, avisos, fechas_inicio, nombres = [], [], [], []
    for archivo in args.yaml:
        nombre_proyecto, ms, av, inicio_yaml = cargar(archivo)
        nombres.append(nombre_proyecto)
        avisos.extend(av)
        if inicio_yaml:
            fechas_inicio.append(inicio_yaml)
        for m in ms:
            m["proyecto"] = nombre_proyecto
        milestones.extend(ms)

    if len(set(nombres)) != len(nombres):
        avisos.append("Hay proyectos con nombres repetidos; se recomienda usar nombres únicos en proyecto.nombre.")

    nombre = "Portafolio institucional"
    inicio = args.inicio or (min(fechas_inicio) if fechas_inicio else date.today())
    recursos = cargar_recursos(args.recursos)

    if args.modo in ("optimizado", "prioridad"):
        inicio, fin, plan = agendar(milestones, inicio, args.modo, avisos, recursos)
    else:
        inicio, fin, plan = agendar(milestones, inicio, args.modo, avisos, recursos)

    gantts, error_gantt = [], None
    if not args.sin_gantt:
        gantts, error_gantt = generar_gantt(
            nombre, milestones, salida.parent, "portafolio", date.today(), plan)
        if error_gantt:
            avisos.append(error_gantt)

    cron = {
        "inicio": inicio, "fin": fin, "modo": args.modo, "plan": plan,
        "gantts": gantts, "error_gantt": error_gantt
    }
    salida.write_text(generar_md(nombre, milestones, avisos, cron), encoding="utf-8")

    for a in avisos:
        print(f"⚠️  {a}", file=sys.stderr)
    print(f"✅ Proyectos: {len(args.yaml)}")
    print(f"✅ Funcionarios configurados: {len(recursos)}")
    print(f"✅ Generado: {salida}")
    for g in gantts:
        print(f"📊 Gantt: {salida.parent / g['archivo']}")


if __name__ == "__main__":
    main()