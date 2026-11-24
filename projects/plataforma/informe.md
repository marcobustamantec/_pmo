---
marp: true
theme: elige-idiem
paginate: true
size: 16:9
footer: "GDD | Reporte de estado del proyecto | 24.nov.2026"
---

<!-- _class: portada -->

# Plataforma de Clientes

## Informe de estado y seguimiento

*Acceso digital a informes históricos y resultados de ensayos*

**Project Status Report**

Período reportado: 01-11-2026 – 30-11-2026

Fecha de actualización: 24-11-2026

---

# 1. Resumen del proyecto

| Dimensión               | Situación                                            |
| ----------------------- | ---------------------------------------------------- |
| Estado general          | 🟡 Atención (→ estable)                               |
| Fase actual             | Desarrollo                                           |
| Avance real             | 50 : 209 puntos — **24%** (planificado: no definido) |
| Célula                  | Célula de clientes                                   |
| Cierre de tareas        | 10 de 36                                             |
| Cumplimiento de hitos   | 1 de 10                                              |
| Riesgos identificados   | 4 (críticos: 2)                                      |
| Bloqueos activos        | 1                                                    |
| Término plan / estimado | 31-03-2027 / 30-04-2027                              |

---

# 1. Resumen del proyecto (cont)

## Resumen ejecutivo

El proyecto se encuentra en fase de desarrollo. Se ha avanzado en la definición funcional y en la construcción de los componentes principales de la plataforma.

**Desviación**

- **Causa:** Dependencia de datos históricos e integraciones, y definición pendiente de autenticación.
- **Acción:** Cerrar autenticación e integraciones; incorporar datos históricos de forma progresiva.

---

# 1. Resumen del proyecto (cont)

## Avances del período

- Definición de alcance funcional
- Diseño de arquitectura de solución
- Desarrollo de componentes iniciales

## Alertas

- Dependencia de disponibilidad y calidad de datos históricos
- Definición de mecanismos de integración con sistemas institucionales

---

# 2. Alcance y objetivos

## Objetivo general

Implementar una plataforma digital que permita a los clientes consultar sus informes históricos y resultados de ensayos, facilitando el acceso oportuno, seguro y centralizado a la información generada por IDIEM.

## Alcance

1. Consulta de informes históricos
2. Consulta de resultados de ensayos
3. Visualización digital de documentos
4. Descarga de informes y resultados
5. Acceso seguro mediante autenticación

## Resultados esperados

- Clientes consultan sus informes sin solicitarlos manualmente
- Clientes acceden a planillas consolidadas de sus resultados

---

# 3. Fases del proyecto

## Avance por hitos

| Componente / Entregable          | Descripción                                                              | Puntos cerrados | Puntos totales | Avance |
| -------------------------------- | ------------------------------------------------------------------------ | --------------: | -------------: | -----: |
| Piloto (desarrollos)             | Fase inicial operativa integrada con LIMS                                |              23 |             47 |    49% |
| Release Áridos/ Químicos         | Entrega de resultados para los servicios de ensayos áridos y de químicos |               8 |              8 |   100% |
| Release Hormigones               | Entrega de resultados para los servicios de hormigones                   |              19 |             49 |    39% |
| Control de cambios Piloto        | —                                                                        |               0 |              9 |     0% |
| Release Aceros                   | Entrega de resultados para los servicios de aceros                       |               0 |              8 |     0% |
| Release Sensores                 | —                                                                        |               0 |             18 |     0% |
| Release Suelos                   | —                                                                        |               0 |             21 |     0% |
| Release Sensores mejora continua | —                                                                        |               0 |             11 |     0% |

---

# 3. Fases del proyecto (cont)

## Avance por hitos

| Componente / Entregable       | Descripción | Puntos cerrados | Puntos totales |  Avance |
| ----------------------------- | ----------- | --------------: | -------------: | ------: |
| UX/UI Agencia                 | —           |               0 |             21 |      0% |
| Mejoras evolutivas plataforma | —           |               0 |             17 |      0% |
| **Total**                     | —           |          **50** |        **209** | **24%** |

