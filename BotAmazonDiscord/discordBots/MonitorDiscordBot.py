import re
import asyncio

from discord.ext import commands

from amazonPriceBot.amazonPriceBot import AmazonPriceBot
from kabumPriceBot.kabumPriceBot import KabumPriceBot

class MonitorDiscordBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.amazon_bot_instance = None
        self.kabum_bot_instance = None

    async def on_ready(self):
        print(f"Bot está pronto, estou conectado como {self.user}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Comando para parar a busca
        if message.content in ['!stop', '!parar']:
            if self.amazon_bot_instance:
                self.amazon_bot_instance.stop_searching()
            if self.kabum_bot_instance:
                self.kabum_bot_instance.stop_searching()
            await message.channel.send("Busca interrompida.")
            # Resetar as instâncias para None depois de parar
            self.amazon_bot_instance = None
            self.kabum_bot_instance = None
            return

        # Detectar a mensagem com o novo formato
        if re.search(r"!pesquisar\(produto\s*=\s*.+?,\s*preço\s*=\s*.+?,\s*paginas\s*=\s*.+?,\s*site\s*=\s*.+?,\s*repetir\s*=\s*.+?\)", message.content):
            match = re.search(r"!pesquisar\(produto\s*=\s*(.+?),\s*preço\s*=\s*(.+?),\s*paginas\s*=\s*(.+?),\s*site\s*=\s*(.+?),\s*repetir\s*=\s*(.+?)\)", message.content)
            product = match.group(1).strip()
            price = int(match.group(2).strip())
            pages = int(match.group(3).strip())
            site = match.group(4).strip().lower()
            times = match.group(5).strip()

            if times.isdigit():
                times = int(times)
            else:
                repeat_message = f" Vou repetir o processo na seguinte quantidade: {times}."

            await message.channel.send(f"Olá, {message.author.name}! Começando a busca pelos preços do produto {product} abaixo de R${price} no site {site}.{repeat_message}")

            if "amazon" in site:
                loop = asyncio.get_running_loop()
                self.amazon_bot_instance = AmazonPriceBot(product, price, pages, message.author, loop, times)
                await self.amazon_bot_instance.search_prices()
            
            elif "kabum" in site:
                loop = asyncio.get_running_loop()
                self.kabum_bot_instance = KabumPriceBot(product, price, pages, message.author, loop, times)
                await self.kabum_bot_instance.search_prices()

        await self.process_commands(message)