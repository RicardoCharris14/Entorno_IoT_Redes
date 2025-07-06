import socket
import struct
import json

HOST = '0.0.0.0'
PORT = 8080

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor TCP esuchando en puerto {PORT}")

    while True:
        conn, addr = s.accept()
        with conn:
            print(f"Conexión desde {addr}")
            data = conn.recv(1024)
            if not data:
                continue

            unpacked_data = struct.unpack('!hqfff', data)
            sensor = {
                "id": unpacked_data[0],
                "fecha_hora": unpacked_data[1],
                "temperatura": unpacked_data[2],
                "presion": unpacked_data[3],
                "humedad": unpacked_data[4]
            }

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_final:
                s_final.connect(('127.0.0.1', 4040))
                s_final.sendall(json.dumps(sensor).encode('utf-8'))