import socket
import threading
from protocolo import enviar, receber

# Thread 1 — Lê input do usuário e envia para o servidor 
def thread_input(sock):
    while True:
        try:
            entrada = input(">> ").strip()

            # Ignora entrada vazia
            if not entrada:
                continue

            # É um comando 
            if entrada.startswith(":"):
                if entrada == ":quit":
                    enviar(sock, "comando", {"comando": ":quit"})
                    break
                elif entrada in [":item", ":tempo"]:
                    enviar(sock, "comando", {"comando": entrada})
                else:
                    print(f" Comando desconhecido: {entrada}")

            # É um lance
            else:
                try:
                    valor = float(entrada)
                    enviar(sock, "lance", {"valor": valor})
                except ValueError:
                    print(" Valor inválido! Digite um número ou um comando com ':'")

        except EOFError:
            # Terminal fechado abruptamente
            break
        except Exception as e:
            print(f"\nErro no input: {e}")
            break

# Thread 2 — Recebe e imprime mensagens do servidor 
def thread_recepcao(sock):
    while True:
        try:
            mensagem = receber(sock)

            if not mensagem:
                print("Conexão encerrada pelo servidor.")
                break

            print(f"\n{formatar(mensagem)}")
            print(">> ", end="", flush=True)  # Reimprime o prompt após a mensagem

            # Se o leilão encerrou, encerra a thread
            if mensagem["tipo"] == "fim":
                break

        except Exception as e:
            print(f"\nErro na recepção: {e}")
            break


#  Formatação das mensagens recebidas 
def formatar(mensagem):
    tipo  = mensagem["tipo"]
    dados = mensagem["dados"]

    if tipo == "conexao":
        return f" {dados['horario']}: {dados['mensagem']}"
    elif tipo == "lance":
        return f" Novo lance: R$ {dados['valor']:.2f}"
    elif tipo == "tempo":
        return f" {dados['mensagem']}"
    elif tipo == "alerta":
        return f" {dados['mensagem']}"
    elif tipo == "eco":
        return f" Você executou: {dados['acao']}"
    elif tipo == "erro":
        return f" Erro: {dados['mensagem']}"
    elif tipo == "info":
        # :item
        if "item" in dados:
            return f" Item: {dados['item']} | Lance atual: R$ {dados['lance_atual']:.2f}"
        # :tempo
        elif "tempo_restante" in dados:
            return f" Tempo restante: {dados['tempo_restante']}s"
        else:
            return f"ℹ {dados.get('mensagem', dados)}"
    elif tipo == "fim":
        return f"\n {dados['mensagem']} | Item: {dados['item']} | Valor final: R$ {dados['valor_final']:.2f}\n"
    else:
        return f"[{tipo}] {dados}"

# Main — Conecta ao servidor e dispara as threads 
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sock.connect(('localhost', 9999))
    except ConnectionRefusedError:
        print("Servidor não encontrado. Verifique se ele está rodando.")
        return

    # Recebe e imprime a mensagem de boas vindas
    boas_vindas = receber(sock)
    dados = boas_vindas["dados"]
    print(f"\n{dados['horario']}: {dados['mensagem']}")
    print(f"Item em leilão: {dados['item']}")
    print(f"Lance inicial:  R$ {dados['lance_inicial']:.2f}")
    print(f"\nComandos: :item | :tempo | :quit | ou digite um valor para dar um lance\n")

    # Dispara as duas threads
    t1 = threading.Thread(target=thread_input, args=(sock,))
    t2 = threading.Thread(target=thread_recepcao, args=(sock,))
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()

    t1.join()
    t2.join()

    sock.close()

if __name__ == "__main__":
    main()