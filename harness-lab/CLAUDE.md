# Harness Lab — instrucciones para el agente constructor

## PARÁMETROS

- MODE: `LEARN`            # LEARN | BUILD — ver "Modo de trabajo"
- LANGUAGE: `Python 3.12`  # núcleo; Rust opcional solo para el sandbox (fase 5)
- MODEL_BACKENDS: `Anthropic Messages API` + `OpenAI-compatible` (modelos locales vía vLLM/llama.cpp)
- BENCHMARK: suite propia de 20 tareas (fase 0) + subconjunto de 50 tareas de SWE-bench Verified (fase 6)
- BUDGET: tope de coste por ejecución de evaluación = `0,50 €`  # el endpoint es gratuito en esta sesión; el tope es un cortafuegos contra bucles, no un presupuesto
- MODELO BASE DEL EXPERIMENTO: el que fija `HARNESS_LAB_MODEL` (el transporte lee el id de ahí; no se escribe el id en el repo)
- BUILD PUNTUAL: `harness_lab/core/loop.py::run_loop` implementado en BUILD (autorizado por el owner, 2026-10-10); el resto de la fase 1 y las demás fases siguen en LEARN

---

## Objetivo

Construir **Harness Lab**: un harness de agente de programación propio, escrito desde cero, con un
núcleo mínimo organizado en los siete subsistemas canónicos del paper *Harness Engineering:
Anatomy, Architecture, and Evolution of Coding Agents* (arXiv 2609.00006):

1. Agent loop
2. LLM integration
3. Tools & actions
4. Memory & context
5. Safety & permissions
6. Orchestration
7. Extensibility

Sobre ese núcleo se implementa, como **variante intercambiable por configuración**, el mecanismo
distintivo de cada harness del paper. El entregable final es un **experimento controlado**: misma
tarea, mismo modelo, distinta variante, con métricas comparables.

Además, el subsistema de memoria se extiende con un **sistema de memoria dinámica** capaz de
escribir, recuperar, corregir, olvidar y asociar recuerdos (fase 7).

## Reglas no negociables

- **Sin frameworks agénticos.** Nada de LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex ni
  similares. Solo SDKs de proveedor (o HTTP directo), stdlib y librerías de propósito general
  (pydantic, httpx, tree-sitter, pytest).
- **Fidelidad verificable.** Cuando se replica el mecanismo de un harness open source, se lee su
  código en el repo público y se cita en el ADR el fichero y el commit. Si no se ha leído, se dice:
  "basado en la descripción del paper, no verificado en código".
- **Claude Code: solo la descripción del paper y la documentación pública.** Ni la snapshot de
  código filtrada ni derivados "clean-room" de ella.
- **Ejecución aislada desde el primer día.** Toda herramienta que ejecute comandos corre dentro de
  un contenedor Docker desechable (`eval/sandbox.py`). Nunca en el host.
- **Cada variante detrás de una interfaz.** El núcleo no conoce las variantes. Se seleccionan por
  config (`harness.toml`) y deben poder combinarse cuando no sean incompatibles; si lo son, el
  registro lo declara y falla al cargar.
- **Nada se da por hecho sin evidencia.** Ninguna fase se cierra sin tests en verde y una ejecución
  de la suite de evaluación registrada. Prohibido declarar "funciona" o "mejora" sin el número.
- **Paradas obligatorias.** Al final de cada fase: resumen, resultados, decisiones abiertas, y
  esperar confirmación.

## Enmiendas aceptadas (fase 0)

Estas cinco enmiendas modifican el plan original y prevalecen sobre él.

1. **Potencia estadística desde la fase 0, diseño pareado.** Las comparaciones entre variantes son
   pareadas por tarea (McNemar exacto, `eval/stats.py`). `n` cuenta tareas, no ejecuciones: las
   semillas de una misma tarea no son independientes. Toda conclusión de la fase 6 cita el efecto
   mínimo detectable (`python -m eval.stats power`). El coste (tokens, turnos) se compara aparte:
   tiene mucha menos varianza que el éxito binario.
