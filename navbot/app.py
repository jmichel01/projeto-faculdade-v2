from functools import wraps
import hashlib
import os
from pathlib import Path
from typing import Callable
from flask import Flask, flash, redirect, render_template, request, session, url_for
from navbot.banco import BancoSmartHome
from navbot.estruturas import FilaAutomacao, PilhaComandos
from navbot.validadores import ErroValidacaoDados, validar_item_geladeira, validar_numero_inteiro


OPCOES_MODO = {
    "tv": [
        "Netflix — Série Sci-Fi",
        "YouTube 4K — Tecnologia",
        "HBO Max — Filmes",
        "Globo Ao Vivo — Jornalismo",
        "ESPN HD — Futebol Ao Vivo",
        "PlayStation 6 / HDMI 1",
    ],
    "ar": [
        "Frio",
        "Eco (Economia)",
        "Sono Silencioso",
        "Ventilar",
        "Turbo Polar",
    ],
    "geladeira": [
        "Super Refrigeração",
        "Férias / Eco",
        "Festa / Bebidas Rápidas",
        "Padrão Inteligente",
    ],
    "som": [
        "Spotify — Rock Clássico",
        "Lo-Fi Chill Beats",
        "Som de Chuva & Relaxamento",
        "Rádio Notícias / Podcast",
        "Jazz Instrumental",
        "Bluetooth Pareado",
    ],
    "luz": [
        "Branco Quente (Conforto)",
        "Branco Frio (Foco Total)",
        "Luz Suave Noturna",
        "Azul Ambiente",
        "Automático por Presença",
    ],
    "porta": [
        "Trancada com Biometria",
        "Trancada com Travas Duplas",
        "Acesso Liberado Internamente",
        "Modo Entrega / Visitante",
    ],
    "camera": [
        "Ao Vivo 1080p",
        "Visão Noturna 4K",
        "Detector de Movimento IA",
        "Infravermelho Perímetro",
    ],
}

LIMITES_CATEGORIA = {
    "ar": ("Temperatura do Ar-Condicionado", 16, 28),
    "geladeira": ("Temperatura da Geladeira", -2, 8),
    "tv": ("Volume da TV", 0, 100),
    "som": ("Volume do Som", 0, 100),
    "luz": ("Intensidade da Luz", 0, 100),
}


def obter_chave_sessao() -> str:
    chave_env = os.environ.get("SECRET_KEY")
    if chave_env:
        return chave_env
    semente = os.environ.get("VERCEL_PROJECT_ID", "smarthome-2050-chave-estavel-padrao")
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()


