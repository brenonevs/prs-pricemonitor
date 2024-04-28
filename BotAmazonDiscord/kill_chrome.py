import os

def kill_chrome():
    # Executa o comando 'taskkill' para encerrar todos os processos do Chrome
    try:
        os.system("taskkill /F /IM chrome.exe")
        print("\n\nTodos os processos do Chrome foram encerrados com sucesso.\n\n")
    except:
        print("Não foi possível encerrar os processos do Chrome.")

kill_chrome()