2. **Tareas de caso límite por mecanismo.** Cada mecanismo que una variante replica necesita al
   menos una tarea construida para dispararlo (campo `targets` de `task.toml`). Si una variante no
   tiene tarea que la active, su resultado nulo no significa nada y el informe lo dice.
3. **Combinación de variantes fuera del experimento.** El registro permite combinarlas, pero la
   fase 6 mide variantes individuales frente a la línea base; las interacciones no se evalúan.
4. **Procedencia en la memoria desde la fase 2.** La compactación de las fases 2 y 4 registra de
   qué mensajes/hechos sale cada resumen. Sin eso, el borrado real propagado de la fase 7 es
   imposible. Se decide en el ADR de memoria de la fase 2.
5. **Tests deterministas, evaluación con modelo real.** Los tests de cada subsistema corren contra
   un backend de modelo guionizado (respuestas grabadas). Solo `eval/` usa modelos reales y cuesta
   dinero. El backend guionizado se especifica en la fase 1 junto a la interfaz de LLM (ver ADR 0005).

## Modo de trabajo

- **LEARN (por defecto):** el humano implementa la lógica central de cada subsistema y variante.
  El agente:
  - escribe la especificación de la interfaz y los tests que debe pasar, antes que el código;
  - escribe la infraestructura no didáctica: evaluación, contenedores, CLI, logging, fixtures;
  - revisa el código del humano con crítica directa: bugs, casos límite, divergencias respecto al
    harness original;
  - **no escribe la implementación central**, aunque se le pida de pasada. Para que lo haga, el
    humano cambia MODE a BUILD explícitamente para esa pieza;
  - cuando el humano se atasca, responde con preguntas o pistas graduadas, no con la solución.
- **BUILD:** implementa el agente, con las mismas reglas de evidencia.

## Estructura del repo

```
harness_lab/
  core/            # loop, messages, config, registry de variantes
  llm/             # transportes por proveedor, caché de prompt, conteo de tokens
  tools/           # bash, read, edit, write, search (ripgrep), glob
  memory/          # gestión de contexto + memoria dinámica (fase 7)
  safety/          # permisos, políticas, sandbox
  orchestration/   # subagentes
  ext/             # hooks, skills, MCP
  variants/        # una carpeta por harness: openhands/, aider/, pi/, ...
eval/
  tasks/           # suite propia (fase 0)
  runner.py        # ejecuta agente × tarea × semilla
  results/         # JSONL por ejecución
docs/
  adr/             # una decisión por fichero
  variants/        # ficha por variante: qué replica, fuente, diferencias
```

## Fases

### Fase 0 — Banco de pruebas (antes de cualquier agente) — CERRADA, ver docs/phase0.md
- 20 tareas reproducibles con repo inicial, enunciado, verificador oculto y solución de referencia.
- Runner con métricas por ejecución: éxito, turnos, tokens de entrada/salida, tokens cacheados,
  coste, tiempo de reloj, llamadas a herramientas y motivo de parada.
- Cierre: agente nulo 0 % con métricas válidas, y agente oráculo 100 % (enmienda: sin el oráculo,
  un 0 % no distingue "el agente no sabe" de "la tarea es imposible").

### Fase 1 — Suelo mínimo (estilo Mini-SWE-Agent)
- Bucle `while` lineal, una sola herramienta bash, historial sin poda, límites de pasos y coste.
- Cierre: línea base registrada en la suite.

### Fase 2 — Núcleo de siete subsistemas
- Interfaces para los siete subsistemas con implementación mínima.
- Herramientas tipadas (read/edit/write/search/glob) con edición por reemplazo exacto de subcadena única.
- Compactación por umbral básica, **con procedencia** (enmienda 4).
- Permisos: allow / ask / deny por herramienta y patrón.
- Cierre: el núcleo iguala o supera a la fase 1 en la suite; ADR por subsistema.

### Fase 3 — Variantes de bucle y control
- `openhands`: conversación event-sourced sobre un EventLog persistente, rama con cabeza movible,
  replay y fork; StuckDetector con sus 5 escenarios.
