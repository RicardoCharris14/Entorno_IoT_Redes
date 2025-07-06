import asyncio
import aiohttp

async def recolectar_datos():
    async with aiohttp.ClientSession() as sesion:
        while True:
            async with sesion.get("http://192.168.1.5:6000/data") as response:
                data = await response.json()
                for registro in data:
                    _, _, temp, pres, hum = registro
                    if temp > 50 or hum > 80:
                        print(f"¡ALERTA! Temperatura: {temp}, Humedad: {hum}\n")
                    else:
                        print(f"Valores normales: {temp}°C, {hum}% humedad\n")
            
            await asyncio.sleep(5)
    

asyncio.run(recolectar_datos())