import argparse

def obter_args():
    parser = argparse.ArgumentParser(description="Servidor de Leilão Online")

    parser.add_argument(
        "--max",
        type=int,
        default=3,
        help="Número máximo de conexões simultâneas (padrão: 3)"
    )

    parser.add_argument(
        "--porta",
        type=int,
        default=9999,
        help="Porta do servidor (padrão: 9999)"
    )

    parser.add_argument(
        "--tempo",
        type=int,
        default=60,
        help="Tempo inicial do leilão em segundos (padrão: 60)"
    )

    return parser.parse_args()