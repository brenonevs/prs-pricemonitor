import pandas as pd
import threading
import asyncio
import os
import pyautogui as pg
import random
import requests
import sys
import undetected_chromedriver as uc 
import pickle

from dotenv import load_dotenv

from bs4 import BeautifulSoup

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains 
from webdriver_manager.opera import OperaDriverManager

from time import sleep, time

load_dotenv()

userAgent = os.getenv("USER_AGENT")

user_agent = userAgent

coupon_list = {}

user_agent = userAgent


service = Service(ChromeDriverManager().install())

def check_coupon(driver):
    sleep(2)
    slide_button(driver)
    sleep(2)

    try:
        sleep(5)
        driver.execute_script("window.scrollTo(0, 70)")
        driver.fullscreen_window()
        sleep(2)

        # Obter o link da loja atual
        current_url = driver.current_url

        # Inicializa a lista de cupons para a URL atual, se ela ainda não existir
        if current_url not in coupon_list:
            coupon_list[current_url] = []

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
                    if elemento.text not in coupon_list[current_url]:
                        print(f"Novo cupom encontrado na loja {current_url}: {elemento.text}")
                        coupon_list[current_url].append(elemento.text)
                        new_coupons_found = True

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

        print(f"Cupons encontrados na loja {current_url}: {coupon_list[current_url]}")
        print(f"Foram encontrados {len(coupon_list[current_url])} cupons na loja {current_url}.")

    except TimeoutException:
        print("Timeout ao esperar pelos elementos.")
    except NoSuchElementException:
        print("Elementos não encontrados na página.")

def slide_button(driver):
    while True: 

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
            save_cookies(driver, cookies_path)

            break


# Configuração das Opções do Navegador para as duas instâncias
def configure_options(user_agent):
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

options = configure_options(user_agent)

service = Service(ChromeDriverManager().install())

# Funções para o Gerenciamento de Cookies
def save_cookies(driver, path):
    if os.path.exists(path):
        os.remove(path)
    with open(path, 'wb') as filehandler:
        pickle.dump(driver.get_cookies(), filehandler)

def load_cookies(driver, path, url):
    driver.get(url)  
    with open(path, 'rb') as cookiesfile:
        cookies = pickle.load(cookiesfile)
        for cookie in cookies:
            if 'expiry' in cookie:
                del cookie['expiry']
            driver.add_cookie(cookie)

# Verificação de Cookies e Captcha
def check_and_refresh_cookies(driver, cookies_path, url):
    if not os.path.exists(cookies_path):
        print("Arquivo de cookies não encontrado. Obtendo novos cookies.")
        driver.get(url)
        sleep(random.uniform(5, 10))  # Intervalo aleatório
        slide_button(driver)
        # Aqui o usuário resolve manualmente o captcha, se necessário
        save_cookies(driver, cookies_path)
    else:
        print("Arquivo de cookies encontrado. Carregando cookies.")
        load_cookies(driver, cookies_path, url)

# Funções existentes (check_coupon e slide_button) permanecem as mesmas

# Arquivo de cookies e URL
cookies_path = 'cookies.pkl'

urls = ["https://pt.aliexpress.com/store/912322050", "https://pt.aliexpress.com/store/5046245", "https://pt.aliexpress.com/store/912487797", 
        "https://pt.aliexpress.com/store/1102128119", "https://pt.aliexpress.com/store/1102566304"]

while True:
    for url in urls:
        url = url
        # Inicialização do driver e carregamento de cookies
        driver = webdriver.Chrome(options=options, service=service)
        check_and_refresh_cookies(driver, cookies_path, url)
        sleep(random.uniform(1, 3))  # Intervalo aleatório antes de verificar cupons
        check_coupon(driver)
        driver.quit()
        sleep(random.uniform(10, 60))  # Intervalo aleatório entre iterações