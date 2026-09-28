# Prueba técnica - Full-stack Product Engineer

## Contexto

Este repositorio contiene una aplicación pequeña de encuestas con:

- Backend en Django y Django REST Framework.
- Frontend en Vue 3.
- Base de datos SQLite para simplificar la ejecución local.

El código simula una parte de un SaaS multiempresa. No esperamos que conozcas previamente todos los componentes. Nos interesa observar cómo entiendes código existente, cómo investigas problemas y cómo validas los cambios.

## Tiempo

Dedica un máximo de **2 horas y 30 minutos**. Si no terminas alguna parte, explica cómo la completarías. Valoraremos más el criterio y la claridad que intentar abarcarlo todo deprisa.

## Tareas

### 1. Corregir un problema de aislamiento entre empresas

Un usuario autenticado puede consultar los resultados de una encuesta perteneciente a otra organización si conoce su identificador.

- Corrige el problema.
- Añade pruebas que demuestren que un usuario solo accede a encuestas de su organización.
- Conserva el comportamiento correcto para usuarios autorizados.

### 2. Evitar respuestas duplicadas

El endpoint de webhook puede recibir varias veces el mismo evento externo. Actualmente, cada reintento crea una nueva respuesta.

- Haz que el procesamiento sea idempotente.
- Ten en cuenta que dos peticiones podrían llegar casi al mismo tiempo.
- Añade las pruebas que consideres necesarias.

### 3. Añadir un filtro de fechas

La pantalla de resultados debe permitir filtrar las respuestas por fecha de envío.

- Añade al endpoint los filtros opcionales `from` y `to`.
- Añade los controles correspondientes en Vue.
- Los filtros deben poder utilizarse juntos o por separado.
- Define un comportamiento claro para fechas inválidas.

## Uso de inteligencia artificial

Puedes utilizar Claude Code, Codex, Cursor, Copilot u otras herramientas. Incluye un archivo `AI_NOTES.md` indicando:

- Qué herramientas utilizaste.
- Para qué las utilizaste.
- Qué propuestas tuviste que revisar, modificar o descartar.
- Cómo comprobaste que el resultado era correcto.

No se penaliza utilizar IA. Sí se valorará negativamente entregar cambios que no puedas explicar.

## Entrega

Entrega el repositorio completo mediante un enlace o archivo comprimido e incluye:

- Código modificado.
- Migraciones necesarias.
- Pruebas automatizadas.
- Un breve `SOLUTION.md` con tus decisiones, riesgos conocidos y mejoras que harías con más tiempo.

No es necesario desplegar la aplicación.

## Ejecución

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Pruebas:

```bash
python manage.py test
```

### Frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Los datos de demostración utilizan el usuario `ana` y la contraseña `ana123`.

