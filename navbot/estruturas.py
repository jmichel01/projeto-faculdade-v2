from typing import Dict, List, Optional


class PilhaNavegacao:
    def __init__(self, capacidade: int = 30) -> None:
        self._passos: List[Dict[str, object]] = []
        self._capacidade = capacidade

    def empilhar(self, passo: Dict[str, object]) -> None:
        if len(self._passos) >= self._capacidade:
            self._passos.pop(0)
        self._passos.append(passo)

    def desempilhar(self) -> Optional[Dict[str, object]]:
        if not self._passos:
            return None
        return self._passos.pop()

    def tamanho(self) -> int:
        return len(self._passos)

    def listar_recentes(self) -> List[Dict[str, object]]:
        return list(reversed(self._passos))


class FilaMissoes:
    def __init__(self) -> None:
        self._itens: List[Dict[str, object]] = []

    def enfileirar_com_prioridade(self, missao: Dict[str, object]) -> None:
        self._itens.append(missao)
        self._itens.sort(key=lambda item: int(item.get("prioridade", 1)), reverse=True)

    def desenfileirar(self) -> Optional[Dict[str, object]]:
        if not self._itens:
            return None
        return self._itens.pop(0)

    def tamanho(self) -> int:
        return len(self._itens)

    def listar_todas(self) -> List[Dict[str, object]]:
        return list(self._itens)
