import socket
import threading
import sys
from protocolo import enviar, receber

leilao_atual = "?"

# Identificação
def identificar(sock):
    msg = receber(sock)
    if not msg:
        raise ConnectionError("Servidor encerrou a conexão durante identificação")

    print(f"\n{msg['dados']['mensagem']}")

    nome = input(">> ").strip()
    while not nome:
        print("Nome não pode ser vazio!")
        nome = input(">> ").strip()

    enviar(sock, "identificacao", {"nome": nome})

    resposta = receber(sock)
    if not resposta:
        raise ConnectionError("Servidor encerrou a conexão durante identificação")

    dados = resposta["dados"]
    if dados.get("novo"):
        print(f"\n Bem vindo, {nome}! Você recebeu R$ 5000.00 de crédito.")
    else:
        print(f"\n Bem vindo de volta, {nome}!")
        print(f" Saldo: R$ {dados['saldo']:.2f}")
        print(f" Itens: {[i['nome'] for i in dados['itens']] or 'nenhum'}")

    return nome

# Thread 1 — Input do usuário
def thread_input(sock, nome, encerrado):
    while not encerrado.is_set():
        try:
            entrada = input(">> ").strip()

            if not entrada:
                continue

            if entrada.startswith(":"):
                if entrada == ":quit":
                    enviar(sock, "comando", {"comando": ":quit"})
                    encerrado.set()
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
                    partes = entrada.split()
                    if len(partes) < 3:
                        print(" Uso correto: :lance <item> <valor>")
                    else:
                        try:
                            item  = " ".join(partes[1:-1])
                            valor = float(partes[-1])
                            enviar(sock, "lance", {"item": item, "valor": valor})
                        except ValueError:
                            print(" Valor inválido! O valor deve ser um número.")

                else:
                    print(f" Comando desconhecido: {entrada}")

            else:
                try:
                    float(entrada)
                    print(f"Use o comando correto: :lance {leilao_atual} {entrada}")
                except ValueError:
                    print(" Entrada inválida! Use um comando com ':' ou ':lance <item> <valor>'")

        except EOFError:
            encerrado.set()
            break
        except OSError:
            # Socket fechado enquanto aguardava input
            encerrado.set()
            break
        except Exception as e:
            print(f"\n Erro no input: {e}")
            encerrado.set()
            break

# Thread 2 — Recepção de mensagens
def thread_recepcao(sock, encerrado):
    global leilao_atual

    while not encerrado.is_set():
        try:
            mensagem = receber(sock)

            if not mensagem:
                if not encerrado.is_set():
                    print("\n Conexão encerrada pelo servidor.")
                encerrado.set()
                break

            tipo  = mensagem["tipo"]
            dados = mensagem["dados"]

            if tipo == "conexao":
                leilao_atual = dados["item"]

            print(f"\r{formatar(mensagem)}")
            print(">> ", end="", flush=True)

            if tipo == "fim":
                encerrado.set()
                break

            if tipo == "erro" and dados.get("mensagem") == "Servidor encerrado pelo administrador.":
                print("\n Servidor encerrado. Encerrando cliente...")
                encerrado.set()
                break

        except OSError:
            if not encerrado.is_set():
                print("\n Conexão perdida com o servidor.")
            encerrado.set()
            break
        except Exception as e:
            if not encerrado.is_set():
                print(f"\n Erro na recepção: {e}")
            encerrado.set()
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
            return f" Tempo restante: {dados['tempo_restante']}s"
        else:
            return f" {dados.get('mensagem', dados)}"
    elif tipo == "fim":
        return (
            f"\n {dados['mensagem']}"
            f"\n Item: {dados['item']}"
            f"\n Valor final: R$ {dados['valor_final']:.2f}"
            f"\n Vencedor: {dados['vencedor']}\n"
        )
    elif tipo == "identificacao":
        return f" {dados.get('mensagem', '')}"
    else:
        return f"[{tipo}] {dados}"

# Main 
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)  # timeout de 10 segundos para conectar

    try:
        sock.connect(('localhost', 9999))
        sock.settimeout(None)  # remove timeout após conectar
    except ConnectionRefusedError:
        print(" Servidor não encontrado. Verifique se ele está rodando.")
        return
    except socket.timeout:
        print(" Timeout ao conectar. Servidor demorou para responder.")
        return
    except OSError as e:
        print(f" Erro ao conectar: {e}")
        return

    # Identificação
    try:
        nome = identificar(sock)
    except ConnectionError as e:
        print(f" Erro na identificação: {e}")
        sock.close()
        return
    except KeyboardInterrupt:
        print("\n Saindo...")
        sock.close()
        return

    # Boas vindas
    try:
        boas_vindas = receber(sock)
        if not boas_vindas:
            print(" Servidor encerrou a conexão.")
            sock.close()
            return
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
    except Exception as e:
        print(f" Erro ao receber boas vindas: {e}")
        sock.close()
        return

    # Event para sinalizar encerramento entre as threads
    encerrado = threading.Event()

    # Threads
    t1 = threading.Thread(target=thread_input, args=(sock, nome, encerrado))
    t2 = threading.Thread(target=thread_recepcao, args=(sock, encerrado))
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()

    try:
        # Aguarda qualquer uma das threads sinalizar encerramento
        encerrado.wait()
    except KeyboardInterrupt:
        print("\n Saindo...")
        encerrado.set()

    finally:
        try:
            sock.close()
        except:
            pass
        print(" Até logo!")
        sys.exit(0)

if __name__ == "__main__":
    main()