import psutil

def get_process_info(pid):
    try:
        # Encontrar o processo pelo PID
        process = psutil.Process(pid)
        
        # Obter informações do processo
        process_info = {
            'PID': process.pid,
            'Name': process.name(),
            'Status': process.status(),
            'CPU Percent': process.cpu_percent(interval=1.0),
            'Memory Info': process.memory_info(),
            'Open Files': process.open_files(),
            'Connections': process.connections(),
            'Threads': len(process.threads()),
            'Create Time': psutil.datetime.datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
        }
        return process_info
    except psutil.NoSuchProcess:
        return f"No process found with PID: {pid}"
    except Exception as e:
        return f"Error retrieving process info: {str(e)}"


process_details = get_process_info(24404)
print(process_details)
