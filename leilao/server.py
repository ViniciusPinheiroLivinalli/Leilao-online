import socket
import threading
import time
from datetime import datetime
from protocolo import enviar, receber

# Variáveis globais (memória compartilhada)
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
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite reutilizar o endereço imediatamente após fechar o servidor
    servidor.bind(('localhost', 9999))
    servidor.listen(1)
    print("Servidor de leilão aguardando conexão...")

    conn, endereco = servidor.accept()
    print(f"Cliente conectado: {endereco}")

    horario = datetime.now().strftime("%H:%M:%S")
    enviar(conn, "conexao", {
        "mensagem": "CONECTADO!!",
        "horario": horario,
        "item": nome_item,
        "lance_inicial": lance_atual
    })

    t1 = threading.Thread(target=thread_lances, args=(conn,))
    t2 = threading.Thread(target=thread_cronometro, args=(conn,))
    t1.daemon = True # Permite que a thread seja finalizada automaticamente quando o programa terminar
    t2.daemon = True  
    t1.start()
    t2.start()  

    t1.join()
    t2.join()

    conn.close()
    servidor.close()

if __name__ == "__main__":
    main()
