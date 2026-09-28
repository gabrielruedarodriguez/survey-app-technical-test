# Solución

## Cómo verificar

```bash
cd backend
python manage.py test
```

## Organización del código

- `surveys/selectors.py`: consultas de lectura, fuera de las vistas.
- `surveys/services.py`: operaciones de escritura.
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

## Riesgos conocidos

- El mixin sigue siendo opcional: una vista nueva que herede de `APIView` sin él no queda aislada.
- La migración `0002` borra filas de forma irreversible. Conviene hacer una copia de seguridad antes de desplegar.
- Si el proveedor reutilizara el mismo `event_id` para actualizar una respuesta (por ejemplo, de `partial` a `complete`), la actualización se ignoraría. Habría que pasar a un upsert.
- No hay un test de concurrencia real: SQLite serializa las escrituras. Manualmente, 5 entregas en paralelo del mismo evento contra el servidor local produjeron un `201`, cuatro `200` y una sola fila.

## Mejoras con más tiempo

- Alcance implícito que falle en modo cerrado: un manager por defecto que lance un error si se consulta un modelo de una organización sin alcance activo. Así, olvidarlo produce una excepción en lugar de una fuga. Exige desactivarlo de forma explícita en el webhook, los comandos y el admin.
- Row-Level Security en PostgreSQL, para que la base de datos imponga el aislamiento.
- Test de concurrencia real con PostgreSQL (`TransactionTestCase` con varios hilos lanzando el mismo evento).
- Registrar un aviso cuando un reintento llega con un payload distinto al guardado.
