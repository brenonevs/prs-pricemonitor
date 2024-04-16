import subprocess
import os

# Lista com os nomes das pastas onde cada main.py está localizado
nomes_das_pastas = [
    "Amazon Buscas Bot",
    "Amazon Listagens Bot",
    "Amazon Produtos Bot",
    "Americanas Buscas Bot",
    "Americanas Listagens Bot",
    "Americanas Produtos Bot",
    "Dafiti Buscas Bot",
    "Dafiti Listagens Bot",
    "Dafiti Produtos Bot",
    "Carrefour Buscas Bot",
    "Carrefour Listagens Bot",
    "Carrefour Produtos Bot",
    "Kabum Buscas Bot",
    "Kabum Listagens Bot",
    "Kabum Produtos Bot",
    "Fast Buscas Bot",
    "Fast Listagens Bot",
    "Fast Produtos Bot",
    "Magazine Buscas Bot",
    "Magazine Listagens Bot",
    "Magazine Produtos Bot",
    "Casas B Buscas Bot",
    "Casas B Listagens Bot",
    "Casas B Produtos Bot",
    "Mercado L Buscas Bot",
    # Adicione o restante dos nomes das pastas aqui
]

# O diretório base onde as pastas estão localizadas
# Isso deve ser o caminho para o diretório "BOTS MONITORA PREÇO" no seu sistema
diretorio_base = r"C:\Users\breno\OneDrive\Área de Trabalho\Price Bots"

# Iniciando todos os scripts main.py simultaneamente, cada um em uma nova janela de CMD
for nome_da_pasta in nomes_das_pastas:
    # Construir o caminho completo para o arquivo main.py
    caminho_script = os.path.join(diretorio_base, nome_da_pasta, "main.py")
    
    # Iniciar o script main.py em uma nova janela de CMD
    subprocess.Popen(["cmd", "/k", "python", caminho_script])

# Neste ponto, as novas janelas de CMD foram abertas e os scripts estão rodando nelas.
# Este script principal pode ser encerrado, ou você pode adicionar código para manter o controle dos processos, se necessário.
