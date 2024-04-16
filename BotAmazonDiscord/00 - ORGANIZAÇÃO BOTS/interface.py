import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt
import subprocess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Bots de Monitoramento de Preço')
        self.setWindowIcon(QIcon('discord-logo.png'))  # Caminho atualizado para o ícone
        self.setGeometry(300, 300, 400, 500)  # X, Y, largura, altura

        # Configuração do widget central e layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Adicionando um espaçador antes da imagem para centralizar verticalmente
        layout.addStretch(1)

        # Adicionando a imagem principal
        main_logo = QLabel(self)
        main_logo_pixmap = QPixmap('discord-logo.png')
        main_logo.setPixmap(main_logo_pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        main_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(main_logo)

        # Adicionando um espaçador após a imagem para manter o centro vertical
        layout.addStretch(1)

        # Adicionando o botão
        button = QPushButton('Iniciar Bots', self)
        button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                color: white;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A82FB, stop:1 #FC5C7D);
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #FFFFFF;
                font-family: 'Arial Rounded MT Bold', Arial;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FC5C7D, stop:1 #6A82FB);
            }
        """)
        button.clicked.connect(self.run_script)
        layout.addWidget(button)

        # Configurações de estilo da janela
        self.setStyleSheet("background-color: #2c3e50;")

    def run_script(self):
        # Método para executar o script run.py
        try:
            subprocess.run(['python', 'run.py'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Erro ao executar run.py: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
