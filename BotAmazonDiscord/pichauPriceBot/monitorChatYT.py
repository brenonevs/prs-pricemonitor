from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from random import randint
from dotenv import load_dotenv

import time
import os
import msvcrt
import json

load_dotenv()

userAgent = os.getenv("USER_AGENT")

class MonitorYTChat():
    def __init__(self):

        self.kill_chrome_processes()

        self.profile_path = r"C:\Users\breno\AppData\Local\Google\Chrome\User Data\Default"

        self.options = Options() 
        self.user_agent = userAgent
        self.options.add_argument(f'user-agent={self.user_agent}')

        # Isso serve para abrir o Chrome com o perfil padrão

        self.options.add_argument(r"user-data-dir=C:\Users\breno\AppData\Local\Google\Chrome\User Data")
        self.options.add_argument("profile-directory=Default")

        self.service = Service(executable_path=r"C:\Users\breno\OneDrive\Área de Trabalho\PROGRAMAÇÃO\Programação\Python\DEVIT\CheckPeopleBot\SeleniumVersion\ChromeDriver\chromedriver.exe")

        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.actions = ActionChains(self.driver)

    def kill_chrome_processes(self):
        os.system("taskkill /f /im chrome.exe")
        os.system("taskkill /f /im chromedriver.exe")

    def openYT(self, link):
        self.driver.get(link)
        print("\n\nAbrindo a live do YouTube...\n\n")
        time.sleep(3)
        print("\n\nLive do YouTube aberta!\n\n")
        time.sleep(1)
        print("\n\nAgora, o bot irá esperar 16 segundos para que você passe pelos anúncios e que comece a aparecer o chat ao vivo da live\n\n")
        time.sleep(16)


    def execute_custom_script(self):
        script = """
        // Inicializa uma lista para armazenar os conteúdos únicos dos links
        let uniqueContents = [];

        // Seleciona o nó alvo usando o ID do contêiner do chat
        const targetNode = document.getElementById('item-scroller');

        // Opções de configuração para o observer (observar a adição de novos elementos filhos)
        const config = { childList: true, subtree: true };

        // Callback que é executado quando ocorrem mutações
        const callback = function(mutationsList, observer) {
            for (let mutation of mutationsList) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        // Verifica se o nó adicionado contém o elemento desejado
                        if (node.querySelector && node.querySelector("a.yt-simple-endpoint.style-scope.yt-live-chat-text-message-renderer")) {
                            const link = node.querySelector("a.yt-simple-endpoint.style-scope.yt-live-chat-text-message-renderer");
                            const content = link.innerText; // Usa innerText para pegar apenas o texto visível
                            // Verifica se o conteúdo já está na lista
                            if (!uniqueContents.includes(content)) {
                                uniqueContents.push(content); // Adiciona o conteúdo à lista
                                console.log('Novo conteúdo detectado e adicionado à lista:', content);

                                window.open(content, '_blank');
                            }
                        }
                    });
                }
            }
        };

        // Cria o MutationObserver com o callback definido
        const observer = new MutationObserver(callback);

        // Inicia a observação
        observer.observe(targetNode, config);

        // Para parar a observação, use observer.disconnect();
        """

        try:
            self.driver.execute_script(script)
        except Exception as e:
            print(f"Erro ao executar script JavaScript: {e}")

    def check_chat_element(self):
        while True:
            try:
                print("\n\nTentando encontrar o chat...\n\n")
                chats = self.driver.find_element(By.ID, "item-list")
                for chat in chats:
                    print(f"\n\nChat encontrado:\n{chat.get_attribute('innerHtml')}\n\n")
            except Exception as e:
                print("\n\nChat não encontrado!\n")
                print(f"jErro: {e}\n\n")
                time.sleep(1)
            
    

    def change_to_live_chat(self):
        pass

    def main(self):
        self.openYT("https://www.youtube.com/watch?v=vsMLFC_7hfU&t=9445s")

        self.check_chat_element()

        time.sleep(3)
        

if __name__ == "__main__":
    monitor = MonitorYTChat()
    monitor.main()