---
marp: true
theme: elige-idiem
paginate: true
size: 16:9
---

<!-- _class: portada -->

# Plataforma de Clientes

## Informe de estado y seguimiento


Fecha de actualización: 24-11-2026

---

## Resumen del proyecto

| Dimensión             | Situación                                           |
| --------------------- | --------------------------------------------------- |
| Estado general        | 🟡 Atención (→ estable)                              |
| Fase actual           | Desarrollo                                          |
| Avance real           | 25 : 84 puntos — **30%** (planificado: no definido) |
| Célula                | Célula de clientes                                  |
| Cierre de tareas      | 10 de 34                                            |
| Cumplimiento de hitos | 2 de 10                                             |
| Riesgos identificados | 4 (críticos: 1)                                     |
| Bloqueos activos      | 1                                                   |

### Resumen ejecutivo

El proyecto se encuentra en fase de desarrollo. Se ha avanzado en la definición funcional y en la construcción de los componentes principales de la plataforma.

---

## Resumen del proyecto (cont)

**Término plan:** 31-03-2027 · **Término estimado:** 30-04-2027

### Desviación

- **Causa:** Dependencia de datos históricos e integraciones, y definición pendiente de autenticación.
- **Acción:** Cerrar autenticación e integraciones; incorporar datos históricos de forma progresiva.

### Avances del período

- Definición de alcance funcional
- Diseño de arquitectura de solución
- Desarrollo de componentes iniciales

### Alertas

- Dependencia de disponibilidad y calidad de datos históricos
- Definición de mecanismos de integración con sistemas institucionales

---

## Alcance y objetivos

### Objetivo general

Implementar una plataforma digital que permita a los clientes consultar sus informes históricos y resultados de ensayos, facilitando el acceso oportuno, seguro y centralizado a la información generada por IDIEM.

### Alcance

1. Consulta de informes históricos
2. Consulta de resultados de ensayos
3. Visualización digital de documentos
4. Descarga de informes y resultados
5. Acceso seguro mediante autenticación

### Resultados esperados

- Clientes consultan sus informes sin solicitarlos manualmente
- Clientes acceden a planillas consolidadas de sus resultados

---

## Fases del proyecto

### Avance por hitos

| Componente / Entregable          | Descripción                                                              | Puntos cerrados | Puntos totales | Avance |
| -------------------------------- | ------------------------------------------------------------------------ | --------------: | -------------: | -----: |
| Piloto                           | Fase inicial operativa integrada con LIMS                                |              13 |             13 |   100% |
| Release Áridos/ Químicos         | Entrega de resultados para los servicios de ensayos áridos y de químicos |               3 |              3 |   100% |
| Control de cambios Piloto        | Mejoras detectadas en la fase de piloto y correcciones de errores        |               0 |              8 |     0% |
| Release Hormigones               | Entrega de resultados para los servicios de hormigones                   |               9 |             21 |    43% |
| Release Aceros                   | Entrega de resultados para los servicios de aceros                       |               0 |              3 |     0% |
| Release Sensores                 | —                                                                        |               0 |             12 |     0% |
| Release Geotecnia                | —                                                                        |               0 |              5 |     0% |
| Release Sensores mejora continua | —                                                                        |               0 |              5 |     0% |

---

## Fases del proyecto (cont)

### Avance por hitos

| Componente / Entregable       | Descripción | Puntos cerrados | Puntos totales |  Avance |
| ----------------------------- | ----------- | --------------: | -------------: | ------: |
| UX/UI Agencia                 | —           |               0 |              5 |      0% |
| Mejoras evolutivas plataforma | —           |               0 |              9 |      0% |
| **Total**                     | —           |          **25** |         **84** | **30%** |

---

## Riesgos y problemas

### Situaciones que pueden afectar o están afectando el proyecto

| ID    | Riesgo / Problema                                     | Probabilidad | Impacto | Nivel      |
| ----- | ----------------------------------------------------- | ------------ | ------- | ---------- |
| R-001 | Disponibilidad de información histórica               | Alta         | Alto    | 🔴 Crítico  |
| R-002 | Dependencia de integraciones institucionales          | Media        | Alto    | 🟠 Alto     |
| R-003 | Control de acceso a información de clientes           | Media        | Alto    | 🟠 Alto     |
| R-004 | Calidad y consistencia de los documentos descargables | Media        | Medio   | 🟡 Moderado |
| P-001 | Definición pendiente del mecanismo de autenticación   | —            | Alto    | 🔴 Crítico  |

---

## Riesgos y problemas (cont)