---

# 4. Riesgos y problemas

## Situaciones que pueden afectar o están afectando el proyecto

| ID    | Riesgo / Problema                                     | Probabilidad | Impacto | Nivel      |
| ----- | ----------------------------------------------------- | ------------ | ------- | ---------- |
| R-001 | Disponibilidad de información histórica               | Alta         | Alto    | 🔴 Crítico  |
| R-002 | Dependencia de integraciones institucionales          | Media        | Alto    | 🟠 Alto     |
| R-003 | Control de acceso a información de clientes           | Media        | Alto    | 🟠 Alto     |
| R-004 | Calidad y consistencia de los documentos descargables | Media        | Medio   | 🟡 Moderado |
| P-001 | Definición pendiente del mecanismo de autenticación   | —            | Alto    | 🔴 Crítico  |

---

# 4. Riesgos y problemas (cont)

## Plan de respuesta

| ID    | Acción preventiva / correctiva                                                                                   | Responsable                 | Fecha      |
| ----- | ---------------------------------------------------------------------------------------------------------------- | --------------------------- | ---------- |
| R-001 | Identificar fuentes, evaluar calidad de los datos y definir incorporación progresiva                             | Líder técnico               | 15-12-2026 |
| R-002 | Identificar sistemas y responsables, definir contratos de servicio y probar integraciones temprano               | Líder de desarrollo         | 10-12-2026 |
| R-003 | Modelo de autorización por cliente, controles a nivel de documento, pruebas de aislamiento y registro de accesos | Responsable de seguridad TI | 15-12-2026 |
| R-004 | Identificadores únicos, validación de integridad y vigencia, reglas de versionamiento                            | Analista funcional          | 15-01-2027 |
| P-001 | Validar alternativas, acordar el mecanismo con responsables institucionales e implementarlo                      | Jefe de proyecto            | 05-12-2026 |

---

# 4. Riesgos y problemas (cont)

## Planes de contingencia

| ID    | Contingencia si el riesgo se materializa                                            |
| ----- | ----------------------------------------------------------------------------------- |
| R-001 | Habilitar primero la información disponible e incorporar fuentes históricas después |
| R-002 | Carga intermedia y priorizar integraciones esenciales para la primera versión       |
| R-003 | Suspender accesos afectados y activar protocolo de respuesta a incidentes           |
| R-004 | Deshabilitar descarga de documentos afectados y publicarlos nuevamente              |

---

# 5. Decisiones y acuerdos

## Definiciones necesarias para mantener la ejecución del proyecto

| Decisión / Acuerdo                                                           | Responsable de decidir                          | Fecha requerida | Estado    |
| ---------------------------------------------------------------------------- | ----------------------------------------------- | --------------- | --------- |
| Mecanismo de autenticación y vinculación de usuarios con cuentas de clientes | Jefe de proyecto / responsables institucionales | 05-12-2026      | Pendiente |

---

# 6. Capacidad

## Puntos asignados por desarrollador

| Persona | Perfil             | Puntos asignados | Cerrados | Pendientes | Tareas abiertas | Observación                            |
| ------- | ------------------ | ---------------: | -------: | ---------: | --------------: | -------------------------------------- |
| NS      | Senior             |              173 |       30 |        143 |              24 | Concentra 44% de los puntos pendientes |
| IV      | Senior             |               11 |        3 |          8 |               1 | —                                      |
| CG      | Senior             |                8 |        0 |          8 |               1 | —                                      |
| EM      | Senior             |               17 |       17 |          0 |               0 | Sin carga pendiente                    |
| DG      | Desarrollador (jr) |               99 |       11 |         88 |               9 | —                                      |
| OS      | Desarrollador (jr) |               84 |       16 |         68 |              15 | —                                      |
| NM      | Desarrollador (jr) |                8 |        0 |          8 |               1 | —                                      |
| JP      | Desarrollador (jr) |               11 |       11 |          0 |               0 | Sin carga pendiente                    |


