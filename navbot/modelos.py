class DispositivoCasa:
    def __init__(
        self,
        id_disp: int,
        comodo_codigo: str,
        nome: str,
        categoria: str,
        ligado: bool,
        valor_num: float,
        modo_atual: str,
        detalhe_extra: str,
        restrito_admin: bool = False,
    ) -> None:
        self._id_disp = int(id_disp)
        self._comodo_codigo = str(comodo_codigo)
        self._nome = str(nome)
        self._categoria = str(categoria)
        self._ligado = bool(ligado)
        self._valor_num = float(valor_num)
        self._modo_atual = str(modo_atual)
        self._detalhe_extra = str(detalhe_extra)
        self._restrito_admin = bool(restrito_admin)

    @property
    def id_disp(self) -> int:
        return self._id_disp

    @property
    def comodo_codigo(self) -> str:
        return self._comodo_codigo

    @property
    def nome(self) -> str:
        return self._nome

    @property
    def categoria(self) -> str:
        return self._categoria

    @property
    def ligado(self) -> bool:
        return self._ligado

    @ligado.setter
    def ligado(self, novo_estado: bool) -> None:
        self._ligado = bool(novo_estado)

    @property
    def valor_num(self) -> float:
        return self._valor_num

    @property
    def valor_int(self) -> int:
        return int(round(self._valor_num))

    @property
    def modo_atual(self) -> str:
        return self._modo_atual

    @property
    def detalhe_extra(self) -> str:
        return self._detalhe_extra

    @property
    def restrito_admin(self) -> bool:
        return self._restrito_admin

    def consumo_watts(self) -> int:
        return 15 if self._ligado else 0

    def resumo_estado(self) -> str:
        return "Ligado" if self._ligado else "Desligado"


class ArCondicionado(DispositivoCasa):
    def consumo_watts(self) -> int:
        if not self._ligado:
            return 0
        esforco = max(1, int(26 - self._valor_num))
        return 650 + (esforco * 55)

    def resumo_estado(self) -> str:
        if not self._ligado:
            return "Desligado"
        return f"Ligado · {self.valor_int}°C · Modo {self._modo_atual}"


class SmartTV(DispositivoCasa):
    def consumo_watts(self) -> int:
        return 140 if self._ligado else 2

    def resumo_estado(self) -> str:
        if not self._ligado:
            return "Em Standby (Desligada)"
        return f"Ligada · Canal/App: {self._modo_atual} · Volume {self.valor_int}%"


class GeladeiraSmart(DispositivoCasa):
    def consumo_watts(self) -> int:
        if not self._ligado:
            return 0
        return 220 if self._valor_num <= 2 else 170

    def resumo_estado(self) -> str:
        return f"Refrigeração Ativa · {self.valor_int}°C · Modo {self._modo_atual}"


class SistemaSom(DispositivoCasa):
    def consumo_watts(self) -> int:
        if not self._ligado:
            return 0
        return 35 + int(self._valor_num * 0.6)

    def resumo_estado(self) -> str:
        if not self._ligado:
            return "Silenciado / Desligado"
        return f"Tocando: {self._modo_atual} · Volume {self.valor_int}%"


class Iluminacao(DispositivoCasa):
    def consumo_watts(self) -> int:
        if not self._ligado:
            return 0
        return max(5, int(self._valor_num * 0.45))

    def resumo_estado(self) -> str:
        if not self._ligado:
            return "Apagada (0%)"
        return f"Acesa · Intensidade {self.valor_int}% · Tom {self._modo_atual}"


class FechaduraPorta(DispositivoCasa):
    def consumo_watts(self) -> int:
        return 8

    def resumo_estado(self) -> str:
        return "TRANCADA (Segura)" if self._ligado else "DESTRANCADA (Aberta)"


class CameraSeguranca(DispositivoCasa):
    def consumo_watts(self) -> int:
        return 18 if self._ligado else 0

    def resumo_estado(self) -> str:
        if not self._ligado:
            return "Câmera Desativada"
        return f"Gravando Ao Vivo ({self._modo_atual}) · {self._detalhe_extra}"


def instanciar_dispositivo(dados: dict) -> DispositivoCasa:
    cat = str(dados["categoria"])
    args = {
        "id_disp": int(dados["id"]),
        "comodo_codigo": str(dados["comodo_codigo"]),
        "nome": str(dados["nome"]),
        "categoria": cat,
        "ligado": bool(dados["ligado"]),
        "valor_num": float(dados["valor_num"]),
        "modo_atual": str(dados["modo_atual"]),
        "detalhe_extra": str(dados["detalhe_extra"]),
        "restrito_admin": bool(dados["restrito_admin"]),
    }
    mapa_classes = {
        "ar": ArCondicionado,
        "tv": SmartTV,
        "geladeira": GeladeiraSmart,
        "som": SistemaSom,
        "luz": Iluminacao,
        "porta": FechaduraPorta,
        "camera": CameraSeguranca,
    }
    classe = mapa_classes.get(cat, DispositivoCasa)
    return classe(**args)
