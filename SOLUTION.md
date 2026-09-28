# Solución

## Cómo verificar

```bash
cd backend
pip install -r requirements.txt   # incluye django-filter
python manage.py migrate
python manage.py test

cd ../frontend
npm run build
```

## Organización del código

- `surveys/selectors.py`: consultas de lectura, fuera de las vistas.
- `surveys/services.py`: operaciones de escritura.
- `surveys/filters.py`: filtros de consulta (django-filter).
- `surveys/mixins.py`: comportamiento reutilizable de las vistas, como el aislamiento por organización.
- Las vistas solo orquestan: validan la entrada, obtienen los datos y serializan la salida.

## 1. Aislamiento entre empresas

**Causa**: `SurveyResultsView` buscaba la encuesta solo por `pk`, sin comprobar la organización del usuario.

**Solución**: `OrganizationScopedMixin` sobrescribe `get_queryset()` para exponer solo los objetos de las organizaciones del usuario (selector `organization_list`). La vista declara `queryset = Survey.objects.all()` y usa `get_object()`, que DRF resuelve siempre a través de `get_queryset()`.

**Decisiones**:

- **El aislamiento lo aplica un mixin, no cada vista**: si cada vista tuviera que llamar al filtro, olvidarlo en una vista nueva expondría datos. Con el mixin la regla vive en un solo lugar y queda declarada en la firma de la clase.
- **No se usa un middleware**: DRF autentica dentro de la vista (`APIView.initial()`), así que un middleware de Django no ve al usuario autenticado con Basic auth.
- **404 en lugar de 403**: una encuesta ajena es indistinguible de una inexistente, así no se revela que el identificador existe.
- **El selector no comprueba la autenticación**: es responsabilidad de la capa de permisos (`IsAuthenticated`, declarado en el mixin).
- **Varias organizaciones por usuario**: el filtro usa una subconsulta (`organization__in`), así que cubre varias membresías sin duplicar filas.

**Pruebas** (`SurveyResultsIsolationTests`):

- Encuesta de otra organización → 404, con la misma respuesta que una encuesta inexistente.
- Usuario sin membresía → 404.
- Usuario con varias organizaciones → 200 en cada una.
- Usuario anónimo → 401.

Los tests se escribieron antes del fix y fallaban con `200 != 404`. El paso posterior de la llamada en la vista al mixin se hizo sin modificarlos.

## 2. Webhook idempotente

**Causa**: el webhook hacía `Response.objects.create()` en cada entrega, y nada impedía repetir `(survey, external_id)`.

**Solución**:

- Una restricción única `(survey, external_id)` en la base de datos.
- El servicio `response_get_or_create()` inserta dentro de `transaction.atomic()`. Si la restricción salta (`IntegrityError`), devuelve la respuesta ya guardada.
- La vista responde `201` si la respuesta es nueva y `200` si es un reintento, siempre con la respuesta guardada.

**Decisiones**:

- **La base de datos arbitra la concurrencia**: cualquier "consultar y, si no existe, crear" en Python deja una ventana en la que dos peticiones simultáneas insertan las dos. Con la restricción, la inserción perdedora falla y lee la fila ganadora.
- **Insertar primero en lugar de `QuerySet.get_or_create()` de Django**: ambas son correctas con la restricción. Pero insertando primero, un reintento recorre el mismo camino que el perdedor de una carrera, y ese camino se prueba sin simular internals de Django.
- **`event_id` es la clave de idempotencia**: se evaluó el header `Idempotency-Key` (Internet-Draft de la IETF) y se descartó. Esa clave la genera el cliente, y aquí el cliente es el proveedor externo, que ya envía `event_id` con ese propósito. Exigir un header nuevo rompería su contrato, y un reenvío con otra clave se duplicaría igual. Encaja cuando somos nosotros quienes exponemos un POST a clientes propios.
- **Unicidad por encuesta, no global**: los identificadores de eventos de proveedores de distintas organizaciones pueden coincidir, y un tenant no debe bloquear eventos de otro.
- **Gana la primera escritura y se responde 2xx**: el draft de `Idempotency-Key` sugiere 422 ante la misma clave con otro payload. En un webhook, cualquier respuesta distinta de 2xx provoca reintentos del proveedor, así que se devuelve `200` con la respuesta original.
- **Migraciones separadas**: `0002` elimina los duplicados existentes (el bug ya los generó en cualquier base real) conservando la primera respuesta recibida, y `0003` añade la restricción. Separar datos y esquema evita problemas en PostgreSQL al mezclarlos en la misma transacción.

**Pruebas**:

- `ResponseWebhookIdempotencyTests`:
  - Primera entrega → 201.
  - Reintento → 200 con la misma respuesta y una sola fila.
  - Reintento con otro payload → se conserva la primera escritura.
  - Mismo `event_id` en otra encuesta → 201.
