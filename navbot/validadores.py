from typing import Tuple


def validar_dados_missao(
    titulo: str,
    origem: str,
    destino: str,
    prioridade_str: str,
    carga_str: str,
) -> Tuple[bool, str, int, float]:
    if len(titulo.strip()) < 3:
        return False, "A descrição da missão deve ter pelo menos 3 caracteres.", 1, 0.0

    if origem == destino:
        return False, "O cômodo de destino deve ser diferente do cômodo de origem.", 1, 0.0

    try:
        prioridade = int(prioridade_str.strip())
    except ValueError:
        return False, "Erro de validação: a prioridade (1 a 5) deve ser um número inteiro.", 1, 0.0

    if prioridade < 1 or prioridade > 5:
        return False, "A prioridade deve estar entre 1 (Baixa) e 5 (Urgente).", 1, 0.0

    try:
        carga = float(carga_str.strip().replace(",", "."))
    except ValueError:
        return False, "Erro de validação: o peso da carga (kg) deve ser um valor numérico.", 1, 0.0

    if carga < 0.0 or carga > 25.0:
        return False, "O limite de carga do robô é de 0 kg até 25 kg.", 1, 0.0

    return True, "", prioridade, round(carga, 2)
