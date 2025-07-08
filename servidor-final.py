import sqlite3           # Para manejar la base de datos SQLite
import uvicorn           # Para ejecutar el servidor FastAPI
import os                # Para manejo de archivos y carpetas
import asyncio           # Para programación asíncrona
from datetime import datetime  # Para trabajar con fechas y horas
from fastapi import FastAPI, Request  # FastAPI: framework web liviano
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates  # Soporte para plantillas HTML
from asyncua import ua, Server, uamethod        # Librería OPC UA asíncrona


# Configuración del host y puertos del servidor OPC UA y API web
HOST_SERVER = '0.0.0.0'      # Escucha en todas las interfaces de red
PORT_SERVER = 4840           # Puerto OPC UA estándar
HOST_API = '0.0.0.0'
PORT_API = 4200              # Puerto para la API web

# Crear carpeta de plantillas HTML si no existe
os.makedirs("templates", exist_ok=True)

# Conexión  y configuracion de la base de datos SQLite
conn = sqlite3.connect("sensors.db", check_same_thread=False)
cursor = conn.cursor()

# Crear tabla para almacenar los datos si no existe
cursor.execute(
"""
    CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY,
    fecha_hora INTEGER,
    temperatura REAL,
    presion REAL,
    humedad REAL)
"""
)
conn.commit()


 #Clase manejadora para las notificaciones de cambio en OPC UA
class SubHandler:
    def __init__(self, cursor, conn, server_nodes):
        self.cursor = cursor
        self.conn = conn
        self.server_nodes = server_nodes
        self.data_buffer = {}     # Almacena datos temporales antes de insertarlos

    async def datachange_notification(self, node, val, data):
        try:
            # Guardar el valor en el buffer temporal
            node_name = await node.read_display_name()
            self.data_buffer[node_name.Text] = val

            # Verificar si tenemos todos los campos
            required_fields = {"ID", "FechaHora", "Temperatura", "Presion", "Humedad"}
            if required_fields.issubset(self.data_buffer.keys()):
                # Insertar en la BD
                sensor_data = {
                    "id": self.data_buffer["ID"],
                    "fecha_hora": self.data_buffer["FechaHora"],
                    "temperatura": round(self.data_buffer["Temperatura"], 1),
                    "presion": round(self.data_buffer["Presion"], 2),
                    "humedad": round(self.data_buffer["Humedad"], 1)
                }

                # Insertar los datos en la base de datos
                self.cursor.execute("""
                    INSERT INTO sensor_data (id, fecha_hora, temperatura, presion, humedad) 
                    VALUES (?, ?, ?, ?, ?)
                """, (sensor_data["id"], sensor_data["fecha_hora"], sensor_data["temperatura"], sensor_data["presion"], sensor_data["humedad"]))
                self.conn.commit()

                # Mostrar por consola
                print(f"Datos guardados en el repositorio:\n{sensor_data}\n")

                # Limpiar buffer para la próxima lectura
                self.data_buffer.clear()


        except Exception as e:
            print(f"Error al procesar el cambio de datos o insertar en la BD: {e}")

# Función principal que lanza el servidor OPC UA y la API FastAPI
async def main():
     # Inicializar el servidor OPC UA
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://{HOST_SERVER}:{PORT_SERVER}/freeopcua/server/")

    # Registrar un namespace para identificar objetos del servidor
    uri = "http://examples.freeopcua.github.io"
    idx = await server.register_namespace(uri)

    # Crear objeto 'MySensor' con variables asociadas
    myobj = await server.nodes.objects.add_object(idx, "MySensor")

    # Agregar variables (nodos) al objeto
    id_var = await myobj.add_variable(idx, "ID", ua.Variant(0, ua.VariantType.Int16))
    fecha_hora_var = await myobj.add_variable(idx, "FechaHora", ua.Variant(0, ua.VariantType.Int64))
    temp_var = await myobj.add_variable(idx, "Temperatura", ua.Variant(0.0, ua.VariantType.Float))
    press_var = await myobj.add_variable(idx, "Presion", ua.Variant(0.0, ua.VariantType.Float))
    hum_var = await myobj.add_variable(idx, "Humedad", ua.Variant(0.0, ua.VariantType.Float))

    # Hacer que todas las variables sean modificables por un cliente OPC UA
    for var in [id_var, fecha_hora_var, temp_var, press_var, hum_var]:
        await var.set_writable()

    # Guardar las referencias de las variables
    server_nodes = {
        "id": id_var, "fecha_hora": fecha_hora_var, "temp": temp_var,
        "press": press_var, "hum": hum_var
    }

    # Crear manejador de suscripciones
    handler = SubHandler(cursor, conn, server_nodes)
    sub = await server.create_subscription(500, handler)

    # Suscribirse a los cambios en las variables
    await sub.subscribe_data_change([id_var, fecha_hora_var, temp_var, press_var, hum_var])

    # Configurar y lanzar el servidor FastAPI
    config = uvicorn.Config(app, host=HOST_API, port=PORT_API, log_level="info")
    server_api = uvicorn.Server(config)

    # Ejecutar ambos servidores simultáneamente
    async with server:
        print(f"Servidor OPC UA escuchando en opc.tcp://{HOST_SERVER}:{PORT_SERVER}")
        await server_api.serve()


# Crear instancia FastAPI y configurar plantillas HTML
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Ruta API para obtener los últimos 3 registros
@app.get("/data")
def get_data():
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC LIMIT 3")
    datos_raw = cursor.fetchall()
    
    # Formatear datos para hacer más legible la fecha
    datos_formateados = []
    for row in datos_raw:
        datos_formateados.append([
            row[0],                                                    
            datetime.fromtimestamp(row[1]).strftime('%d/%m/Y %H:%M:%S'), 
            round(row[2], 1),                                         
            round(row[3], 2),                                        
            round(row[4], 1)
        ])
    
    return datos_formateados

# Ruta principal para ver todos los datos en una página HTML
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC")
    registros_raw = cursor.fetchall()
    
    registros = []
    for row in registros_raw:
        registros.append([
            row[0],                                                   
            datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d %H:%M:%S'), 
            round(row[2], 1),                                          
            round(row[3], 2),                                         
            round(row[4], 1)                                         
        ])
    # Renderizar plantilla con los registros   
    return templates.TemplateResponse("index.html", {"request": request, "registros": registros})


# Ejecutar la API
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Servidores detenidos.")