- `ResponseGetOrCreateTests`: con la fila ya insertada por una entrega concurrente, el servicio devuelve esa fila sin duplicar.
- `RemoveDuplicateResponsesMigrationTests`: sobre una base con duplicados, migrar de `0001` a `0003` conserva solo la primera respuesta de cada evento. Sin la deduplicación, el test falla con `IntegrityError` al añadir la restricción.

## 3. Filtro de fechas

**Solución**:

- **Backend**: `GET /api/surveys/<id>/results/?from=YYYY-MM-DD&to=YYYY-MM-DD`. `ResponseFilter` (django-filter) filtra `submitted_at` sobre las respuestas de la encuesta, ya acotada por organización. `count` refleja el resultado filtrado.
- **Frontend**: dos campos de fecha con los botones *Apply* y *Clear*. Los parámetros vacíos no se envían, y los errores de validación del backend se muestran junto al nombre del campo.

**Comportamiento**:

| Caso | Resultado |
| --- | --- |
| Solo `from` | Respuestas enviadas desde ese día (inclusive). |
| Solo `to` | Respuestas enviadas hasta ese día, **incluido el día completo**. |
| `from` y `to` | Intersección de ambos. |
| Parámetro vacío (`?from=`) | Se ignora. |
| Fecha inválida o con otro formato | `400` con el error en su campo: `{"from": ["Introduzca una fecha válida."]}`. |
| `from` posterior a `to` | `400` con el error en `to`. |

**Decisiones**:

- **Los días se interpretan en UTC**, la zona horaria del servidor. Para que la pantalla sea coherente con el filtro, la columna de envío se muestra en UTC (*Submitted (UTC)*).
- **`FilterSet` explícito en lugar de `DjangoFilterBackend`**: el `queryset` de la vista es de encuestas, y `get_object()` pasa por los filter backends, así que el filtro se aplica directamente sobre las respuestas.
- **Validación explícita**: `FilterSet.qs` descarta en silencio los valores inválidos, así que la vista comprueba `is_valid()` y responde 400 con `translate_validation`.
- **`from` es palabra reservada en Python**: los filtros se declaran sobrescribiendo `FilterSet.get_filters()` en lugar de como atributos de clase.
- **Versión**: se fijó `django-filter==25.1`, la última compatible con Django 5.1. La 26.1 exige una versión más nueva de Django.
- **`min`/`max` cruzados en los campos**: el navegador no deja elegir un rango invertido, aunque el backend lo valida igualmente.

**Pruebas** (`SurveyResultsDateFilterTests`): solo `from`, `to` inclusivo (una respuesta a las 23:59 del día `to` aparece), ambos combinados, parámetros vacíos, fecha inválida → 400 y rango invertido → 400. El frontend se verificó con `npm run build` y ejecutando `api.js` contra el servidor local.

## Riesgos conocidos

- El mixin sigue siendo opcional: una vista nueva que herede de `APIView` sin él no queda aislada.
- La migración `0002` borra filas de forma irreversible. Conviene hacer una copia de seguridad antes de desplegar.
- Si el proveedor reutilizara el mismo `event_id` para actualizar una respuesta (por ejemplo, de `partial` a `complete`), la actualización se ignoraría. Habría que pasar a un upsert.
- El filtro `__date` aplica una función sobre la columna y no aprovecha un índice sobre `submitted_at`. Con volumen, conviene filtrar por rango de datetimes o añadir un índice funcional.
- El mensaje propio de rango inválido se muestra en inglés, mientras que los de Django salen en español por `LANGUAGE_CODE = "es-es"`. Está marcado como traducible, pero no hay catálogo de traducciones.
- No hay tests automáticos del frontend.
- No hay un test de concurrencia real: SQLite serializa las escrituras. Manualmente, 5 entregas en paralelo del mismo evento contra el servidor local produjeron un `201`, cuatro `200` y una sola fila.

## Mejoras con más tiempo

- Alcance implícito que falle en modo cerrado: un manager por defecto que lance un error si se consulta un modelo de una organización sin alcance activo. Así, olvidarlo produce una excepción en lugar de una fuga. Exige desactivarlo de forma explícita en el webhook, los comandos y el admin.
- Row-Level Security en PostgreSQL, para que la base de datos imponga el aislamiento.
- Test de concurrencia real con PostgreSQL (`TransactionTestCase` con varios hilos lanzando el mismo evento).
- Registrar un aviso cuando un reintento llega con un payload distinto al guardado.
- Permitir elegir la zona horaria del filtro (por ejemplo, la del navegador) en lugar de fijarla en UTC.
- Tests de componentes del frontend con Vitest y Vue Test Utils.
