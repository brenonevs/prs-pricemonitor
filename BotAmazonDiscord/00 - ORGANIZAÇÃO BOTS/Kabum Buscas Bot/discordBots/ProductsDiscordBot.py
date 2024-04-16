import requests

class DiscordBot():
    def __init__(self):
        self.webhook_url = 'https://discord.com/api/webhooks/1201629300533768192/-R_gup4cM2vKLK7JfyHHXRv3KOLvK597UoARkYyUq9vJQ9QEHi6jJtBois10aWGuzuK_'

    def send_message(self, mensagem):
        data = {"content": mensagem}
        response = requests.post(self.webhook_url, json=data)
        if response.status_code == 204:
            print("Mensagem enviada com sucesso.")    