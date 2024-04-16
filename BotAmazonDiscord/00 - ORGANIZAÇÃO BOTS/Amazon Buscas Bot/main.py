import discord

import os

from discordBots.MonitorDiscordBot import MonitorDiscordBot

from dotenv import load_dotenv

load_dotenv()

# Obtém o ID do bot a partir das variáveis de ambiente
bot_id = os.getenv("BOT_ID")

# Configura as intenções do bot para permitir acessar o conteúdo das mensagens
intents = discord.Intents.default()
intents.message_content = True

# Cria uma instância do bot MonitorDiscordBot
bot = MonitorDiscordBot(command_prefix="!", intents=intents)
    
# Inicia o bot e o conecta ao servidor Discord
bot.run(bot_id)

    