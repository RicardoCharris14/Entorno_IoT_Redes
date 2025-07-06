import asyncio
import aiohttp

async def recolectar_datos():
    async with aiohttp.clientSession() as sesion:
        while True:
            async with sesion.get("http://127.0.0.1:6000/data") as response:
                data = await response.json()
                for registro in data:
                    _, _, temp, pres, hum = registro
                    if temp > 50 or hum > 80:
                        print(f"¡ALERTA! Temperatura: {temp}, Humedad: {hum}")
                    else:
                        print(f"Valores normales: {temp}°C, {hum}% humedad")
            
            await asyncio.sleep(5)
    

asyncio.run(recolectar_datos())