import subprocess
from time import sleep

def list_chrome_processes():
    try:
        # Executa o comando 'tasklist' e filtra a saída para linhas contendo 'chrome.exe'
        result = subprocess.run(['tasklist'], capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        chrome_processes = [line for line in lines if 'chromedriver.exe' in line]
        
        pid_list = []
        print(f"Instâncias do Chrome Driver e seus PIDs - Quantidade de instâncias: {len(chrome_processes) if chrome_processes else 0}\n")
        for process in chrome_processes:
            parts = process.split()
            pid = parts[1]  # O PID está em parts[1]
            print(f"Nome: {parts[0]}, PID: {pid}")
            pid_list.append(pid)
        print("\n\n")

        return pid_list
    except subprocess.CalledProcessError:
        print("Não foi possível listar os processos do Chrome.")
        return []

def kill_process_by_pid(pid):
    try:
        subprocess.run(f"taskkill /F /PID {pid}", check=True, shell=True)
        print(f"\n\nProcesso com PID {pid} foi encerrado com sucesso.\n\n")
    except subprocess.CalledProcessError:
        print(f"Não foi possível encerrar o processo com PID {pid}.")

if __name__ == "__main__":
    # Obtem a lista de PIDs dos processos do Chrome
    while True:
        chrome_pids = list_chrome_processes()
        sleep(3)
    
