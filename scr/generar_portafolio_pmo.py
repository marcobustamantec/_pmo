#!/usr/bin/env python3
"""
Genera un .md de seguimiento PMO de portafolio (varios YAML de proyectos),
con recursos compartidos, disponibilidad individual y ausencias.

Programación cruzada: todos los proyectos se agendan juntos sobre los mismos
recursos. Los proyectos se ordenan por `proyecto.prioridad` (1 = más alta),
sin importar el orden en que se pasen los archivos; el proyecto prioritario
reserva primero a sus desarrolladores y los de menor prioridad usan los huecos.

El .md y los HTML de los Gantt se guardan en el directorio desde donde se
ejecuta el script (no en el del YAML), salvo que uses -o.

Uso:
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --inicio 2026-12-01
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --modo prioridad
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --modo secuencial
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml -o otra/ruta/seguimiento.md
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --sin-gantt
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --sin-proyectos
    python generar_seguimiento_pmo.py proyectos/*.yml --recursos recursos.yml --esfuerzo puntos

Salidas (junto al .md del portafolio): seguimiento_portafolio.md + gantt_portafolio_*.html
y, por cada proyecto, seguimiento_<proyecto>.md + gantt_<proyecto>_*.html con las
MISMAS fechas del cronograma del portafolio.

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
    prio = proyecto.get("prioridad")
    if isinstance(prio, bool) or not isinstance(prio, (int, float)):
        if prio is not None:
            avisos.append(f"{path.name}: prioridad '{prio}' no es numérica; se ignoró.")
        prio = None
    return (
        proyecto.get("nombre", "Proyecto"),
        milestones,
        avisos,
        parse_fecha(proyecto.get("inicio")),   # campo opcional proyecto.inicio
        prio,                                  # 1 = prioridad más alta
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
            # puntos por semana a jornada completa (opcional; solo --esfuerzo puntos)
            "velocidad": (float(cfg["velocidad"]) if cfg.get("velocidad") is not None else None),
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
    def reg(persona, rol, dias, proyecto):
        e = c.setdefault((persona, rol), {"dias": 0.0, "items": 0, "proy": []})
        e["dias"] += dias
        e["items"] += 1
        if proyecto not in e["proy"]:
            e["proy"].append(proyecto)
    for m in milestones:
        pr = m.get("proyecto", "")
        for i in m["items"]:
            if i["estado"] == "finalizado" or i["dias"] is None:
                continue
            rest = i["dias"] * (1 - i["avance"])
            for p in i["jr"]:
                reg(p, "Junior", rest, pr)
            if i["ded_sr"] is not None:
                for p in i["sr"]:
                    reg(p, "Senior", rest * i["ded_sr"] / len(i["sr"]), pr)
            else:
                for p in i["sr"]:
                    reg(p, "Senior", 0.0, pr)
    return sorted(((p, r, e["items"], e["dias"], e["proy"])
                   for (p, r), e in c.items()),
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


def _repartir_puntos(i):
    """Reparte los puntos pendientes del item en partes iguales entre sus días hábiles."""
    pts = (i["puntos"] or 0) * (1 - i["avance"])
    d, ds = i["ini"], []
    while len(ds) < i["rest"]:
        if d.weekday() < 5:
            ds.append(d)
        d += timedelta(days=1)
    i["pts_dia"] = {x: pts / len(ds) for x in ds}


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
            _repartir_puntos(i)
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


def velocidad_defecto(milestones) -> float:
    """Puntos por día-persona implícitos en las estimaciones del propio portafolio
    (suma de puntos / suma de días de los items que tienen ambos)."""
    par = [(i["puntos"], i["dias"]) for m in milestones for i in m["items"]
           if i["puntos"] and i["dias"]]
    return (sum(p for p, _ in par) / sum(d for _, d in par)) if par else 0.6


def _tareas(milestones, avisos, recursos=None, esfuerzo="dias"):
    """
    Work items pendientes de todos los proyectos. Cada tarea conserva la
    prioridad de su proyecto.
      esfuerzo="dias":    duración fija = días pendientes (÷ disponibilidad del junior
                          más lento). Más juniors NO acortan la tarea.
      esfuerzo="puntos":  la tarea necesita `puntos × (1 − avance)`; cada día aporta
                          la velocidad × disponibilidad de los juniors asignados
                          (se SUMAN). Sin junior, trabaja(n) el/los senior(s) a
                          velocidad × su dedicación.
    """
    recursos = recursos or {}
    vel_def = velocidad_defecto(milestones)          # pts/día
    tareas = []
    for mi, m in enumerate(milestones):
        prio = m.get("prioridad", math.inf)
        for i in m["items"]:
            if i["estado"] == "finalizado":
                continue
            pts_pend = (i["puntos"] or 0) * (1 - i["avance"])
            usa_pts = esfuerzo == "puntos" and bool(i["puntos"])
            if esfuerzo == "puntos" and not i["puntos"] and i["dias"] is not None:
                avisos.append(f"'{i['nombre']}': sin puntos; en modo puntos se agenda por días.")
            if not usa_pts and i["dias"] is None:
                continue
            dur_base = math.ceil(i["dias"] * (1 - i["avance"])) if i["dias"] is not None else 0
            if usa_pts and pts_pend <= EPS:
                continue
            if not usa_pts and dur_base <= 0:
                continue

            jr = list(dict.fromkeys(i["jr"]))
            sr = {}
            if i["sr"] and i["ded_sr"]:
                ded = i["ded_sr"]
                if ded > 1:
                    avisos.append(f"'{i['nombre']}': dedicacion_sr {ded} > 1; se limitó a 1 (100%).")
                    ded = 1.0
                sr = {p: ded / len(i["sr"]) for p in i["sr"]}
                for p, demanda in sr.items():
                    base = recursos.get(p, {}).get("disponibilidad", 1.0)
                    if demanda > base + EPS:
                        raise ValueError(
                            f"El work item '{i['nombre']}' requiere {demanda:.0%} de {p}, "
                            f"pero su disponibilidad base es {base:.0%}. "
                            "Ajusta dedicacion_sr o la disponibilidad."
                        )

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

            vel = {}
            if usa_pts:
                for p in (jr or list(sr)):
                    v_sem = recursos.get(p, {}).get("velocidad")
                    vel[p] = (v_sem / 5.0) if v_sem else vel_def
                # tasa diaria estimada (disponibilidad / dedicación base)
                tasa = (sum(vel[p] * jr_load[p] for p in jr) if jr
                        else sum(vel[p] * sr[p] for p in sr))
                if tasa <= EPS:
                    avisos.append(f"'{i['nombre']}': sin junior ni dedicacion_sr; "
                                  "no hay quién aporte puntos, se agenda por días.")
                    usa_pts = False
                    if i["dias"] is None:
                        continue
                    dur_base = math.ceil(i["dias"] * (1 - i["avance"]))
                    if dur_base <= 0:
                        continue
            if usa_pts:
                dur = max(1, math.ceil(pts_pend / tasa - EPS))
            else:
                dur = math.ceil(dur_base * factor)
            tareas.append({
                "item": i, "mi": mi, "idx": len(tareas), "dur": dur,
                "dur_base": dur_base, "jr": jr, "jr_load": jr_load, "sr": sr,
                "prio": prio, "proy": m.get("proyecto", ""),
                "modo": "puntos" if usa_pts else "dias",
                "pts": pts_pend, "vel": vel,
            })
    return tareas


def _dia(fechas, d):
    """Fecha del índice d (si excede el calendario, se extrapola)."""
    if d < len(fechas):
        return fechas[d]
    return fechas[-1] + timedelta(days=d - len(fechas) + 1)


def _ventana(t, s, uso, fechas, recursos):
    """
    Días hábiles que ocuparía la tarea t si parte en el índice s.
    - Si alguien asignado está ausente ese día, la tarea se PAUSA (no consume
      capacidad ni avanza) y continúa al volver; no se obliga a saltar la ausencia.
      (En modo puntos, la ausencia de UN junior no frena a los demás juniors; la de
      un senior, o la de todos los juniors, sí pausa.)
    - Si hay sobrecarga por otra tarea (de cualquier proyecto), devuelve el
      índice del conflicto para reintentar después de él.
    - Modo "dias": termina tras t["dur"] días. Modo "puntos": termina cuando los
      puntos aportados cada día alcanzan t["pts"].
    Devuelve (dias, puntos_por_dia, None) o (None, None, indice_conflicto).
    """
    personas = list(t["jr"]) + list(t["sr"])
    por_puntos = t.get("modo") == "puntos"
    dias, pts, d, acum = [], [], s, 0.0
    limite = len(fechas) + 3650

    def pendiente():
        return acum < t["pts"] - EPS if por_puntos else len(dias) < t["dur"]

    while pendiente():
        if d > limite:
            raise ValueError(
                f"No se pudo agendar '{t['item']['nombre']}': revisa las ausencias "
                "y disponibilidades de " + ", ".join(personas) + ".")
        dia = _dia(fechas, d)
        if por_puntos:
            activos = [p for p in t["jr"] if disponibilidad_persona(p, dia, recursos) > 0]
            if (t["jr"] and not activos) or any(
                    disponibilidad_persona(p, dia, recursos) <= 0 for p in t["sr"]):
                d += 1
                continue
        else:
            if any(disponibilidad_persona(p, dia, recursos) <= 0 for p in personas):
                d += 1
                continue
            activos = t["jr"]
        for p in activos:
            cap = disponibilidad_persona(p, dia, recursos)
            if uso.get(("J", p, d), 0.0) + t["jr_load"].get(p, 0.0) > cap + EPS:
                return None, None, d
        for p, demanda in t["sr"].items():
            cap = disponibilidad_persona(p, dia, recursos)
            if uso.get(("S", p, d), 0.0) + demanda > cap + EPS:
                return None, None, d
        dias.append(d)
        if por_puntos:
            if t["jr"]:
                tasa = sum(t["vel"][p] * disponibilidad_persona(p, dia, recursos)
                           for p in activos)
            else:
                tasa = sum(t["vel"][p] * t["sr"][p] for p in t["sr"])
            aporte = min(tasa, t["pts"] - acum)
            pts.append(aporte)
            acum += tasa
        d += 1
    if not por_puntos:
        pts = [t["pts"] / len(dias)] * len(dias) if dias else []
    return dias, pts, None


def _programar(tareas, orden, fechas, recursos, proyectos):
    """
    Cronograma serial con capacidad diaria por funcionario, COMPARTIDA entre
    todos los proyectos: la tarea que primero se coloca reserva capacidad y
    las siguientes se ubican en el primer hueco disponible.
    Juniors: una tarea a la vez; disponibilidad parcial alarga su duración.
    Seniors: su dedicación simultánea no puede superar su disponibilidad diaria.
    Ausencias: capacidad cero (la tarea se pausa).
    `proyectos`: nombres en orden de prioridad (para el puntaje).
    """
    uso, uso_pr = {}, {}
    inicios, fines, fin_ms, fin_pr, dias_pts = {}, {}, {}, {}, {}
    for t in orden:
        s = 0
        while True:
            dias, pts, choque = _ventana(t, s, uso, fechas, recursos)
            if dias is not None:
                break
            s = choque + 1
        dias_pts[t["idx"]] = (dias, pts)
        for d in dias:
            for p in t["jr"]:
                uso[("J", p, d)] = uso.get(("J", p, d), 0.0) + t["jr_load"].get(p, 0.0)
            for p, demanda in t["sr"].items():
                uso[("S", p, d)] = uso.get(("S", p, d), 0.0) + demanda
                k = (t["proy"], "S", p, d)
                uso_pr[k] = uso_pr.get(k, 0.0) + demanda
        inicios[t["idx"]] = dias[0]
        fines[t["idx"]] = dias[-1] + 1
        fin_ms[t["mi"]] = max(fin_ms.get(t["mi"], 0), fines[t["idx"]])
        fin_pr[t["proy"]] = max(fin_pr.get(t["proy"], 0), fines[t["idx"]])

    makespan = max(fines.values(), default=0)
    # Puntaje lexicográfico: primero termina lo antes posible el proyecto de
    # mayor prioridad, luego el siguiente, etc.; después makespan y suma de milestones.
    score = tuple(fin_pr.get(p, 0) for p in proyectos) + (makespan, sum(fin_ms.values()))
    return {
        "inicios": inicios, "fines": fines, "uso": uso, "uso_pr": uso_pr,
        "dias_pts": dias_pts,
        "makespan": makespan,
        "fin_proy": fin_pr, "score": score
    }


def agendar_recursos(milestones, inicio: date, modo: str, avisos: list, recursos=None,
                     esfuerzo="dias"):
    """
    Planifica conjuntamente todos los proyectos con disponibilidad compartida.
    Los milestones deben venir ya ordenados por prioridad de proyecto (main()).
    Prioridad estricta entre proyectos; el modo 'optimizado' solo reordena
    tareas DENTRO de cada proyecto.
    """
    recursos = recursos or {}
    base = proximo_habil(inicio)
    tareas = _tareas(milestones, avisos, recursos, esfuerzo)
    for m in milestones:
        m["ini"] = m["fin"] = None
    if not tareas:
        return base, None, None

    proyectos = sorted({t["proy"] for t in tareas},
                       key=lambda p: (min(t["prio"] for t in tareas if t["proy"] == p),
                                      min(t["idx"] for t in tareas if t["proy"] == p)))

    # Horizonte de fechas suficientemente amplio para absorber ausencias.
    dur_total = sum(t["dur"] for t in tareas)
    fechas = _calendario(base, max(dur_total * 3 + 30, 365))

    def no_wip(t):
        return t["item"]["estado"] != "wip"

    # Clave base: prioridad del proyecto > (en curso primero) > orden del YAML.
    base_orden = sorted(tareas, key=lambda t: (t["prio"], t["proy"], no_wip(t), t["idx"]))
    res0 = _programar(tareas, base_orden, fechas, recursos, proyectos)
    mejor, ensayos = res0, 1

    carga_j = Counter()
    for t in tareas:
        for p in t["jr"]:
            carga_j[p] += t["dur"]

    if modo == "optimizado":
        candidatos = [
            sorted(tareas, key=lambda t: (t["prio"], t["proy"], no_wip(t),
                   -max([carga_j[p] for p in t["jr"]] or [0]), -t["dur"], t["idx"])),
            sorted(tareas, key=lambda t: (t["prio"], t["proy"], no_wip(t),
                                          -t["dur"], t["idx"])),
        ]
        rng = random.Random(7)
        for _ in range(600):
            spread = rng.choice([3, 8, 20, 60])
            candidatos.append(sorted(
                tareas, key=lambda t: (t["prio"], t["proy"], no_wip(t),
                                       t["idx"] + rng.uniform(0, spread))))
        for orden in candidatos:
            r = _programar(tareas, orden, fechas, recursos, proyectos)
            ensayos += 1
            if r["score"] < mejor["score"]:
                mejor = r

    # Asegurar calendario real hasta el último día programado.
    fechas = _calendario(base, mejor["makespan"])
    for t in tareas:
        i, s, f = t["item"], mejor["inicios"][t["idx"]], mejor["fines"][t["idx"]]
        dias_t, pts_t = mejor["dias_pts"][t["idx"]]
        i["rest"] = len(dias_t)            # días hábiles efectivamente trabajados
        i["pts_dia"] = {fechas[d]: v for d, v in zip(dias_t, pts_t)}
        i["ini"] = fechas[s]
        i["fin"] = fechas[f]
        i["dias_calendario"] = f - s   # incluye pausas por ausencias

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
    cuello = carga_j.most_common(1)[0] if carga_j else None

    # Vista por proyecto del MISMO cronograma (para los informes por proyecto).
    carga_sr_proy, cuello_proy = {}, {}
    for pr in proyectos:
        tps = [t for t in tareas if t["proy"] == pr]
        srs = sorted({p for t in tps for p in t["sr"]})
        carga_sr_proy[pr] = {
            p: [round(mejor["uso_pr"].get((pr, "S", p, d), 0.0), 4)
                for d in range(mejor["makespan"])] for p in srs}
        cj = Counter()
        for t in tps:
            for p in t["jr"]:
                cj[p] += t["dur"]
        cuello_proy[pr] = cj.most_common(1)[0] if cj else None
    # Capacidad diaria de cada senior (disponibilidad, 0 en ausencias).
    cap_sr = {p: [round(disponibilidad_persona(p, fechas[d], recursos), 4)
                  for d in range(mejor["makespan"])] for p in seniors}
    plan = {
        "fechas": fechas, "makespan": mejor["makespan"], "cuello": cuello,
        "fin_prioridad": fechas[res0["makespan"]],
        "fin_proyectos": {p: fechas[mejor["fin_proy"][p]] for p in proyectos},
        "orden_proyectos": proyectos,
        "carga_sr": carga_sr, "carga_jr": carga_jr, "ensayos": ensayos,
        "carga_sr_proy": carga_sr_proy, "cuello_proy": cuello_proy,
        "cap_sr": cap_sr, "recursos": recursos,
        "esfuerzo": esfuerzo, "vel_def": velocidad_defecto(milestones) * 5,
    }
    return base, fechas[mejor["makespan"]], plan


def agendar(milestones, inicio: date, modo: str, avisos: list, recursos=None,
            esfuerzo="dias"):
    """Devuelve (inicio, fin, plan)."""
    if modo in ("secuencial", "paralelo"):
        base, fin = agendar_simple(milestones, inicio, modo)
        if recursos:
            avisos.append("El modo secuencial/paralelo no aplica disponibilidad individual; usa optimizado o prioridad.")
        if esfuerzo == "puntos":
            avisos.append("--esfuerzo puntos solo aplica con modo optimizado o prioridad; se usó días.")
        return base, fin, None
    return agendar_recursos(milestones, inicio, modo, avisos, recursos, esfuerzo)


# --------------------------------------------------------------------------
# Puntos resueltos por semana
# --------------------------------------------------------------------------
def lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def puntos_semanales(milestones) -> dict:
    """
    Puntos por semana (lunes a domingo) según el cronograma calculado.
      avanzados: puntos de trabajo realizado cada semana (cada item reparte sus
                 puntos pendientes según su aporte diario; en modo días, en partes
                 iguales sobre sus días trabajados).
      entregados: puntos COMPLETOS del item en la semana en que termina.
    `base` = puntos ya hechos antes de la fecha de corte (puntos × avance).
    """
    sem, proyectos = {}, []
    total = base = agendado = 0.0
    for m in milestones:
        pr = m.get("proyecto", "")
        if pr not in proyectos:
            proyectos.append(pr)
        for i in m["items"]:
            pts = i["puntos"]
            if pts is None:
                continue
            total += pts
            base += pts * i["avance"]
            pd = i.get("pts_dia")
            if not pd:
                continue
            for d, v in pd.items():
                w = sem.setdefault(lunes(d), {"avanz": {}, "entreg": {}})
                w["avanz"][pr] = w["avanz"].get(pr, 0.0) + v
                agendado += v
            w = sem.setdefault(lunes(max(pd)), {"avanz": {}, "entreg": {}})
            w["entreg"][pr] = w["entreg"].get(pr, 0.0) + pts
    filas = []
    if sem:
        k, fin, acum = min(sem), max(sem), base
        while k <= fin:
            w = sem.get(k, {"avanz": {}, "entreg": {}})
            av, en = sum(w["avanz"].values()), sum(w["entreg"].values())
            acum += av
            filas.append({"semana": k, "avanz": av, "entreg": en, "acum": acum,
                          "pct": (acum / total) if total else 0.0,
                          "por_proy": dict(w["avanz"])})
            k += timedelta(days=7)
    return {"filas": filas, "total": total, "base": base, "agendado": agendado,
            "sin_agendar": max(total - base - agendado, 0.0), "proyectos": proyectos}


# --------------------------------------------------------------------------
# Gantt con Plotly
# --------------------------------------------------------------------------
def _ms(d1: date, d2: date) -> float:
    return (d2 - d1).days * 86_400_000


# Colores por PROYECTO (distintos de los de incertidumbre y de la paleta general).
PALETA_PROY = ["#0d9488", "#c026d3", "#ea580c", "#2563eb",
               "#65a30d", "#be123c", "#7c3aed", "#0891b2"]
COLOR_CONTEXTO = "#c9ccd6"


def slug_archivo(txt: str) -> str:
    """Nombre de archivo seguro (ASCII) a partir del nombre del proyecto."""
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "proyecto"


def colores_proyectos(milestones) -> dict:
    """Un color fijo por proyecto (en orden de prioridad), igual en todas las vistas."""
    nombres = list(dict.fromkeys(m.get("proyecto", "") for m in milestones))
    return {n: PALETA_PROY[k % len(PALETA_PROY)] for k, n in enumerate(nombres)}


def generar_gantt(nombre, milestones, carpeta: Path, stem: str, hoy: date,
                  plan=None, rango=None, contexto=None, por_proyecto=False,
                  colores=None):
    """
    Escribe HTML interactivos en `carpeta` y devuelve (lista, error); la lista
    contiene dicts {archivo, titulo, alto}. plotly.min.js se guarda una sola vez
    en la carpeta (funciona offline, sin CDN).

    rango:         (fecha_ini, fecha_fin) para fijar el eje X (así las vistas por
                   proyecto quedan alineadas con el Gantt del portafolio).
    contexto:      milestones de OTROS proyectos; en el Gantt por desarrollador
                   se dibujan en gris para ver por qué hay huecos.
    por_proyecto:  vista de un solo proyecto (etiquetas sin prefijo de proyecto).
    colores:       {proyecto: color}; por defecto en orden de aparición.
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
    if rango:
        ini_proy, fin_proy = min(ini_proy, rango[0]), max(fin_proy, rango[1])

    nombres_proy = list(dict.fromkeys(m.get("proyecto", nombre) for m in milestones))
    colores = dict(colores or {})
    for pr in nombres_proy:
        colores.setdefault(pr, PALETA_PROY[len(colores) % len(PALETA_PROY)])

    def prefijo(m):
        return "" if por_proyecto else f"{m.get('proyecto', nombre)} · "

    def etiqueta_proy(pr):
        prio = next((m.get("prioridad") for m in milestones
                     if m.get("proyecto", nombre) == pr), None)
        return pr + (f" (P{prio:g})" if prio not in (None, math.inf) else "")

    def dt(d):
        return datetime.combine(d, datetime.min.time())

    def linea_hoy(fig):
        if ini_proy <= hoy <= fin_proy:
            x = dt(hoy)
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
        if rango:
            fig.update_xaxes(range=[dt(rango[0] - timedelta(days=3)),
                                    dt(rango[1] + timedelta(days=3))])
        fig.update_yaxes(autorange="reversed", automargin=True,
                         categoryorder="array", categoryarray=etiquetas)

    def guardar(fig, sufijo, titulo, alto):
        archivo = f"gantt_{stem}_{sufijo}.html"
        fig.write_html(carpeta / archivo, include_plotlyjs="directory",
                       full_html=True, config=config)
        salida.append({"archivo": archivo, "titulo": titulo, "alto": alto})

    # ---- Gantt 1: resumen por milestone, una traza por proyecto (filtrable)
    filas = [(n, m) for n, m in enumerate(milestones, 1) if m["ini"]]
    etiquetas = [f"{prefijo(m)}M{n} · {m['nombre']}" for n, m in filas]
    fig = go.Figure()
    por_pr = []   # (proyecto, etiquetas de ese proyecto), alineado con las trazas
    for pr in nombres_proy:
        sel = [(n, m, e) for (n, m), e in zip(filas, etiquetas)
               if m.get("proyecto", nombre) == pr]
        if not sel:
            continue
        por_pr.append((pr, [e for _, _, e in sel]))
        tot = [totales(m["items"]) for _, m, _ in sel]
        fig.add_trace(go.Bar(
            name=etiqueta_proy(pr),
            y=[e for _, _, e in sel],
            x=[_ms(m["ini"], m["fin"]) for _, m, _ in sel],
            base=[dt(m["ini"]) for _, m, _ in sel],
            orientation="h",
            marker=dict(color=colores[pr], line=dict(color="white", width=1)),
            text=[f"{t_['dias_rest']:g} d" for t_ in tot],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white"),
            customdata=[[pr, m["nombre"], fecha_txt(m["ini"]), fecha_txt(m["fin"]),
                         t_["dias_rest"], t_["puntos"], t_["n"]]
                        for (_, m, _), t_ in zip(sel, tot)],
            hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                           "Inicio: %{customdata[2]}<br>Fin: %{customdata[3]}<br>"
                           "Días pendientes: %{customdata[4]}<br>"
                           "Pts: %{customdata[5]} · Items: %{customdata[6]}"
                           "<extra></extra>"),
        ))
    alto = max(260, 46 * len(filas) + 140)
    layout(fig, f"{nombre} — Gantt por milestone", alto, etiquetas)
    fig.update_layout(legend=dict(orientation="h", y=-0.06, x=0, xanchor="left"),
                      margin=dict(l=10, r=20, t=100, b=70))
    if len(por_pr) > 1:
        # Filtro por proyecto: muestra solo sus trazas y reordena el eje Y sin huecos.
        botones = [dict(label="Todos los proyectos", method="update",
                        args=[{"visible": [True] * len(por_pr)},
                              {"yaxis.categoryarray": etiquetas}])]
        for k, (pr, ets) in enumerate(por_pr):
            botones.append(dict(
                label=etiqueta_proy(pr), method="update",
                args=[{"visible": [j == k for j in range(len(por_pr))]},
                      {"yaxis.categoryarray": ets}]))
        fig.update_layout(updatemenus=[dict(
            type="dropdown", direction="down", showactive=True, buttons=botones,
            x=1, xanchor="right", y=1.0, yanchor="bottom")])
    linea_hoy(fig)
    guardar(fig, "resumen", "Gantt por milestone", alto)

    # ---- Gantt 2: detalle por work item, ordenado por fecha de inicio
    ranking = []
    for n, m in enumerate(milestones, 1):
        for i in m["items"]:
            if i["ini"]:
                ranking.append((n, f"{prefijo(m)}M{n} · {i['nombre']}", i))
    ranking.sort(key=lambda r: (r[2]["ini"], r[2]["fin"],
                                milestones[r[0] - 1].get("prioridad", math.inf), r[0]))
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
            base=[dt(i["ini"]) for _, _, i in sel],
            orientation="h",
            marker=dict(color=COLOR_INC[inc], line=dict(color="white", width=1)),
            text=[f"{i['rest']} d" for _, _, i in sel],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(color="white"),
            customdata=[[fecha_txt(i["ini"]), fecha_txt(i["fin"]),
                         f"{i['rest']} de {fmt(i['dias'])}",
                         fmt(i["puntos"]), i["tamaño"], responsables_txt(i),
                         f"{milestones[n - 1].get('proyecto', nombre)} · "
                         f"{milestones[n - 1]['nombre']}"] for n, _, i in sel],
            hovertemplate=("<b>%{y}</b><br>%{customdata[6]}<br>"
                           "Inicio: %{customdata[0]}<br>"
                           "Fin: %{customdata[1]}<br>Días pend.: %{customdata[2]} · "
                           "Pts: %{customdata[3]} · Tamaño: %{customdata[4]}<br>"
                           "%{customdata[5]}<extra></extra>"),
        ))
    alto = max(320, 30 * len(ranking) + 150)
    layout(fig, f"{nombre} — Gantt por work item (orden por fecha de inicio)",
           alto, [e for _, e, _ in ranking])
    linea_hoy(fig)
    guardar(fig, "detalle", "Gantt por work item", alto)

    # ---- Gantt 3: por desarrollador (una fila por junior), color por proyecto
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
    # Contexto: trabajo de otros proyectos sobre los mismos desarrolladores (gris)
    ctx = [(p, i, m) for m in (contexto or []) for i in m["items"] if i["ini"]
           for p in i["jr"] if p in juniors]
    if ctx:
        fig.add_trace(go.Bar(
            name="Otros proyectos (mismo cronograma)",
            y=[p for p, _, _ in ctx],
            x=[_ms(i["ini"], i["fin"]) for _, i, _ in ctx],
            base=[dt(i["ini"]) for _, i, _ in ctx],
            orientation="h",
            marker=dict(color=COLOR_CONTEXTO, line=dict(color="white", width=1.5)),
            text=[i["nombre"][:38] + ("…" if len(i["nombre"]) > 38 else "")
                  for _, i, _ in ctx],
            textposition="inside", insidetextanchor="start",
            textfont=dict(color="#555a6a", size=10),
            customdata=[[i["nombre"], fecha_txt(i["ini"]), fecha_txt(i["fin"]),
                         f"{m.get('proyecto', '')} · {m['nombre']}"] for _, i, m in ctx],
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[3]}<br>"
                           "Inicio: %{customdata[1]}<br>Fin: %{customdata[2]}"
                           "<extra></extra>"),
        ))
    for pr in nombres_proy:
        sel = [(p, i, nn) for p in orden_filas for (nn, i) in filas_dev[p]
               if milestones[nn - 1].get("proyecto", nombre) == pr]
        if not sel:
            continue
        fig.add_trace(go.Bar(
            name=etiqueta_proy(pr),
            y=[p for p, _, _ in sel],
            x=[_ms(i["ini"], i["fin"]) for _, i, _ in sel],
            base=[dt(i["ini"]) for _, i, _ in sel],
            orientation="h",
            marker=dict(color=colores[pr], line=dict(color="white", width=1.5)),
            text=[i["nombre"][:38] + ("…" if len(i["nombre"]) > 38 else "")
                  for _, i, _ in sel],
            textposition="inside", insidetextanchor="start",
            textfont=dict(color="white", size=10),
            customdata=[[i["nombre"], fecha_txt(i["ini"]), fecha_txt(i["fin"]),
                         f"{i['rest']} de {fmt(i['dias'])}",
                         ICONO_INC.get(i["inc"], i["inc"]),
                         responsables_txt(i),
                         f"{pr} · {milestones[nn - 1]['nombre']}"] for _, i, nn in sel],
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[6]}<br>"
                           "Inicio: %{customdata[1]}<br>"
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
    guardar(fig, "desarrolladores", "Gantt por desarrollador", alto)

    # ---- Gantt 4: carga de cada senior (sólida) vs. su capacidad (punteada)
    if plan and plan.get("carga_sr"):
        fechas, ms = plan["fechas"], plan["makespan"]
        cap = plan.get("cap_sr", {})
        xs = [dt(d) for d in fechas[:ms + 1]]
        fig = go.Figure()
        for k, (p, carga) in enumerate(sorted(plan["carga_sr"].items())):
            color = PALETA[k % len(PALETA)]
            ys = [c * 100 for c in carga] + [carga[-1] * 100 if carga else 0]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, name=f"Senior {p}", mode="lines", line_shape="hv",
                line=dict(color=color, width=2.5),
                hovertemplate=f"<b>{p}</b><br>%{{x|%d-%m-%Y}}: %{{y:.0f}}%<extra></extra>"))
            if cap.get(p):
                yc = [c * 100 for c in cap[p]] + [cap[p][-1] * 100]
                fig.add_trace(go.Scatter(
                    x=xs, y=yc, name=f"Capacidad {p}", mode="lines", line_shape="hv",
                    line=dict(color=color, width=1.5, dash="dot"),
                    hovertemplate=(f"<b>Capacidad {p}</b><br>"
                                   "%{x|%d-%m-%Y}: %{y:.0f}%<extra></extra>")))
        layout(fig, f"{nombre} — Carga de seniors vs. capacidad (punteada)", 400, [])
        fig.update_yaxes(autorange=True, range=[0, 115], ticksuffix="%",
                         categoryorder="trace", categoryarray=None)
        fig.update_xaxes(side="bottom")
        guardar(fig, "carga_seniors", "Carga de seniors", 400)

    # ---- Gantt 5: puntos resueltos por semana (barras por proyecto) + acumulado
    ps = puntos_semanales(milestones)
    if ps["filas"]:
        filas_s = ps["filas"]
        xs = [dt(f["semana"]) for f in filas_s]
        fig = go.Figure()
        for pr in nombres_proy:
            fig.add_trace(go.Bar(
                name=etiqueta_proy(pr), x=xs,
                y=[round(f["por_proy"].get(pr, 0.0), 2) for f in filas_s],
                width=6 * 86_400_000,
                marker=dict(color=colores[pr], line=dict(color="white", width=1)),
                hovertemplate=(f"<b>{pr}</b><br>Semana del %{{x|%d-%m-%Y}}<br>"
                               "%{y:.1f} pts<extra></extra>")))
        fig.add_trace(go.Scatter(
            name="Acumulado (% del total, incl. ya hecho)", x=xs,
            y=[round(f["pct"] * 100, 1) for f in filas_s], yaxis="y2",
            mode="lines+markers", line=dict(color="#6e56cf", width=2.5),
            hovertemplate="Acumulado: %{y:.0f}%<extra></extra>"))
        layout(fig, f"{nombre} — Puntos resueltos por semana", 430, [])
        fig.update_yaxes(autorange=True, rangemode="tozero", title="Puntos por semana",
                         categoryorder="trace", categoryarray=None)
        fig.update_xaxes(side="bottom")
        fig.update_layout(
            barmode="stack",
            yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix="%",
                        showgrid=False),
            legend=dict(orientation="h", y=-0.15, x=0, xanchor="left"),
            margin=dict(l=10, r=20, t=70, b=90))
        linea_hoy(fig)
        guardar(fig, "puntos_semana", "Puntos resueltos por semana", 430)

    return salida, None


