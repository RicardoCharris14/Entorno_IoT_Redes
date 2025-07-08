import asyncio
import aiohttp

# Función principal que se encarga de recolectar datos de forma asíncrona desde la API
async def recolectar_datos():
    # Crea una sesión HTTP reutilizable
    async with aiohttp.ClientSession() as sesion:
        contador = 1  # Lleva el conteo de cuántas lecturas se han hecho

        while True:  # Bucle infinito para consultar cada 5 segundos
            # Realiza una solicitud GET a la API que entrega los datos del sensor
            async with sesion.get("http://127.0.0.1:4200/data") as response:
                data = await response.json()  # Convierte la respuesta en formato JSON
                print(f"***LECTURA DE DATOS NÚMERO {contador}***\n")

                # Itera por cada registro recibido
                for i, registro in enumerate(data):
                    _, _, temp, pres, hum = registro  # Extrae los valores de temperatura, presión y humedad

                    # Detecta si los valores están en rangos anómalos (alerta)
                    temperatura = (0.0 <= temp <= 3.0 or 27.0 <= temp <= 30.0)
                    presion = (0.7 <= pres <= 0.75 or 1.25 <= pres <= 1.3)
                    humedad = (0.0 <= hum <= 10.0 or 90.0 <= hum <= 100.0)

                    # Si todos los valores están normales
                    if not temperatura and not presion and not humedad: 
                        print(f"Registro {i+1}: Condiciones normales: {temp}°C, {pres} atm y {hum}% de humedad.")
                    else:
                        # Si hay alguna anomalía, mostrar alerta detallada por parámetro
                        print(f"Registro {i+1}:\n{{")                        
                        if temperatura:
                            print(f"\t¡ALERTA! Temperatura: {temp}°C")
                        else:
                            print(f"\tTemperatura normal: {temp}°C")
                        if presion:
                            print(f"\t¡ALERTA! Presion: {pres} atm")
                        else: 
                            print(f"\tPresion normal: {pres} atm")
                        if humedad:
                            print(f"\t¡ALERTA! Humedad: {hum}%")
                        else: 
                            print(f"\tHumedad normal: {hum}%")
                        
                        print("}")
                    
                    # Cuando se procesan todos los registros, imprime separación y aumenta contador
                    if (i == len(data)-1):
                        print("\n\n")
                        contador += 1
            
            # Espera 5 segundos antes de hacer otra lectura
            await asyncio.sleep(5)
    

# Ejecuta la función asíncrona principal
asyncio.run(recolectar_datos())
