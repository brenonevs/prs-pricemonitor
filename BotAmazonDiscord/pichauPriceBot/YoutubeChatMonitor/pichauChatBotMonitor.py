import pyautogui
import time
import webbrowser
import sys

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon

pyautogui.FAILSAFE = False

class BotPichauApp(QWidget):
    def __init__(self):
        super().__init__()
        self.automator = BrowserAutomator()  # Instância da classe BrowserAutomator
        self.initUI()
        
    def initUI(self):
        self.setWindowIcon(QIcon('pichau.png'))  # Modifique com o caminho correto do seu ícone
        self.setWindowTitle('BOT PICHAU')
        self.setGeometry(100, 100, 400, 600)
        self.setStyleSheet("background-color: #1c1c1c;")
        
        layout = QVBoxLayout()

        self.image_label = QLabel(self)
        pixmap = QPixmap('pichau.jpg')
        self.image_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        title = QLabel('BOT PICHAU')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        instruction = QLabel('DIGITE A URL DO PRODUTO PARA O MACETE DO CARRINHO:')
        instruction.setAlignment(Qt.AlignCenter)
        instruction.setFont(QFont("Verdana", 12))
        instruction.setStyleSheet("color: white;")
        layout.addWidget(instruction)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('URL do produto')
        self.url_input.setFont(QFont("Arial", 12))
        self.url_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #aaa;
                border-radius: 15px;
                padding: 10px;
                margin-bottom: 10px;
                color: white;
                background-color: #333;
            }
        """)
        layout.addWidget(self.url_input)

        self.start_button = QPushButton('INICIAR')
        self.start_button.setFont(QFont("Arial", 12))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #8000ff;
                border-style: none;
                border-radius: 20px;
                padding: 15px;
                color: white;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #6700cc;
            }
        """)
        self.start_button.clicked.connect(self.startAutomation)
        layout.addWidget(self.start_button)
        
        self.setLayout(layout)

    def startAutomation(self):
        self.automator.url = self.url_input.text()
        print("URL submitted:", self.automator.url)
        self.automator.main()

class BrowserAutomator:
    def __init__(self, url=''):
        self.url = url
        self.chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    def open_chrome_and_access_site(self):
        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(self.chrome_path))
        webbrowser.get('chrome').open(self.url)

    def click_image(self, image, attempts=0, interval=0.3, confidence=0.7):
        attempt = 0
        image_name = image.split('/')[-1].split('.')[0]

        while True:
            try:
                location = pyautogui.locateCenterOnScreen(image, confidence=confidence)
                if location is not None:
                    pyautogui.click(location)
                    print(f"Botão {image_name} encontrado e clicado em {location}.")
                    break
                else:
                    print(f"Botão {image_name} não encontrado, tentando novamente...")
                    attempt += 1
                    if 0 < attempts <= attempt:
                        print("Número máximo de tentativas atingido. Desistindo.")
                        break
            except pyautogui.ImageNotFoundException:
                print(f"Botão {image_name} não encontrado, ajuste a confiança ou verifique o caminho da imagem.")
            time.sleep(interval)

    def localize_image(self, image, confidence=0.7):
        location = pyautogui.locateCenterOnScreen(image, confidence=confidence)
        return location

    def add_to_cart(self):
        self.open_chrome_and_access_site()
        self.click_image('images/buy_button.png', confidence=0.7)
        self.click_image('images/finish_order.png', confidence=0.7)
        time.sleep(2) # ajustar para 1
        pyautogui.scroll(-50)
        self.click_image('images/braspress.png', confidence=0.7)
        pyautogui.scroll(-75)
        time.sleep(0.5)
        self.click_image('images/continue_to_payment.png', confidence=0.7)
        self.click_image('images/boleto_payment.png', confidence=0.7)
        pyautogui.hotkey('ctrl', 'shift', 'tab')

    def buy_process(self):
        while True:
            self.click_image('images/buy_button.png', confidence=0.7)
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'tab')
            self.click_image('images/pix_payment.png', confidence=0.7)
            time.sleep(1.3)
            self.click_image('images/continue_to_revision.png', confidence=0.7)
            self.click_image('images/checkbox.png', confidence=0.7)
            time.sleep(0.5)
            self.click_image('images/order.png', confidence=0.7)
            self.click_image('images/order.png', confidence=0.7)
            time.sleep(0.5)
            self.click_image('images/order.png', confidence=0.7)
            time.sleep(3)
            pyautogui.hotkey('ctrl', 'w')
            pyautogui.hotkey('ctrl', 'w')
            self.add_to_cart()

    def main(self):
        self.add_to_cart()
        self.buy_process()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BotPichauApp()
    ex.show()
    sys.exit(app.exec_())