<small>Los puntos de una tarea con más de un desarrollador se cuentan completos para cada uno.</small>

---

# 7. Dependencias y bloqueos

## Condiciones externas necesarias para continuar la ejecución

| Dependencia                              | Contraparte              | Requerimiento                              | Fecha requerida | Estado    |
| ---------------------------------------- | ------------------------ | ------------------------------------------ | --------------- | --------- |
| Datos históricos de informes y ensayos   | Por definir              | Fuentes disponibles y con calidad validada | 15-12-2026      | Pendiente |
| Integración con sistemas institucionales | Responsables de sistemas | Contratos de servicio e interfaces         | 10-12-2026      | En curso  |

### Bloqueos actuales

- **Bloqueo:** Definición pendiente del mecanismo de autenticación.
  - **Impacto:** Impide cerrar el diseño de acceso de usuarios y condiciona las pruebas integrales.
  - **Responsable de resolver:** Jefe de proyecto.
  - **Fecha comprometida:** 05-12-2026.

**Apoyo requerido:** Acordar con los responsables institucionales el mecanismo de autenticación.


---

# 8. Plan de trabajo pendiente

## Actividades necesarias para completar el proyecto

| Actividad (hito)                 | Responsables       | Tareas abiertas | Puntos pendientes | Estado    |
| -------------------------------- | ------------------ | --------------: | ----------------: | --------- |
| Piloto (desarrollos)             | CG, DG, IV, NM, NS |          3 de 9 |                24 | En curso  |
| Release Hormigones               | DG, NS             |          5 de 8 |                30 | En curso  |
| Control de cambios Piloto        | NS, OS             |          3 de 3 |                 9 | Pendiente |
| Release Aceros                   | DG, NS             |          1 de 1 |                 8 | Pendiente |
| Release Sensores                 | NS, OS             |          6 de 6 |                18 | Pendiente |
| Release Suelos                   | DG, NS             |          1 de 1 |                21 | Pendiente |
| Release Sensores mejora continua | NS, OS             |          2 de 2 |                11 | Pendiente |
| UX/UI Agencia                    | DG, NS, OS         |          1 de 1 |                21 | Pendiente |

---

# 8. Plan de trabajo pendiente (cont)

## Actividades necesarias para completar el proyecto

| Actividad (hito)              | Responsables | Tareas abiertas | Puntos pendientes | Estado    |
| ----------------------------- | ------------ | --------------: | ----------------: | --------- |
| Mejoras evolutivas plataforma | DG, NS, OS   |          4 de 4 |                17 | Pendiente |

**Siguiente hito:** Primera versión funcional para validación — 15-12-2026 (resp.: Célula de clientes). Criterio: Versión funcional disponible para validación.

---

# 9. Próximos pasos

## Compromisos concretos para el siguiente período

| N°  | Acción                                               | Responsable         | Fecha compromiso | Resultado esperado               |
| --- | ---------------------------------------------------- | ------------------- | ---------------- | -------------------------------- |
| 1   | Validar disponibilidad y calidad de datos históricos | Líder técnico       | 15-12-2026       | Diagnóstico de fuentes y calidad |
| 2   | Cerrar definición de autenticación                   | Jefe de proyecto    | 05-12-2026       | Mecanismo acordado               |
| 3   | Acordar integraciones con sistemas institucionales   | Líder de desarrollo | 10-12-2026       | Contratos de servicio definidos  |
| 4   | Entregar primera versión funcional para validación   | Líder de desarrollo | 15-12-2026       | Versión validada                 |

### Foco del siguiente período

1. Validar disponibilidad y calidad de datos históricos.
2. Cerrar definición de autenticación.
3. Acordar integraciones con sistemas institucionales.


---

# Conclusión

El proyecto avanza con una desviación moderada. Cumplir los próximos compromisos depende de cerrar la autenticación y asegurar los datos históricos.
