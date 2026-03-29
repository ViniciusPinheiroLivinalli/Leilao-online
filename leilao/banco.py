import json
import os

ARQUIVO = "banco.json" # Arquivo onde os dados dos usuários serão armazenados

# Estrutura padrão de um usuário
def novo_usuario():
    return {
        "saldo": 5000.0,
        "bloqueado": 0.0,
        "itens": []  # [{"nome": "Banana", "valor_compra": 1000.0}]
    }

def carregar():
    if not os.path.exists(ARQUIVO):
        return {}  # banco vazio se arquivo não existe ainda
    with open(ARQUIVO, "r", encoding="utf-8") as f: # reading mode, utf-8 encoding
        return json.load(f)

def salvar(banco):
    with open(ARQUIVO, "w", encoding="utf-8") as f: # writing mode, utf-8 encoding
        json.dump(banco, f, indent=4, ensure_ascii=False) # indent=4 para legibilidade, ensure_ascii=False para suportar caracteres acentuados

# Buscar ou criar um usuário
def buscar_ou_criar(nome):
    banco = carregar()
    novo = False

    if nome not in banco:
        banco[nome] = novo_usuario()
        salvar(banco)
        novo = True

    return banco[nome], novo

# Atualiza os dados de um usuário no disco 
def atualizar(nome, dados):
    banco = carregar()
    banco[nome] = dados
    salvar(banco)