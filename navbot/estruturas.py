from typing import Any, Dict, List, Optional


class PilhaComandos:
    def __init__(self, capacidade: int = 30) -> None:
        self._itens: List[Dict[str, Any]] = []
        self._capacidade = capacidade

    def empilhar(self, estado_anterior: Dict[str, Any]) -> None:
        if len(self._itens) >= self._capacidade:
            self._itens.pop(0)
        self._itens.append(estado_anterior)

    def desempilhar(self) -> Optional[Dict[str, Any]]:
        if not self._itens:
            return None
        return self._itens.pop()

    def tamanho(self) -> int:
        return len(self._itens)

    def esta_vazia(self) -> bool:
        return len(self._itens) == 0

    def listar_historico(self) -> List[Dict[str, Any]]:
        return list(reversed(self._itens))

    def listar_todos(self) -> List[Dict[str, Any]]:
        return list(self._itens)


class FilaAutomacao:
    def __init__(self) -> None:
        self._fila: List[Any] = []

    def enfileirar(self, comando: Any) -> None:
        self._fila.append(comando)

    def desenfileirar(self) -> Optional[Any]:
        if not self._fila:
            return None
        return self._fila.pop(0)

    def esta_vazia(self) -> bool:
        return len(self._fila) == 0

    def tamanho(self) -> int:
        return len(self._fila)
