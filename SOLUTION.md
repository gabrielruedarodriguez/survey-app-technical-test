# Solución

## Cómo verificar

```bash
cd backend
python manage.py test
```

## Organización del código

- `surveys/selectors.py`: consultas de lectura, fuera de las vistas.
- `surveys/mixins.py`: comportamiento reutilizable de las vistas, como el aislamiento por organización.
- Las vistas solo orquestan: validan la entrada, obtienen los datos y serializan la salida.

## 1. Aislamiento entre empresas

**Causa**: `SurveyResultsView` buscaba la encuesta solo por `pk`, sin comprobar la organización del usuario.

**Solución**: `OrganizationScopedMixin` sobrescribe `get_queryset()` para exponer solo los objetos de las organizaciones del usuario (selector `organizations_for_user`). La vista declara `queryset = Survey.objects.all()` y usa `get_object()`, que DRF resuelve siempre a través de `get_queryset()`.

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

## Riesgos conocidos

- El mixin sigue siendo opcional: una vista nueva que herede de `APIView` sin él no queda aislada.

## Mejoras con más tiempo

- Alcance implícito que falle en modo cerrado: un manager por defecto que lance un error si se consulta un modelo de una organización sin alcance activo. Así, olvidarlo produce una excepción en lugar de una fuga. Exige desactivarlo de forma explícita en el webhook, los comandos y el admin.
- Row-Level Security en PostgreSQL, para que la base de datos imponga el aislamiento.
