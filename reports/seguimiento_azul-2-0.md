# Seguimiento PMO — Azul 2.0

- **Prioridad en el portafolio:** 2
- **Fecha de corte:** 19-11-2026
- **PM / Responsable:** _por definir_
- **Leyenda de estado:** ⬜ Pendiente | 🔵 En curso | ✅ Listo | ⏸️ Pausado

## 1. Resumen ejecutivo

| Indicador | Valor |
|---|---:|
| Milestones | 10 |
| Work items | 36 |
| Días estimados totales | 370 |
| Días pendientes | 277.5 |
| Story points totales | 209 |
| Items sin estimar | 0 |
| Incertidumbre alta / media / baja | 4 / 14 / 18 |
| Inicio planificado | 19-11-2026 |
| Término estimado (optimizado) | 01-05-2029 |
| Cuello de botella (junior) | DG (173 días hábiles pendientes) |
| Pico de carga senior (máx. simultáneo) | 40% |
| Finalizados / en curso / pausados / backlog | 10 / 1 / 1 / 24 |
| % avance global (ponderado por días) | 25% |

## 2. Tablero por milestone

| # | Milestone | Items | Días | Pend. | Pts | Inicio | Fin | Sin estimar | Estado | % Avance |
|--:|---|--:|--:|--:|--:|---|---|--:|---|--:|
| 1 | [Migración 1](#1-migración-1-azul-20) | 9 | 85 | 45 | 47 | 19-11-2026 | 29-09-2028 | 0 | 🔵 En curso | 47% |
| 2 | [Release Áridos/ Químicos](#2-release-áridos-químicos-azul-20) | 1 | 15 | 0 | 8 | — | — | 0 | ✅ Listo | 100% |
| 3 | [Release Hormigones](#3-release-hormigones-azul-20) | 8 | 90 | 52.5 | 49 | 19-11-2026 | 24-11-2028 | 0 | 🔵 En curso | 42% |
| 4 | [Control de cambios Piloto](#4-control-de-cambios-piloto-azul-20) | 3 | 15 | 15 | 9 | 16-04-2027 | 12-05-2027 | 0 | ⬜ Pendiente | 0% |
| 5 | [Release Aceros](#5-release-aceros-azul-20) | 1 | 15 | 15 | 8 | 24-11-2028 | 19-12-2028 | 0 | ⬜ Pendiente | 0% |
| 6 | [Release Sensores](#6-release-sensores-azul-20) | 6 | 30 | 30 | 18 | 12-05-2027 | 01-07-2027 | 0 | ⏸️ Pausado | 0% |
| 7 | [Release Suelos](#7-release-suelos-azul-20) | 1 | 35 | 35 | 21 | 07-03-2029 | 01-05-2029 | 0 | ⬜ Pendiente | 0% |
| 8 | [Release Sensores mejora continua](#8-release-sensores-mejora-continua-azul-20) | 2 | 20 | 20 | 11 | 01-07-2027 | 03-08-2027 | 0 | ⬜ Pendiente | 0% |
| 9 | [UX/UI Agencia](#9-uxui-agencia-azul-20) | 1 | 35 | 35 | 21 | 11-01-2029 | 07-03-2029 | 0 | ⬜ Pendiente | 0% |
| 10 | [Mejoras evolutivas plataforma](#10-mejoras-evolutivas-plataforma-azul-20) | 4 | 30 | 30 | 17 | 03-08-2027 | 11-01-2029 | 0 | ⬜ Pendiente | 0% |

## 3. Cronograma (Gantt)

**Gantt por milestone** · [abrir en pestaña nueva](gantt_azul-2-0_resumen.html)

<iframe src="gantt_azul-2-0_resumen.html" width="100%" height="564" style="border:0" loading="lazy"></iframe>

**Gantt por work item** · [abrir en pestaña nueva](gantt_azul-2-0_detalle.html)

<iframe src="gantt_azul-2-0_detalle.html" width="100%" height="940" style="border:0" loading="lazy"></iframe>

**Gantt por desarrollador** · [abrir en pestaña nueva](gantt_azul-2-0_desarrolladores.html)

<iframe src="gantt_azul-2-0_desarrolladores.html" width="100%" height="490" style="border:0" loading="lazy"></iframe>

**Carga de seniors** · [abrir en pestaña nueva](gantt_azul-2-0_carga_seniors.html)

<iframe src="gantt_azul-2-0_carga_seniors.html" width="100%" height="410" style="border:0" loading="lazy"></iframe>

> **Supuestos del cronograma:** inicio 19-11-2026; días hábiles (lun-vie) sin feriados; solo se agenda el trabajo pendiente (los finalizados no aparecen y los avanzados cuentan solo sus días restantes); los proyectos se agendan juntos sobre los mismos recursos, por orden de prioridad; una ausencia pausa el item (no suma días) y se retoma al volver; por desarrollador: cada junior hace una tarea a la vez, ninguna senior supera el 100% de carga (suma de dedicacion_sr de sus tareas simultáneas) y el orden se optimiza para terminar lo antes posible.

> Cronograma tomado del portafolio (no se reprograma este proyecto por separado); prioridad 2. Recursos compartidos con Plataforma 3.0: CG, DG, IV, NM, NS, OS.

## 4. Detalle de work items

### 1. Migración 1 (Azul 2.0)

**Total:** 85 días (45 pendientes) · 47 pts · 9 items · 47% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Módulo Servicios informes (filtros) | S | 5 | 3 | 🟢 baja | — | — | ✅ Listo | Jr: DG · Sr: NS (20%) | 100% |  |
| Corrección de informes con mal clasificados | M | 15 | 8 | 🟢 baja | — | — | ✅ Listo | Jr: JP · Sr: EM (20%) | 100% |  |
| Bloqueo Intranet Azul para evitar informes mal clasificados | S | 5 | 3 | 🟡 media | — | — | ✅ Listo | Jr: JP · Sr: EM (20%) | 100% |  |
| Sincronización servicios ejecutados módulo resultados (muestreo y ensayos) | S | 5 | 3 | 🟡 media | — | — | ✅ Listo | Sr: NS (20%) | 100% |  |
| Dashboard (genérico) Release Piloto | S | 5 | 3 | 🟡 media | — | — | ✅ Listo | Sr: EM (20%) | 100% |  |
| Actualización campos fecha de ensayo (inicio- termino) | S | 5 | 3 | 🟢 baja | — | — | ✅ Listo | Sr: IV (20%) | 100% |  |
| Correcciones detectadas Piloto | M | 15 | 8 | 🟢 baja | 06-09-2028 | 29-09-2028 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |
| Integración LIMS > Capa 2 | M | 15 | 8 | 🔴 alta | 14-12-2026 | 06-01-2027 | ⬜ Pendiente | Jr: NM · Sr: IV (20%) | 0% |  |
| Integración ProjectUpdate (LIMS > SOL) | M | 15 | 8 | 🔴 alta | 19-11-2026 | 10-12-2026 | ⬜ Pendiente | Sr: CG (20%) | 0% |  |

### 2. Release Áridos/ Químicos (Azul 2.0)

**Total:** 15 días (0 pendientes) · 8 pts · 1 items · 100% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Módulo Resultados (aridos/ químicos) - Muestreo y Ensayos | M | 15 | 8 | 🟢 baja | — | — | ✅ Listo | Jr: DG · Sr: NS (20%) | 100% |  |

### 3. Release Hormigones (Azul 2.0)

**Total:** 90 días (52.5 pendientes) · 49 pts · 8 items · 42% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Migración data (muestreo y samplings > capa 2) | S | 5 | 3 | 🟢 baja | — | — | ✅ Listo | Sr: EM (50%) | 100% |  |
| Módulo Resultados hormigones (Muestreo y Ensayos) | M | 15 | 8 | 🟢 baja | — | — | ✅ Listo | Jr: OS · Sr: NS (20%) | 100% |  |
| Libro de obras | S | 5 | 3 | 🟡 media | 29-09-2028 | 09-10-2028 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |
| Módulo de Administración FTP / Integración | S | 5 | 3 | 🟢 baja | 31-08-2028 | 06-09-2028 | 🔵 En curso | Jr: DG · Sr: NS (20%) | 50% |  |
| Análisis y tendencias (UX/UI) | M | 15 | 8 | 🟡 media | — | — | ✅ Listo | Jr: OS · Sr: NS (20%) | 100% |  |
| Análisis y tendencias (Refactorización Consolidate Data) | M | 15 | 8 | 🟡 media | 19-11-2026 | 10-12-2026 | ⬜ Pendiente | Sr: NS (20%) | 0% |  |
| Email de alertas clientes | M | 15 | 8 | 🟡 media | 09-10-2028 | 01-11-2028 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |
| Migración alertas operacionales internas Hormigones | M | 15 | 8 | 🟡 media | 01-11-2028 | 24-11-2028 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |

### 4. Control de cambios Piloto (Azul 2.0)

**Total:** 15 días (15 pendientes) · 9 pts · 3 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Perfil de usuario interno | S | 5 | 3 | 🟢 baja | 16-04-2027 | 26-04-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Mejoras en formato de descargas | S | 5 | 3 | 🟢 baja | 26-04-2027 | 04-05-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Mejoras en filtros (quedan) | S | 5 | 3 | 🟢 baja | 04-05-2027 | 12-05-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |

### 5. Release Aceros (Azul 2.0)

**Total:** 15 días (15 pendientes) · 8 pts · 1 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Servicios Aceros Muestreo y ensayos para informes DAC | M | 15 | 8 | 🟢 baja | 24-11-2028 | 19-12-2028 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |

### 6. Release Sensores (Azul 2.0)

**Total:** 30 días (30 pendientes) · 18 pts · 6 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Módulos de administración de proyectos | S | 5 | 3 | 🟢 baja | 07-06-2027 | 15-06-2027 | ⏸️ Pausado | Jr: OS · Sr: NS (20%) | 0% |  |
| Gráficos inclinómetros | S | 5 | 3 | 🟢 baja | 15-06-2027 | 23-06-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Gráficos acelerómetros | S | 5 | 3 | 🟢 baja | 28-05-2027 | 07-06-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Gráficos Strain Gages | S | 5 | 3 | 🟢 baja | 12-05-2027 | 20-05-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Modificación gestión de permisos de usuario | S | 5 | 3 | 🟢 baja | 20-05-2027 | 28-05-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Alertas internas por intermitencia | S | 5 | 3 | 🟢 baja | 23-06-2027 | 01-07-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |

### 7. Release Suelos (Azul 2.0)

**Total:** 35 días (35 pendientes) · 21 pts · 1 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Servicios cd Muestreo y ensayos e informes DGL (suelos) | L | 35 | 21 | 🟡 media | 07-03-2029 | 01-05-2029 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |

### 8. Release Sensores mejora continua (Azul 2.0)

**Total:** 20 días (20 pendientes) · 11 pts · 2 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Mejora continua (nuevas alertas y nuevas funcionalidades) | M | 15 | 8 | 🔴 alta | 01-07-2027 | 26-07-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Dashboard de inicio | S | 5 | 3 | 🔴 alta | 26-07-2027 | 03-08-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |

### 9. UX/UI Agencia (Azul 2.0)

**Total:** 35 días (35 pendientes) · 21 pts · 1 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Ajustes UX/ UI | L | 35 | 21 | 🟡 media | 11-01-2029 | 07-03-2029 | ⬜ Pendiente | Jr: DG, OS · Sr: NS (40%) | 0% |  |

### 10. Mejoras evolutivas plataforma (Azul 2.0)

**Total:** 30 días (30 pendientes) · 17 pts · 4 items · 0% avance

| Work item | Tamaño | Días | Pts | Incertidumbre | Inicio plan | Fin plan | Estado | Responsable | % | Notas |
|---|:-:|--:|--:|:-:|---|---|---|---|--:|---|
| Dashboard DHI (cementos- áridos- químicos) | M | 15 | 8 | 🟡 media | 19-12-2028 | 11-01-2029 | ⬜ Pendiente | Jr: DG · Sr: NS (20%) | 0% |  |
| Dashboard Hormigones | S | 5 | 3 | 🟡 media | 11-08-2027 | 19-08-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Dashboard DAC | S | 5 | 3 | 🟡 media | 03-08-2027 | 11-08-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |
| Dashboard DGL (suelos) | S | 5 | 3 | 🟡 media | 19-08-2027 | 27-08-2027 | ⬜ Pendiente | Jr: OS · Sr: NS (20%) | 0% |  |

## 5. Carga por responsable (trabajo pendiente)

| Persona | Rol | Proyectos | Items abiertos | Días-persona pendientes | Carga pico |
|---|---|---|--:|--:|--:|
| DG | Junior | Azul 2.0 | 9 | 152.5 | — |
| OS | Junior | Azul 2.0 | 15 | 115.0 | — |
| NS | Senior | Azul 2.0 | 24 | 56.5 | 40% |
| NM | Junior | Azul 2.0 | 1 | 15.0 | — |
| CG | Senior | Azul 2.0 | 1 | 3.0 | 20% |
| IV | Senior | Azul 2.0 | 1 | 3.0 | 20% |

> Supuestos: cada junior asignado dedica los días pendientes completos del item; el senior aporta días pendientes × dedicacion_sr. Carga pico = máximo simultáneo de la senior en el cronograma.

## 6. Riesgos y alertas (derivados de la estimación y el estado)

| Milestone | Work item | Motivo | Días | Mitigación / Acción | Dueño | Estado |
|---|---|---|--:|---|---|---|
| Migración 1 | Integración LIMS > Capa 2 | incertidumbre alta | 15 |  |  | ⬜ Abierto |
| Migración 1 | Integración ProjectUpdate (LIMS > SOL) | incertidumbre alta | 15 |  |  | ⬜ Abierto |
| Release Sensores mejora continua | Mejora continua (nuevas alertas y nuevas funcionalidades) | incertidumbre alta | 15 |  |  | ⬜ Abierto |
| Release Sensores mejora continua | Dashboard de inicio | incertidumbre alta | 5 |  |  | ⬜ Abierto |
| Mejoras evolutivas plataforma | Dashboard DHI (cementos- áridos- químicos) | incertidumbre media | 15 |  |  | ⬜ Abierto |
| Mejoras evolutivas plataforma | Dashboard Hormigones | incertidumbre media | 5 |  |  | ⬜ Abierto |
| Mejoras evolutivas plataforma | Dashboard DAC | incertidumbre media | 5 |  |  | ⬜ Abierto |
| Mejoras evolutivas plataforma | Dashboard DGL (suelos) | incertidumbre media | 5 |  |  | ⬜ Abierto |
| Release Hormigones | Libro de obras | incertidumbre media | 5 |  |  | ⬜ Abierto |
| Release Hormigones | Análisis y tendencias (Refactorización Consolidate Data) | incertidumbre media | 15 |  |  | ⬜ Abierto |
| Release Hormigones | Email de alertas clientes | incertidumbre media | 15 |  |  | ⬜ Abierto |
| Release Hormigones | Migración alertas operacionales internas Hormigones | incertidumbre media | 15 |  |  | ⬜ Abierto |
| Release Suelos | Servicios cd Muestreo y ensayos e informes DGL (suelos) | incertidumbre media | 35 |  |  | ⬜ Abierto |
| UX/UI Agencia | Ajustes UX/ UI | incertidumbre media | 35 |  |  | ⬜ Abierto |
| Release Sensores | Módulos de administración de proyectos | pausado | 5 |  |  | ⬜ Abierto |

## 7. Registro de riesgos adicionales

| ID | Riesgo | Probabilidad | Impacto | Mitigación | Dueño | Estado |
|---|---|---|---|---|---|---|
| R-01 |  |  |  |  |  | ⬜ Abierto |

## 8. Bloqueos y dependencias

| Fecha | Descripción | Afecta a | Responsable | Fecha compromiso | Estado |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 9. Decisiones y acuerdos

| Fecha | Decisión / acuerdo | Participantes |
|---|---|---|
|  |  |  |

## 10. Control de cambios de alcance

| Fecha | Cambio | Impacto (días/pts) | Aprobado por |
|---|---|---|---|
|  |  |  |  |
