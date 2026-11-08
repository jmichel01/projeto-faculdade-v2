import heapq
from typing import Dict, List, Set, Tuple


ARESTAS_CASA: List[Tuple[str, str, float]] = [
    ("BASE", "SALA", 4.0),
    ("BASE", "COZ", 5.5),
    ("BASE", "Q1", 6.0),
    ("BASE", "LAB", 4.5),
    ("SALA", "COZ", 3.5),
    ("SALA", "JAR", 5.0),
    ("SALA", "Q2", 6.5),
    ("COZ", "GAR", 4.0),
    ("COZ", "JAR", 4.5),
    ("Q1", "Q2", 3.0),
    ("Q1", "LAB", 3.5),
    ("Q2", "JAR", 4.0),
    ("LAB", "GAR", 5.0),
]


class GrafoPlantaCasa:
    def __init__(self, arestas: List[Tuple[str, str, float]] | None = None) -> None:
        self._adjacencia: Dict[str, List[Tuple[str, float]]] = {}
        lista = arestas or ARESTAS_CASA
        for origem, destino, distancia in lista:
            self.adicionar_corredor(origem, destino, distancia)

    def adicionar_corredor(self, u: str, v: str, metros: float) -> None:
        if u not in self._adjacencia:
            self._adjacencia[u] = []
        if v not in self._adjacencia:
            self._adjacencia[v] = []
        self._adjacencia[u].append((v, metros))
        self._adjacencia[v].append((u, metros))

    def listar_arestas_unicas(self) -> List[Dict[str, object]]:
        vistos: Set[Tuple[str, str]] = set()
        resultado: List[Dict[str, object]] = []
        for u, vizinhos in self._adjacencia.items():
            for v, peso in vizinhos:
                chave = tuple(sorted((u, v)))
                if chave not in vistos:
                    vistos.add(chave)
                    resultado.append({"origem": u, "destino": v, "metros": peso})
        return resultado

    def calcular_menor_caminho_dijkstra(
        self,
        origem: str,
        destino: str,
        comodos_bloqueados: Set[str] | None = None,
    ) -> Tuple[List[str], float]:
        bloqueados = comodos_bloqueados or set()
        if origem in bloqueados or destino in bloqueados:
            return [], 0.0
        if origem == destino:
            return [origem], 0.0

        distancias: Dict[str, float] = {no: float("inf") for no in self._adjacencia}
        anteriores: Dict[str, str | None] = {no: None for no in self._adjacencia}
        distancias[origem] = 0.0

        fila_prioridade: List[Tuple[float, str]] = [(0.0, origem)]

        while fila_prioridade:
            dist_atual, atual = heapq.heappop(fila_prioridade)
            if atual == destino:
                break
            if dist_atual > distancias.get(atual, float("inf")):
                continue

            for vizinho, peso in self._adjacencia.get(atual, []):
                if vizinho in bloqueados:
                    continue
                nova_dist = round(dist_atual + peso, 2)
                if nova_dist < distancias.get(vizinho, float("inf")):
                    distancias[vizinho] = nova_dist
                    anteriores[vizinho] = atual
                    heapq.heappush(fila_prioridade, (nova_dist, vizinho))

        if distancias.get(destino, float("inf")) == float("inf"):
            return [], 0.0

        caminho: List[str] = []
        cursor: str | None = destino
        while cursor is not None:
            caminho.append(cursor)
            cursor = anteriores.get(cursor)
        caminho.reverse()

        return caminho, round(distancias[destino], 2)
