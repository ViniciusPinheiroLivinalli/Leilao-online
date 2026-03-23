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

# Carrega o banco do disco 
def carregar():
    if not os.path.exists(ARQUIVO):
        return {}  # banco vazio se arquivo não existe ainda
    with open(ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)

# Salva o banco no disco
def salvar(banco):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(banco, f, indent=4, ensure_ascii=False)

# Busca ou cria um usuário
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