def criar_app(caminho_banco: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = obter_chave_sessao()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    banco = BancoSmartHome(caminho_banco)
    app.config["BANCO"] = banco

    def obter_pilha_sessao() -> PilhaComandos:
        pilha = PilhaComandos()
        for item in session.get("pilha_comandos", []):
            if isinstance(item, dict):
                pilha.empilhar(dict(item))
        return pilha

    def salvar_pilha_sessao(pilha: PilhaComandos) -> None:
        session["pilha_comandos"] = list(reversed(pilha.listar_historico()))
        session.modified = True

    def exigir_login(f: Callable) -> Callable:
        @wraps(f)
        def decorada(*args, **kwargs):
            if "usuario" not in session:
                return redirect(url_for("login"))
            return f(*args, **kwargs)

        return decorada

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            senha = request.form.get("senha", "")
            user = banco.autenticar(username, senha)
            if user:
                session["usuario"] = user
                session["pilha_comandos"] = []
                banco.registrar_log(
                    user["username"],
                    user["perfil"],
                    "Acessou a Central da Casa Inteligente",
                )
                return redirect(url_for("painel"))
            flash("Usuário ou senha inválidos. Utilize os botões de acesso rápido abaixo.", "erro")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        user = session.pop("usuario", None)
        session.pop("pilha_comandos", None)
        if user:
            banco.registrar_log(user["username"], user["perfil"], "Encerrou a sessão no painel")
        return redirect(url_for("login"))

    @app.route("/")
    @exigir_login
    def painel():
        comodos = banco.listar_comodos()
        codigos_validos = [str(c["codigo"]) for c in comodos] + ["TODOS"]
        comodo_selecionado = request.args.get("comodo", "SALA").upper()
        if comodo_selecionado not in codigos_validos:
            comodo_selecionado = "SALA"

        todos_dispositivos = banco.listar_dispositivos()
        if comodo_selecionado == "TODOS":
            dispositivos_visiveis = todos_dispositivos
            info_comodo = {
                "codigo": "TODOS",
                "nome": "Visão Geral de Todos os Cômodos",
                "descricao": "Todos os 23 equipamentos da residência exibidos simultaneamente",
            }
        else:
            dispositivos_visiveis = [d for d in todos_dispositivos if d.comodo_codigo == comodo_selecionado]
            info_comodo = next(
                (c for c in comodos if c["codigo"] == comodo_selecionado),
                comodos[0],
            )

        potencia_total_watts = sum(d.consumo_watts() for d in todos_dispositivos)
        dispositivos_ligados = sum(1 for d in todos_dispositivos if d.ligado)

        ares_ligados = [d for d in todos_dispositivos if d.categoria == "ar" and d.ligado]
        media_ar = (
            round(sum(d.valor_num for d in ares_ligados) / len(ares_ligados), 1)
            if ares_ligados
            else None
        )

        luzes = [d for d in todos_dispositivos if d.categoria == "luz"]
        luzes_acesas = sum(1 for d in luzes if d.ligado)

        portas = [d for d in todos_dispositivos if d.categoria == "porta"]
        portas_trancadas = sum(1 for d in portas if d.ligado)

        cameras_casa = [d for d in todos_dispositivos if d.categoria == "camera"]
        itens_geladeira = banco.listar_itens_geladeira()
        pilha = obter_pilha_sessao()

        mapa_nomes_comodos = {str(c["codigo"]): str(c["nome"]) for c in comodos}

        return render_template(
            "painel.html",
            usuario=session["usuario"],
            comodos=comodos,
            comodo_atual=comodo_selecionado,
            info_comodo=info_comodo,
            mapa_nomes_comodos=mapa_nomes_comodos,
            dispositivos=dispositivos_visiveis,
            todos_dispositivos=todos_dispositivos,
            cameras_casa=cameras_casa,
            itens_geladeira=itens_geladeira,
            opcoes_modo=OPCOES_MODO,
            potencia_total_watts=potencia_total_watts,
            dispositivos_ligados=dispositivos_ligados,
            total_dispositivos=len(todos_dispositivos),
            media_ar=media_ar,
            total_ares=len([d for d in todos_dispositivos if d.categoria == "ar"]),
            ares_ativos=len(ares_ligados),
            luzes_acesas=luzes_acesas,
            total_luzes=len(luzes),
            portas_trancadas=portas_trancadas,
            total_portas=len(portas),
            pilha_acoes=pilha.listar_historico(),
            logs=banco.listar_logs(10),
        )

    @app.route("/dispositivo/<int:id_disp>/atualizar", methods=["POST"])
    @exigir_login
    def atualizar_dispositivo(id_disp: int):
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "SALA")
        disp = banco.buscar_dispositivo(id_disp)
        if not disp:
            flash("Dispositivo não encontrado.", "erro")
            return redirect(url_for("painel", comodo=comodo_retorno))

        if disp.restrito_admin and user["perfil"] != "administrador":
            banco.registrar_log(
                user["username"],
                user["perfil"],
                f"BLOQUEADO: Tentou alterar '{disp.nome}' (restrito a Administrador)",
            )
            flash(
                f"Acesso negado: '{disp.nome}' exige perfil de Morador Principal (Administrador).",
                "erro",
            )
            return redirect(url_for("painel", comodo=comodo_retorno))

        acao_rapida = request.form.get("acao_rapida", "")
        if acao_rapida == "alternar":
            novo_ligado = not disp.ligado
        else:
            novo_ligado = request.form.get("ligado", "1") == "1"

        novo_valor = disp.valor_num
        if disp.categoria in LIMITES_CATEGORIA and "valor_num" in request.form:
            rotulo, minimo, maximo = LIMITES_CATEGORIA[disp.categoria]
            try:
                novo_valor = float(
                    validar_numero_inteiro(
                        request.form.get("valor_num", ""),
                        rotulo,
                        minimo,
                        maximo,
                    )
                )
            except ErroValidacaoDados as exc:
                flash(str(exc), "erro")
                return redirect(url_for("painel", comodo=comodo_retorno))

        novo_modo = request.form.get("modo_atual", disp.modo_atual).strip() or disp.modo_atual

        pilha = obter_pilha_sessao()
        pilha.empilhar(
            {
                "id_disp": disp.id_disp,
                "nome": disp.nome,
                "ligado_antigo": disp.ligado,
                "valor_antigo": disp.valor_num,
                "modo_antigo": disp.modo_atual,
                "descricao": f"{disp.nome} ({disp.resumo_estado()})",
            }
        )
        salvar_pilha_sessao(pilha)

        banco.atualizar_dispositivo(disp.id_disp, novo_ligado, novo_valor, novo_modo)
        disp_atualizado = banco.buscar_dispositivo(disp.id_disp)
        resumo_novo = disp_atualizado.resumo_estado() if disp_atualizado else novo_modo
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"Alterou {disp.nome} para: {resumo_novo}",
        )
        flash(f"{disp.nome} atualizado: {resumo_novo}.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno))

    @app.route("/geral/ar", methods=["POST"])
    @exigir_login
    def geral_ar():
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "SALA")
        acao_ar = request.form.get("acao_ar", "temperatura")

        ares = banco.listar_por_categoria("ar")
        fila = FilaAutomacao()
        pilha = obter_pilha_sessao()

        if acao_ar == "desligar_todos":
            for ar in ares:
                fila.enfileirar({"disp": ar, "ligado": False, "temp": ar.valor_num, "modo": ar.modo_atual})
            cont = 0
            while not fila.esta_vazia():
                tarefa = fila.desenfileirar()
                if tarefa:
                    d = tarefa["disp"]
                    pilha.empilhar(
                        {
                            "id_disp": d.id_disp,
                            "nome": d.nome,
                            "ligado_antigo": d.ligado,
                            "valor_antigo": d.valor_num,
                            "modo_antigo": d.modo_atual,
                            "descricao": f"{d.nome} ({d.resumo_estado()})",
                        }
                    )
                    banco.atualizar_dispositivo(d.id_disp, False, d.valor_num, d.modo_atual)
                    cont += 1
            salvar_pilha_sessao(pilha)
            banco.registrar_log(
                user["username"],
                user["perfil"],
                f"COMANDO GERAL: Desligou todos os {cont} aparelhos de Ar-Condicionado",
            )
            flash(f"Todos os {cont} aparelhos de Ar-Condicionado foram desligados.", "sucesso")
            return redirect(url_for("painel", comodo=comodo_retorno))

        try:
            temp_alvo = validar_numero_inteiro(
                request.form.get("temperatura_geral", "20"),
                "Temperatura Geral da Casa",
                16,
                28,
            )
        except ErroValidacaoDados as exc:
            flash(str(exc), "erro")
            return redirect(url_for("painel", comodo=comodo_retorno))

        for ar in ares:
            fila.enfileirar({"disp": ar, "ligado": True, "temp": float(temp_alvo), "modo": "Frio"})

        cont = 0
        while not fila.esta_vazia():
            tarefa = fila.desenfileirar()
            if tarefa:
                d = tarefa["disp"]
                pilha.empilhar(
                    {
                        "id_disp": d.id_disp,
                        "nome": d.nome,
                        "ligado_antigo": d.ligado,
                        "valor_antigo": d.valor_num,
                        "modo_antigo": d.modo_atual,
                        "descricao": f"{d.nome} ({d.resumo_estado()})",
                    }
                )
                banco.atualizar_dispositivo(d.id_disp, True, float(temp_alvo), "Frio")
                cont += 1

        salvar_pilha_sessao(pilha)
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"COMANDO GERAL: Sincronizou todos os {cont} Ar-Condicionados em {temp_alvo}°C",
        )
        flash(
            f"Comando Geral executado: Todos os {cont} Ar-Condicionados da casa agora estão ligados em {temp_alvo}°C.",
            "sucesso",
        )
        return redirect(url_for("painel", comodo=comodo_retorno))

    @app.route("/geral/luzes", methods=["POST"])
    @exigir_login
    def geral_luzes():
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "SALA")
        acao = request.form.get("acao", "desligar")
        ligar_alvo = acao == "ligar"

        luzes = banco.listar_por_categoria("luz")
        fila = FilaAutomacao()
        pilha = obter_pilha_sessao()

        for luz in luzes:
            fila.enfileirar(luz)

        cont = 0
        while not fila.esta_vazia():
            d = fila.desenfileirar()
            if d:
                pilha.empilhar(
                    {
                        "id_disp": d.id_disp,
                        "nome": d.nome,
                        "ligado_antigo": d.ligado,
                        "valor_antigo": d.valor_num,
                        "modo_antigo": d.modo_atual,
                        "descricao": f"{d.nome} ({d.resumo_estado()})",
                    }
                )
                intensidade = 100.0 if ligar_alvo and d.valor_num == 0 else d.valor_num
                banco.atualizar_dispositivo(d.id_disp, ligar_alvo, intensidade, d.modo_atual)
                cont += 1

        salvar_pilha_sessao(pilha)
        verbo = "Ligou" if ligar_alvo else "Apagou"
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"COMANDO GERAL: {verbo} todas as {cont} lâmpadas da casa",
        )
        flash(f"Comando Geral executado: {verbo} todas as {cont} lâmpadas da casa.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno))

    @app.route("/geral/portas", methods=["POST"])
    @exigir_login
    def geral_portas():
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "SALA")
        if user["perfil"] != "administrador":
            banco.registrar_log(
                user["username"],
                user["perfil"],
                "BLOQUEADO: Convidado tentou acionar o travamento geral de portas",
            )
            flash("Apenas o Morador Principal (Admin) pode controlar as fechaduras e portões.", "erro")
            return redirect(url_for("painel", comodo=comodo_retorno))

        acao = request.form.get("acao", "trancar")
        trancar_alvo = acao == "trancar"

        portas = banco.listar_por_categoria("porta")
        fila = FilaAutomacao()
        pilha = obter_pilha_sessao()

        for porta in portas:
            fila.enfileirar(porta)

        cont = 0
        while not fila.esta_vazia():
            d = fila.desenfileirar()
            if d:
                pilha.empilhar(
                    {
                        "id_disp": d.id_disp,
                        "nome": d.nome,
                        "ligado_antigo": d.ligado,
                        "valor_antigo": d.valor_num,
                        "modo_antigo": d.modo_atual,
                        "descricao": f"{d.nome} ({d.resumo_estado()})",
                    }
                )
                modo_porta = "Trancada com Biometria" if trancar_alvo else "Acesso Liberado Internamente"
                banco.atualizar_dispositivo(d.id_disp, trancar_alvo, 1.0, modo_porta)
                cont += 1

        salvar_pilha_sessao(pilha)
        estado_txt = "trancadas" if trancar_alvo else "destrancadas"
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"SEGURANÇA GERAL: Todas as {cont} portas e portões foram {estado_txt}",
        )
        flash(f"Segurança Geral: Todas as {cont} portas e portões foram {estado_txt}.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno))

    @app.route("/geladeira/adicionar", methods=["POST"])
    @exigir_login
    def geladeira_adicionar():
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "COZ")
        try:
            nome_limpo, qtd = validar_item_geladeira(
                request.form.get("nome_item", ""),
                request.form.get("quantidade", ""),
            )
        except ErroValidacaoDados as exc:
            flash(str(exc), "erro")
            return redirect(url_for("painel", comodo=comodo_retorno, geladeira="aberta"))

        unidade = request.form.get("unidade", "unidades").strip() or "unidades"
        categoria_item = request.form.get("categoria_item", "Alimentos").strip() or "Alimentos"
        banco.adicionar_item_geladeira(nome_limpo, qtd, unidade, categoria_item)
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"Geladeira Inteligente: Adicionou {qtd} {unidade} de '{nome_limpo}'",
        )
        flash(f"Item '{nome_limpo}' ({qtd} {unidade}) registrado na Geladeira Inteligente.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno, geladeira="aberta"))

    @app.route("/geladeira/item/<int:id_item>/qtd", methods=["POST"])
    @exigir_login
    def geladeira_alterar_qtd(id_item: int):
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "COZ")
        delta = 1 if request.form.get("operacao") == "mais" else -1
        banco.alterar_quantidade_geladeira(id_item, delta)
        sinal = "+1" if delta > 0 else "-1"
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"Geladeira Inteligente: Ajustou quantidade de item ({sinal})",
        )
        flash("Estoque da Geladeira Inteligente atualizado.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno, geladeira="aberta"))

    @app.route("/pilha/desfazer", methods=["POST"])
    @exigir_login
    def desfazer_acao():
        user = session["usuario"]
        comodo_retorno = request.form.get("comodo_retorno", "SALA")
        pilha = obter_pilha_sessao()
        ultimo = pilha.desempilhar()
        salvar_pilha_sessao(pilha)

        if not ultimo:
            flash("A pilha de alterações está vazia. Nenhuma ação para desfazer.", "aviso")
            return redirect(url_for("painel", comodo=comodo_retorno))

        banco.atualizar_dispositivo(
            int(ultimo["id_disp"]),
            bool(ultimo["ligado_antigo"]),
            float(ultimo["valor_antigo"]),
            str(ultimo["modo_antigo"]),
        )
        banco.registrar_log(
            user["username"],
            user["perfil"],
            f"DESFEZ AÇÃO (Pilha LIFO): Restaurou {ultimo['descricao']}",
        )
        flash(f"Ação desfeita com sucesso: {ultimo['descricao']} restaurado.", "sucesso")
        return redirect(url_for("painel", comodo=comodo_retorno))

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True, port=8000)
