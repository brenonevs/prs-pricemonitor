import pandas as pd
import threading
import asyncio
import os

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from time import sleep, time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o valor da variável de ambiente "USER_AGENT"
userAgent = os.getenv("USER_AGENT")

# Classe que representa o bot para verificar preços na Amazon
class AmazonPriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop):
        self.url = "https://www.amazon.com.br"
        self.search_query = search_query
        self.priceList = []  # Lista para armazenar os preços encontrados
        self.expected_price = expected_price
        self.pages = pages  # Número de páginas a serem verificadas
        self.user = user  # Objeto para enviar notificações para o usuário
        self.loop = loop

        # Configurações do navegador Chrome
        options = Options()
        user_agent = userAgent
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Suprime logs específicos

        # Configura o serviço do WebDriver com opções de log
        service = Service(ChromeDriverManager().install())
        service.log_path = 'NUL'

        self.driver = webdriver.Chrome(service=service, options=options)

    # Método assíncrono para notificar o usuário no Discord
    async def notify_discord(self, title, price, url):
        message = "-" * 70 + f"\n\n**Produto:** {title}\n**Preço Abaixo do Esperado:** ${price}\n**Link:** {url}\n\n" + "-" * 70
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
                print(f"Ocorreu um erro ao tentar realizar a busca por {self.search_query}: {e}")
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

                    if price <= self.expected_price:
                        # Agenda a execução da coroutine notify_discord
                        asyncio.run_coroutine_threadsafe(self.notify_discord(title, price, product["url"]), self.loop)

                        print(f"Preço encontrado para '{title}': ${price}")

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
                        if price <= self.expected_price:
                            asyncio.run_coroutine_threadsafe(self.notify_discord(title, price, product["url"]), self.loop)
                    except NoSuchElementException:
                        print(f"Não foi possível encontrar o preço para {title}")
                        continue

                except Exception as e:
                    print(f"Erro ao processar o preço para {title}: {e}")
                    continue

                finally:
                    self.priceList.append({"titulo": title, "preço": price})

        except Exception as e:
            print(f"Ocorreu um erro geral ao tentar buscar os produtos e preços: {e}")

        print(self.priceList)
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

    # Método para perguntar ao usuário quantas páginas ele deseja verificar
    def ask_pages(self):
        try:
            pages = int(input("Digite a quantidade de páginas que você quer verificar: "))
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ler o número de páginas: {e}")
            pages = 1

        return pages

    # Método para perguntar ao usuário quantas vezes ele deseja verificar os preços
    def ask_times(self):
        try:
            times = int(input("Digite quantas vezes você deseja verificar os preços: "))
        except Exception as e:
            print(f"Ocorreu um erro ao tentar ler a informação da quantidade de vezes: {e}")
            times = 1  

        return times

    # Método para realizar a busca de preços de forma síncrona
    def search_prices_sync(self):
        self.driver.get(self.url)
        sleep(0.7)
        self.search_product()
        sleep(1)
        search_url = self.driver.current_url

        for _ in range(self.pages):
            self.check_prices()
            sleep(1)
            self.driver.get(search_url)
            self.next_page()
            search_url = self.driver.current_url
            sleep(1) 
        
        self.driver.quit()

    # Método assíncrono para realizar a busca de preços
    async def search_prices(self):
        await asyncio.get_event_loop().run_in_executor(None, self.search_prices_sync)

    # Método para salvar os dados em um arquivo CSV
    def data_to_csv(self):
        df = pd.DataFrame(self.priceList)
        df = df.dropna(how='all')
        df.to_csv(f"{self.search_query}.csv", index=False)
