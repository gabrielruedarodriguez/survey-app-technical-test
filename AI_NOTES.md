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
- **Header `Idempotency-Key` (tarea 2)**: le planteé añadir una clave única en la cabecera. La IA verificó el Internet-Draft de la IETF: la clave la genera el cliente, y aquí el cliente es el proveedor externo, que ya envía `event_id` con ese propósito. Coincidí en no añadirla y quedó documentada como alternativa descartada.
- **Estrategia de escritura (tarea 2)**: propuso insertar primero y capturar `IntegrityError` en lugar de `QuerySet.get_or_create()` de Django, para poder probar sin mocks el camino de una inserción concurrente. Lo acepté tras revisar que ambas opciones dependen de la restricción única.
- **Validación de filtros (tarea 3)**: propuso un serializer propio para los parámetros `from` y `to`. Le indiqué usar django-filter, que está hecho para este caso. Al revisar el código de la librería, la IA detectó que `FilterSet.qs` ignora en silencio los valores inválidos, y añadió la validación explícita.
- **Instalación de django-filter (tarea 3)**: al instalar la última versión (26.1), el gestor de paquetes actualizó Django de 5.1.6 a 6.1.1 como efecto colateral. Lo detectamos, se restauró Django 5.1.6 y se fijó `django-filter==25.1`, la última compatible con la versión de Django del proyecto.

## Cómo comprobé el resultado

- **Tarea 1**: los tests que reproducen el acceso entre organizaciones se escribieron antes del fix y fallaban (`200 != 404`); con el fix pasan, y siguieron pasando sin cambios tras mover el filtro al mixin. También lo comprobé contra el servidor local con los datos de demostración: en la misma encuesta, `ana` obtiene 200, `bob` (otra organización) 404 y un usuario anónimo 401.
- **Tarea 2**:
  - Los tests de reintento se escribieron antes del fix y fallaban (`201 != 200`).
  - Para comprobar que el test de migración no es trivial, desactivé temporalmente la deduplicación y verifiqué que fallaba con `IntegrityError`.
  - Contra el servidor local: dos entregas del mismo evento devuelven `201` y `200`; cinco entregas en paralelo producen un `201` y cuatro `200`, con una sola fila en la base de datos.
- **Tarea 3**:
  - Los tests del filtro se escribieron antes de implementarlo y fallaban (se devolvían todas las respuestas).
  - Contra el servidor local comprobé el `to` inclusivo, los parámetros vacíos, la fecha inválida (400) y el rango invertido (400).
  - En el frontend, `npm run build` y la ejecución del `api.js` real contra el servidor: omite los parámetros vacíos y muestra los errores de validación por campo.
