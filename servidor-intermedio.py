import socket
import ssl
import struct
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
from pymodbus.client import ModbusTcpClient
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.constants import Endian

HOST = '0.0.0.0'
PORT = 8080

# Contexto TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')

# Cargar clave pública del sensor
with open("public_key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

# Servidor TCP con TLS
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((HOST, PORT))
    sock.listen()
    print(f"Servidor TLS escuchando en puerto {PORT}")

    with context.wrap_socket(sock, server_side=True) as ssock:
        while True:
            conn, addr = ssock.accept()
            print(f"Conexión TLS desde {addr}")

            with conn:
                data = conn.recv(1024)
                if not data:
                    continue

                message = data[:22]
                signature = data[22:]

                # Verificar la firma
                try:
                    public_key.verify(
                        signature,
                        message,
                        padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    print("Firma válida.")
                except InvalidSignature:
                    print("Firma inválida. El mensaje fue alterado.")
                    continue

                # Desempaquetar datos binarios
                unpacked_data = struct.unpack('!hqfff', message)
                sensor = {
                    "id": unpacked_data[0],
                    "fecha_hora": unpacked_data[1],
                    "temperatura": unpacked_data[2],
                    "presion": unpacked_data[3],
                    "humedad": unpacked_data[4]
                }

                print(f"Datos recibidos:{sensor}\n")

                # Reenviar al servidor final (sin TLS en este ejemplo)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_final:
                        s_final.connect(('127.0.0.1', 8000))
                        s_final.sendall(json.dumps(sensor).encode('utf-8'))
                except Exception as e:
                    print(f"Error al conectar con el servidor final: {e}\n")
