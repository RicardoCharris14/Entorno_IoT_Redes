import asyncio
import aiohttp

async def recolectar_datos():
    async with aiohttp.ClientSession() as sesion:
        contador = 1
        while True:
            async with sesion.get("http://127.0.0.1:4200/data") as response:
                data = await response.json()
                print(f"***LECTURA DE DATOS NÚMERO {contador}***\n")
                for i, registro in enumerate(data):
                    _, _, temp, pres, hum = registro
                    temperatura = (0.0 <= temp <= 3.0 or 27.0 <= temp <= 30.0)
                    presion = (0.7 <= pres <= 0.75 or 1.25 <= pres <= 1.3)
                    humedad = (0.0 <= hum <= 10.0 or 90.0 <= hum <= 100.0)
                    
                    if not temperatura and not presion and not humedad: 
                        print(f"Registro {i+1}: Condiciones normales: {temp}°C, {pres} atm y {hum}% de humedad.")
                    else:
                        print(f"Registro {i+1}:\n{{")                        
                        if temperatura:
                            print(f"\t¡ALERTA! Temperatura: {temp}°C")
                        else:
                            print(f"\tTemperatura normal: {temp}°C")
                        if  presion:
                            print(f"\t¡ALERTA! Presion: {pres} atm")
                        else: 
                            print(f"\tPresion normal: {pres} atm")
                        if humedad:
                            print(f"\t¡ALERTA! Humedad: {hum}%")
                        else: 
                            print(f"\tHumedad normal: {hum}%")
                        
                        print("}")
                    
                    if (i == len(data)-1):
                        print("\n\n")
                        contador+=1
                        
                    

                        
            
            await asyncio.sleep(5)
    

asyncio.run(recolectar_datos())