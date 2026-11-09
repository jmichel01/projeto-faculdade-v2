from pathlib import Path
import pytest
from navbot.app import criar_app
from navbot.banco import BancoSmartHome
from navbot.estruturas import FilaAutomacao, PilhaComandos
from navbot.modelos import (
    ArCondicionado,
    CameraSeguranca,
    FechaduraPorta,
    GeladeiraSmart,
    Iluminacao,
    SistemaSom,
    SmartTV,
)
from navbot.validadores import (
    ErroValidacaoDados,
    validar_item_geladeira,
    validar_numero_inteiro,
)


def test_polimorfismo_e_encapsulamento_dispositivos():
    ar = ArCondicionado(1, "SALA", "Ar Sala", "ar", True, 20.0, "Frio", "Inverter", False)
    tv = SmartTV(2, "SALA", "TV Sala", "tv", True, 50.0, "Netflix", "4K", False)
    geladeira = GeladeiraSmart(3, "COZ", "Geladeira", "geladeira", True, 2.0, "Super", "Filtro OK", False)
    som = SistemaSom(4, "SALA", "Som", "som", True, 50.0, "Spotify", "Dolby", False)
    luz = Iluminacao(5, "SALA", "Luz", "luz", True, 100.0, "Branco", "LED", False)
    porta = FechaduraPorta(6, "SALA", "Porta", "porta", True, 1.0, "Biometria", "Digital", True)
    cam = CameraSeguranca(7, "EXTERNA", "Cam 01", "camera", True, 1.0, "4K", "Sem alerta", True)

    assert ar.consumo_watts() > tv.consumo_watts()
    assert geladeira.consumo_watts() == 220
    assert som.consumo_watts() > 0
    assert luz.consumo_watts() == 45
    assert porta.consumo_watts() == 8
    assert cam.consumo_watts() == 18

    ar.ligado = False
    assert ar.consumo_watts() == 0
    assert "Desligado" in ar.resumo_estado()


def test_estruturas_fila_e_pilha():
    fila = FilaAutomacao()
    fila.enfileirar({"acao": "ar_20"})
    fila.enfileirar({"acao": "apagar_luzes"})
    assert fila.tamanho() == 2
    primeiro = fila.desenfileirar()
    assert primeiro["acao"] == "ar_20"

    pilha = PilhaComandos()
    pilha.empilhar({"id_disp": 1, "descricao": "Ar 22C"})
    pilha.empilhar({"id_disp": 2, "descricao": "TV Ligada"})
    topo = pilha.desempilhar()
    assert topo["id_disp"] == 2
    assert pilha.tamanho() == 1


def test_validadores_bloqueiam_strings_em_campos_numericos():
    assert validar_numero_inteiro("20", "Temperatura", 16, 28) == 20

    with pytest.raises(ErroValidacaoDados):
        validar_numero_inteiro("vinte graus", "Temperatura", 16, 28)

    with pytest.raises(ErroValidacaoDados):
        validar_numero_inteiro("35", "Temperatura", 16, 28)

    nome, qtd = validar_item_geladeira("Suco de Uva", "4")
    assert nome == "Suco de Uva"
    assert qtd == 4

    with pytest.raises(ErroValidacaoDados):
        validar_item_geladeira("Suco", "abc")


def test_banco_sqlite_e_fluxo_web_completo(tmp_path: Path):
    caminho_db = tmp_path / "teste_casa.db"
    banco = BancoSmartHome(caminho_db)

    assert len(banco.listar_comodos()) == 5
    assert len(banco.listar_dispositivos()) >= 20
    assert len(banco.listar_itens_geladeira()) >= 5

    app = criar_app(caminho_db)
    app.config["TESTING"] = True
    client = app.test_client()

    resp_login = client.post("/login", data={"perfil_demo": "admin"}, follow_redirects=True)
    assert resp_login.status_code == 200
    assert "Smart Home" in resp_login.get_data(as_text=True)

    resp_ar_geral = client.post(
        "/geral/ar",
        data={"temperatura_geral": "20", "comodo_retorno": "SALA"},
        follow_redirects=True,
    )
    assert resp_ar_geral.status_code == 200
    ares = banco.listar_por_categoria("ar")
    assert all(a.valor_num == 20.0 and a.ligado for a in ares)

    resp_luzes = client.post(
        "/geral/luzes",
        data={"acao": "desligar", "comodo_retorno": "SALA"},
        follow_redirects=True,
    )
    assert resp_luzes.status_code == 200
    luzes = banco.listar_por_categoria("luz")
    assert all(not l.ligado for l in luzes)

    resp_geladeira = client.post(
        "/geladeira/adicionar",
        data={
            "nome_item": "Iogurte Grego",
            "quantidade": "5",
            "unidade": "potes",
            "categoria_item": "Laticínios",
            "comodo_retorno": "COZ",
        },
        follow_redirects=True,
    )
    assert "Iogurte Grego" in resp_geladeira.get_data(as_text=True)

    resp_desfazer = client.post("/pilha/desfazer", data={"comodo_retorno": "SALA"}, follow_redirects=True)
    assert resp_desfazer.status_code == 200

    client.get("/logout")
    client.post("/login", data={"perfil_demo": "convidado"}, follow_redirects=True)
    portas = banco.listar_por_categoria("porta")
    porta_id = portas[0].id_disp
    resp_bloqueio = client.post(
        f"/dispositivo/{porta_id}/atualizar",
        data={"acao_rapida": "alternar", "comodo_retorno": "SALA"},
        follow_redirects=True,
    )
    assert "Acesso negado" in resp_bloqueio.get_data(as_text=True)
