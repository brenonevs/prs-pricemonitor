import asyncio

from discord.ext import commands

from amazonPriceBot.amazonPriceBot import AmazonPriceBot

# Classe que representa o bot do Discord
class MonitorDiscordBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def on_ready(self):
        print(f"Bot está pronto, estou conectado como {self.user}")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Verifica se a mensagem contém a palavra-chave "pesquisar"
        if "pesquisar" in message.content:

            # Extrai informações sobre o produto, preço e número de páginas da mensagem
            part = message.content.split(":")[1].strip()
            product, price, pages = part.split(",")
            price = int(price.strip())
            pages = int(pages.strip())

            print(f"Produto: {product} | Preço: {price}")
            await message.channel.send(f"Olá, {message.author.name}! Começando a busca pelos preços do produto {product} abaixo de R${price}...")

            # Obtém o loop assíncrono em execução
            loop = asyncio.get_running_loop()

            # Cria uma instância da classe AmazonPriceBot para realizar a pesquisa de preços
            amazonPriceBot = AmazonPriceBot(product, price, pages, message.author, loop)

            # Inicia a pesquisa de preços de forma assíncrona
            await amazonPriceBot.search_prices() 

        # Processa os comandos do bot
        await self.process_commands(message)
