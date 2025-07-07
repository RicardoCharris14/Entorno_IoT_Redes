import asyncio
import aiohttp

async def recolectar_datos():
    async with aiohttp.ClientSession() as sesion:
        while True:
            async with sesion.get("http://192.168.1.5:6000/data") as response:
                data = await response.json()
                for registro in data:
                    _, _, temp, pres, hum = registro
                    temperatura = (0.0 <= temp <= 5.0 or 25.0 <= temp <= 30.0)
                    presion = (0.7 <= pres <= 0.8 or 1.2 <= pres <= 1.3)
                    humedad = (0.0 <= hum <= 15.0 or 85.0 <= hum <= 100.0)
                    if not temperatura and not presion and not humedad: 
                        print(f"Condiciones normales: {temp}°C, {pres} atm y {hum}% de humedad. ")
                    else:                        
                        if temperatura:
                            print(f"¡ALERTA! Temperatura: {temp}°C")
                        else:
                            print(f"Temperatura normal: {temp}°C")
                        if  presion:
                            print(f"¡ALERTA! Presion: {pres} atm")
                        else: 
                            print(f"Presion normal: {pres} atm")
                        if humedad:
                            print(f"¡ALERTA! Humedad: {hum}% \n")
                        else: 
                            print(f"Humedad normal: {hum}% \n")
                        
                    

                        
            
            await asyncio.sleep(5)
    

asyncio.run(recolectar_datos())