import hashlib
import os
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, session, url_for
from navbot.banco import BancoNavBot
from navbot.estruturas import FilaMissoes, PilhaNavegacao
from navbot.grafo import GrafoPlantaCasa
from navbot.validadores import validar_dados_missao


def obter_chave_sessao() -> str:
    chave_env = os.environ.get("SECRET_KEY")
    if chave_env:
        return chave_env
    semente = f"navbot-2050-{os.environ.get('VERCEL_GIT_COMMIT_SHA', ' padrao-estavel')}"
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()


def criar_app(caminho_banco: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = obter_chave_sessao()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    banco = BancoNavBot(caminho_banco=caminho_banco)
    grafo = GrafoPlantaCasa()
    pilha_nav = PilhaNavegacao()
    fila_missoes = FilaMissoes()

    app.config["BANCO"] = banco
    app.config["GRAFO"] = grafo

    def sincronizar_fila_pendentes() -> None:
        fila_missoes.limpar()
        for m in banco.listar_missoes():
            if m.status == "pendente":
                fila_missoes.enfileirar_com_prioridade(
                    {
                        "id_missao": m.id_missao,
                        "titulo": m.titulo,
                        "origem": m.origem,
                        "destino": m.destino,
                        "prioridade": m.prioridade,
                    }
                )

    def carregar_pilha_sessao() -> None:
        historico = session.get("pilha_passos", [])
        if isinstance(historico, list) and pilha_nav.tamanho() == 0:
            for item in historico:
                if isinstance(item, dict):
                    pilha_nav.empilhar(item)

    def salvar_pilha_sessao() -> None:
        session["pilha_passos"] = list(reversed(pilha_nav.listar_recentes()))
        session.modified = True

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            senha = request.form.get("senha", "").strip()
            usuario = banco.autenticar(username, senha)
            if usuario:
                session.clear()
                session["usuario"] = usuario
                session["pilha_passos"] = []
                banco.registrar_log(
                    str(usuario["username"]),
                    str(usuario["perfil"]),
                    "Entrou no painel de controle do Robô R-2050.",
                )
                flash(f"Bem-vindo, {usuario['nome_exibicao']}!", "sucesso")
                return redirect(url_for("painel"))
            flash("Usuário ou senha incorretos. Use admin / 1234 ou convidado / 1234.", "erro")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        usuario = session.get("usuario")
        if usuario:
            banco.registrar_log(
                str(usuario["username"]),
                str(usuario["perfil"]),
                "Saiu do painel de controle.",
            )
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def painel():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        carregar_pilha_sessao()
        sincronizar_fila_pendentes()

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
            flash("Permissão negada: apenas o Administrador pode fechar ou liberar cômodos na planta.", "erro")
            banco.registrar_log(
                str(usuario["username"]),
                str(usuario["perfil"]),
                f"Tentativa bloqueada de interditar o cômodo '{codigo}'.",
            )
            return redirect(url_for("painel"))

        if codigo == "BASE":
            flash("A Base de Recarga (BASE) não pode ser interditada.", "erro")
            return redirect(url_for("painel"))

        ficou_bloqueado = banco.alternar_bloqueio_comodo(codigo)
        estado_txt = "FECHADO (Com Obstáculo)" if ficou_bloqueado else "LIBERADO"
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Alterou o cômodo '{codigo}' para {estado_txt}.",
        )
        flash(f"Cômodo '{codigo}' agora está {estado_txt}. O robô vai desviar dele nas próximas rotas!", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/navegar/dijkstra", methods=["POST"])
    def navegar_dijkstra():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        carregar_pilha_sessao()
        destino = request.form.get("destino", "SALA")
        comodo_destino = banco.buscar_comodo(destino)
        if not comodo_destino:
            flash("Cômodo de destino inválido.", "erro")
            return redirect(url_for("painel"))

        if comodo_destino["restrito_admin"] and usuario["perfil"] != "administrador":
            flash(
                f"ACESSO RESTRITO: O ambiente '{comodo_destino['nome']}' ({destino}) só pode ser acessado pelo Administrador.",
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

        if origem == destino:
            flash(f"O robô já está em '{comodo_destino['nome']}' ({destino}). Escolha outro cômodo!", "sucesso")
            return redirect(url_for("painel"))

        caminho, distancia = grafo.calcular_menor_caminho_dijkstra(
            origem=origem,
            destino=destino,
            comodos_bloqueados=bloqueados,
        )

        if not caminho:
            flash(
                f"Rota bloqueada! Não existe caminho livre até '{comodo_destino['nome']}' ({destino}) porque os corredores estão fechados.",
                "erro",
            )
            return redirect(url_for("painel"))

        gasto = round(distancia * 0.85, 1)
        bateria_atual = float(robo["bateria_pct"])
        if bateria_atual < gasto and destino != "BASE":
            flash("Bateria baixa para essa distância! Clique em 'Recarregar na Base' primeiro.", "erro")
            return redirect(url_for("painel"))

        pilha_nav.empilhar(
            {
                "no_anterior": origem,
                "rota_anterior": str(robo["ultima_rota"]),
                "bateria_anterior": bateria_atual,
            }
        )
        salvar_pilha_sessao()

        nova_bateria = 100.0 if destino == "BASE" else max(5.0, bateria_atual - gasto)
        rota_formatada = " -> ".join(caminho)
        banco.atualizar_estado_robo(destino, nova_bateria, rota_formatada, distancia)

        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Rota ótima executada ({distancia}m): {rota_formatada}.",
        )
        flash(f"Rota ótima executada: {rota_formatada} (Distância total: {distancia}m).", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/robo/recarregar", methods=["POST"])
    def recarregar_base():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        carregar_pilha_sessao()
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
        salvar_pilha_sessao()
        banco.atualizar_estado_robo("BASE", 100.0, rota_str, distancia)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Robô voltou para a BASE ({rota_str}) e recarregou a bateria em 100%.",
        )
        flash("Robô voltou para a Base de Recarga e está com 100% de bateria!", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/pilha/desfazer", methods=["POST"])
    def desfazer_passo_pilha():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        carregar_pilha_sessao()
        ultimo = pilha_nav.desempilhar()
        if not ultimo:
            flash("Ainda não há movimentos para desfazer. Mova o robô primeiro!", "erro")
            return redirect(url_for("painel"))

        salvar_pilha_sessao()
        no_ant = str(ultimo["no_anterior"])
        rota_ant = str(ultimo["rota_anterior"])
        bat_ant = float(ultimo["bateria_anterior"])
        banco.atualizar_estado_robo(no_ant, bat_ant, rota_ant, 0.0)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Desfez último movimento (Pilha LIFO): robô voltou para '{no_ant}'.",
        )
        flash(f"Movimento desfeito! O robô voltou para o cômodo anterior: {no_ant}.", "sucesso")
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
            flash("Permissão negada: Visitantes não podem criar tarefas para áreas restritas (Escritório / Garagem).", "erro")
            return redirect(url_for("painel"))

        if tipo in ("patrulha", "emergencia") and usuario["perfil"] != "administrador":
            flash("Permissão negada: Tarefas de Patrulha e Emergência são exclusivas do Administrador.", "erro")
            return redirect(url_for("painel"))

        ok, erro, prioridade, carga = validar_dados_missao(
            titulo, origem, destino, prioridade_str, carga_str
        )
        if not ok:
            flash(erro, "erro")
            return redirect(url_for("painel"))

        banco.cadastrar_missao(titulo.strip(), tipo, origem, destino, prioridade, carga)
        sincronizar_fila_pendentes()
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Criou nova tarefa '{titulo.strip()}' ({origem} -> {destino}, Prioridade {prioridade}).",
        )
        flash(f"Tarefa '{titulo.strip()}' adicionada na Fila de Prioridade!", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/fila/carregar", methods=["POST"])
    def carregar_fila():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        sincronizar_fila_pendentes()
        total = fila_missoes.tamanho()
        if total == 0:
            flash("Não há tarefas pendentes na fila no momento.", "erro")
            return redirect(url_for("painel"))

        flash(f"{total} tarefas organizadas por ordem de prioridade!", "sucesso")
        return redirect(url_for("painel"))

    @app.route("/fila/executar", methods=["POST"])
    def executar_proxima_fila():
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        carregar_pilha_sessao()
        sincronizar_fila_pendentes()
        item = fila_missoes.desenfileirar()
        if not item:
            flash("Todas as tarefas da fila já foram concluídas! Cadastre uma nova tarefa abaixo.", "erro")
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
                f"Não foi possível executar '{missao.titulo}': o caminho entre {missao.origem} e {missao.destino} está bloqueado!",
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
        salvar_pilha_sessao()

        gasto = missao.calcular_gasto_bateria(distancia)
        nova_bat = max(5.0, float(robo["bateria_pct"]) - gasto)
        rota_str = " -> ".join(caminho)

        banco.concluir_missao(missao.id_missao, rota_str, distancia)
        banco.atualizar_estado_robo(missao.destino, nova_bat, rota_str, distancia)
        banco.registrar_log(
            str(usuario["username"]),
            str(usuario["perfil"]),
            f"Concluiu tarefa prioritária (P{missao.prioridade}): '{missao.titulo}' | Rota: {rota_str} ({distancia}m, -{gasto}% bateria).",
        )
        flash(
            f"Tarefa '{missao.titulo}' concluída! Menor caminho: {rota_str} ({distancia}m | Consumo: -{gasto}% de bateria).",
            "sucesso",
        )
        return redirect(url_for("painel"))

    @app.route("/missao/<int:id_missao>/excluir", methods=["POST"])
    def excluir_missao(id_missao: int):
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("login"))

        if usuario["perfil"] != "administrador":
            flash("Apenas o Administrador pode remover tarefas do histórico.", "erro")
            return redirect(url_for("painel"))

        banco.excluir_missao(id_missao)
        flash("Tarefa removida com sucesso.", "sucesso")
        return redirect(url_for("painel"))

    return app


app = criar_app()