# --------------------------------------------------------------------------
# Generación del markdown
# --------------------------------------------------------------------------
def titulo_ms(n, m) -> str:
    """Título (y base del ancla) del detalle de un milestone."""
    return f"{n}. {m['nombre']} ({m.get('proyecto', '')})"


def generar_md(nombre, milestones, avisos, cron, portafolio=True) -> str:
    """
    cron = dict(inicio, fin, modo, gantts, error_gantt, plan, [reportes], [nota])
    portafolio=False: informe de UN proyecto (sin resumen por proyecto ni columna
    de proyecto) que usa las fechas ya calculadas en el cronograma del portafolio.
    """
    todos = [i for m in milestones for i in m["items"]]
    t = totales(todos)
    inc = Counter(i["inc"] for i in todos)
    pe = t["por_estado"]
    plan = cron.get("plan")
    extra_plan = []
    if plan:
        if cron["modo"] == "optimizado" and plan.get("fin_prioridad"):
            extra_plan.append(f"| Término sin optimizar (orden por prioridad y YAML) | "
                              f"{fecha_txt(plan['fin_prioridad'])} |")
        if plan.get("cuello"):
            extra_plan.append(f"| Cuello de botella (junior) | {plan['cuello'][0]} "
                              f"({plan['cuello'][1]} días hábiles pendientes) |")
        picos = [max(c) for c in plan["carga_sr"].values() if c]
        if plan.get("orden_proyectos"):
            extra_plan.append("| Orden de prioridad aplicado | "
                              + " → ".join(plan["orden_proyectos"]) + " |")
        if picos:
            extra_plan.append(f"| Pico de carga senior (máx. simultáneo) | "
                              f"{max(picos):.0%} |")
    L = []

    L += [f"# Seguimiento PMO — {nombre}", ""]
    if not portafolio and cron.get("prioridad") not in (None, math.inf):
        L += [f"- **Prioridad en el portafolio:** {cron['prioridad']:g}"]
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

    # ---- 2. Resumen por proyecto (solo portafolio)
    if portafolio:
        L += ["## 2. Resumen por proyecto", "",
              "| Prioridad | Proyecto | Milestones | Items | Días pendientes | Inicio | Término | Avance |",
              "|:-:|---|--:|--:|--:|---|---|--:|"]
        proyectos = {}
        for m in milestones:
            proyectos.setdefault(m.get("proyecto", nombre), []).extend(m["items"])
        for p, items_p in proyectos.items():
            mp = [m for m in milestones if m.get("proyecto", nombre) == p]
            ag = [i for i in items_p if i["ini"]]
            tp = totales(items_p)
            pr = mp[0].get("prioridad", math.inf) if mp else math.inf
            L.append(
                f"| {'—' if pr == math.inf else f'{pr:g}'} | "
                f"{esc(p)} | {len(mp)} | {tp['n']} | {tp['dias_rest']:g} | "
                f"{fecha_txt(min((i['ini'] for i in ag), default=None))} | "
                f"{fecha_txt(max((i['fin'] for i in ag), default=None))} | "
                f"{tp['avance']:.0%} |"
            )
        L.append("")
        if cron.get("reportes"):
            L += ["**Dashboards detallados por proyecto** (usan las fechas de este "
                  "mismo cronograma): "
                  + " · ".join(f"[{esc(n)}]({a})" for n, a in cron["reportes"]), ""]

    # ---- 3. Tablero por milestone
    L += ["## 3. Tablero por milestone", ""]
    if portafolio:
        L += [
            "| # | Proyecto | Milestone | Items | Días | Pend. | Pts | Inicio | Fin | Sin estimar | Estado | % Avance |",
            "|--:|---|---|--:|--:|--:|--:|---|---|--:|---|--:|",
        ]
    else:
        L += [
            "| # | Milestone | Items | Días | Pend. | Pts | Inicio | Fin | Sin estimar | Estado | % Avance |",
            "|--:|---|--:|--:|--:|--:|---|---|--:|---|--:|",
        ]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        estado = estado_milestone(m["items"])
        L.append(
            f"| {n} | "
            + (f"{esc(m.get('proyecto', nombre))} | " if portafolio else "")
            + f"[{esc(m['nombre'])}](#{slug(titulo_ms(n, m))}) | {mt['n']} | "
            f"{mt['dias']} | {mt['dias_rest']:g} | {mt['puntos']} | "
            f"{fecha_txt(m['ini'])} | {fecha_txt(m['fin'])} | "
            f"{mt['sin_est']} | {estado} | {mt['avance']:.0%} |"
        )
    L.append("")

    # ---- 3. Cronograma (Gantt)
    L += ["## 4. Cronograma (Gantt)", ""]
    if cron["gantts"]:
        for g in cron["gantts"]:
            if "puntos_semana" in g["archivo"]:
                continue          # se muestra en su propia sección
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
        "avanzados cuentan solo sus días restantes); los proyectos se agendan juntos "
        "sobre los mismos recursos, por orden de prioridad; una ausencia pausa el "
        "item (no suma días) y se retoma al volver; "
        + DESC_MODO[cron["modo"]]
        + (" Esfuerzo medido en PUNTOS: cada tarea requiere puntos × (1 − avance); los "
           "juniors asignados a una misma tarea suman su velocidad (puntos/semana × "
           "disponibilidad), por lo que más juniors la terminan antes; sin junior, trabaja "
           "el senior a velocidad × dedicación. Velocidad por defecto: "
           f"{plan['vel_def']:.1f} pts/semana (calibrada con puntos÷días del portafolio)."
           if plan and plan.get("esfuerzo") == "puntos" else "")
        + (f" Sin calendarizar por no tener estimación: {', '.join(sin_est)}."
           if sin_est else ""),
        "",
    ]
    if cron.get("nota"):
        L += [f"> {cron['nota']}", ""]

    # ---- Puntos resueltos por semana
    ps = puntos_semanales(milestones)
    L += ["## 5. Puntos resueltos por semana", ""]
    if ps["filas"]:
        mp = (plan or {}).get("esfuerzo", "dias")
        if portafolio:
            cols_pr = ps["proyectos"]
            cab = ("| Semana (lun) | " + " | ".join(esc(p) for p in cols_pr)
                   + " | Pts avanzados | Pts entregados* | Acumulado | % del total |")
            sep = "|---|" + "--:|" * len(cols_pr) + "--:|--:|--:|--:|"
        else:
            cols_pr = []
            cab = "| Semana (lun) | Pts avanzados | Pts entregados* | Acumulado | % del total |"
            sep = "|---|--:|--:|--:|--:|"
        L += [
            f"- **Total del alcance:** {ps['total']:g} pts · **ya completados al corte:** "
            f"{ps['base']:.1f} pts ({(ps['base'] / ps['total']) if ps['total'] else 0:.0%}) · "
            f"**pendientes calendarizados:** {ps['agendado']:.1f} pts"
            + (f" · **sin calendarizar:** {ps['sin_agendar']:.1f} pts"
               if ps["sin_agendar"] > 0.05 else ""),
            "",
        ]
        g_pts = next((g for g in cron["gantts"] if "puntos_semana" in g["archivo"]), None)
        if g_pts:
            L += [f"**{g_pts['titulo']}** · [abrir en pestaña nueva]({g_pts['archivo']})", "",
                  f'<iframe src="{g_pts["archivo"]}" width="100%" height="{g_pts["alto"] + 10}" '
                  f'style="border:0" loading="lazy"></iframe>', ""]
        L += [cab, sep]
        for f in ps["filas"]:
            celdas = "".join(f"{f['por_proy'].get(p, 0.0):.1f} | " for p in cols_pr)
            L.append(f"| {f['semana']:%d-%m-%Y} | {celdas}{f['avanz']:.1f} | "
                     f"{f['entreg']:g} | {f['acum']:.1f} | {f['pct']:.0%} |")
        L += ["",
              "> **Pts avanzados:** puntos de trabajo realizado en la semana "
              + ("(modo puntos: según el aporte diario de los juniors asignados)."
                 if mp == "puntos" else
                 "(cada item reparte sus puntos pendientes en partes iguales entre sus días trabajados).")
              + " **Pts entregados\\*:** puntos completos de los items que terminan esa semana. "
              "**Acumulado:** incluye lo ya completado al corte (puntos × avance).", ""]
    else:
        L += ["_Sin trabajo pendiente con puntos calendarizado._", ""]

    # ---- 4. Detalle
    L += ["## 6. Detalle de work items", ""]
    for n, m in enumerate(milestones, 1):
        mt = totales(m["items"])
        L += [f"### {titulo_ms(n, m)}", ""]
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
            "| Persona | Rol | Proyectos | Items abiertos | Días-persona pendientes | Carga pico |",
            "|---|---|---|--:|--:|--:|",
        ]
        carga_plan = (plan or {}).get("carga_sr", {})
        for p, r, n, d, proys in carga:
            pico = (f"{max(carga_plan[p]):.0%}"
                    if r == "Senior" and carga_plan.get(p) else "—")
            L.append(f"| {esc(p)} | {r} | {esc(', '.join(proys))} | {n} | {d:.1f} | {pico} |")
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

    # Numeración automática de las secciones "## N. ..."
    import re
    k = 0
    for idx, linea in enumerate(L):
        if re.match(r"## \d+\. ", linea):
            k += 1
            L[idx] = re.sub(r"^## \d+\. ", f"## {k}. ", linea)

    return "\n".join(L)


