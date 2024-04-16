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

# Classe que representa o bot para verificar preços na Amazon
class AmazonPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://www.amazon.com.br"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop
        self.times = times
        self.stop_search = False  # Controle de interrupção
        self.product_info = []
        self.product_names = []

        # Configurações do navegador Chrome
        self.options = Options()
        user_agent = userAgent
        self.options.add_argument(f'user-agent={user_agent}')
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


    # Método para realizar a pesquisa do produto na Amazon
    def search_product(self):
        try:
            searchBox = self.driver.find_element(By.XPATH, '//input[@id="twotabsearchtextbox"]')
            searchBox.click()
            searchBox.send_keys(self.search_query)
            searchBox.submit()
        except NoSuchElementException:
            try:
                searchBox = self.driver.find_element(By.XPATH, '//input[@id="nav-bb-search"]')
                searchBox.click()
                searchBox.send_keys(self.search_query)
                searchBox.submit()
            except Exception as e:
                print(f"Ocorreu um erro ao tentar realizar a busca por {self.search_query}: {e}\n")
                exit()

    # Verifica se uma string representa um preço válido
    def is_valid_price(self, price_str):
        try:
            float(price_str)
            return True
        except ValueError:
            return False

    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self):
        product_links = []
        try:
            # Obtém os títulos e links dos produtos na página atual
            product_titles = self.driver.find_elements(By.XPATH, '//h2[contains(@class, "a-size-mini a-spacing-none")]/a')
            for title_link in product_titles:
                product_links.append({
                    "url": title_link.get_attribute('href'),
                    "title": title_link.text
                })

            print(f"Encontrados {len(product_links)} produtos na página atual.")

            for product in product_links:
                if self.stop_search:  # Verificar antes de cada ação
                    break
                self.driver.get(product["url"])
                sleep(1)
                title = product["title"]
                price = None

                try:
                    # Tenta obter o preço do produto
                    price_whole = self.driver.find_element(By.CLASS_NAME, 'a-price-whole').text.replace('.', '').replace(',', '')
                    price_fraction = self.driver.find_element(By.CLASS_NAME, 'a-price-fraction').text
                    price_str = f"{price_whole}.{price_fraction}"

                    if not self.is_valid_price(price_str):
                        raise NoSuchElementException

                    price = float(price_str)

                    product_data = {
                        "titulo": title,
                        "preço": price,
                        "url": product["url"]
                    }

                    if product_data["titulo"] not in self.product_names:
                        self.product_names.append(product_data["titulo"])
                        self.product_info.append(product_data)

                        if self.expected_price == None:
                            
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(product['title'], price, product["url"]), self.loop)
                            
                            print(f"Novo produto!\nPreço encontrado para '{product['title']}' \nPreço: R${price}\n\n")

                        elif price <= self.expected_price:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(product['title'], price, product["url"]), self.loop)

                            print(f"Novo produto!\nPreço encontrado para '{product['title']}' \nPreço: R${price}\n\n")

                    else:
                        for product in self.product_info:

                            if product["titulo"] == product_data["titulo"]:

                                if product["preço"] != product_data["preço"]:

                                    product["preço"] = product_data["preço"]

                                    if self.expected_price == None:
                                        
                                        asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(product['title'], price, product["url"]), self.loop)
                                        
                                        print(f"Preço mudou para '{product['title']}' \nPreço: R${price}\n\n")

                                    elif price <= self.expected_price:

                                        asyncio.run_coroutine_threadsafe(self.notify_discord_about_change_in_price(product['title'], price, product["url"]), self.loop)

                                        print(f"Preço mudou para '{product['title']}' \nPreço: R${price}\n\n")
                    


                except NoSuchElementException:
                    try:
                        # Tenta obter o preço de outra forma, caso o anterior não funcione
                        price_element = self.driver.find_element(By.XPATH, '//span[contains(@id, "price") and contains(@class, "a-size-medium")]')
                        price_text = price_element.get_attribute('innerHTML')
                        price_text = price_text.replace('R$', '').replace('&nbsp;', '').replace('.', '').strip()
                        if ',' in price_text:
                            price_whole, price_fraction = price_text.split(',')
                        else:
                            price_whole = price_text
                            price_fraction = '00'  

                        price = float(f"{price_whole}.{price_fraction}")
                        print(f"Preço encontrado para '{title}': ${price}")

                        product_data = {
                            "titulo": title,
                            "preço": price,
                            "url": product["url"]
                        }

                        print(product_data)

                        if product_data["titulo"] not in self.product_names:
                            self.product_names.append(product_data["titulo"])
                            self.product_info.append(product_data)
                        
                            if self.expected_price == None:
                                
                                asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(product['title'], price, product["url"]), self.loop)
                                
                                print(f"Novo produto!\nPreço encontrado para '{product['title']}' \nPreço: R${price}\n\n")

                            elif price <= self.expected_price:

                                asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(product['title'], price, product["url"]), self.loop)

                                print(f"Novo produto!\nPreço encontrado para '{product['title']}' \nPreço: R${price}\n\n")

                        else:
                            for product in self.product_info:

                                if product["titulo"] == product_data["titulo"]:

                                    if product["preço"] != product_data["preço"]:

                                        product["preço"] = product_data["preço"]

                                        if self.expected_price == None:
                                            
                                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(product['title'], price, product["url"]), self.loop)
                                            
                                            print(f"Preço mudou para '{product['title']}' \nPreço: R${price}\n\n")

                                        elif price <= self.expected_price:

                                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_change_in_price(product['title'], price, product["url"]), self.loop)

                                            print(f"Preço mudou para '{product['title']}' \nPreço: R${price}\n\n")
                            
                    except NoSuchElementException:
                        print(f"Não foi possível encontrar o preço para {title}. Site pode estar fora do ar.\n")
                        continue

                except Exception as e:
                    print(f"Erro ao processar o preço para {title}: {e}. Site pode estar fora do ar.")
                    continue

                finally:
                    self.priceList.append({"titulo": title, "preço": price})

        except Exception as e:
            print(f"Ocorreu um erro geral ao tentar buscar os produtos e preços: {e}. Site pode estar fora do ar.")

        return self.priceList

    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            next_page = self.driver.find_element(By.XPATH, '//a[contains(@class, "s-pagination-next")]')
            next_page.click()
            return True
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ir para a próxima página: {e}")
            return False

    # Método para navegar para a página anterior de resultados
    def previous_page(self):
        try:
            previous_page = self.driver.find_element(By.XPATH, '//a[contains(@class, "s-pagination-previous")]')
            previous_page.click()
            return True
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ir para a página anterior: {e}")
            return False

    def stop_searching(self):
        self.stop_search = True

    def search_prices_sync(self):
        if self.times == "indeterminado":
            while not self.stop_search:
                self.restart_driver()
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
        else:
            for _ in range(self.times):
                if self.stop_search:
                    break
                self.restart_driver()
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
        if self.times == "indeterminado":
            while not self.stop_search:
                self.restart_driver()
                self.driver.get(link)
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
                self.restart_driver()
                self.driver.get(link)
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
                sleep(1)        
            except TimeoutException:
                # Se ocorrer um timeout, recarregue a página e vá para a próxima iteração
                print(f"Timeout ao carregar {link}, tentando recarregar.")
                try:
                    self.driver.refresh()
                except Exception as e:
                    print(f"Erro ao tentar recarregar a página: {e}")
                    continue  # Pula para a próxima iteração do loop
                continue

            try:
                # Tenta localizar o título do produto
                title_element = self.driver.find_element(By.ID, "productTitle")
                title = title_element.text.strip()

                # Tenta localizar a parte inteira do preço
                price_whole_element = self.driver.find_element(By.CSS_SELECTOR, "span.a-price-whole")
                price_whole_text = price_whole_element.text.replace('.', '').strip()

                # Tenta localizar a fração do preço
                price_fraction_element = self.driver.find_element(By.CSS_SELECTOR, "span.a-price-fraction")
                price_fraction_text = price_fraction_element.text.strip()

                price_text = f"{price_whole_text},{price_fraction_text}"
                price = float(price_text.replace(',', '.'))

                if last_price is None:
                    last_price = price

                if first_notification:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(title, price, link), self.loop)
                    first_notification = False

                # Condição para enviar notificação apenas quando o preço diminuir ou for menor que o esperado
                if price < last_price or (price < expected_price and not notified_for_price_drop):
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(title, price, link), self.loop)
                    print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")
                    last_price = price  # Atualiza o último preço verificado
                    notified_for_price_drop = True
                    
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