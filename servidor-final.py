import sqlite3
import socket
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import threading
import os

HOST = '127.0.0.1'
PORT_SERVER = 8000
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

# Función para iniciar servidor TCP
def iniciar_servidor_tcp():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT_SERVER))
        s.listen()
        print(f"Servidor TCP escuchando en puerto {PORT_SERVER}")
        while True:
            conn_socket, addr = s.accept()
            with conn_socket:
                data = conn_socket.recv(1024)
                if data:
                    sensor_data = json.loads(data.decode('utf-8'))
                    try:
                        cursor.execute(
                        """
                            INSERT INTO sensor_data (id, fecha_hora, temperatura, presion, humedad) 
                            VALUES (?, ?, ?, ?, ?)    
                        """, (sensor_data["id"], sensor_data["fecha_hora"],
                            sensor_data["temperatura"], sensor_data["presion"], sensor_data["humedad"])
                        )
                        conn.commit()
                        print(f"Datos guardados en el repositorio:\n{sensor_data}\n")   
                    except Exception as e:
                        print(f"Error al insertar los datos: {e}")

# Iniciar FastAPI y configurar plantillas
app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/data")
def get_data():
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC LIMIT 20")
    return cursor.fetchall()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC")
    registros = cursor.fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "registros": registros})

# Hilo para servidor TCP
threading.Thread(target=iniciar_servidor_tcp, daemon=True).start()

# Ejecutar la API
if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT_API)
