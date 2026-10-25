# Autos Colombia · Gestión de parqueaderos

Aplicación web para administrar la operación de uno o varios parqueaderos: clientes, vehículos, inventario configurable de celdas, mensualidades, pagos, entradas, salidas e historial de novedades. El repositorio incluye una interfaz Angular, una API FastAPI, una base **PostgreSQL** y migraciones Alembic.

> **Versión local de demostración:** no incluye autenticación ni autorización. No la expongas en Internet ni ingreses información personal real.

## Funcionalidades

- Consultar el estado del parqueadero y la ocupación de celdas.
- Registrar clientes y sus vehículos.
- Configurar sedes, zonas, celdas y los tipos de vehículo que admite cada celda.
- Registrar pagos y mensualidades, incluyendo periodos anticipados.
- Registrar entradas y salidas; el sistema valida mensualidad, compatibilidad y disponibilidad de la celda.
- Consultar movimientos y novedades.
- Administrar varios parqueaderos desde *Administración → Parqueaderos*: crear el parqueadero y su estructura (sede → zona → celda) paso a paso.
- Registrar el equipo y sus turnos en *Administración → Empleados y turnos*, con el detalle de quién responde por cada operación.
- Consultar *Administración → Reportes*: inventario por compatibilidad, cobertura de mensualidades, pagos, entradas y salidas del día, con filtros por fecha, sede, zona y tipo de vehículo y **exportación a CSV** (la exportación a PDF usa el diálogo de impresión del navegador).
- Administrar *Administración → Tarifas y vigencias*: cada tarifa se registra con su periodo de aplicación y cierra la vigencia anterior sin alterar pagos ya cobrados.
- Ajustar *Administración → Configuración*: inventario de celdas, tipos de vehículo, reglas operativas y roles.
- Mantener la información de varios parqueaderos separada dentro de la misma instalación.

La capacidad se calcula a partir de las celdas operativas configuradas; no está fijada como un número en el código.

## Tecnologías

| Componente | Tecnología |
| --- | --- |
| Interfaz web | Angular 22, TypeScript y SCSS |
| API | FastAPI y Pydantic |
| Modelos y acceso a datos | SQLAlchemy 2 |
| Migraciones de esquema | Alembic |
| Base de datos | PostgreSQL 14 o superior (probado con PostgreSQL 17) |
| Driver Python | `psycopg` 3 |
| Despliegue | Docker (nginx como reverse proxy) y Render Blueprint |

## Requisitos

- **PostgreSQL 14 o superior** con una base de datos creada y sus credenciales a la mano. El proyecto **no funciona con SQLite**: no existe ningún respaldo local.
- Python 3.12 o superior (probado con Python 3.13).
- Node.js 22.12 o superior y npm.
- Bash: `bash` en Linux/macOS o **Git Bash** en Windows (viene con Git para Windows). También funciona en WSL.
- **Docker (opcional)**: solo para levantar todo con `docker compose` o para construir las imágenes que despliega Render. Desarrollar con `run-local.sh` no lo necesita.

## Ejecutar con `run-local.sh`

### Primer uso

1. Abre una terminal en la raíz del proyecto, donde está este `README.md`. En Windows, abre **Git Bash** y navega hasta la carpeta.
2. Si el script no tiene permiso de ejecución, habilítalo una vez (Linux/macOS):

   ```bash
   chmod +x run-local.sh
   ```

   En Windows no es necesario.