- `claude_code`: partición de llamadas en lotes por seguridad de concurrencia (por defecto no seguro).
- `codex`: ejecución paralela ordenada de herramientas.
- `gemini_cli`: detección de bucles híbrida (hash SHA-256 + chequeo con LLM a partir de N turnos).
- `mistral_vibe`: bucle como pipeline de middlewares (límites de turnos, coste y tokens, autocompactación).
- `hermes`: presupuesto de iteraciones + guardia verify-on-stop.
- `pi`: colas steer/followUp y guardia de envenenamiento por truncado.
- `opencode`: bucle log-as-queue, reanudable tras reinicio del proceso.
- `aider`: bucle de reflexión con lint y tests, con máximo de reflexiones.

### Fase 4 — Variantes de contexto y edición
- `aider`: resumen recursivo por mitades + repo map con tree-sitter (ranking de símbolos).
- `hermes`: compactación por linaje (`parent_session_id`).
- `pi`: árbol de sesión JSONL append-only con `/fork` y resúmenes de rama.
- `opencode`: resúmenes incrementales anclados con secciones obligatorias.
- `gemini_cli`: niveles de compresión por fichero (FULL/PARTIAL/SUMMARY/EXCLUDED).
- Edición: cascada difusa (`opencode`/`hermes`), RelativeIndenter (`aider`), reparación con LLM (`gemini_cli`).
- Caché de prompt: frontera estática/dinámica y auditoría de coste por fallos de caché (`pi`).

### Fase 5 — Seguridad, orquestación y extensibilidad
- Sandbox a nivel de SO en Linux con bubblewrap (`codex`); opcionalmente en Rust.
- Permisos sintácticos de comandos con tree-sitter-bash (`opencode`, `mistral_vibe`).
- Subagentes coordinador-trabajador con contexto bifurcado (`claude_code`, `codex`).
- Hooks de ciclo de vida, skills `SKILL.md` con divulgación progresiva y cliente MCP.
- Carga diferida de herramientas con búsqueda BM25 (`codex`, `hermes`).
- `openclaw`: subagente de memoria activa antes de cada respuesta (enlaza con la fase 7).

### Fase 6 — Experimento comparativo
- Matriz variante × tarea × 3 semillas, mismo modelo y presupuesto.
- Ampliar con el subconjunto de SWE-bench Verified (imágenes por instancia; riesgo de
  contaminación: válido para comparar variantes entre sí, no como medida absoluta).
- Informe: qué variantes mueven el éxito y cuáles solo el coste; intervalos de confianza y efecto
  mínimo detectable; ninguna conclusión con n insuficiente.

### Fase 7 — Memoria dinámica
- **Escritura:** hechos atómicos con procedencia (fuente, turno, autor, confianza) y deduplicación.
- **Bi-temporal:** cuándo fue cierto y cuándo se supo. Un hecho reemplazado se invalida, no se borra.
- **Corrección:** detección de contradicciones y supersesión con trazabilidad.
- **Olvido:** decaimiento por uso, supersesión y borrado real a petición, propagado a resúmenes y
  consolidaciones derivadas.
- **Asociación:** enlaces entre recuerdos y consolidación offline.
- **Recuperación** con presupuesto de contexto fijo.
- **Evaluación propia:** tareas multi-sesión con hechos que cambian, hechos a olvidar y preguntas
  que exigen asociar. Métricas: exactitud, recuerdos obsoletos servidos, fugas de hechos borrados,
  tokens de contexto. Comparar con la compactación de la fase 2.
- Justificar con datos cualquier uso de embeddings.

## Al cerrar cada fase entrega

1. Resumen de lo hecho (máximo 10 líneas).
2. Tabla de resultados de evaluación frente a la fase anterior.
3. ADRs nuevos.
4. Decisiones abiertas y riesgos.
5. Propuesta concreta para la siguiente fase, y **parada**.

## Comandos

```
python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m eval.setup [--ca /ruta/ca.crt]        # imagen del sandbox
.venv/bin/python -m pytest -q                              # tests (los de Docker se saltan sin daemon)
.venv/bin/python -m eval.runner --agent null --tasks all --seeds 0 --out eval/results/x.jsonl
.venv/bin/python -m eval.report eval/results/x.jsonl [--compare A B]
.venv/bin/python -m eval.stats power
```
