import pandas as pd
import threading
import asyncio
import os

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from time import sleep, time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o valor da variável de ambiente "USER_AGENT"
userAgent = os.getenv("USER_AGENT")

# Classe que representa o bot para verificar preços na Pichau
class PichauPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://www.pichau.com.br"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop
        self.times = times
        self.stop_search = False  # Controle de interrupção
        self.processed_links = set()  # Conjunto para armazenar URLs já processados neste ciclo
        self.products_info = []
        self.products_names = []

        # Configurações do navegador Chrome
        self.options = Options() 
        self.user_agent = userAgent
        self.options.add_argument(f'user-agent={self.user_agent}')
        #self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920x1080')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_experimental_option('excludeSwitches', ['enable-logging']  )
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-images')
        self.options.add_experimental_option("excludeSwitches", ['enable-automation'])

        service = Service(ChromeDriverManager().install())
        service.log_path = 'NUL'

        self.driver = webdriver.Chrome(service=service, options=self.options)

    async def notify_discord_about_new_product(self, title, price, url):
        message = "-" * 70 + f"\n\n**Novo Produto!**\n**Produto:** {title}\n**Preço Abaixo do Esperado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_change_in_price(self, title, price, url):
        message = "-" * 70 + f"\n\n**Mudança no preço**\n**Produto:** {title}\n**Preço Abaixo do Esperado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)


    async def notify_discord_about_monitoring_new_product(self, title, price, url):
        message = "-" * 70 + f"\n\n**Novo Produto!**\n**Produto:** {title}\n**Preço Monitorado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_monitoring_new_price(self, title, price, url):
        message = "-" * 70 + f"\n\n**Mudança no preço!**\n**Produto:** {title}\n**Preço Monitorado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_error(self):
        message = "-" * 70 + f"\n\nOcorreu um erro ao monitorar o produto. \n\nO produto pode estar sem estoque, a página pode estar indisponível ou a estrutura do site mudou!\n\n" + "-" * 70
        await self.user.send(message)

    # Método para realizar a pesquisa do produto na Pichau
    def search_product(self):
        if " " in self.search_query:
            self.search_query = self.search_query.replace(" ", "%20")
        search_url = f"{self.url}/search?q={self.search_query}"
        self.driver.get(search_url)
        self.driver.fullscreen_window()
        sleep(1)

    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self):
        try:
            self.driver.fullscreen_window()
            sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            sleep(1)
            try:
                product_cards = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'MuiGrid-root') and contains(@class, 'MuiGrid-item')]/a[contains(@class, 'jss16')]")
                print(f"Encontrados {len(product_cards)} cartões de produto na página.")
            except NoSuchElementException:
                print("Erro: Não foi possível encontrar os cartões de produto na página.")
            except WebDriverException as e:
                print(f"Erro do WebDriver")
            except Exception as e:
                print(f"Erro geral ao tentar encontrar os cartões de produto")

            for card in product_cards:
                if self.stop_search:
                    break

                try:
                    product_link = card.get_attribute('href')
                except Exception as e:
                    print(f"Erro ao tentar encontrar o link do produto")
                    continue

                try: 
                    title_element = WebDriverWait(card, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h2.MuiTypography-root"))
                    )
                    product_title = title_element.text if title_element else "Título não encontrado"
                except Exception as e:
                    print(f"Erro ao tentar encontrar o título do produto")
                    continue

                try:
                    price_element = WebDriverWait(card, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.jss83"))
                    )
                    price_text = price_element.text
                except Exception as e:
                    print(f"Erro ao tentar encontrar o preço do produto")
                    continue

                product_info = {
                    "link": product_link,
                    "title": product_title,
                    "price": price_text
                }

                if product_info['title'] not in self.products_names:
                    self.products_names.append(product_info['title'])
                    self.products_info.append(product_info)

                    try:
                        price = float(price_text.replace('R$', '').replace('.', '').replace(',', '.').strip())
                    except ValueError:
                        print(f"Erro ao converter o preço do produto '{product_title}'. Preço encontrado: '{price_text}'")
                        continue

                    if self.expected_price is None:
                        try:
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(product_info['title'], price, product_info["link"]), self.loop)
                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                        except Exception as e:
                            print(f"Erro ao notificar sobre o novo produto")
                    elif price <= self.expected_price:
                        try:
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(product_info['title'], price, product_info["link"]), self.loop)
                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                        except Exception as e:
                            print(f"Erro ao notificar sobre o novo produto")
                else:
                    for product in self.products_info:
                        if product_info['title'] == product['title'] and product_info['price'] != product['price']:
                            try:
                                price = float(product_info['price'].replace('R$', '').replace('.', '').replace(',', '.').strip())
                            except ValueError:
                                print(f"Erro ao converter o preço do produto '{product_info['title']}'. Preço encontrado: '{product_info['price']}'")
                                continue

                            product['price'] = product_info['price']

                            if self.expected_price is None:
                                try:
                                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(product_info['title'], price, product_info["link"]), self.loop)
                                    print(f"Novo Preço!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                                except Exception as e:
                                    print(f"Erro ao notificar sobre o novo preço")
                            elif price <= self.expected_price:
                                try:
                                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_change_in_price(product_info['title'], price, product_info["link"]), self.loop)
                                    print(f"Novo Preço!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                                except Exception as e:
                                    print(f"Erro ao notificar sobre o novo preço")

        except Exception as e:
            print(f"Erro geral na busca de produtos e preços")

        return self.products_info

    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            self.driver.execute_script("window.scrollBy(0, 2400);")
            sleep(5)
            # Encontra o botão de próxima página usando o seletor CSS para o ícone SVG
            print("\nTentando encontrar o botão de próxima página...\n")

            next_page_button = self.driver.find_element(By.XPATH, "//*[@id='__next']/main/div[2]/div/div[1]/nav/ul/li[9]/button")

            next_page_button.click()

            print("\nClicou no botão de próxima página.\n")

            return True

        except NoSuchElementException:
            print("O botão de próxima página não foi encontrado.")
            return False
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ir para a próxima página")
            return False

    def stop_searching(self):
        self.stop_search = True

    # Método para realizar a busca de preços de forma síncrona
    def search_prices_sync(self):
        if self.times == "indeterminado":
            while not self.stop_search:
                self.restart_driver()
                sleep(0.7)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    if not self.next_page():
                        break
                    sleep(1)
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.next_page_counter = 2
                self.restart_driver()
                sleep(0.7)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    if not self.next_page():
                        break
                    sleep(1)
        
        self.driver.quit()

    
    # Método para realizar a busca de preços de forma síncrona
    def check_link_prices(self, link):
        if self.times == "indeterminado":
            while not self.stop_search:
                self.restart_driver()
                self.driver.get(link)
                sleep(0.7)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    if not self.next_page():
                        break
                    sleep(1)
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.restart_driver()
                self.driver.get(link)
                sleep(0.7)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices()
                    sleep(1)
                    if not self.next_page():
                        break
                    sleep(1)
        
        self.driver.quit()

    def restart_driver(self):
        self.driver.quit()
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    # Função para monitorar um link de um produto específico e se o preço dele mudou   
    def check_specific_product(self, link, expected_price):
        last_price = None  # Variável para armazenar o último preço verificado

        notified_for_price_drop = False 

        expected_price = float(expected_price)

        first_notification = True

        in_stock = True

        while not self.stop_search:
            try:
                # Tente carregar a página
                self.restart_driver()
                self.driver.get(link)
                self.driver.fullscreen_window()

                sleep(2)
            except TimeoutException:
                # Se ocorrer um timeout, recarregue a página e vá para a próxima iteração
                print(f"Timeout ao carregar {link}, tentando recarregar.")
                try:
                    self.driver.refresh()
                except Exception as e:
                    print(f"Erro ao tentar recarregar a página")
                    continue  # Pula para a próxima iteração do loop
                continue

            try:
                # Localizar o título do produto com o novo seletor
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.MuiTypography-root.jss39.MuiTypography-h6")
                title = title_element.text

                # Localizar o preço do produto com o novo seletor
                price_element = self.driver.find_element(By.CSS_SELECTOR, "div.jss88")
                price_text = price_element.text.replace('R$', '').replace('&nbsp;', '').replace('.', '').replace(',', '.').strip()

                price = float(price_text)

                print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")

                if last_price is None:
                    last_price = price

                if first_notification:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(title, price, link), self.loop)
                    first_notification = False

                # Condição modificada para enviar notificação apenas quando o preço diminuir ou for menor que o esperado
                if price < last_price or (price < expected_price and not notified_for_price_drop):
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(title, price, link), self.loop)
                    print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")
                    last_price = price  # Atualiza o último preço verificado
                    notified_for_price_drop = True
                
                in_stock = True

            except NoSuchElementException:
                print(f"Não foi possível encontrar o título ou preço para a URL: {link}")
                if in_stock:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_error(), self.loop)
                    in_stock = False    
                continue

            except WebDriverException as e:
                if "Out of Memory" in str(e):
                    print("Detectado erro 'Out of Memory'. Reiniciando o driver...")
                    self.restart_driver()


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