3. Crea el archivo de conexión a partir de la plantilla y complétalo:

   ```bash
   cp .env.example .env
   ```

   Abre `.env` y escribe tu usuario, clave y nombre de base:

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres:tu_clave@127.0.0.1:5432/autos_colombia_app
   ```

   `.env` está en `.gitignore`: nunca se sube al repositorio. Si prefieres, puedes exportar `DATABASE_URL` en la terminal en lugar de usar el archivo.

4. Inicia la aplicación:

   ```bash
   ./run-local.sh
   ```

La primera ejecución puede tardar mientras instala dependencias. El script detecta Python y Node, prepara el entorno virtual de Python en `backend/.venv` (carpeta `Scripts/` en Windows o `bin/` en Linux/macOS), instala las dependencias del backend, instala las del frontend con `npm ci` si aún no existen, aplica las migraciones de base de datos y luego inicia FastAPI y Angular. El consentimiento de analítica de Angular está desactivado para evitar una pregunta interactiva.

### Usar la aplicación

Mantén abierta la terminal mientras trabajas. Cuando aparezcan los mensajes de inicio de ambos servidores, abre:

- **Aplicación:** <http://localhost:4200>
- **API:** <http://127.0.0.1:8000>
- **Documentación interactiva de la API:** <http://127.0.0.1:8000/docs>
- **Estado de conexión de la API:** <http://127.0.0.1:8000/api/health>

Para detener los dos servidores, vuelve a la terminal y pulsa **Ctrl+C**.

### Datos iniciales

En una base vacía, la API genera un parqueadero demostrativo con 8 celdas para carro/camioneta y 4 para moto. Las tarifas de $250.000 y $100.000 también son valores de referencia. **Estos datos no representan la capacidad ni los precios reales de Autos Colombia.** Puedes modificar el inventario desde la sección *Celdas* de la aplicación.

La demostración **no** siembra empleados ni turnos: la pantalla *Empleados y turnos* inicia con un estado vacío honesto porque no hay personal confirmado. Registra en esa pantalla las personas que operen el parqueadero; sus nombres, documentos y roles quedan en tu base local.

### Solución de problemas de inicio

- **`Permission denied`:** ejecuta `chmod +x run-local.sh` y vuelve a intentarlo.
- **El puerto 4200 o 8000 ya está ocupado:** detén la instancia anterior con Ctrl+C o cierra el proceso que usa ese puerto; vuelve a ejecutar el script.
- **No carga la página o dice que no conecta con el parqueadero:** deja la terminal abierta y confirma que los dos servidores arrancaron. Comprueba la API en <http://127.0.0.1:8000/api/health>.
- **Aparece un aviso de actualización de pip:** es informativo y no impide ejecutar la aplicación.
- **`npm ci` falla o pide una versión de Node diferente:** instala Node.js 22.12 o superior y vuelve a ejecutar el script.
- **`DATABASE_URL no está definida`:** falta el archivo `.env`. Copia `.env.example` a `.env` y completa la conexión.
- **`DATABASE_URL debe apuntar a PostgreSQL`:** la variable apunta a otro motor. Solo se admite `postgresql+psycopg://`.
- **`no existe la base de datos ...`:** créala antes de iniciar, por ejemplo `createdb autos_colombia_app`, o corrige el nombre en `.env`.

## Base de datos y persistencia

El proyecto usa **PostgreSQL exclusivamente**. La conexión vive en `DATABASE_URL` y se lee desde `.env` (o desde la terminal); si falta o apunta a otro motor, el backend no arranca.

```bash
createdb autos_colombia_app        # desde psql: CREATE DATABASE autos_colombia_app;
./run-local.sh
```

Alembic aplica el esquema versionado desde `backend/alembic/versions/` sobre esa base. La API agrega datos de demostración solo si la base todavía no contiene parqueaderos.

Para **reiniciar desde cero**, borra la base y déjala vacía; al siguiente inicio Alembic vuelve a crear el esquema y la API siembra la demostración:

```sql
DROP DATABASE autos_colombia_app;
CREATE DATABASE autos_colombia_app;
```

> `backend/autos_colombia.db` es un archivo **heredado de una versión anterior con SQLite**. Ya no se usa: el proyecto no lo abre. Puedes conservarlo como respaldo o eliminarlo.

El diagrama de relaciones, las reglas de integridad y el flujo de creación de la base están en [docs/modelo-er.md](docs/modelo-er.md).

## Ejecutar pruebas y compilación

```bash
# Pruebas del backend
cd backend

# Linux / macOS
.venv/bin/pytest -q

# Windows (Git Bash)
.venv/Scripts/python.exe -m pytest -q

cd ..

# Compilar el frontend (requiere node_modules: ya los crea run-local.sh)
cd frontend
npm run build
```

Las pruebas derivan de tu `DATABASE_URL` una base propia, `autos_colombia_test`, y la vacían antes y después de cada prueba: **también corren en PostgreSQL** y nunca tocan tus datos reales. Crea esa base una sola vez:

```sql
CREATE DATABASE autos_colombia_test;
```

> Los ficheros `backend/autos_colombia.db` y `backend/autos_colombia_test.db` son restos de la etapa con SQLite. El proyecto ya no los usa y puedes borrarlos; además `.gitignore` los mantiene fuera del repositorio.

## Desplegar con Docker y Render

