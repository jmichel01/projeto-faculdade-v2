from typing import Tuple


class ErroValidacaoDados(ValueError):
    pass


def validar_numero_inteiro(
    valor_str: str,
    nome_campo: str,
    minimo: int,
    maximo: int,
) -> int:
    texto = str(valor_str).strip()
    try:
        numero = int(float(texto.replace(",", ".")))
    except ValueError as exc:
        raise ErroValidacaoDados(
            f"Erro de validação: o campo '{nome_campo}' aceita apenas números (você digitou '{texto}')."
        ) from exc

    if numero < minimo or numero > maximo:
        raise ErroValidacaoDados(
            f"Valor fora do limite: '{nome_campo}' deve ficar entre {minimo} e {maximo}."
        )

    return numero


def validar_item_geladeira(nome_item: str, qtd_str: str) -> Tuple[str, int]:
    limpo = str(nome_item).strip()
    if len(limpo) < 2:
        raise ErroValidacaoDados(
            "Informe o nome do produto para colocar na geladeira (mínimo 2 letras)."
        )

    qtd = validar_numero_inteiro(qtd_str, "Quantidade do item", 1, 99)
    return limpo, qtd
