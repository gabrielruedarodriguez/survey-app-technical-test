# Solución

Nueva dependencia: `django-filter==25.1`, la última compatible con Django 5.1. Tras `pip install -r requirements.txt` y `python manage.py migrate`, `python manage.py test` ejecuta 19 tests.

Las lecturas están en `selectors.py`, las escrituras en `services.py`, los filtros en `filters.py` y el aislamiento por organización en `mixins.py`.

## Decisiones

**1. Aislamiento entre empresas**

- `OrganizationScopedMixin` acota `get_queryset()` a las organizaciones del usuario, y la vista usa `get_object()`. La regla vive en un solo lugar, no en una llamada que cada vista pueda olvidar.
- Se responde 404 en lugar de 403, para no revelar que la encuesta existe.
- No se usa un middleware: DRF autentica dentro de la vista, así que un middleware no vería al usuario de Basic auth.

**2. Webhook idempotente**

- Una restricción única `(survey, external_id)` hace que la base de datos arbitre las entregas simultáneas. El servicio inserta y, ante un `IntegrityError`, devuelve la fila existente: `201` si es nueva, `200` si es un reintento.
- `event_id` es la clave de idempotencia. No se añadió `Idempotency-Key` porque el proveedor ya envía `event_id` con ese fin.
- Gana la primera escritura y se responde `200`, porque un webhook reintenta ante cualquier respuesta que no sea 2xx.
- La migración `0002` elimina los duplicados que el bug ya generó antes de que `0003` añada la restricción. Sin esa limpieza, el despliegue fallaría.

**3. Filtro de fechas**

- `from` y `to` (`YYYY-MM-DD`) son inclusivos y se interpretan en UTC. La tabla muestra las fechas en UTC para que coincidan con el filtro.
- Una fecha inválida o un `from` posterior a `to` devuelve `400` con el error en su campo. Un parámetro vacío se ignora.
- La vista valida con `is_valid()`, porque `FilterSet.qs` descarta en silencio los valores inválidos.

## Riesgos conocidos

- El mixin es opcional: una vista nueva que no lo use no queda aislada.
- La migración `0002` borra filas de forma irreversible, así que conviene hacer una copia de seguridad antes de desplegar.
- Si el proveedor reutilizara un `event_id` para actualizar una respuesta, la actualización se ignoraría.
- El lookup `__date` no aprovecha un índice sobre `submitted_at`.
- No hay test de concurrencia real (SQLite serializa las escrituras) ni tests del frontend.
- Fuera del alcance: el token del webhook se compara con `!=` (debería usarse `secrets.compare_digest`) y es el mismo para todas las organizaciones. Además, el frontend tiene la credencial y el `surveyId` escritos en el código.

## Mejoras con más tiempo

- Un aislamiento que falle en modo cerrado, o Row-Level Security en PostgreSQL.
- Un test de concurrencia con PostgreSQL y varios hilos.
- Secretos o firmas HMAC por organización en el webhook.
- Una zona horaria configurable para el filtro y tests de componentes con Vitest.