La rama `docker-render` empaqueta el proyecto como **dos servicios independientes** más una base gestionada:

| Servicio | Fichero | Escucha en | Contenido |
| --- | --- | --- | --- |
| `autos-colombia-api` | `backend/Dockerfile` | `0.0.0.0:${PORT}` | FastAPI + uvicorn; ejecuta `alembic upgrade head` antes de aceptar tráfico |
| `autos-colombia-web` | `frontend/Dockerfile` | `0.0.0.0:${PORT}` | nginx con el bundle de Angular y reverse proxy de `/api` |
| `autos-colombia-db` | `render.yaml` | 5432 | PostgreSQL 17 gestionado por Render |

El navegador solo habla con la interfaz. El build de producción reemplaza `environment.ts` por `environment.prod.ts`, que fija la API en `/api`, y nginx la reenvía al backend con la variable `API_URL`. El desarrollo local no cambia: `ng serve` sigue usando `http://127.0.0.1:8000/api`. Como la interfaz y la API comparten origen en producción, además desaparece la necesidad de CORS.

### En local (opcional)

```bash
docker compose up --build
# Interfaz: http://localhost:8080  ·  API: http://localhost:8000/api/health
```

Levanta PostgreSQL, la API y la interfaz con la misma arquitectura que en Render. Si prefieres trabajar como hasta ahora con `ng serve` y `uvicorn`, sigue usando `./run-local.sh`: no hace falta Docker para desarrollar.

### En Render

1. Sube la rama y conecta el repositorio en Render: **New → Blueprint**.
2. Elige el repositorio y la rama. Render lee `render.yaml` y crea los tres recursos.
3. Espera a que los tres queden en estado *Live*. La API se comprueba en `/api/health` y la interfaz en `/`.

Si quieres probar sin fusionar a `main`, descomenta la línea `branch: docker-render` en cada servicio de `render.yaml`. Recuerda volver a dejarla comentada tras la fusión para que los despliegues automáticos sigan a la rama por defecto.

### Ajustes habituales

- **Plan.** `render.yaml` usa el plan `free` en servicios y base de datos. Conviene conocer sus límites: los servicios se duermen a los 15 minutos sin tráfico (y tardan ~1 minuto en despertar), hay 750 horas de instancia al mes por espacio de trabajo —no alcanzan para dos servicios 24/7— y **las bases gratuitas caducan a los 30 días**. Para algo siempre encendido, cambia `plan: free` por `plan: starter` (unos 7 USD por servicio y mes).
- **Puerto.** Render asigna `PORT` (10000 por defecto) y enruta a ese puerto; por eso los dos contenedores escuchan en `${PORT}`. El esquema del blueprint no admite un campo `port`.
- **`API_URL`.** Debe ser solo el origen del backend, sin barra final (`https://autos-colombia-api.onrender.com`). Si renombras el servicio de la API, actualízalo aquí.
- **`DATABASE_URL`.** Render entrega la conexión con el esquema heredado `postgres://`; `app/database.py` y `alembic/env.py` lo normalizan a `postgresql+psycopg://`, así que no hace falta tocar nada.

### Limitación de esta rama

En este equipo **no hay Docker instalado**, por lo que los Dockerfiles, el `docker-compose.yml` y el `render.yaml` se han verificado de forma estática (sintaxis YAML, contraste con el esquema oficial del blueprint, rutas de `COPY`, resolución de la plantilla de nginx y build de producción de Angular), pero **no se han ejecutado los builds de imagen**. El primer `docker compose up --build` o despliegue en Render puede requerir ajustes menores.

## API

La API expone recursos bajo `/api` y se documenta en <http://127.0.0.1:8000/docs>. Grupos principales:

| Grupo | Endpoints |
| --- | --- |
| Sistema | `GET /api/health`, `GET /api/bootstrap`, `GET /api/dashboard`, `GET /api/activity` |
| Parqueaderos y estructura | `/api/parking-lots`, `/api/sites`, `/api/zones`, `/api/cells`, `/api/vehicle-types` |
| Clientes y vehículos | `/api/customers`, `/api/vehicles`, `/api/contracts` |
| Operación | `POST /api/movements/entry`, `POST /api/movements/{id}/exit`, `GET /api/movements` |
| Cobro | `POST /api/payments`, `GET /api/payments`, `/api/tariffs`, `/api/tariffs/history` |
| Administración | `/api/employees`, `/api/shifts`, `/api/reports`, `/api/novelties`, `/api/activity` |