### Plan de respuesta

| ID    | Acción preventiva / correctiva                                                                                   | Responsable                 | Fecha      |
| ----- | ---------------------------------------------------------------------------------------------------------------- | --------------------------- | ---------- |
| R-001 | Identificar fuentes, evaluar calidad de los datos y definir incorporación progresiva                             | Líder técnico               | 15-12-2026 |
| R-002 | Identificar sistemas y responsables, definir contratos de servicio y probar integraciones temprano               | Líder de desarrollo         | 10-12-2026 |
| R-003 | Modelo de autorización por cliente, controles a nivel de documento, pruebas de aislamiento y registro de accesos | Responsable de seguridad TI | 15-12-2026 |
| R-004 | Identificadores únicos, validación de integridad y vigencia, reglas de versionamiento                            | Analista funcional          | 15-01-2027 |
| P-001 | Validar alternativas, acordar el mecanismo con responsables institucionales e implementarlo                      | Jefe de proyecto            | 05-12-2026 |

---

## Riesgos y problemas (cont)

### Planes de contingencia

| ID    | Contingencia si el riesgo se materializa                                            |
| ----- | ----------------------------------------------------------------------------------- |
| R-001 | Habilitar primero la información disponible e incorporar fuentes históricas después |
| R-002 | Carga intermedia y priorizar integraciones esenciales para la primera versión       |
| R-003 | Suspender accesos afectados y activar protocolo de respuesta a incidentes           |
| R-004 | Deshabilitar descarga de documentos afectados y publicarlos nuevamente              |

---

## Decisiones y acuerdos

### Definiciones necesarias para mantener la ejecución del proyecto

| Decisión / Acuerdo                                                           | Responsable de decidir                          | Fecha requerida | Estado    |
| ---------------------------------------------------------------------------- | ----------------------------------------------- | --------------- | --------- |
| Mecanismo de autenticación y vinculación de usuarios con cuentas de clientes | Jefe de proyecto / responsables institucionales | 05-12-2026      | Pendiente |

---

## Capacidad

### Puntos asignados por desarrollador

| Recurso / Perfil | Puntos asignados | Cerrados | Pendientes | Tareas abiertas | Observación                            |
| ---------------- | ---------------: | -------: | ---------: | --------------: | -------------------------------------- |
| NS               |               57 |        6 |         51 |              20 | Concentra 46% de los puntos pendientes |
| OS               |               42 |        6 |         36 |              16 | —                                      |
| DG               |               31 |        6 |         25 |               8 | —                                      |
| JP               |                5 |        5 |          0 |               0 | Sin carga pendiente                    |
| EM               |                9 |        9 |          0 |               0 | Sin carga pendiente                    |
| IV               |                2 |        2 |          0 |               0 | Sin carga pendiente                    |


<small>Los puntos de una tarea con más de un desarrollador se cuentan completos para cada uno.</small>

---

## Dependencias y bloqueos

### Condiciones externas necesarias para continuar la ejecución

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

## Plan de trabajo pendiente

### Actividades necesarias para completar el proyecto

| Actividad                                | Responsable | Inicio      | Término     | Prioridad | Estado    |
| ---------------------------------------- | ----------- | ----------- | ----------- | --------- | --------- |
| Control de cambios Piloto (8 pts)        | OS          | Por definir | Por definir | Media     | Pendiente |
| Release Hormigones (12 pts)              | DG, NS      | Por definir | Por definir | Alta      | En curso  |
| Release Aceros (3 pts)                   | DG, NS      | Por definir | Por definir | Media     | Pendiente |
| Release Sensores (12 pts)                | NS, OS      | Por definir | Por definir | Media     | Pendiente |
| Release Geotecnia (5 pts)                | DG, NS      | Por definir | Por definir | Media     | Pendiente |
| Release Sensores mejora continua (5 pts) | NS, OS      | Por definir | Por definir | Media     | Pendiente |
| UX/UI Agencia (5 pts)                    | DG, NS, OS  | Por definir | Por definir | Media     | Pendiente |
| Mejoras evolutivas plataforma (9 pts)    | DG, NS, OS  | Por definir | Por definir | Media     | Pendiente |

**Siguiente hito:** Primera versión funcional para validación — 15-12-2026 (resp.: Célula de clientes). Criterio: Versión funcional disponible para validación.

---

## Próximos pasos

### Compromisos concretos para el siguiente período

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

## Conclusión

El proyecto avanza con una desviación moderada. Cumplir los próximos compromisos depende de cerrar la autenticación y asegurar los datos históricos.
