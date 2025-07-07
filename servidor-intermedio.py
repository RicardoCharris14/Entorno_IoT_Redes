import socket
import ssl
import struct
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature
import asyncio
from asyncua import Client, ua


HOST = '0.0.0.0'
PORT = 8080
OPCUA_SERVER_URL = "opc.tcp://127.0.0.1:4840/freeopcua/server/"

# Contexto TLS
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')

# Cargar clave pública del sensor
with open("public_key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())


async def send_opcua_data(sensor_data):
    try:
        async with Client(url=OPCUA_SERVER_URL) as client:
            ns_idx = await client.get_namespace_index("http://examples.freeopcua.github.io")

            base_node_path = f"{ns_idx}:MySensor"
            node_id = await client.nodes.objects.get_child(base_node_path)

            id_var = await node_id.get_child(f"{ns_idx}:ID")
            fecha_hora_var = await node_id.get_child(f"{ns_idx}:FechaHora")
            temp_var = await node_id.get_child(f"{ns_idx}:Temperatura")
            press_var = await node_id.get_child(f"{ns_idx}:Presion")
            hum_var = await node_id.get_child(f"{ns_idx}:Humedad")            

            await id_var.write_value(ua.Variant(sensor_data["id"], ua.VariantType.Int16))
            await fecha_hora_var.write_value(ua.Variant(sensor_data["fecha_hora"], ua.VariantType.Int64))
            await temp_var.write_value(ua.Variant(sensor_data["temperatura"], ua.VariantType.Float))
            await press_var.write_value(ua.Variant(sensor_data["presion"], ua.VariantType.Float))
            await hum_var.write_value(ua.Variant(sensor_data["humedad"], ua.VariantType.Float))

            print("Datos enviados correctamente al servidor OPC UA.\n")
    except Exception as e:
        print(f"Error al conectar o enviar datos al servidor OPC UA: {e}\n")


def main():

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

                    # Reenviar datos al servidor final mediante OPC UA
                    asyncio.run(send_opcua_data(sensor))


if __name__=="__main__":
    main()
