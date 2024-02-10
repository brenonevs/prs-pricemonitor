import pandas as pd
import threading
import asyncio
import os
import random

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from time import sleep, time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o valor da variável de ambiente "USER_AGENT"
userAgent = os.getenv("USER_AGENT")

# Classe que representa o bot para verificar preços na Americanas
class AmericanasPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://www.americanas.com.br"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop
        self.times = times
        self.url_busca = None
        self.stop_search = False  # Controle de interrupção

        # Configurações do navegador Chrome
        options = Options()
        user_agent = userAgent
        options.add_argument(f'user-agent={user_agent}')
        #options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(ChromeDriverManager().install())
        service.log_path = 'NUL'

        self.driver = webdriver.Chrome(service=service, options=options)

    async def notify_discord(self, title, price, url):
        message = "-" * 70 + f"\n\n**Produto:** {title}\n**Preço Abaixo do Esperado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_monitoring(self, title, price, url):
        message = "-" * 70 + f"\n\n**Produto:** {title}\n**Preço Monitorado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_error(self):
        message = "-" * 70 + f"\n\nOcorreu um erro ao monitorar o produto. \n\nO produto pode estar sem estoque, a página pode estar indisponível ou a estrutura do site mudou!\n\n" + "-" * 70
        await self.user.send(message)

    # Método para realizar a pesquisa do produto na Americanas
    def search_product(self):
        search_url = f"https://www.americanas.com.br/busca/{self.search_query}"
        if " " in self.search_query:
            self.search_query = self.search_query.replace(" ", "-")
        self.driver.get(search_url)


    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self):
        product_links = []

        try:
            # Encontrar cartões de produto
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.inStockCard__Wrapper-sc-1ngt5zo-0.iRvjrG a")
            if not product_cards:
                print("Primeira tentativa falhou. Tentando novamente...")
                product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.src__Wrapper-sc-1wgxjb2-0.dUUAKQ a")

            print(f"Foram encontrados {len(product_cards) // 2} produtos na página {self.driver.current_url}")

            for card in product_cards:
                product_link = {"url": card.get_attribute('href')}
                # Encontrar título do produto
                title_selectors = ["h3.product-name__Name-sc-1shovj0-0.gUjFDF", "span.product-name__Name-sc-n8j4w0-0.fcRttM"]
                for selector in title_selectors:
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, selector)
                        if title_element:
                            product_link["title"] = title_element.text
                            break
                    except Exception:
                        continue

                # Encontrar preço do produto
                price_selectors = ["span.price__PromotionalPrice-sc-h6xgft-1.ctBJlj", "span.price__PromotionalPrice-sc-1i4tohf-1.hjtXiU"]
                for selector in price_selectors:
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, selector)
                        if price_element:
                            price_text = price_element.text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                            try:
                                price = float(price_text)
                                product_link["preço"] = price
                                break
                            except ValueError:
                                print(f"Formato de preço inválido para '{product_link.get('title', 'Unknown')}'")
                    except Exception:
                        continue

                product_links.append(product_link)

                # Enviar notificação para o Discord
                if self.stop_search:
                    break
                
                if product_link["url"] is not None:

                    if self.expected_price is None:
                        asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(product_link['title'], product_link["preço"], product_link["url"]), self.loop)
                        print(f"Preço encontrado para '{product_link['title']}' \nPreço: R${product_link['preço']}\n\n")
                        sleep(1)
                    elif product_link["preço"] <= self.expected_price:
                        asyncio.run_coroutine_threadsafe(self.notify_discord(product_link['title'], product_link["preço"], product_link["url"]), self.loop)
                        print(f"Preço encontrado para '{product_link['title']}' \nPreço: R${product_link['preço']}\n\n")
                        sleep(1)

        except Exception as e:
            print(f"Ocorreu um erro geral ao tentar buscar os produtos e preços: {e}")

        self.priceList = product_links
        print("\n\n\n\n\n\n\n\n\n")
        return self.priceList

    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            # Encontra o link que contém o SVG para a próxima página
            next_page_link = self.driver.find_element(By.CSS_SELECTOR, "a.src__PageLink-sc-82ugau-3.exDCiw")

            # Verifica se o link está habilitado para clique
            if not next_page_link.get_attribute("href"):
                print("Link de próxima página não está disponível.")
                return False

            # Clique no link se ele estiver disponível
            next_page_link.click()
            return True
        except NoSuchElementException:
            print("O link de próxima página não foi encontrado.")
            return False
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ir para a próxima página: {e}")
            return False
            
    def stop_searching(self):
        self.stop_search = True

    # Método para realizar a busca de preços de forma síncrona
    def search_prices_sync(self):
        print(f"Monitorando a busca por '{self.search_query}' na Americanas")
        if self.times == "indeterminado":
            while not self.stop_search:
                self.search_product()
                sleep(1)
                search_url = self.driver.current_url
                
                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    self.driver.get(search_url)
                    if not self.next_page():
                        break
                    search_url = self.driver.current_url
                    sleep(1)
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.driver.get(self.url)
                sleep(0.7)
                self.search_product()
                sleep(1)
                search_url = self.driver.current_url

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    self.driver.get(search_url)
                    if not self.next_page():
                        break
                    search_url = self.driver.current_url
                    sleep(1)
        
        self.driver.quit()

    
    # Método para realizar a busca de preços de forma síncrona
    def check_link_prices(self, link):
        print(f"Monitorando link: {link}")
        if self.times == "indeterminado":
            while not self.stop_search:
                self.driver.get(link)
                self.driver.fullscreen_window()
                self.driver.execute_script("window.scrollTo(0, 700)")
                sleep(0.7)
                search_url = self.driver.current_url

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    self.driver.get(search_url)
                    if not self.next_page():
                        break
                    search_url = self.driver.current_url
                    sleep(1)
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.driver.get(link)
                self.driver.fullscreen_window()
                self.driver.execute_script("window.scrollTo(0, 700)")
                sleep(0.7)
                search_url = self.driver.current_url

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    self.driver.get(search_url)
                    if not self.next_page():
                        break
                    search_url = self.driver.current_url
                    sleep(1)
        
        self.driver.quit()

    # Função para monitorar um link de um produto específico e se o preço dele mudou   
    def check_specific_product(self, link, expected_price):
        last_price = None  # Variável para armazenar o último preço verificado

        expected_price = float(expected_price)

        first_notification = True

        in_stock = True

        while not self.stop_search:
            self.driver.get(link)
            sleep(2)  # Aguarda um tempo fixo para a página carregar

            try:
                # Tenta localizar o título do produto
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.sc-fdfabab6-6.jNQQeD")
                title = title_element.text

                # Tenta localizar o preço do produto
                price_element = self.driver.find_element(By.CSS_SELECTOR, "h4.sc-5492faee-2.ipHrwP.finalPrice")
                price_text = price_element.text.replace('R$', '').replace('.', '').replace(',', '.').strip()

                price = float(price_text)

                if last_price is None:
                    last_price = price

                if first_notification:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(title, price, link), self.loop)
                    first_notification = False

                # Condição modificada para enviar notificação apenas quando o preço diminuir ou for menor que o esperado
                if price < last_price or price < expected_price:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(title, price, link), self.loop)
                    print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")
                    last_price = price  # Atualiza o último preço verificado

            except NoSuchElementException:
                print(f"Não foi possível encontrar o título ou preço para a URL: {link}")
                if in_stock:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_error(), self.loop)
                    in_stock = False
                continue

    async def search_specific_product(self, link, expected_price):
        await asyncio.get_event_loop().run_in_executor(None, self.check_specific_product, link, expected_price)

    async def search_prices(self):
        await asyncio.get_event_loop().run_in_executor(None, self.search_prices_sync)

    async def search_link_prices(self, link):
        await asyncio.get_event_loop().run_in_executor(None, self.check_link_prices, link)

    # Método para salvar os dados em um arquivo CSV
    def data_to_csv(self):
        df = pd.DataFrame(self.priceList)
        df = df.dropna(how='all')
        df.to_csv(f"{self.search_query}.csv", index=False)


