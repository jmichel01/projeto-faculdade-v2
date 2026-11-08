class MissaoRobo:
    def __init__(
        self,
        id_missao: int,
        titulo: str,
        tipo: str,
        origem: str,
        destino: str,
        prioridade: int,
        carga_kg: float = 0.0,
        status: str = "pendente",
        rota_calculada: str = "",
        distancia_metros: float = 0.0,
    ) -> None:
        self._id_missao = id_missao
        self._titulo = titulo
        self._tipo = tipo
        self._origem = origem
        self._destino = destino
        self._prioridade = max(1, min(5, int(prioridade)))
        self._carga_kg = max(0.0, float(carga_kg))
        self._status = status
        self._rota_calculada = rota_calculada
        self._distancia_metros = max(0.0, float(distancia_metros))

    @property
    def id_missao(self) -> int:
        return self._id_missao

    @property
    def titulo(self) -> str:
        return self._titulo

    @property
    def tipo(self) -> str:
        return self._tipo

    @property
    def origem(self) -> str:
        return self._origem

    @property
    def destino(self) -> str:
        return self._destino

    @property
    def prioridade(self) -> int:
        return self._prioridade

    @property
    def carga_kg(self) -> float:
        return self._carga_kg

    @property
    def status(self) -> str:
        return self._status

    @property
    def rota_calculada(self) -> str:
        return self._rota_calculada

    @property
    def distancia_metros(self) -> float:
        return self._distancia_metros

    def calcular_gasto_bateria(self, metros: float) -> float:
        return round(metros * 0.8, 1)

    def descricao_operacao(self) -> str:
        return "Deslocamento Padrão"


class MissaoEntrega(MissaoRobo):
    def calcular_gasto_bateria(self, metros: float) -> float:
        fator_peso = 1.0 + (self._carga_kg * 0.18)
        return round(metros * 0.9 * fator_peso, 1)

    def descricao_operacao(self) -> str:
        return f"Transporte de Carga ({self._carga_kg} kg)"


class MissaoLimpeza(MissaoRobo):
    def calcular_gasto_bateria(self, metros: float) -> float:
        return round((metros * 0.7) + 6.5, 1)

    def descricao_operacao(self) -> str:
        return "Higienização UV + Aspiração"


class MissaoPatrulha(MissaoRobo):
    def calcular_gasto_bateria(self, metros: float) -> float:
        return round((metros * 1.1) + 4.0, 1)

    def descricao_operacao(self) -> str:
        return "Varredura Térmica & Sensores"


class MissaoEmergencia(MissaoRobo):
    def calcular_gasto_bateria(self, metros: float) -> float:
        return round((metros * 1.45) + 5.0, 1)

    def descricao_operacao(self) -> str:
        return "Resposta Rápida Prioridade P5"


def instanciar_missao(dados: dict) -> MissaoRobo:
    tipo = dados["tipo"]
    argumentos = {
        "id_missao": dados["id"],
        "titulo": dados["titulo"],
        "tipo": tipo,
        "origem": dados["origem"],
        "destino": dados["destino"],
        "prioridade": dados["prioridade"],
        "carga_kg": dados["carga_kg"],
        "status": dados["status"],
        "rota_calculada": dados["rota_calculada"],
        "distancia_metros": dados["distancia_metros"],
    }
    if tipo == "entrega":
        return MissaoEntrega(**argumentos)
    if tipo == "limpeza":
        return MissaoLimpeza(**argumentos)
    if tipo == "patrulha":
        return MissaoPatrulha(**argumentos)
    if tipo == "emergencia":
        return MissaoEmergencia(**argumentos)
    return MissaoRobo(**argumentos)
