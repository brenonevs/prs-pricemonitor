import pandas as pd
import threading
import asyncio
import os

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from time import sleep, time

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o valor da variável de ambiente "USER_AGENT"
userAgent = os.getenv("USER_AGENT")

# Classe que representa o bot para verificar preços na Terabyte
class TerabytePriceBot():
    def __init__(self, search_query, expected_price, pages, user, loop, times):
        self.url = "https://www.terabyteshop.com.br"    
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

    # Método para realizar a pesquisa do produto na Terabyte        
    def search_product(self):
        sleep(0.5)
        search_input = self.driver.find_element(By.ID, 'isearch')
        search_input.send_keys(self.search_query)
        search_input.submit()

    def close_popup(self, x, y):
        try:
            action = ActionChains(self.driver)
            action.move_by_offset(x, y).click().perform()
        except Exception as e:  
            print(f"\nBotão de fechar popup não encontrado\n")
        

    def click_continue_button(self):
        try:
            # Encontrar o botão pelo ID
            continue_button = self.driver.find_element(By.ID, "submitFormContinuar")
            
            # Clicar no botão
            continue_button.click()
        except NoSuchElementException:
            print("\nBotão de continuar não encontrado.\n")

    # Método para verificar os preços dos produtos nas páginas
    def check_prices(self, x, y):

        sleep(3)

        self.close_popup(x, y)

        sleep(3)

        try:

            scroll_increment = 500
            scrolls = 1

            for _ in range(scrolls):
                self.driver.execute_script(f"window.scrollBy(0, {scroll_increment});")

                sleep(1)  # Aguarda o carregamento da página após o scroll.

                try:   
                    product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.pbox")

                except NoSuchElementException:
                    print("Erro: Não foi possível encontrar os cartões de produto na página.")
                    break
                except WebDriverException as e:
                    print(f"Erro do WebDriver")
                    break
                
                except Exception as e:
                    print(f"Erro geral ao tentar encontrar os cartões de produto")
                    break


                for card in product_cards:
                    if self.stop_search:
                        break

                    try:
                        product_link_element = card.find_element(By.CSS_SELECTOR, "a.commerce_columns_item_image").get_attribute("href")
                    
                    except Exception as e:
                        print(f"Erro ao tentar encontrar o link do produto")
                        
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, "h2").text

                    except Exception as e:
                        print(f"Erro ao tentar encontrar o título do produto")
                    
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, "div.prod-new-price span").text.replace('R$', '').replace('.', '').replace(',', '.').strip()

                    except Exception as e:
                        try:
                            price_element = card.find_element(By.CLASS_NAME, "tbt_esgotado").text
                        except Exception as e:
                            print(f"Erro ao tentar encontrar o preço do produto '{title_element}'")
                            continue


                    product_info = {
                        'link': product_link_element,
                        'title': title_element,
                        'price': price_element
                    }
                    
                    if product_info['title'] not in self.products_names:
                        self.products_names.append(product_info['title'])
                        self.products_info.append(product_info)

                        try:
                            price = float(price_element)
                        except ValueError:
                            if price_element == "Todos vendidos":
                                print(f"Produto '{title_element}' está esgotado.")
                            continue

                        if self.expected_price is None:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(product_info['title'], price, product_info["link"]), self.loop)

                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

                        elif price <= self.expected_price:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(product_info['title'], price, product_info["link"]), self.loop)

                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

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
                                        
                                        asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(product_info['title'], price, product_info["link"]), self.loop)
    
                                        print(f"Novo Preço!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")
                                
                                elif price <= self.expected_price:
                                        
                                        asyncio.run_coroutine_threadsafe(self.notify_discord_about_change_in_price(product_info['title'], price, product_info["link"]), self.loop)
    
                                        print(f"Novo Preço!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

        except Exception as e:
            print(f"Erro geral na busca de produtos e preços")

        return self.products_info

    # Método para navegar para a próxima página de resultados
    def next_page(self):
        try:
            # Rola a página até o final
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//*[@id='pdmore']")))

            # Verifica e fecha o alerta de cookies, se estiver presente
            try:
                cookie_alert_close_button = self.driver.find_element(By.XPATH, "//*[@id='submitFormContinuar']//button")
                cookie_alert_close_button.click()
            except NoSuchElementException:
                # Não faz nada se o botão de fechar o alerta de cookies não for encontrado
                pass

            # Tenta clicar no botão de próxima página
            next_page_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//*[@id='pdmore']")))
            next_page_button.click()
            return True
        
        except ElementClickInterceptedException:
            # Se o clique normal falhar, tenta um clique forçado via JavaScript
            self.driver.execute_script("arguments[0].click();", next_page_button)
            return True
        except (NoSuchElementException, TimeoutException) as e:
            print(f"Erro ao tentar encontrar o botão de próxima página ou ao clicar nele.")
            return False
        except Exception as e:
            print(f"Outro erro ocorreu")
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
                sleep(1)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices(1, 1)
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
                    self.check_prices(1, 1)
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
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    sleep(1)
                    self.check_prices(200, 200)
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
                self.driver.fullscreen_window()
                sleep(0.7)
                self.search_product()
                sleep(1)

                for _ in range(self.pages):
                    if self.stop_search:
                        break
                    self.check_prices(200, 200)
                    sleep(1)
                    if not self.next_page():
                        break
                    sleep(1)
        
        self.driver.quit()

    def restart_driver(self):
        self.driver.quit()
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)

    # Função para monitorar um link de um produto específico e se o preço dele mudou   
    def handle_product_out_of_stock(self, link, in_stock):
        print(f"\n\nNão foi possível encontrar o título ou preço para a URL: {link}\nPode ser que o produto esteja sem estoque ou a estrutura do site mudou.\n\n")
        if in_stock:
            asyncio.run_coroutine_threadsafe(self.notify_discord_about_error(), self.loop)
            self.in_stock = False

    def check_specific_product(self, link, expected_price):
        last_price = None  # Variável para armazenar o último preço verificado

        notified_for_price_drop = False 

        expected_price = float(expected_price)

        first_notification = True

        in_stock = True

        while not self.stop_search:
            try:
                self.restart_driver()
                self.driver.get(link)
                self.driver.fullscreen_window()
                sleep(3)
                self.close_popup(1, 1)
            except TimeoutException:
                print(f"Timeout ao carregar {link}, tentando recarregar.")
                try:
                    self.driver.refresh()
                except Exception as e:
                    print(f"Erro ao tentar recarregar a página")
                    continue
                continue

            try:
                title_element = self.driver.find_element(By.CSS_SELECTOR, "h1.tit-prod")
                title = title_element.text

                price_element = self.driver.find_element(By.CSS_SELECTOR, "p.val-prod.valVista")
                price_text = price_element.text.replace('R$', '').replace('.', '').replace(',', '.').strip()

                if not price_text:
                    self.handle_product_out_of_stock(link, in_stock)
                    continue

                try:
                    price = float(price_text)
                except ValueError:
                    price = price_text

                print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")

                if last_price is None:
                    last_price = price

                if first_notification:
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(title, price, link), self.loop)
                    first_notification = False

                if price < last_price or (price < expected_price and not notified_for_price_drop):
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(title, price, link), self.loop)
                    print(f"Preço encontrado para '{title}' \nPreço: R${price}\n\n")
                    last_price = price
                    notified_for_price_drop = True
                
                in_stock = True

            except NoSuchElementException:
                self.handle_product_out_of_stock(link, in_stock)
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




