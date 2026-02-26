import json
import struct

def enviar(sock, tipo, dados):
    mensagem = {
        "tipo": tipo, # ex: "oferta", "leilao", etc.
        "dados": dados
    }

    payload = json.dumps(mensagem).encode('utf-8') # Dicionário → string JSON → bytes

    cabecalho = struct.pack('!I', len(payload)) # Cria um cabeçalho de 4 bytes com o tamanho do payload (formato big-endian)
 
    sock.sendall(cabecalho + payload) # Envia o cabeçalho e payload

def receber(sock):
    cabecalho = _ler_exato(sock, 4)
    if not cabecalho:
        return None

    tamanho = struct.unpack('!I', cabecalho)[0] # Converte os 4 bytes do cabeçalho para um inteiro (tamanho do payload)

    payload = _ler_exato(sock, tamanho)
    if not payload:
        return None

    return json.loads(payload.decode('utf-8')) # Bytes → string JSON → dicionário Python

def _ler_exato(sock, tamanho):
    """Garante que lemos exatamente 'tamanho' bytes do socket"""
    dados = b""
    while len(dados) < tamanho:
        parte = sock.recv(tamanho - len(dados))
        if not parte:
            # Conexão encerrada no meio da leitura
            return None
        dados += parte
    return dados