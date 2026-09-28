# Uso de IA

## Herramientas

- Claude Code (Claude Opus 5.5), integrado en VS Code.

## Para qué la utilicé

- Analizar el código existente y el enunciado, y localizar el origen de cada problema.
- Implementar las soluciones paso a paso, siguiendo mi guía y con mi revisión en cada tarea.
- Redactar los tests y esta documentación.

## Propuestas revisadas, modificadas o descartadas

- **Rama por funcionalidad**: propuso trabajar en una rama aparte. La descarté por sobreingeniería en una entrega de un único autor y sin PRs; trabajo en `main` con un commit por tarea.
- **Consulta de acceso (tarea 1)**: propuso un método `for_user()` en un QuerySet del modelo. Pedí aislar las consultas de lectura en un archivo propio (`selectors.py`) para separar lecturas de escrituras.
- **Autenticación en el selector (tarea 1)**: añadió una comprobación que devolvía un conjunto vacío para usuarios anónimos. La eliminé: la autenticación es responsabilidad de la capa de permisos, y esa comprobación ocultaría una vista mal protegida en lugar de hacerla fallar.
- **Llamar al selector desde cada vista (tarea 1)**: la primera versión dependía de que cada vista llamara al filtro. Lo señalé como frágil. La IA descartó un middleware tras comprobar que DRF autentica dentro de la vista, y me planteó dos opciones: una vista base con `get_queryset()` acotado, o un manager con alcance implícito que falle en modo cerrado. Elegí la primera por proporcionalidad y dejé la segunda documentada como mejora.
- **Ubicación de la vista base (tarea 1)**: la colocó en `tenancy.py` como `OrganizationScopedAPIView`. La rechacé porque es un mixin de la capa de vistas; quedó como `OrganizationScopedMixin` en `mixins.py`, siguiendo la convención de DRF.

## Cómo comprobé el resultado

- **Tarea 1**: los tests que reproducen el acceso entre organizaciones se escribieron antes del fix y fallaban (`200 != 404`); con el fix pasan, y siguieron pasando sin cambios tras mover el filtro al mixin. También lo comprobé contra el servidor local con los datos de demostración: en la misma encuesta, `ana` obtiene 200, `bob` (otra organización) 404 y un usuario anónimo 401.