# --------------------------------------------------------------------------
# Informes por proyecto (integración con el formato de seguimiento individual)
# --------------------------------------------------------------------------
def generar_informe_proyecto(pn, prio, ms, otros, todos_ms, plan, args, carpeta,
                             inicio_pf, fin_pf, colores):
    """
    Genera el seguimiento detallado de UN proyecto (.md + Gantt) SIN reprogramar:
    usa las fechas ini/fin que el portafolio ya calculó, de modo que el
    informe del proyecto es coherente con el Gantt del portafolio. El eje de
    tiempo de los Gantt queda alineado con el del portafolio y, en el Gantt por
    desarrollador, el trabajo de los otros proyectos aparece en gris.
    """
    stem = slug_archivo(pn)
    archivo = carpeta / f"seguimiento_{stem}.md"
    items = [i for m in ms for i in m["items"]]
    ag = [i for i in items if i["ini"]]
    ini_p = min((i["ini"] for i in ag), default=None)
    fin_p = max((i["fin"] for i in ag), default=None)

    # Plan "vista proyecto": mismo calendario, pero cargas solo de este proyecto.
    plan_p = None
    if plan:
        plan_p = {
            "fechas": plan["fechas"], "makespan": plan["makespan"],
            "cuello": plan["cuello_proy"].get(pn),
            "carga_sr": plan["carga_sr_proy"].get(pn, {}),
            "cap_sr": plan.get("cap_sr", {}),
            "fin_prioridad": None,
        }

    # Recursos compartidos con otros proyectos (explican demoras del cronograma)
    def personas(lista):
        return {p for m in lista for i in m["items"]
                if i["estado"] != "finalizado" and i["dias"] is not None
                for p in i["jr"] + i["sr"]}
    mias = personas(ms)
    comp = {}
    for m in otros:
        for p in personas([m]) & mias:
            comp.setdefault(m.get("proyecto", ""), set()).add(p)
    nota = ("Cronograma tomado del portafolio (no se reprograma este proyecto "
            "por separado)")
    if prio not in (None, math.inf):
        nota += f"; prioridad {prio:g}"
    nota += "."
    if comp:
        nota += " Recursos compartidos con " + "; ".join(
            f"{pr}: {', '.join(sorted(ps))}" for pr, ps in comp.items()) + "."

    gantts, err = [], None
    if not args.sin_gantt:
        gantts, err = generar_gantt(
            pn, ms, carpeta, stem, date.today(), plan_p,
            rango=(inicio_pf, fin_pf) if fin_pf else None,
            contexto=otros, por_proyecto=True, colores=colores)
    cron = {
        "inicio": ini_p, "fin": fin_p, "modo": args.modo, "plan": plan_p,
        "gantts": gantts, "error_gantt": err, "nota": nota, "prioridad": prio,
    }
    archivo.write_text(generar_md(pn, ms, [], cron, portafolio=False), encoding="utf-8")
    return {"nombre": pn, "archivo": archivo, "n_gantts": len(gantts)}


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
    ap.add_argument("--esfuerzo", choices=["dias", "puntos"], default="dias",
                    help="dias: duración fija = días del YAML (default). puntos: la duración "
                         "sale de puntos pendientes ÷ velocidad de los juniors asignados")
    ap.add_argument("--sin-gantt", action="store_true",
                    help="No generar los gráficos Gantt")
    ap.add_argument("--sin-proyectos", action="store_true",
                    help="No generar los informes/dashboards individuales por proyecto")
    args = ap.parse_args()

    salida = args.output or Path.cwd() / "seguimiento_portafolio.md"
    salida.parent.mkdir(parents=True, exist_ok=True)

    proyectos_cargados, avisos, fechas_inicio = [], [], []
    for orden_arg, archivo in enumerate(args.yaml):
        nombre_proyecto, ms, av, inicio_yaml, prio = cargar(archivo)
        avisos.extend(av)
        if inicio_yaml:
            fechas_inicio.append(inicio_yaml)
        if prio is None:
            avisos.append(f"{archivo.name}: proyecto '{nombre_proyecto}' sin 'prioridad'; "
                          "se agenda después de los que sí la tienen.")
        for m in ms:
            m["proyecto"] = nombre_proyecto
            m["prioridad"] = prio if prio is not None else math.inf
        proyectos_cargados.append((prio if prio is not None else math.inf,
                                   orden_arg, nombre_proyecto, ms))

    nombres = [p[2] for p in proyectos_cargados]
    if len(set(nombres)) != len(nombres):
        avisos.append("Hay proyectos con nombres repetidos; se recomienda usar nombres únicos en proyecto.nombre.")
    prios = [p[0] for p in proyectos_cargados if p[0] != math.inf]
    if len(set(prios)) != len(prios):
        avisos.append("Hay proyectos con la misma prioridad; se desempata por el orden "
                      "en que se pasaron los archivos.")

    # Los proyectos se ordenan por prioridad (1 = más alta), no por orden de archivos.
    proyectos_cargados.sort(key=lambda x: (x[0], x[1]))
    milestones = [m for *_, ms in proyectos_cargados for m in ms]

    nombre = "Portafolio institucional"
    inicio = args.inicio or (min(fechas_inicio) if fechas_inicio else date.today())
    recursos = cargar_recursos(args.recursos)

    # Toda persona asignada debe existir en el catálogo de recursos.
    if args.recursos:
        asignados = {p for m in milestones for i in m["items"] for p in i["jr"] + i["sr"]}
        for p in sorted(asignados - set(recursos)):
            avisos.append(f"'{p}' está asignado en los proyectos pero no figura en "
                          f"{args.recursos.name}; se asumió disponible al 100%.")
        for m in milestones:
            for i in m["items"]:
                for campo, rol in (("jr", "junior"), ("sr", "senior")):
                    for p in i[campo]:
                        r = recursos.get(p, {}).get("rol")
                        if r and r != rol:
                            avisos.append(f"'{i['nombre']}': {p} figura como {r} en el "
                                          f"catálogo pero está asignado como {rol}.")
    elif any(i["jr"] or i["sr"] for m in milestones for i in m["items"]):
        avisos.append("Sin --recursos: todos los funcionarios se consideran disponibles al 100%.")

    inicio, fin, plan = agendar(milestones, inicio, args.modo, avisos, recursos,
                                args.esfuerzo)

    colores = colores_proyectos(milestones)
    gantts, error_gantt = [], None
    if not args.sin_gantt:
        gantts, error_gantt = generar_gantt(
            nombre, milestones, salida.parent, "portafolio", date.today(), plan,
            rango=(inicio, fin) if fin else None, colores=colores)
        if error_gantt:
            avisos.append(error_gantt)

    cron = {
        "inicio": inicio, "fin": fin, "modo": args.modo, "plan": plan,
        "gantts": gantts, "error_gantt": error_gantt, "reportes": []
    }

    # ---- Informes por proyecto: mismas fechas que el cronograma del portafolio
    informes = []
    if not args.sin_proyectos:
        for prio, _, pn, ms in proyectos_cargados:
            propios = {id(m) for m in ms}
            informes.append(generar_informe_proyecto(
                pn, prio, ms, [m for m in milestones if id(m) not in propios],
                milestones, plan, args, salida.parent, inicio, fin, colores))
        cron["reportes"] = [(r["nombre"], r["archivo"].name) for r in informes]

    avisos[:] = list(dict.fromkeys(avisos))
    salida.write_text(generar_md(nombre, milestones, avisos, cron), encoding="utf-8")

    for a in avisos:
        print(f"⚠️  {a}", file=sys.stderr)
    print("✅ Orden de prioridad: " + " → ".join(
        f"{p[2]} (P{p[0]:g})" if p[0] != math.inf else f"{p[2]} (sin prioridad)"
        for p in proyectos_cargados))
    print(f"✅ Proyectos: {len(args.yaml)}")
    print(f"✅ Funcionarios configurados: {len(recursos)}")
    print(f"✅ Generado: {salida}")
    for g in gantts:
        print(f"📊 Gantt: {salida.parent / g['archivo']}")
    for r in informes:
        print(f"📄 Proyecto {r['nombre']}: {r['archivo']}"
              + (f" (+{r['n_gantts']} Gantt)" if r["n_gantts"] else ""))


if __name__ == "__main__":
    main()