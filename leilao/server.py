import socket
import threading
import time
from datetime import datetime
from protocolo import enviar, receber
from banco import buscar_ou_criar, atualizar
from args import obter_args
import signal
import sys

# Memória Compartilhada 
leilao = {
    "item": "Relógio Vintage",
    "lance_atual": 1000.0,
    "lance_lider": None,  # nome do usuário com o maior lance
}
tempo_restante = 60
clientes = {}       # conexões ativas {"joao": conn, "maria": conn} 
usuarios = {}       # dados do usuário (saldo, itens, bloqueado) {"joao": {...}, "maria": {...}} 
lock = threading.Lock() # para sincronizar acesso a clientes, usuarios e leilao
servidor_ativo = threading.Event() # para controlar o estado do servidor (ativo ou encerrado)
servidor_ativo.set()  # começa ativo

# Encerramento seguro com CTRL+C
def encerrar_servidor(sig, frame):
    print("\n\n  Servidor interrompido! Salvando dados...")
    servidor_ativo.clear() # sinaliza para threads que o servidor está encerrado

    with lock:
        # Salva todos os usuários ativos no banco
        for nome, dados in usuarios.items():
            try:
                # Devolve bloqueios pendentes antes de salvar
                dados["saldo"] += dados["bloqueado"]
                dados["bloqueado"] = 0.0
                atualizar(nome, dados)
                print(f" [{nome}] salvo — saldo: R$ {dados['saldo']:.2f}")
            except Exception as e:
                print(f" [{nome}] erro ao salvar: {e}")

        # Avisa todos os clientes conectados
        for nome, conn in clientes.items():
            try:
                enviar(conn, "erro", {"mensagem": "Servidor encerrado pelo administrador."})
                conn.close()
            except:
                pass

    print(" Dados salvos! Encerrando...")
    sys.exit(0)

# Broadcast 
def broadcast(tipo, dados, exceto=None): # envia para todos, exceto o nome em exceto
    with lock:
        for nome, conn in clientes.items():
            if nome != exceto:
                try: 
                    enviar(conn, tipo, dados)
                except:
                    pass  # cliente desconectado

# Identificação
def identificar_cliente(conn):
    enviar(conn, "identificacao", {"mensagem": "Digite seu nome de usuário:"})
    msg = receber(conn) # ex: {"tipo": "identificacao", "dados": {"nome": "joao"}}
    nome = msg["dados"]["nome"].strip()
    usuario, novo = buscar_ou_criar(nome) # ex: {"saldo": 5000.0, "itens": [], "bloqueado": 0.0}, True/False
    enviar(conn, "identificacao", {
        "novo": novo,
        "saldo": usuario["saldo"],
        "itens": usuario["itens"]
    })
    return nome, usuario

# Thread 1 — Lances e comandos
def thread_lances(conn, nome):
    global tempo_restante

    try:
        while True:
            try:
                mensagem = receber(conn)

                if not mensagem:
                    raise ConnectionError("Cliente desconectou sem :quit")

                tipo  = mensagem["tipo"]
                dados = mensagem["dados"]

                if tipo == "lance":
                    processar_lance(conn, nome, dados)
                elif tipo == "comando":
                    resultado = processar_comando(conn, nome, dados)
                    if resultado == "quit": 
                        print(f"[{nome}] Saiu com :quit")
                        break  # sai do while limpo, sem exception

            except ConnectionError as e:
                print(f"[{nome}] Desconexão: {e}")
                break
            except OSError:
                print(f"[{nome}] Conexão perdida abruptamente")
                break

    finally: # SEMPRE executa — com erro ou sem erro
        with lock:
            try:
                # Devolve bloqueio se era o líder
                if leilao["lance_lider"] == nome:
                    leilao["lance_lider"] = None
                    leilao["lance_atual"] = 1000.0

                # Salva no banco
                if nome in usuarios:
                    atualizar(nome, usuarios[nome])
                    print(f"[{nome}] Dados salvos")

                # Remove da memória
                clientes.pop(nome, None)
                usuarios.pop(nome, None)

            except Exception as e:
                print(f"[{nome}] Erro ao limpar conexão: {e}")

        # Fecha a conexão
        try:
            conn.close()
        except:
            pass

        print(f"[{nome}] Desconectado — clientes ativos: {len(clientes)}")


def processar_lance(conn, nome, dados):
    global tempo_restante

    item  = dados.get("item")
    valor = float(dados.get("valor", 0))

    with lock:
        usuario = usuarios[nome]

        # Validações
        if item != leilao["item"]:
            enviar(conn, "erro", {"mensagem": f"Item '{item}' não está em leilão!"})
            return

        if valor <= leilao["lance_atual"]:
            enviar(conn, "erro", {"mensagem": f"Lance inválido! O atual é R$ {leilao['lance_atual']:.2f}"})
            return

        saldo_disponivel = usuario["saldo"] - usuario["bloqueado"]
        if valor > saldo_disponivel:
            enviar(conn, "erro", {"mensagem": f"Saldo insuficiente! Disponível: R$ {saldo_disponivel:.2f}"})
            return

        # Devolve o bloqueio do líder anterior
        lider_anterior = leilao["lance_lider"]
        if lider_anterior and lider_anterior in usuarios:
            usuarios[lider_anterior]["bloqueado"] -= leilao["lance_atual"]

        # Bloqueia o valor do novo lance
        usuario["bloqueado"] += valor
        leilao["lance_atual"] = valor
        leilao["lance_lider"] = nome
        tempo_restante = tempo_inicial  # reseta o cronômetro

    # Eco para quem deu o lance
    enviar(conn, "eco", {"acao": f":lance {item} R$ {valor:.2f}"})

    # Broadcast para todos
    for n, c in clientes.items():
        try:
            enviar(c, "lance", {
                "item": leilao["item"],
                "valor": leilao["lance_atual"],
                "lider": leilao["lance_lider"]
            })
        except:
            pass


