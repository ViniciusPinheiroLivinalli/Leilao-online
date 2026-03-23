import socket
import threading
from protocolo import enviar, receber

leilao_atual = "?"

# Identificação 
def identificar(sock):
    msg = receber(sock)
    print(f"\n{msg['dados']['mensagem']}")

    nome = input(">> ").strip()
    while not nome:
        print("Nome não pode ser vazio!")
        nome = input(">> ").strip()

    enviar(sock, "identificacao", {"nome": nome})

    resposta = receber(sock)
    dados = resposta["dados"]

    if dados.get("novo"):
        print(f"\n Bem vindo, {nome}! Você recebeu R$ 5000.00 de crédito.")
    else:
        print(f"\n Bem vindo de volta, {nome}!")
        print(f" Saldo: R$ {dados['saldo']:.2f}")
        print(f" Itens: {[i['nome'] for i in dados['itens']] or 'nenhum'}")

    return nome

# Thread 1 — Input do usuário 
def thread_input(sock, nome):
    while True:
        try:
            entrada = input(">> ").strip()

            if not entrada:
                continue

            # É um comando
            if entrada.startswith(":"):

                if entrada == ":quit":
                    enviar(sock, "comando", {"comando": ":quit"})
                    break

                elif entrada in [":item", ":tempo"]:
                    enviar(sock, "comando", {"comando": entrada})

                elif entrada.startswith(":vender"):
                    partes = entrada.split()
                    if len(partes) < 2:
                        print(" Uso correto: :vender <item>")
                    else:
                        enviar(sock, "comando", {"comando": entrada})

                elif entrada.startswith(":lance"):
                    # :lance <item> <valor>
                    partes = entrada.split()
                    if len(partes) < 3:
                        print(" Uso correto: :lance <item> <valor>")
                    else:
                        try:
                            item  = " ".join(partes[1:-1])  # tudo entre :lance e o valor
                            valor = float(partes[-1])        # último elemento é o valor
                            enviar(sock, "lance", {"item": item, "valor": valor})
                        except ValueError:
                            print(" Valor inválido! O valor deve ser um número.")

                else:
                    print(f" Comando desconhecido: {entrada}")

            # É um número solto — sugere o comando correto
            else:
                try:
                    float(entrada)
                    print(f" Use o comando correto: :lance {leilao_atual} {entrada}")
                except ValueError:
                    print(" Entrada inválida! Use um comando com ':' ou ':lance <item> <valor>'")

        except EOFError:
            break
        except Exception as e:
            print(f"\nErro no input: {e}")
            break

# Thread 2 — Recepção de mensagens
def thread_recepcao(sock):
    global leilao_atual  # precisa declarar que é a variável global
    
    while True:
        try:
            mensagem = receber(sock)

            if not mensagem:  # verifica None primeiro
                print("Conexão encerrada pelo servidor.")
                break

            # extrai tipo e dados antes de usar
            tipo  = mensagem["tipo"]
            dados = mensagem["dados"]

            # agora sim pode verificar o tipo
            if tipo == "conexao":
                leilao_atual = dados["item"]

            print(f"\r{formatar(mensagem)}")
            print(">> ", end="", flush=True)

            if tipo == "fim":
                break

        except Exception as e:
            print(f"\nErro na recepção: {e}")
            break

# Formatação
def formatar(mensagem):
    tipo  = mensagem["tipo"]
    dados = mensagem["dados"]

    if tipo == "conexao":
        return f" {dados['horario']}: {dados['mensagem']}"
    elif tipo == "lance":
        return f" [{dados['item']}] Novo lance: R$ {dados['valor']:.2f} — Líder: {dados['lider']}"
    elif tipo == "tempo":
        return f" {dados['mensagem']}"
    elif tipo == "alerta":
        return f" {dados['mensagem']}"
    elif tipo == "eco":
        return f" Você executou: {dados['acao']}"
    elif tipo == "erro":
        return f" Erro: {dados['mensagem']}"
    elif tipo == "info":
        if "item" in dados:
            return f" Item: {dados['item']} | Lance: R$ {dados['lance_atual']:.2f} | Líder: {dados.get('lider') or 'nenhum'}"
        elif "tempo_restante" in dados:
            return f"  Tempo restante: {dados['tempo_restante']}s"
        else:
            return f" {dados.get('mensagem', dados)}"
    elif tipo == "fim":
        return (
            f"\n {dados['mensagem']}"
            f"\n  Item: {dados['item']}"
            f"\n  Valor final: R$ {dados['valor_final']:.2f}"
            f"\n  Vencedor: {dados['vencedor']}\n"
        )
    elif tipo == "identificacao":
        return f" {dados.get('mensagem', '')}"
    else:
        return f"[{tipo}] {dados}"

# Main
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', 9999))
    except ConnectionRefusedError:
        print(" Servidor não encontrado. Verifique se ele está rodando.")
        return

    # Identificação
    nome = identificar(sock)

    # Boas vindas com dados do leilão
    boas_vindas = receber(sock)
    dados = boas_vindas["dados"]
    print(f"\n{dados['horario']}: {dados['mensagem']}")
    print(f" Item em leilão: {dados['item']}")
    print(f" Lance atual:    R$ {dados['lance_atual']:.2f}")
    print(f" Tempo restante: {dados['tempo_restante']}s")
    print(f"\nComandos disponíveis:")
    print(f"  :item                    → info do item")
    print(f"  :tempo                   → tempo restante")
    print(f"  :lance <item> <valor>    → dar um lance")
    print(f"  :vender <item>           → vender um item seu")
    print(f"  :quit                    → sair\n")

    # Threads
    t1 = threading.Thread(target=thread_input, args=(sock, nome))
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