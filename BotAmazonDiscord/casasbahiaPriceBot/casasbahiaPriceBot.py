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

from time import sleep, time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o valor da variável de ambiente "USER_AGENT"
userAgent = os.getenv("USER_AGENT")

# Classe que representa o bot para verificar preços na Casas
class CasasBahiaPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://www.casasbahia.com.br"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop
        self.times = times
        self.stop_search = False  # Controle de interrupção
        self.processed_links = set()  # Conjunto para armazenar URLs já processados neste ciclo
        self.product_info = {}  # Dicionário para armazenar informações dos produtos

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
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-images')

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

    # Método para realizar a pesquisa do produto na Casas Bahia
    def search_product(self):
        search_input = self.driver.find_element(By.ID, 'search-form-input')
        search_input.send_keys(self.search_query)
        search_input.submit()

    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self):

        scrolls = 5

        try:
            for scroll in range(scrolls):
                self.driver.execute_script("window.scrollBy(0, 200)")
                sleep(1)  # Espera para a página carregar mais itens
                    
                # Verifica novos product cards
                product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.css-1enexmx div.styles__ProductCardWrapper-sc-43255755-3")
                for card in product_cards:
                    link_element = card.find_element(By.CSS_SELECTOR, "h3.product-card__title a").get_attribute('href')

                    if link_element in self.processed_links:
                        continue  # Ignora se o produto já foi processado neste ciclo

                    self.processed_links.add(link_element)
                    title_element = card.find_element(By.CSS_SELECTOR, "h3.product-card__title a")
                    price_element = card.find_element(By.CSS_SELECTOR, "div.product-card__highlight-price")
                    title = title_element.text.strip()
                    price_text = price_element.text.replace('R$', '').replace('.', '').replace(',', '.').strip()
                    price = float(price_text)

                    product_data = {
                        "title": title,
                        "price": price,
                        "url": link_element
                    }

                    # Verifica se o produto já foi processado antes e se o preço mudou
                    if link_element in self.product_info:

                        if self.product_info[link_element]['price'] != price:

                            self.product_info[link_element]['price'] = price
                            
                            if self.expected_price == None:

                                asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(title, price, link_element), self.loop)
                                    
                                print(f"Preço mudou para '{title}' \nPreço: R${price}\n\n")

                            elif price <= self.expected_price:

                                asyncio.run_coroutine_threadsafe(self.notify_discord_about_change_in_price(title, price, link_element), self.loop)

                                print(f"Preço mudou para '{title}' \nPreço: R${price}\n\n")
                    else:
                        # Novo produto encontrado
                        if self.expected_price == None:
                            
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(title, price, link_element), self.loop)
                                
                            print(f"Novo Preço encontrado para '{title}' \nPreço: R${price}\n\n")

                        elif price <= self.expected_price:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(title, price, link_element), self.loop)

                            print(f"Novo Preço encontrado para '{title}' \nPreço: R${price}\n\n")

                    # Atualiza as informações do produto no dicionário
                    self.product_info[link_element] = product_data
                            
            print(f"Encontrados {len(self.product_info)} produtos.")

        except Exception as e:
            print(f"Ocorreu um erro ao buscar produtos: {e}")

        self.priceList = list(self.product_info.values())
        print(self.priceList)
        return self.priceList
    
    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            # Primeiro, tenta encontrar o link da próxima página pelo aria-label
            next_page = self.driver.find_element(By.CSS_SELECTOR, "a[aria-label='Próxima página']")

            # Verifica se o link está habilitado para clique
            if next_page.get_attribute("aria-disabled") != "true":
                next_page.click()
                return True
            else:
                print("Link de próxima página está desabilitado.")
                return False
        except NoSuchElementException:
            try:
                # Se o link não for encontrado, tenta encontrar o botão "Carregar mais produtos" pelo CSS Selector original
                load_more_button = self.driver.find_element(By.CSS_SELECTOR, "button.styles__Button-sc-2d44249c-1.csFtFT")
                load_more_button.click()
                return True
            except NoSuchElementException:
                try:
                    # Se o botão original não for encontrado, tenta encontrar pelo texto do botão
                    load_more_button = self.driver.find_element(By.CLASS_NAME, "styles__Button-sc-2d44249c-1")
                    load_more_button.click()
                    return True
                except NoSuchElementException:
                    print("Nem o botão de próxima página nem o botão 'Carregar mais produtos' foram encontrados.")
                    return False
                except Exception as e:
                    print(f"Ocorreu um erro ao tentar clicar no botão 'Carregar mais produtos' pelo texto: {e}")
                    return False
            except Exception as e:
                print(f"Ocorreu um erro ao tentar clicar no botão 'Carregar mais produtos' pelo CSS Selector: {e}")
                return False
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ir para a próxima página: {e}")
            return False
        
    def stop_searching(self):
        self.stop_search = True

    # Método para realizar a busca de preços de forma síncrona
    def search_prices_sync(self):
        if self.times == "indeterminado":
            while not self.stop_search:
                self.restart_driver()
                self.driver.get(self.url)
                self.driver.fullscreen_window()
                sleep(0.7)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.driver.fullscreen_window() 
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
                self.driver.get(self.url)
                self.driver.fullscreen_window()
                sleep(0.7)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.driver.fullscreen_window() 
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
                self.driver.fullscreen_window()
                sleep(0.7)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.driver.fullscreen_window()
                    
                    self.check_prices()
                    
                    # Rola para o final da página após verificar os preços
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    sleep(1)  # Dá tempo para a página carregar após a rolagem

                    if not self.next_page():
                        break
                    sleep(1)
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.restart_driver()
                self.driver.get(link)
                self.driver.fullscreen_window()
                sleep(0.7)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.driver.fullscreen_window()

                    self.check_prices()

                    # Rola para o final da página após verificar os preços
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
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
        last_price = None
        notified_for_price_drop = False
        expected_price = float(expected_price)
        first_notification = True
        in_stock = True

        while not self.stop_search:
            try:
                self.restart_driver()
                self.driver.get(link)
                sleep(1)
            except TimeoutException:
                print(f"Timeout ao carregar {link}, tentando recarregar.")
                try:
                    self.driver.refresh()
                except Exception as e:
                    print(f"Erro ao tentar recarregar a página: {e}")
                    continue
                continue

            try:
                # Localizando o título do produto com o novo seletor CSS
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.dsvia-heading.css-1xmpwke")
                title = title_element.text

                # Localizando o preço do produto com o novo seletor CSS
                price_element = self.driver.find_element(By.CSS_SELECTOR, "p.dsvia-text.css-1luipqs")
                price_text = price_element.text.replace('R$', '').replace('.', '').replace(',', '.').strip()
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
