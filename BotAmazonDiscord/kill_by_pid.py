import os
import signal

def kill_process(pid):
    try:
        os.kill(pid, signal.SIGTERM)  # Envia o sinal SIGTERM
        print(f"Processo {pid} terminado com sucesso.")
    except PermissionError:
        print(f"Permissão negada para terminar o processo {pid}. Você pode precisar de privilégios de administrador.")
    except ProcessLookupError:
        print(f"Nenhum processo encontrado com PID {pid}.")
    except Exception as e:
        print(f"Erro ao tentar terminar o processo {pid}: {e}")

# Exemplo de uso:
# Substitua 1234 pelo PID do processo que você deseja terminar
kill_process(10536)
