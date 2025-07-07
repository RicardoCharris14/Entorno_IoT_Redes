import sqlite3
import socket
import json
from fastapi import FastAPI
import uvicorn
import threading

HOST = '0.0.0.0'
PORT_SERVER = 4040
PORT_API = 6000

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


app = FastAPI()

@app.get("/data")
def get_data():
    cursor.execute("SELECT * FROM sensor_data ORDER BY fecha_hora DESC LIMIT 20")
    return cursor.fetchall()

threading.Thread(target=iniciar_servidor_tcp, daemon=True).start()

if __name__=="__main__":
    uvicorn.run(app, host=HOST, port=PORT_API)