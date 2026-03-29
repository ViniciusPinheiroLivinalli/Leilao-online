import json
import struct

def enviar(sock, tipo, dados):
    try:
        mensagem = {"tipo": tipo, "dados": dados}
        payload  = json.dumps(mensagem).encode('utf-8')
        cabecalho = struct.pack('!I', len(payload))
        sock.sendall(cabecalho + payload)
    except OSError:
        pass  # socket já foi fechado

def receber(sock):
    try:
        cabecalho = _ler_exato(sock, 4)
        if not cabecalho:
            return None
        tamanho = struct.unpack('!I', cabecalho)[0]
        payload = _ler_exato(sock, tamanho)
        if not payload:
            return None
        return json.loads(payload.decode('utf-8'))
    except OSError: # Socket fechado ou erro de rede
        return None
    except json.JSONDecodeError:
        return None

def _ler_exato(sock, tamanho):
    dados = b""
    try:
        while len(dados) < tamanho:
            parte = sock.recv(tamanho - len(dados))
            if not parte:
                return None
            dados += parte
        return dados
    except OSError: # Socket fechado ou erro de rede
        return None