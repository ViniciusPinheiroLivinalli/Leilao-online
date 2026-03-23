import socket
import threading
import time
from datetime import datetime
from protocolo import enviar, receber
from banco import buscar_ou_criar, atualizar
from args import obter_args

# Memória Compartilhada 
leilao = {
    "item": "Relógio Vintage",
    "lance_atual": 1000.0,
    "lance_lider": None,  # nome do usuário com o maior lance
}
tempo_restante = 60
clientes = {}       # {"joao": conn, "maria": conn}
usuarios = {}       # {"joao": {...}, "maria": {...}}
lock = threading.Lock()

# Broadcast 
def broadcast(tipo, dados, exceto=None):
    """Envia mensagem para todos os clientes conectados"""
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
    msg = receber(conn) 
    nome = msg["dados"]["nome"].strip()
    usuario, novo = buscar_ou_criar(nome) 
    enviar(conn, "identificacao", {
        "novo": novo,
        "saldo": usuario["saldo"],
        "itens": usuario["itens"]
    })
    return nome, usuario

# Thread 1 — Lances e comandos
def thread_lances(conn, nome):
    global tempo_restante

    while True:
        try:
            mensagem = receber(conn)
            if not mensagem:
                print(f"[{nome}] Desconectado")
                with lock:
                # Devolve o bloqueio se era o líder
                    if leilao["lance_lider"] == nome:
                        leilao["lance_lider"] = None
                        leilao["lance_atual"] = 1000.0  # volta ao inicial
                    atualizar(nome, usuarios[nome])  # salva no banco
                break

            tipo  = mensagem["tipo"]
            dados = mensagem["dados"]

            if tipo == "lance":
                processar_lance(conn, nome, dados)

            elif tipo == "comando":
                processar_comando(conn, nome, dados)

        except Exception as e:
            print(f"Erro na thread de lances [{nome}]: {e}")
            break

    # Remove o cliente ao desconectar
    with lock:
        clientes.pop(nome, None) 
        usuarios.pop(nome, None) 


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
        atualizar(nome, usuarios[nome])
        print(f"[{nome}] Saiu com :quit")
        raise Exception("quit")

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

    while True:
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
    tempo_inicial = args.tempo

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('localhost', args.porta))
    servidor.listen(args.max)
    print(f"Servidor rodando | porta: {args.porta} | max clientes: {args.max} | tempo: {args.tempo}s")

    # Dispara o cronômetro global — uma única thread para todos
    tc = threading.Thread(target=thread_cronometro)
    tc.daemon = True
    tc.start()

    while True:
        conn, endereco = servidor.accept()
        print(f"Nova conexão: {endereco}")

        with lock:
            if len(clientes) >= args.max:
                enviar(conn, "erro", {"mensagem": "Servidor lotado! Tente mais tarde."})
                conn.close()
                continue

        # Identificação
        nome, usuario = identificar_cliente(conn)
        print(f"[{nome}] Identificado")

        with lock:
            clientes[nome] = conn
            usuarios[nome] = usuario

        # Envia boas vindas com dados do leilão
        horario = datetime.now().strftime("%H:%M:%S")
        enviar(conn, "conexao", {
            "mensagem": "CONECTADO!!",
            "horario": horario,
            "item": leilao["item"],
            "lance_atual": leilao["lance_atual"],
            "tempo_restante": tempo_restante
        })

        # Dispara as 2 threads dedicadas para este cliente
        t1 = threading.Thread(target=thread_lances, args=(conn, nome))
        t1.daemon = True
        t1.start()

if __name__ == "__main__":
    main()