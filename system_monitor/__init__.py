import psutil

def run():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    print(f"CPU-Auslastung: {cpu}% | RAM-Auslastung: {ram}%") 