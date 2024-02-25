import pandas as pd
import threading
import asyncio
import os
import random
import pyautogui as pg
import pickle

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
        self.coupon_list = {}
        self.cookies_path = 'cookies.pkl'
        self.priceListInformation = []
        self.products_names = []

        # Configurações do navegador Chrome
        self.options = Options() 
        self.user_agent = userAgent
        self.options.add_argument(f'user-agent={self.user_agent}')
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

    async def notify_discord_about_coupon(self, url, coupon):
        message = "-" * 70 + f"\n\nCupom encontrado na loja {url}\n Cupom:{coupon}\n\n" + "-" * 70
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
                
                except Exception as e:
                    print(f"Erro geral ao tentar encontrar os cartões de produto: {e}")
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
                    except Exception as e:
                        print(f"Erro geral ao tentar encontrar os elementos do cartão de produto: {e}")
                        continue

                    product_info = {
                        'link': product_link,
                        'title': product_title,
                        'price': product_price
                    }

                    if product_info['title'] not in self.products_names:
                        self.products_names.append(product_info['title'])
                        self.priceListInformation.append(product_info)

                        try:
                            price = float(product_price.replace('R$', '').replace('.', '').replace(',', '.').strip())
                        except ValueError:
                            print(f"Erro ao converter o preço do produto '{product_title}'. Preço encontrado: '{product_price}'")
                            continue

                        if self.expected_price is None:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(product_info['title'], price, product_info["link"]), self.loop)

                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

                        elif price <= self.expected_price:

                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_new_product(product_info['title'], price, product_info["link"]), self.loop)

                            print(f"Novo Produto!\nPreço encontrado para '{product_info['title']}' \nPreço: R${price}\n\n")

                    else:
                        for product in self.priceListInformation:
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
                self.slide_button(self.driver)
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
                self.slide_button(self.driver)
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
                self.slide_button(self.driver)
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
                self.slide_button(self.driver)
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
                self.slide_button(self.driver)
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
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_product(title, price, link), self.loop)
                    print(f"\n\nProduto: {title}\nPreço: R${price}\nLink: {link}\n\n")
                    first_notification = False

                if price < last_price or (price < expected_price and not notified_for_price_drop):
                    asyncio.run_coroutine_threadsafe(self.notify_discord_about_monitoring_new_price(title, price, link), self.loop)
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

    def save_cookies(self, driver, path):
        if os.path.exists(path):
            os.remove(path)
        with open(path, 'wb') as filehandler:
            pickle.dump(driver.get_cookies(), filehandler)

    def load_cookies(self, driver, path, url):
        driver.get(url)  
        with open(path, 'rb') as cookiesfile:
            cookies = pickle.load(cookiesfile)
            for cookie in cookies:
                if 'expiry' in cookie:
                    del cookie['expiry']
                driver.add_cookie(cookie)

    def check_and_refresh_cookies(self, driver, cookies_path, url):
        if not os.path.exists(cookies_path):
            print("Arquivo de cookies não encontrado. Obtendo novos cookies.")
            driver.get(url)
            sleep(random.uniform(5, 10))  # Intervalo aleatório
            self.slide_button(driver)
            # Aqui o usuário resolve manualmente o captcha, se necessário
            self.save_cookies(driver, cookies_path)
        else:
            print("Arquivo de cookies encontrado. Carregando cookies.")
            self.load_cookies(driver, cookies_path, url)

    def slide_button(self, driver):
        while not self.stop_search: 
            largura_tela, altura_tela = pg.size()
            centro_x = largura_tela / 2
            centro_y = altura_tela / 2
            sleep(2)

            try:
                # Localizar o elemento do botão
                driver.fullscreen_window()
                button = driver.find_element(By.ID, "nc_1_n1z")
                print("Botão encontrado.")

                # Espera após encontrar o botão
                sleep(1)

                # Clicar e segurar o botão
                action = ActionChains(driver)
                pg.moveTo(centro_x, centro_y)
                sleep(1)
                action.click_and_hold(button).perform()
                pg.moveRel(350, 0)

                # Mover o botão em pequenos incrementos
                for _ in range(10):
                    action.move_by_offset(50, 0).perform()
                    sleep(random.uniform(0.01, 0.05))

                # Soltar o botão
                action.release().perform()
                # Espera após a ação
                sleep(1)

                # Pressionar F5 para recarregar a página
                driver.refresh()

                sleep(1.5)

            except Exception as e:
                # Se não encontrar o botão, interrompe o loop
                print(f"Botão não encontrado, saindo do loop.")
                self.save_cookies(driver, self.cookies_path)

                break 

    def configure_options(self, user_agent):
        options = Options()
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-infobars')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-images')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-web-security')
        options.add_argument('--no-zygote')
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        return options

    def find_coupons(self, urls):
        options = self.configure_options(self.user_agent)
        service = Service(ChromeDriverManager().install())

        while not self.stop_search:
            for url in urls:
                # Inicialização do driver e carregamento de cookies
                driver = webdriver.Chrome(options=options, service=service)
                self.check_and_refresh_cookies(driver, self.cookies_path, url)
                sleep(random.uniform(1, 3))  # Intervalo aleatório antes de verificar cupons
                self.check_coupon(driver)
                driver.quit()
                sleep(random.uniform(10, 60))  # Intervalo aleatório entre iterações

    def check_coupon(self, driver):
        sleep(2)
        self.slide_button(driver)
        sleep(2)

        try:
            sleep(5)
            driver.execute_script("window.scrollTo(0, 70)")
            driver.fullscreen_window()
            sleep(2)

            # Obter o link da loja atual
            current_url = driver.current_url

            # Inicializa a lista de cupons para a URL atual, se ela ainda não existir
            if current_url not in self.coupon_list:
                self.coupon_list[current_url] = []

            while True:
                try:
                    elementos = driver.find_elements(By.XPATH, "//div[contains(@style, 'font-size: 12px')][contains(@style, 'color: rgb(25, 25, 25)')][contains(@style, 'text-align: center')]")
                except NoSuchElementException:
                    print("Cupons não encontrados na loja.")
                    continue
                new_coupons_found = False
                for elemento in elementos:
                    if elemento.text:
                        # Verificar e adicionar cupons no dicionário
                        if elemento.text not in self.coupon_list[current_url]:
                            print(f"Novo cupom encontrado na loja {current_url}: {elemento.text}")
                            self.coupon_list[current_url].append(elemento.text)
                            new_coupons_found = True
                            asyncio.run_coroutine_threadsafe(self.notify_discord_about_coupon(current_url, elemento.text), self.loop)

                if not new_coupons_found:
                    print(f"Não foram encontrados novos cupons na loja {current_url}.")
                    break

                try:
                    load_more_button = driver.find_element(By.XPATH, "//img[@src='//ae01.alicdn.com/kf/H1ae6b346a06441d7ac7b26b5702efea9M.png']")
                    driver.execute_script("arguments[0].scrollIntoView();", load_more_button)

                    actions = ActionChains(driver)
                    actions.move_to_element(load_more_button).click().perform()

                    print("Carregando mais cupons...")
                    sleep(2)
                except NoSuchElementException:
                    print("Não há mais botões para carregar cupons.")
                    break
                except ElementClickInterceptedException:
                    print("Botão não clicável no momento, tentando novamente...")
                    sleep(2)

            print(f"Cupons encontrados na loja {current_url}: {self.coupon_list[current_url]}")
            print(f"Foram encontrados {len(self.coupon_list[current_url])} cupons na loja {current_url}.")

        except TimeoutException:
            print("Timeout ao esperar pelos elementos.")
        except NoSuchElementException:
            print("Elementos não encontrados na página.")


    async def search_specific_product(self, link, expected_price):
        await asyncio.get_event_loop().run_in_executor(None, self.check_specific_product, link, expected_price)

    async def search_prices(self):
        await asyncio.get_event_loop().run_in_executor(None, self.search_prices_sync)

    async def search_link_prices(self, link):
        await asyncio.get_event_loop().run_in_executor(None, self.check_link_prices, link)

    async def search_for_coupons(self, urls):
        await asyncio.get_event_loop().run_in_executor(None, self.find_coupons, urls)

    # Método para salvar os dados em um arquivo CSV
    def data_to_csv(self):
        df = pd.DataFrame(self.priceList)
        df = df.dropna(how='all')
        df.to_csv(f"{self.search_query}.csv", index=False)