Casi todas las peticiones llevan el parámetro `parking_lot_id`, que es el que mantiene aislados los datos de cada parqueadero.

## Estructura del proyecto

```text
.
├── run-local.sh                  # Prepara dependencias, migra la BD e inicia la app
├── .env.example                  # Plantilla de conexión a PostgreSQL (copia a .env)
├── README.md                     # Esta guía de instalación y uso
├── PRODUCT.md                    # Alcance, decisiones y reglas de producto
├── render.yaml                   # Blueprint de Render: API + interfaz + PostgreSQL
├── docker-compose.yml            # Misma arquitectura ejecutada en local
├── pyrightconfig.json            # Configuración de análisis Python del proyecto
├── .vscode/                      # Ajustes de intérprete y rutas del editor
├── backend/
│   ├── app/
│   │   ├── main.py               # API REST, reglas de operación y datos demo
│   │   ├── models.py             # Entidades/tablas SQLAlchemy y relaciones
│   │   ├── schemas.py            # Esquemas de entrada/salida y validación
│   │   └── database.py           # DATABASE_URL, motor y sesiones de PostgreSQL
│   ├── alembic/                  # Configuración e historial de migraciones
│   │   └── versions/             # Migraciones versionadas del esquema
│   ├── tests/                    # Pruebas del flujo de negocio
│   ├── Dockerfile                # Imagen de la API (migraciones + uvicorn)
│   ├── .dockerignore             # Excluye venv, cachés y pruebas del contexto
│   ├── requirements.txt          # Dependencias Python
│   └── pyrightconfig.json        # Configuración de tipos del backend
├── frontend/
│   ├── src/app/
│   │   ├── app.ts                # Estado y acciones de la interfaz
│   │   ├── app.html              # Plantilla de pantallas y formularios
│   │   ├── app.scss              # Estilos y diseño adaptable
│   │   └── api.service.ts        # Comunicación HTTP con FastAPI
│   ├── src/environments/         # URL de la API por entorno (dev / producción)
│   ├── nginx/templates/          # Plantilla de nginx (proxy de ${API_URL})
│   ├── public/icons/             # Iconos SVG locales (sin CDN)
│   ├── README.md                 # Sistema de diseño y tokens de la interfaz
│   ├── Dockerfile                # Imagen de la interfaz (Angular + nginx)
│   ├── .dockerignore             # Excluye node_modules y dist del contexto
│   ├── angular.json              # Configuración de Angular
│   └── package.json              # Dependencias y comandos npm
└── docs/
    ├── arquitectura.md           # Arquitectura de la solución
    ├── modelo-er.md              # Diagramas Mermaid ER y de conexión de la BD
    └── requisitos-y-historias.md # Requisitos e historias de usuario
```

## Documentación relacionada

- [PRODUCT.md](PRODUCT.md) — alcance, usuarios, capacidades y restricciones del producto.
- [docs/arquitectura.md](docs/arquitectura.md) — componentes, flujos y decisiones técnicas.
- [docs/modelo-er.md](docs/modelo-er.md) — modelo entidad-relación y reglas de integridad.
- [docs/requisitos-y-historias.md](docs/requisitos-y-historias.md) — requisitos e historias de usuario.
- [frontend/README.md](frontend/README.md) — sistema de diseño, tokens de color y tipografía.

## Reglas y decisiones provisionales

- Una mensualidad vencida o cuya fecha de inicio aún no llega bloquea el ingreso.
- Un pago anticipado cubre periodos consecutivos; el vencimiento conserva el día del ciclo y se ajusta al último día cuando un mes no tiene ese día.
- Una celda compatible con varios tipos cuenta una sola vez en la capacidad física total.
- Documentos de clientes y placas son únicos dentro de cada parqueadero.
- Los datos de clientes, vehículos, movimientos y pagos quedan aislados por parqueadero: cambiar de parqueadero en la interfaz cambia el contexto de la operación.
- Una vigencia de tarifa nueva cierra la anterior el día anterior a su inicio; el sistema rechaza solapamientos entre periodos ya cerrados.
- El inventario y las tarifas de demostración se deben reemplazar por datos confirmados antes de un uso real.
- Antes de desplegar se deben incorporar autenticación y autorización, configurar el servidor y revisar las medidas de seguridad y privacidad.
