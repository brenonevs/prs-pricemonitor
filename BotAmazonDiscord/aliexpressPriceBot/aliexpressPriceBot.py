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

# Classe que representa o bot para verificar preços na Ali Express

class AliExpressPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://best.aliexpress.com"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop
        self.times = times
        self.stop_search = False  # Controle de interrupção

        # Configurações do navegador Chrome
        self.options = Options() 
        user_agent = userAgent
        self.options.add_argument(f'user-agent={user_agent}')
        #options.add_argument('--headless')
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

    async def notify_discord(self, title, price, url):
        message = "-" * 70 + f"\n\n**Produto:** {title}\n**Preço Abaixo do Esperado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_monitoring(self, title, price, url):
        message = "-" * 70 + f"\n\n**Produto:** {title}\n**Preço Monitorado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
        await self.user.send(message)

    async def notify_discord_about_error(self):
        message = "-" * 70 + f"\n\nOcorreu um erro ao monitorar o produto. \n\nO produto pode estar sem estoque, a página pode estar indisponível ou a estrutura do site mudou!\n\n" + "-" * 70
        await self.user.send(message)

    # Método para realizar a pesquisa do produto na Ali Express
    def search_product(self):
        self.driver.get(self.url)
        # Encontrar o campo de pesquisa e inserir a consulta de pesquisa
        search_input = self.driver.find_element(By.ID, 'search-words')
        search_input.send_keys(self.search_query)

        # Encontrar o botão de envio pelo seletor de classe e clicar nele
        submit_button = self.driver.find_element(By.CLASS_NAME, 'search--submit--2VTbd-T')
        submit_button.click()

    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self):
        self.priceListInformation = []

        try:
            self.driver.fullscreen_window()
            sleep(1)

            scroll_increment = 500
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            while True:
                try:
                    product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.multi--outWrapper--SeJ8lrF")
                except NoSuchElementException:
                    print("Erro: Não foi possível encontrar os cartões de produto na página.")
                    break
                except WebDriverException as e:
                    print(f"Erro do WebDriver: {e}")
                    break

                for card in product_cards:
                    if self.stop_search:
                        break

                    try:
                        product_link = card.find_element(By.CSS_SELECTOR, "a.multi--container--1UZxxHY").get_attribute("href")
                        product_title = card.find_element(By.CSS_SELECTOR, "h3.multi--titleText--nXeOvyr").text
                        product_price = card.find_element(By.CSS_SELECTOR, "div.multi--price-sale--U-S0jtj").text
                    except NoSuchElementException:
                        print("Erro: Não foi possível encontrar um ou mais elementos do cartão de produto.")
                        continue

                    product_info = {
                        'link': product_link,
                        'title': product_title,
                        'price': product_price
                    }

                    if product_info not in self.priceListInformation:
                        self.priceListInformation.append(product_info)

                        try:
                            price = float(product_price.replace('R$', '').replace('.', '').replace(',', '.').strip())
                        except ValueError:
                            print(f"Erro ao converter o preço do produto '{product_title}'. Preço encontrado: '{product_price}'")
                            continue

                        if self.expected_price is None:
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(product_info['title'], price, product_info["link"]), self.loop)
                            print(f"Preço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                        elif price <= self.expected_price:
                            asyncio.run_coroutine_threadsafe(self.notify_discord(product_info['title'], price, product_info["link"]), self.loop)
                            print(f"Preço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

                try:
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                    sleep(2)

                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                except WebDriverException as e:
                    print(f"Erro ao executar a rolagem da página: {e}")
                    break

            print(f"Foram encontrados {len(self.priceListInformation)} produtos únicos na página.")

        except Exception as e:
            print(f"Erro geral na busca de produtos e preços: {e}")

        return self.priceListInformation

    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            # Encontra o botão de próxima página usando o seletor CSS
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.comet-pagination-item-link")

            # Encontrar o botão correto (o último na lista)
            if next_buttons:
                next_button = next_buttons[-1]
                
                # Verifica se o botão está habilitado para clique
                if not next_button.get_attribute("disabled"):
                    next_button.click()
                    return True
                else:
                    print("Botão de próxima página está desabilitado.")
                    return False
            else:
                print("Nenhum botão de próxima página foi encontrado.")
                return False

        except NoSuchElementException:
            print("O botão de próxima página não foi encontrado.")
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
                # Localiza o título do produto
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1[data-pl='product-title']")
                title = title_element.text

                # Localiza os elementos do preço e os concatena para formar o preço completo
                price_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.es--wrap--erdmPRe span")
                price_text = ''.join([element.text for element in price_elements]).replace('R$', '').replace(',', '.').strip()

                price = float(price_text)
                print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")

                if last_price is None:
                    last_price = price

                if first_notification:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(title, price, link), self.loop)
                    print(f"\n\nProduto: {title}\nPreço: R${price}\nLink: {link}\n\n")
                    first_notification = False

                if price < last_price or (price < expected_price and not notified_for_price_drop):
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring(title, price, link), self.loop)
                    print(f"\n\nProduto: {title}\nPreço: R${price}\nLink: {link}\n\n")
                    last_price = price
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


if __name__ == "__main__":
    # Exemplo de uso
    bot = AliExpressPriceBot("smartwatch", 500, 2, None, None, "indeterminado")
    bot.check_specific_product(r"https://pt.aliexpress.com/item/1005005388090518.html", 250)