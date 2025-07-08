# 📦 Requisitos Generales

- Python 3.10 o superior
- g++ (para compilar el cliente en C++)
- OpenSSL instalado (versión >= 1.1)
- Acceso a puertos locales (`8080`, `4200`, `4840`)


## 🐍 Dependencias de Python

Instala las dependencias necesarias usando `pip`:

```bash
pip install cryptography asyncua fastapi uvicorn aiohttp jinja2
```

> ⚠️ Se recomienda usar un entorno virtual para mantener el proyecto aislado:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```


## 🧩 Estructura del Sistema

1. **Cliente en C++** simula un sensor industrial que:
   - Genera datos aleatorios
   - Firma el mensaje con RSA
   - Envía los datos binarios a través de un canal TLS

2. **Servidor intermedio (Python)**:
   - Verifica la firma con la clave pública
   - Reenvía los datos al servidor OPC UA

3. **Servidor final OPC UA (Python)**:
   - Almacena los datos en una base de datos SQLite
   - Expone API REST y sitio web con visualización en tiempo real

4. **Cliente de consulta (Python)**:
   - Consulta la API periódicamente
   - Detecta y alerta condiciones anómalas

---

## ⚙️ Configuración y Ejecución

### 1. 🔐 Generar Claves y Certificados

Asegúrate de tener los siguientes archivos en la raíz del proyecto:

- `private_key.pem` y `public_key.pem` (para firma RSA)
- `server_cert.pem` y `server_key.pem` (para TLS)

> Puedes generarlos con OpenSSL:

```bash
# Claves RSA
openssl genpkey -algorithm RSA -out private_key.pem
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Certificado y clave para TLS
openssl req -x509 -newkey rsa:2048 -keyout server_key.pem -out server_cert.pem -days 365 -nodes
```

### 2. 🧠 Ejecutar el servidor final OPC UA + API REST

```bash
python servidor-final.py
```

Esto inicia el servidor OPC UA (puerto `4840`) y el backend web (FastAPI en el puerto `4200`).

### 3. 🚀 Ejecutar el servidor intermedio

```bash
python servidor-intermedio.py
```

Este servidor escuchará conexiones TLS, verificará firmas y reenviará los datos al servidor OPC UA.

### 4. 🖥️ Compilar y ejecutar el cliente-sensor

```bash
g++ cliente-sensor.cpp -o sensor -lssl -lcrypto -pthread
./sensor
```

> El cliente leerá el ID desde un archivo `id.txt` y enviará nuevos datos cada 5 segundos.


### 5. 🌐 Ver página web con datos

Abre tu navegador en:

```
http://localhost:4200/
```

Podrás ver la tabla de registros en tiempo real, obtenida desde la base de datos.

### 6. 🔎 Ejecutar cliente de análisis de datos

```bash
python cliente-consulta.py
```

Este módulo consulta la API REST cada 5 segundos e imprime alertas si se detectan valores anómalos de temperatura, presión o humedad.

---

## 📂 Archivos clave

- `cliente-sensor.cpp`: cliente C++ que genera y envía datos
- `servidor-intermedio.py`: servidor intermedio que recibe y verifica
- `servidor-final.py`: servidor OPC UA + API + web
- `cliente-consulta.py`: detección de condiciones fuera de rango
- `templates/index.html`: plantilla web
- `sensors.db`: base de datos SQLite generada automáticamente


