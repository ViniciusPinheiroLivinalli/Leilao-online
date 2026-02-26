# Variáveis globais (memória compartilhada)
import threading


lance_atual = 0.0
nome_item = ""
tempo_restante = 60
lock = threading.Lock()  # Protege acesso simultâneo

def thread_lances(conn):
    # Thread 1 — recebe e valida lances e comandos do cliente
    pass

def thread_cronometro(conn):
    # Thread 2 — contagem regressiva, envia atualizações e "Item Vendido"
    pass

def main():
    # Cria socket, aceita conexão, dispara as duas threads
    pass