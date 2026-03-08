# API TechNova

Backend REST construido con Django y Django REST Framework para una app tipo e-commerce con autenticacion JWT, catalogo de productos, carrito, direcciones de entrega, pedidos, seguimiento de envios y utilidades geograficas.

## Funcionalidades

- Registro e inicio de sesion con JWT.
- Perfil de usuario y cambio de contrasena.
- Roles de usuario con grupos de Django: `CLIENTE`, `DRIVER`, `PROVIDER`, `ADMIN`.
- Catalogo de categorias, banners y productos.
- Carrito de compras por usuario autenticado.
- Direcciones de entrega.
- Creacion y consulta de pedidos.
- Seguimiento de envios y ubicacion en tiempo real.
- Endpoints geo para autocompletado, geocodificacion, validacion de direccion y estimacion de ruta.

## Stack

- Python 3.12
- Django 6.0.1
- Django REST Framework 3.16.1
- Simple JWT 5.5.1
- django-cors-headers 4.9.0
- PostgreSQL
- Pillow

## Estructura

```text
api_technova/
  api_technova/   # settings, urls, asgi, wsgi
  app/            # modelos, vistas, serializers, permisos
  media/          # archivos subidos
  manage.py
```

## Requisitos

- Python 3.12 o compatible
- PostgreSQL corriendo localmente si vas a usar la base principal
- Entorno virtual recomendado

## Instalacion

### 1. Crear y activar entorno virtual

En Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

Este proyecto no incluye `requirements.txt` actualmente, asi que instala al menos:

```powershell
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers pillow psycopg2-binary
```

### 3. Configurar base de datos

La configuracion actual en `api_technova/settings.py` apunta por defecto a PostgreSQL local:

- Base de datos: `app_TechNova`
- Usuario: `guayabal_user`
- Host: `localhost`
- Puerto: `5432`

Conviene ajustar estos valores antes de desplegar o compartir el proyecto.

### 4. Aplicar migraciones

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### 5. Ejecutar el servidor

```powershell
.\venv\Scripts\python.exe manage.py runserver
```

La API quedara disponible en:

```text
http://127.0.0.1:8000/
```

## Configuracion importante

Variables leidas desde entorno:

- `USE_SQLITE_FOR_TESTS`: usa SQLite en memoria para tests. Por defecto esta activa si corres `manage.py test`.
- `GOOGLE_MAPS_SERVER_API_KEY`: clave de Google Maps/Places para backend.
- `GOOGLE_MAPS_LANGUAGE`: idioma para servicios de Google. Default: `es`.
- `GOOGLE_MAPS_REGION`: region para servicios de Google. Default: `ec`.
- `GEO_PROVIDER`: proveedor geografico. Default: `osm`. Opciones: `osm`, `google`.
- `GEOCODER_USER_AGENT`: User-Agent para Nominatim/OSM.
- `OSM_NOMINATIM_BASE_URL`: URL base de Nominatim.
- `OSM_ROUTER_BASE_URL`: URL base de OSRM.

## Autenticacion

La API usa JWT por header:

```http
Authorization: Bearer <access_token>
```

### Login

`POST /login/`

Acepta `email` o `username` junto con `password`.

Ejemplo:

```json
{
  "email": "cliente@example.com",
  "password": "password123"
}
```

Respuesta esperada:

```json
{
  "access": "<jwt_access>",
  "refresh": "<jwt_refresh>",
  "user": {
    "id": 1,
    "username": "cliente",
    "email": "cliente@example.com"
  }
}
```

### Refresh token

`POST /token/refresh/`

```json
{
  "refresh": "<jwt_refresh>"
}
```

## Flujo de registro y roles

`POST /register/`

Campos principales:

- `email`
- `phone`
- `password`
- `password2`
- `full_name` o `first_name` + `last_name`
- `address`
- `role` opcional: `client`, `driver`, `provider`
- `role_reason` opcional

Comportamiento:

- Todo usuario nuevo recibe el grupo `CLIENTE`.
- Si se registra como `driver` o `provider`, se crea una solicitud pendiente en `role-requests/`.
- El telefono debe tener 10 digitos y comenzar con `09`.

Ejemplo:

```json
{
  "full_name": "Maria Perez",
  "email": "maria@example.com",
  "phone": "0999999999",
  "password": "password123",
  "password2": "password123",
  "role": "driver",
  "role_reason": "Tengo moto propia"
}
```

## Endpoints principales

### Publicos

- `GET /`
- `POST /register/`
- `POST /login/`
- `POST /token/refresh/`
- `GET /banners/`
- `GET /categories/`
- `GET /products/`
- `GET /products/<id>/`

### Requieren autenticacion

- `GET/PATCH /me/`
- `POST /me/change-password/`
- `GET/POST /cart/`
- `GET /cart/count/`
- `GET/POST /orders/`
- `GET /orders/<id>/`
- `GET /orders/<id>/tracking/`
- `POST /orders/<id>/tracking/location/`
- `POST /orders/<id>/tracking/assign-driver/`
- `GET/POST /addresses/`
- `GET/PATCH/DELETE /addresses/<id>/`
- `GET/POST /role-requests/`
- `GET /geo/autocomplete/`
- `GET /geo/geocode/`
- `POST /geo/validate-address/`
- `GET /geo/routes/estimate/`

### Solo administracion o staff

- `GET /users/`
- `GET/PATCH/PUT /users/<id>/`

## Recursos del dominio

Modelos principales definidos en `app/models.py`:

- `Category`
- `Banner`
- `Product`
- `Cart`
- `UserProfile`
- `DeliveryAddress`
- `RoleChangeRequest`
- `Order`
- `OrderItem`
- `Shipment`
- `ShipmentLocation`

## Notas sobre pedidos y seguimiento

- Los pedidos almacenan una copia de la direccion de entrega al momento de crear el pedido.
- Un pedido puede tener un `Shipment` asociado.
- El shipment guarda ultima ubicacion, velocidad, rumbo, ETA y un historial de puntos.
- El endpoint de tracking permite consultar el estado del envio y su ruta reciente.

## Pruebas

Ejecutar tests:

```powershell
.\venv\Scripts\python.exe manage.py test
```

La configuracion actual usa SQLite en memoria para tests cuando `USE_SQLITE_FOR_TESTS=1`, evitando depender de PostgreSQL durante la suite.

## Estado actual

Verificado localmente:

- `manage.py check`
- `manage.py test`

## Mejoras recomendadas

- Agregar `requirements.txt` o `pyproject.toml`.
- Mover secretos y credenciales de base de datos a variables de entorno.
- Agregar documentacion OpenAPI/Swagger.
- Separar configuraciones por entorno: desarrollo, testing y produccion.
- Definir politicas CORS mas restrictivas para produccion.
