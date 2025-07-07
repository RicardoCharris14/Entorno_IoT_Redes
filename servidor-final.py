import sqlite3
import uvicorn
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from asyncua import ua, Server, uamethod


HOST_SERVER = '0.0.0.0'
PORT_SERVER = 4840
HOST_API = '0.0.0.0'
PORT_API = 4200

# Crear carpeta de plantillas si no existe
os.makedirs("templates", exist_ok=True)

# Conexión SQLite
conn = sqlite3.connect("sensors.db", check_same_thread=False)
cursor = conn.cursor()
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


class SubHandler:
    def __init__(self, cursor, conn, server_nodes):
        self.cursor = cursor
        self.conn = conn
        self.server_nodes = server_nodes
        self.data_buffer = {}

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

                self.cursor.execute("""
                    INSERT INTO sensor_data (id, fecha_hora, temperatura, presion, humedad) 
                    VALUES (?, ?, ?, ?, ?)
                """, (sensor_data["id"], sensor_data["fecha_hora"], sensor_data["temperatura"], sensor_data["presion"], sensor_data["humedad"]))
                self.conn.commit()
                print(f"Datos guardados en el repositorio:\n{sensor_data}\n")

                # Limpiar buffer para la próxima lectura
                self.data_buffer.clear()


        except Exception as e:
            print(f"Error al procesar el cambio de datos o insertar en la BD: {e}")


async def main():
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://{HOST_SERVER}:{PORT_SERVER}/freeopcua/server/")

    uri = "http://examples.freeopcua.github.io"
    idx = await server.register_namespace(uri)

    myobj = await server.nodes.objects.add_object(idx, "MySensor")

    id_var = await myobj.add_variable(idx, "ID", ua.Variant(0, ua.VariantType.Int16))
    fecha_hora_var = await myobj.add_variable(idx, "FechaHora", ua.Variant(0, ua.VariantType.Int64))
    temp_var = await myobj.add_variable(idx, "Temperatura", ua.Variant(0.0, ua.VariantType.Float))
    press_var = await myobj.add_variable(idx, "Presion", ua.Variant(0.0, ua.VariantType.Float))
    hum_var = await myobj.add_variable(idx, "Humedad", ua.Variant(0.0, ua.VariantType.Float))

    for var in [id_var, fecha_hora_var, temp_var, press_var, hum_var]:
        await var.set_writable()

    server_nodes = {
        "id": id_var, "fecha_hora": fecha_hora_var, "temp": temp_var,
        "press": press_var, "hum": hum_var
    }

    handler = SubHandler(cursor, conn, server_nodes)
    sub = await server.create_subscription(500, handler)

    await sub.subscribe_data_change([id_var, fecha_hora_var, temp_var, press_var, hum_var])

    config = uvicorn.Config(app, host=HOST_API, port=PORT_API, log_level="info")
    server_api = uvicorn.Server(config)

    async with server:
        print(f"Servidor OPC UA escuchando en opc.tcp://{HOST_SERVER}:{PORT_SERVER}")
        await server_api.serve()


# Iniciar FastAPI y configurar plantillas
app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/data")
def get_data():
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC LIMIT 3")
    datos_raw = cursor.fetchall()
    
    # Formatear datos con fecha legible
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
    return templates.TemplateResponse("index.html", {"request": request, "registros": registros})


# Ejecutar la API
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Servidores detenidos.")
