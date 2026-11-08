import os
from pathlib import Path
import secrets
from flask import Flask, flash, redirect, render_template, request, session, url_for
from navbot.banco import BancoNavBot
from navbot.estruturas import FilaMissoes, PilhaNavegacao
from navbot.grafo import GrafoPlantaCasa
from navbot.validadores import validar_dados_missao


def criar_app(caminho_banco: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    banco = BancoNavBot(caminho_banco=caminho_banco)
    grafo = GrafoPlantaCasa()
    pilha_nav = PilhaNavegacao()
    fila_missoes = FilaMissoes()

    app.config["BANCO"] = banco
    app.config["GRAFO"] = grafo

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            senha = request.form.get("senha", "")
            usuario = banco.autenticar(username, senha)
            if usuario:
                session["usuario"] = usuario
                banco.registrar_log(
                    str(usuario["username"]),
                    str(usuario["perfil"]),
                    "Conectou ao terminal de navegação do Robô R-2050.",
                )
                return redirect(url_for("painel"))
            flash("Credenciais inválidas. Verifique usuário e senha.", "erro")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        usuario = session.pop("usuario", None)
        if usuario:
            banco.registrar_log(
                str(usuario["username"]),
                str(usuario["perfil"]),
                "Encerrou sessão no terminal.",
            )
        return redirect(url_for("login"))

    @app.route("/")
    def painel():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        comodos = banco.listar_comodos()
        mapa_comodos = {str(c["codigo"]): c for c in comodos}
        arestas = grafo.listar_arestas_unicas()
        robo = banco.obter_estado_robo()
        missoes = banco.listar_missoes()
        logs = banco.listar_logs()

        rota_nos = [n.strip() for n in str(robo["ultima_rota"]).split("->") if n.strip()]

        return render_template(
            "painel.html",
            usuario=usuario,
            comodos=comodos,
            mapa_comodos=mapa_comodos,
            arestas=arestas,
            robo=robo,
            rota_nos=rota_nos,
            missoes=missoes,
            logs=logs,
            total_pilha=pilha_nav.tamanho(),
            fila_atual=fila_missoes.listar_todas(),
        )

    @app.route("/grafo/comodo/<codigo>/bloqueio", methods=["POST"])
    def alternar_obstaculo(codigo: str):
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        if usuario["perfil"] != "administrador":
            flash("Permissão negada: apenas o Administrador pode interditar cômodos ou alterar obstáculos no Grafo.", "erro")
            banco.registrar_log(
                str(usuario["username"]),
                str(usuario["perfil"]),
                f"Tentativa bloqueada de interditar o nó '{codigo}' no grafo.",
            )
            return redirect(url_for("painel"))

        if codigo == "BASE":
            flash("A Base de Recarga Central (BASE) não pode ser bloqueada.", "erro")
            return redirect(url_for("painel"))

        ficou_bloqueado = banco.alternar_bloqueio_comodo(codigo)
        estado_txt = "INTERDITADO (Obstáculo Ativo)" if ficou_bloqueado else "LIBERADO"
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Alterou o nó '{codigo}' no Grafo para {estado_txt}.",
        )
        flash(f"Nó '{codigo}' atualizado no Grafo: {estado_txt}.", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/navegar/dijkstra", methods=["POST"])
    def navegar_dijkstra():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        destino = request.form.get("destino", "SALA")
        comodo_destino = banco.buscar_comodo(destino)
        if not comodo_destino:
            flash("Cômodo de destino inválido.", "erro")
            return redirect(url_for("painel"))

        if comodo_destino["restrito_admin"] and usuario["perfil"] != "administrador":
            flash(
                f"ACESSO RESTRITO: O cômodo '{comodo_destino['nome']}' ({destino}) exige perfil Administrador.",
                "erro",
            )
            banco.registrar_log(
                str(usuario["username"]),
                str(usuario["perfil"]),
                f"BLOQUEIO DE SEGURANÇA: Visitante tentou enviar o robô para área restrita '{destino}'.",
            )
            return redirect(url_for("painel"))

        robo = banco.obter_estado_robo()
        origem = str(robo["no_atual"])
        bloqueados = banco.obter_conjunto_bloqueados()

        caminho, distancia = grafo.calcular_menor_caminho_dijkstra(
            origem=origem,
            destino=destino,
            comodos_bloqueados=bloqueados,
        )

        if not caminho:
            flash(
                f"Rota inacessível! Não há caminho livre no Grafo entre '{origem}' e '{destino}' devido a obstáculos.",
                "erro",
            )
            return redirect(url_for("painel"))

        gasto = round(distancia * 0.85, 1)
        bateria_atual = float(robo["bateria_pct"])
        if bateria_atual < gasto and destino != "BASE":
            flash("Bateria insuficiente para essa rota! Recarregue o robô na BASE primeiro.", "erro")
            return redirect(url_for("painel"))

        pilha_nav.empilhar(
            {
                "no_anterior": origem,
                "rota_anterior": str(robo["ultima_rota"]),
                "bateria_anterior": bateria_atual,
            }
        )

        nova_bateria = 100.0 if destino == "BASE" else max(5.0, bateria_atual - gasto)
        rota_formatada = " -> ".join(caminho)
        banco.atualizar_estado_robo(destino, nova_bateria, rota_formatada, distancia)

        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Dijkstra calculou menor caminho ({distancia}m): {rota_formatada}.",
        )
        flash(f"Rota ótima executada via Dijkstra: {rota_formatada} ({distancia}m).", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/robo/recarregar", methods=["POST"])
    def recarregar_base():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        robo = banco.obter_estado_robo()
        origem = str(robo["no_atual"])
        bloqueados = banco.obter_conjunto_bloqueados()
        caminho, distancia = grafo.calcular_menor_caminho_dijkstra(origem, "BASE", bloqueados)
        rota_str = " -> ".join(caminho) if caminho else "BASE"

        pilha_nav.empilhar(
            {
                "no_anterior": origem,
                "rota_anterior": str(robo["ultima_rota"]),
                "bateria_anterior": float(robo["bateria_pct"]),
            }
        )
        banco.atualizar_estado_robo("BASE", 100.0, rota_str, distancia)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Retornou o robô à BASE ({rota_str}) e recarregou bateria para 100%.",
        )
        flash("Robô retornou para a BASE e recarregou a bateria para 100%.", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/pilha/desfazer", methods=["POST"])
    def desfazer_passo_pilha():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        ultimo = pilha_nav.desempilhar()
        if not ultimo:
            flash("A Pilha de Navegação (LIFO) está vazia.", "erro")
            return redirect(url_for("painel"))

        no_ant = str(ultimo["no_anterior"])
        rota_ant = str(ultimo["rota_anterior"])
        bat_ant = float(ultimo["bateria_anterior"])
        banco.atualizar_estado_robo(no_ant, bat_ant, rota_ant, 0.0)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Desempilhou retorno (Pilha LIFO): robô voltou ao nó '{no_ant}'.",
        )
        flash(f"Retorno via Pilha LIFO executado: robô voltou para '{no_ant}'.", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/missao/nova", methods=["POST"])
    def nova_missao():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        titulo = request.form.get("titulo", "")
        tipo = request.form.get("tipo", "entrega")
        origem = request.form.get("origem", "BASE")
        destino = request.form.get("destino", "SALA")
        prioridade_str = request.form.get("prioridade", "3")
        carga_str = request.form.get("carga_kg", "0")

        comodo_dest = banco.buscar_comodo(destino)
        if comodo_dest and comodo_dest["restrito_admin"] and usuario["perfil"] != "administrador":
            flash("Permissão negada: Visitantes não podem criar missões para áreas restritas (LAB / GAR).", "erro")
            return redirect(url_for("painel"))

        if tipo in ("patrulha", "emergencia") and usuario["perfil"] != "administrador":
            flash("Permissão negada: Missões de Patrulha e Emergência são exclusivas do Administrador.", "erro")
            return redirect(url_for("painel"))

        ok, erro, prioridade, carga = validar_dados_missao(
            titulo, origem, destino, prioridade_str, carga_str
        )
        if not ok:
            flash(erro, "erro")
            return redirect(url_for("painel"))

        banco.cadastrar_missao(titulo.strip(), tipo, origem, destino, prioridade, carga)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Cadastrou missão '{titulo.strip()}' ({origem} -> {destino}, P{prioridade}).",
        )
        flash(f"Missão '{titulo.strip()}' adicionada com sucesso.", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/fila/carregar", methods=["POST"])
    def carregar_fila():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        pendentes = [m for m in banco.listar_missoes() if m.status == "pendente"]
        if not pendentes:
            flash("Não há missões pendentes para enfileirar.", "erro")
            return redirect(url_for("painel"))

        for m in pendentes:
            fila_missoes.enfileirar_com_prioridade(
                {
                    "id_missao": m.id_missao,
                    "titulo": m.titulo,
                    "origem": m.origem,
                    "destino": m.destino,
                    "prioridade": m.prioridade,
                }
            )
        flash(f"{len(pendentes)} missões carregadas na Fila de Prioridade!", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/fila/executar", methods=["POST"])
    def executar_proxima_fila():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        item = fila_missoes.desenfileirar()
        if not item:
            flash("A Fila de Missões está vazia. Clique em 'Enfileirar Pendentes' primeiro.", "erro")
            return redirect(url_for("painel"))

        missao = banco.buscar_missao(int(item["id_missao"]))
        if not missao:
            return redirect(url_for("painel"))

        bloqueados = banco.obter_conjunto_bloqueados()
        caminho, distancia = grafo.calcular_menor_caminho_dijkstra(
            missao.origem, missao.destino, bloqueados
        )
        if not caminho:
            flash(
                f"Missão '{missao.titulo}' bloqueada: sem caminho livre entre {missao.origem} e {missao.destino}!",
                "erro",
            )
            return redirect(url_for("painel"))

        robo = banco.obter_estado_robo()
        pilha_nav.empilhar(
            {
                "no_anterior": str(robo["no_atual"]),
                "rota_anterior": str(robo["ultima_rota"]),
                "bateria_anterior": float(robo["bateria_pct"]),
            }
        )

        gasto = missao.calcular_gasto_bateria(distancia)
        nova_bat = max(5.0, float(robo["bateria_pct"]) - gasto)
        rota_str = " -> ".join(caminho)

        banco.concluir_missao(missao.id_missao, rota_str, distancia)
        banco.atualizar_estado_robo(missao.destino, nova_bat, rota_str, distancia)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Executou missão da Fila (P{missao.prioridade}): '{missao.titulo}' | Rota: {rota_str} ({distancia}m, -{gasto}% bat).",
        )
        flash(
            f"Missão '{missao.titulo}' concluída! Rota Dijkstra: {rota_str} ({distancia}m | Polimorfismo POO: -{gasto}% bateria).",
            "sucesso",
        )
        return redirect(url_for("painel"))

    @app.route("/missao/<int:id_missao>/excluir", methods=["POST"])
    def excluir_missao(id_missao: int):
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        if usuario["perfil"] != "administrador":
            flash("Apenas o Administrador pode remover registros de missões.", "erro")
            return redirect(url_for("painel"))

        banco.excluir_missao(id_missao)
        flash("Missão removida do banco de dados.", "sucesso")
        return redirect(url_for("painel"))

    return app


app = criar_app()