def processar_comando(conn, nome, dados):
    cmd = dados["comando"]

    if cmd == ":item":
        with lock:
            enviar(conn, "info", {
                "item": leilao["item"],
                "lance_atual": leilao["lance_atual"],
                "lider": leilao["lance_lider"]
            })

    elif cmd == ":tempo":
        with lock:
            enviar(conn, "info", {"tempo_restante": tempo_restante})

    elif cmd.startswith(":vender"):
        processar_venda(conn, nome, cmd)

    elif cmd == ":quit":
        enviar(conn, "info", {"mensagem": "Até logo!"})
        return "quit"

    else:
        enviar(conn, "erro", {"mensagem": f"Comando desconhecido: {cmd}"})


def processar_venda(conn, nome, cmd):
    partes = cmd.split()
    if len(partes) < 2:
        enviar(conn, "erro", {"mensagem": "Uso: :vender <item>"})
        return

    nome_item = " ".join(partes[1:])

    with lock:
        usuario = usuarios[nome]
        item_encontrado = None  # começa como None

        for i in usuario["itens"]:
            if i["nome"].lower() == nome_item.lower():
                item_encontrado = i
                break  # para ao encontrar

        if not item_encontrado:
            enviar(conn, "erro", {"mensagem": f"Você não possui o item '{nome_item}'"})
            return

        valor_venda = item_encontrado["valor_compra"] * 0.9
        usuario["saldo"] += valor_venda
        usuario["itens"].remove(item_encontrado)
        atualizar(nome, usuario)

    enviar(conn, "eco",  {"acao": f":vender {nome_item} por R$ {valor_venda:.2f}"})
    enviar(conn, "info", {"mensagem": f"Item vendido! R$ {valor_venda:.2f} creditados."})


# Thread 2 — Cronômetro
def thread_cronometro():
    global tempo_restante

    while servidor_ativo.is_set():
        time.sleep(1)
        with lock:
            tempo_restante -= 1

            if tempo_restante % 10 == 0 and tempo_restante > 0:
                for conn in clientes.values():
                    try:
                        enviar(conn, "tempo", {"mensagem": f"Tempo restante: {tempo_restante}s"})
                    except:
                        pass

            if tempo_restante <= 5 and tempo_restante > 0:
                for conn in clientes.values():
                    try:
                        enviar(conn, "alerta", {"mensagem": f"Encerrando em {tempo_restante}s!"})
                    except:
                        pass

            if tempo_restante <= 0:
                encerrar_leilao()
                break


def encerrar_leilao():
    """Finaliza o leilão, debita o vencedor e salva no banco"""
    lider = leilao["lance_lider"]

    if lider and lider in usuarios:
        vencedor = usuarios[lider]
        vencedor["bloqueado"] -= leilao["lance_atual"]
        vencedor["itens"].append({
            "nome": leilao["item"],
            "valor_compra": leilao["lance_atual"]
        })
        atualizar(lider, vencedor)

    # Avisa todos
    for conn in clientes.values():
        try:
            enviar(conn, "fim", {
                "mensagem": "Item Vendido!",
                "item": leilao["item"],
                "valor_final": leilao["lance_atual"],
                "vencedor": lider or "nenhum"
            })
        except:
            pass


# Main
def main():
    global tempo_restante, tempo_inicial
    args = obter_args()
    tempo_restante = args.tempo
    tempo_inicial  = args.tempo

    signal.signal(signal.SIGINT, encerrar_servidor)

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('localhost', args.porta))
    servidor.listen(args.max)
    print(f"Servidor rodando | porta: {args.porta} | max clientes: {args.max} | tempo: {args.tempo}s")

    # Cronômetro global
    tc = threading.Thread(target=thread_cronometro)
    tc.daemon = True
    tc.start()

    while True:
        try:
            conn, endereco = servidor.accept()
            print(f"Nova conexão: {endereco}")

        except OSError:
            # Servidor foi fechado pelo CTRL+C
            print("Servidor encerrado.")
            break

        # Verifica limite de conexões
        with lock:
            total_ativos = len(clientes)

        if total_ativos >= args.max:
            try:
                enviar(conn, "erro", {"mensagem": f"Servidor lotado! Limite de {args.max} conexões atingido."})
                conn.close()
            except:
                pass
            print(f"Conexão recusada — servidor lotado ({total_ativos}/{args.max})")
            continue  # volta ao accept() sem encerrar o servidor

        # Identificação em try/except — cliente pode cair durante o processo
        try:
            nome, usuario = identificar_cliente(conn)
            print(f"[{nome}] Identificado ({total_ativos + 1}/{args.max})")
        except Exception as e:
            print(f"Erro na identificação: {e}")
            try:
                conn.close()
            except:
                pass
            continue  # volta ao accept()

        # Registra o cliente na memória
        with lock:
            clientes[nome] = conn
            usuarios[nome] = usuario

        # Envia boas vindas
        try:
            horario = datetime.now().strftime("%H:%M:%S")
            enviar(conn, "conexao", {
                "mensagem": "CONECTADO!!",
                "horario": horario,
                "item": leilao["item"],
                "lance_atual": leilao["lance_atual"],
                "tempo_restante": tempo_restante
            })
        except Exception as e:
            print(f"[{nome}] Erro ao enviar boas vindas: {e}")
            with lock:
                clientes.pop(nome, None)
                usuarios.pop(nome, None)
            continue

        # Dispara thread dedicada para este cliente
        t1 = threading.Thread(target=thread_lances, args=(conn, nome))
        t1.daemon = True
        t1.start()

    servidor.close()

if __name__ == "__main__":
    main()