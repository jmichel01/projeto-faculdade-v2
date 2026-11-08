from pathlib import Path
from navbot.app import criar_app
from navbot.estruturas import FilaMissoes, PilhaNavegacao
from navbot.grafo import GrafoPlantaCasa
from navbot.modelos import MissaoEmergencia, MissaoEntrega, MissaoLimpeza
from navbot.validadores import validar_dados_missao


def test_dijkstra_menor_caminho_e_desvio_de_obstaculo() -> None:
    grafo = GrafoPlantaCasa()
    caminho_livre, dist_livre = grafo.calcular_menor_caminho_dijkstra("BASE", "JAR")
    assert caminho_livre == ["BASE", "SALA", "JAR"]
    assert dist_livre == 9.0

    caminho_desvio, dist_desvio = grafo.calcular_menor_caminho_dijkstra(
        "BASE", "JAR", comodos_bloqueados={"SALA"}
    )
    assert "SALA" not in caminho_desvio
    assert caminho_desvio == ["BASE", "COZ", "JAR"]
    assert dist_desvio == 10.0


def test_polimorfismo_consumo_bateria_missoes() -> None:
    entrega = MissaoEntrega(1, "Café", "entrega", "COZ", "SALA", 3, carga_kg=5.0)
    limpeza = MissaoLimpeza(2, "Aspirar", "limpeza", "BASE", "SALA", 2)
    emergencia = MissaoEmergencia(3, "Socorro", "emergencia", "BASE", "Q1", 5)

    assert entrega.calcular_gasto_bateria(10.0) > limpeza.calcular_gasto_bateria(10.0)
    assert emergencia.calcular_gasto_bateria(10.0) > 15.0


def test_fila_prioridade_e_pilha_lifo() -> None:
    fila = FilaMissoes()
    fila.enfileirar_com_prioridade({"id_missao": 1, "prioridade": 2})
    fila.enfileirar_com_prioridade({"id_missao": 2, "prioridade": 5})
    primeiro = fila.desenfileirar()
    assert primeiro is not None
    assert primeiro["id_missao"] == 2

    pilha = PilhaNavegacao()
    pilha.empilhar({"no_anterior": "BASE"})
    pilha.empilhar({"no_anterior": "SALA"})
    topo = pilha.desempilhar()
    assert topo is not None
    assert topo["no_anterior"] == "SALA"


def test_validacao_e_bloqueio_visitante_flask(tmp_path: Path) -> None:
    ok, msg, _, _ = validar_dados_missao("Entrega", "BASE", "SALA", "3", "texto_invalido")
    assert ok is False
    assert "numérico" in msg

    db_teste = tmp_path / "teste_navbot.db"
    app = criar_app(caminho_banco=db_teste)
    client = app.test_client()

    client.post("/login", data={"username": "convidado", "senha": "1234"}, follow_redirects=True)
    resp_restrito = client.post("/navegar/dijkstra", data={"destino": "LAB"}, follow_redirects=True)
    assert "ACESSO RESTRITO" in resp_restrito.get_data(as_text=True)

    resp_social = client.post("/navegar/dijkstra", data={"destino": "SALA"}, follow_redirects=True)
    assert "Rota ótima executada" in resp_social.get_data(as_text=True)
