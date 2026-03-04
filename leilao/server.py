import socket
import threading
import time
from datetime import datetime
from protocolo import enviar, receber

# Variáveis globais (memória compartilhada)
lance_atual = 1000.0
nome_item = "Banana"
tempo_restante = 60
lock = threading.Lock()  # Protege acesso simultâneo

def thread_lances(conn):
    global lance_atual

    while True:
        try:
            mensagem = receber(conn)

            # Se receber None o cliente desconectou
            if not mensagem:
                print("Cliente desconectado")
                break
            tipo  = mensagem["tipo"]
            dados = mensagem["dados"]

            # É um lance 
            if tipo == "lance":
                valor = float(dados["valor"])

                with lock:
                    if valor > lance_atual:
                        lance_atual = valor
                        # tempo_restante = 60  # Reseta o cronômetro para 60 segundos a cada lance válido
                        enviar(conn, "eco", {"acao": f"Lance de R$ {valor:.2f} aceito!"})
                        enviar(conn, "lance", {"valor": lance_atual})
                    else:
                        enviar(conn, "erro", {
                            "mensagem": f"Lance inválido! O atual é R$ {lance_atual:.2f}"
                        })

            # É um comando
            elif tipo == "comando":
                cmd = dados["comando"]

                if cmd == ":item":
                    with lock:
                        enviar(conn, "info", {
                            "item": nome_item,
                            "lance_atual": lance_atual
                        })

                elif cmd == ":tempo":
                    with lock:
                        enviar(conn, "info", {
                            "tempo_restante": tempo_restante
                        })

                elif cmd == ":quit":
                    enviar(conn, "info", {"mensagem": "Até logo!"})
                    print("Cliente saiu com :quit")
                    break

        except Exception as e:
            print(f"Erro na thread de lances: {e}")
            break
    

def thread_cronometro(conn):
    global tempo_restante

    while True:
        time.sleep(1)

        with lock:
            tempo_restante -= 1

            # Avisa o cliente a cada 10 segundos
            if tempo_restante % 10 == 0 and tempo_restante > 0:
                enviar(conn, "tempo", {
                    "mensagem": f"Tempo restante: {tempo_restante}s"
                })

            # Avisa nos últimos 5 segundos
            if tempo_restante <= 5 and tempo_restante > 0:
                enviar(conn, "alerta", {
                    "mensagem": f"Encerrando em {tempo_restante}s!"
                })

            # Tempo esgotado
            if tempo_restante <= 0:
                enviar(conn, "fim", {
                    "mensagem": "Item Vendido!",
                    "item": nome_item,
                    "valor_final": lance_atual
                })
                break
    
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