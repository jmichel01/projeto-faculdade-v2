from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional
from werkzeug.security import check_password_hash, generate_password_hash
from navbot.modelos import DispositivoCasa, instanciar_dispositivo


def obter_caminho_banco() -> Path:
    if os.environ.get("VERCEL"):
        return Path("/tmp/smarthome2050.db")
    return Path(__file__).parent.parent / "smarthome2050.db"


class BancoSmartHome:
    def __init__(self, caminho_banco: Path | None = None) -> None:
        self.caminho_banco = caminho_banco or obter_caminho_banco()
        self.inicializar_tabelas()

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.caminho_banco))
        conn.row_factory = sqlite3.Row
        return conn

    def inicializar_tabelas(self) -> None:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS usuarios ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "username TEXT UNIQUE NOT NULL, "
                "nome_exibicao TEXT NOT NULL, "
                "senha_hash TEXT NOT NULL, "
                "perfil TEXT NOT NULL)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS comodos ("
                "codigo TEXT PRIMARY KEY, "
                "nome TEXT NOT NULL, "
                "descricao TEXT NOT NULL, "
                "ordem INTEGER NOT NULL)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS dispositivos ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "comodo_codigo TEXT NOT NULL, "
                "nome TEXT NOT NULL, "
                "categoria TEXT NOT NULL, "
                "ligado INTEGER NOT NULL DEFAULT 1, "
                "valor_num REAL NOT NULL DEFAULT 20.0, "
                "modo_atual TEXT NOT NULL DEFAULT '', "
                "detalhe_extra TEXT NOT NULL DEFAULT '', "
                "restrito_admin INTEGER NOT NULL DEFAULT 0)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS itens_geladeira ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "nome_item TEXT NOT NULL, "
                "quantidade INTEGER NOT NULL, "
                "unidade TEXT NOT NULL, "
                "categoria_item TEXT NOT NULL, "
                "validade_status TEXT NOT NULL)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS historico_eventos ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "data_hora TEXT NOT NULL, "
                "usuario TEXT NOT NULL, "
                "perfil TEXT NOT NULL, "
                "acao TEXT NOT NULL)"
            )
            conn.commit()
            self._popular_dados_iniciais(conn)

    def _popular_dados_iniciais(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        if cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            hash_padrao = (
                "pbkdf2:sha256:1000000$MutllI2zfJzYxZWa$"
                "306d10667b62d9511abe7ef4f3239411ff67917bcd31a6167a7dcd2be905df85"
            )
            admin_user = os.environ.get("NAVBOT_ADMIN_USER", "admin")
            admin_pass = os.environ.get("NAVBOT_ADMIN_PASS", "")
            guest_user = os.environ.get("NAVBOT_GUEST_USER", "convidado")
            guest_pass = os.environ.get("NAVBOT_GUEST_PASS", "")
            hash_admin = generate_password_hash(admin_pass) if admin_pass else hash_padrao
            hash_guest = generate_password_hash(guest_pass) if guest_pass else hash_padrao
            usuarios = [
                (admin_user, "Morador Principal (Admin)", hash_admin, "administrador"),
                (guest_user, "Visitante / Convidado", hash_guest, "comum"),
            ]
            cursor.executemany(
                "INSERT INTO usuarios (username, nome_exibicao, senha_hash, perfil) VALUES (?, ?, ?, ?)",
                usuarios,
            )

        if cursor.execute("SELECT COUNT(*) FROM comodos").fetchone()[0] == 0:
            comodos = [
                ("SALA", "Sala de Estar", "TV 8K, Ar-Condicionado, Som Ambiente, Luzes e Porta Principal", 1),
                ("COZ", "Cozinha", "Geladeira Inteligente (Estoque Interno), Climatização e Iluminação", 2),
                ("SUITE", "Suíte Principal", "Ar-Condicionado, TV do Quarto, Som Relaxante, Luzes e Fechadura", 3),
                ("QUARTO2", "Quarto de Hóspedes", "TV / Monitor Gamer, Ar-Condicionado, Som Bluetooth e Luz LED", 4),
                ("EXTERNA", "Segurança & Garagem", "Central de Câmeras Ao Vivo, Portão Eletrônico e Luzes Externas", 5),
            ]
            cursor.executemany(
                "INSERT INTO comodos (codigo, nome, descricao, ordem) VALUES (?, ?, ?, ?)",
                comodos,
            )

        if cursor.execute("SELECT COUNT(*) FROM dispositivos").fetchone()[0] == 0:
            dispositivos = [
                ("SALA", "Smart TV 75\" Sala", "tv", 1, 45, "Netflix — Série Sci-Fi", "4K HDR Ativo", 0),
                ("SALA", "Ar-Condicionado da Sala", "ar", 1, 22, "Frio", "Inverter Dual", 0),
                ("SALA", "Som Ambiente Dolby", "som", 1, 50, "Spotify — Rock Clássico", "Subwoofer Ativo", 0),
                ("SALA", "Luzes do Teto da Sala", "luz", 1, 85, "Branco Quente", "Dimmer Inteligente", 0),
                ("SALA", "Porta Social de Entrada", "porta", 1, 1, "Trancada com Biometria", "Fechadura Digital", 1),
                ("SALA", "Câmera Interna da Sala", "camera", 1, 1, "Ao Vivo 1080p", "Ambiente interno normal · Sem alerta", 1),
                ("COZ", "Geladeira Smart Vision", "geladeira", 1, 3, "Super Refrigeração", "Filtro de água 98%", 0),
                ("COZ", "Ar-Condicionado da Cozinha", "ar", 1, 23, "Ventilar", "Anti-odor ativo", 0),
                ("COZ", "Iluminação de Bancada & Teto", "luz", 1, 100, "Branco Frio", "LED Econômico", 0),
                ("COZ", "Som Ambiente da Cozinha", "som", 0, 35, "Rádio Notícias / Podcast", "Bluetooth Pronto", 0),
                ("COZ", "Câmera da Cozinha", "camera", 1, 1, "Ao Vivo HD", "Fogão desligado · Ambiente seguro", 1),
                ("SUITE", "Ar-Condicionado da Suíte", "ar", 1, 20, "Sono Silencioso", "Timer Noturno", 0),
                ("SUITE", "Smart TV 65\" da Suíte", "tv", 0, 30, "HBO Max — Filmes", "Modo Cinema", 0),
                ("SUITE", "Som de Cabeceira", "som", 1, 25, "Som de Chuva & Relaxamento", "Timer 60 min", 0),
                ("SUITE", "Luz Indireta da Suíte", "luz", 1, 40, "Luz Suave Noturna", "Conforto Visual", 0),
                ("SUITE", "Porta Privativa da Suíte", "porta", 1, 1, "Trancada pelo Morador", "Acesso Exclusivo", 1),
                ("QUARTO2", "Smart TV & Console Hóspedes", "tv", 1, 55, "PlayStation 6 / HDMI 1", "120Hz Modo Jogo", 0),
                ("QUARTO2", "Ar-Condicionado Hóspedes", "ar", 0, 24, "Eco", "Economia de Energia", 0),
                ("QUARTO2", "Luz Principal & Fita LED", "luz", 1, 90, "Azul Ambiente", "Sincronizado com TV", 0),
                ("QUARTO2", "Caixa de Som Bluetooth", "som", 0, 40, "Lo-Fi Chill Beats", "Pareado", 0),
                ("EXTERNA", "Câmera 01 — Portão da Rua", "camera", 1, 1, "Visão Noturna 4K", "Calçada livre · Gravação contínua", 1),
                ("EXTERNA", "Câmera 02 — Garagem", "camera", 1, 1, "Detector de Movimento IA", "Veículo estacionado · Portão fechado", 1),
                ("EXTERNA", "Câmera 03 — Quintal & Muro", "camera", 1, 1, "Infravermelho Perímetro", "Sensores de muro normais · Sem intrusão", 1),
                ("EXTERNA", "Portão Eletrônico da Garagem", "porta", 1, 1, "Trancado com Travas Duplas", "Motor Rápido", 1),
                ("EXTERNA", "Porta Lateral de Serviço", "porta", 1, 1, "Trancada", "Sensor Magnético Ativo", 1),
                ("EXTERNA", "Refletores LED da Fachada", "luz", 1, 100, "Automático por Presença", "Fotocélula Ativa", 0),
            ]
            cursor.executemany(
                "INSERT INTO dispositivos "
                "(comodo_codigo, nome, categoria, ligado, valor_num, modo_atual, detalhe_extra, restrito_admin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                dispositivos,
            )

        if cursor.execute("SELECT COUNT(*) FROM itens_geladeira").fetchone()[0] == 0:
            itens = [
                ("Leite Integral", 3, "caixas", "Laticínios", "Fresco · Validade OK"),
                ("Refrigerante Zero Lata", 6, "latas", "Bebidas", "Gelado (3°C)"),
                ("Água Mineral com Gás", 4, "garrafas", "Bebidas", "Gelado (3°C)"),
                ("Peito de Frango / Filé", 2, "bandejas", "Carnes & Proteínas", "Conservado"),
                ("Morangos & Uvas Lavadas", 2, "potes", "Frutas & Verduras", "Fresco"),
                ("Queijo Mussarela Fatiado", 1, "pacote", "Laticínios", "Aberto há 2 dias"),
                ("Suco Natural de Laranja", 2, "garrafas", "Bebidas", "Pronto para consumo"),
            ]
            cursor.executemany(
                "INSERT INTO itens_geladeira (nome_item, quantidade, unidade, categoria_item, validade_status) "
                "VALUES (?, ?, ?, ?, ?)",
                itens,
            )
        conn.commit()

    def autenticar(self, username: str, senha: str) -> Optional[Dict[str, object]]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT id, username, nome_exibicao, senha_hash, perfil FROM usuarios WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if row and check_password_hash(row["senha_hash"], senha):
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "nome_exibicao": row["nome_exibicao"],
                    "perfil": row["perfil"],
                }
        return None

    def autenticar_perfil_demo(self, username: str) -> Optional[Dict[str, object]]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT id, username, nome_exibicao, perfil FROM usuarios WHERE username = ?",
                (username.strip(),),
            ).fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "nome_exibicao": row["nome_exibicao"],
                    "perfil": row["perfil"],
                }
        return None

    def listar_comodos(self) -> List[Dict[str, object]]:
        with self._conectar() as conn:
            rows = conn.execute("SELECT codigo, nome, descricao, ordem FROM comodos ORDER BY ordem").fetchall()
            return [dict(r) for r in rows]

    def listar_dispositivos(self, comodo_codigo: Optional[str] = None) -> List[DispositivoCasa]:
        with self._conectar() as conn:
            if comodo_codigo:
                rows = conn.execute(
                    "SELECT id, comodo_codigo, nome, categoria, ligado, valor_num, modo_atual, detalhe_extra, restrito_admin "
                    "FROM dispositivos WHERE comodo_codigo = ? ORDER BY id",
                    (comodo_codigo,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, comodo_codigo, nome, categoria, ligado, valor_num, modo_atual, detalhe_extra, restrito_admin "
                    "FROM dispositivos ORDER BY id"
                ).fetchall()
            return [instanciar_dispositivo(dict(r)) for r in rows]

    def listar_por_categoria(self, categoria: str) -> List[DispositivoCasa]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT id, comodo_codigo, nome, categoria, ligado, valor_num, modo_atual, detalhe_extra, restrito_admin "
                "FROM dispositivos WHERE categoria = ? ORDER BY id",
                (categoria,),
            ).fetchall()
            return [instanciar_dispositivo(dict(r)) for r in rows]

    def buscar_dispositivo(self, id_disp: int) -> Optional[DispositivoCasa]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT id, comodo_codigo, nome, categoria, ligado, valor_num, modo_atual, detalhe_extra, restrito_admin "
                "FROM dispositivos WHERE id = ?",
                (id_disp,),
            ).fetchone()
            return instanciar_dispositivo(dict(row)) if row else None

    def atualizar_dispositivo(
        self,
        id_disp: int,
        ligado: bool,
        valor_num: float,
        modo_atual: str,
    ) -> None:
        with self._conectar() as conn:
            conn.execute(
                "UPDATE dispositivos SET ligado = ?, valor_num = ?, modo_atual = ? WHERE id = ?",
                (1 if ligado else 0, valor_num, modo_atual, id_disp),
            )
            conn.commit()

    def listar_itens_geladeira(self) -> List[Dict[str, object]]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT id, nome_item, quantidade, unidade, categoria_item, validade_status "
                "FROM itens_geladeira ORDER BY categoria_item, nome_item"
            ).fetchall()
            return [dict(r) for r in rows]

    def adicionar_item_geladeira(
        self,
        nome_item: str,
        quantidade: int,
        unidade: str,
        categoria_item: str,
    ) -> None:
        with self._conectar() as conn:
            conn.execute(
                "INSERT INTO itens_geladeira (nome_item, quantidade, unidade, categoria_item, validade_status) "
                "VALUES (?, ?, ?, ?, 'Fresco · Adicionado agora')",
                (nome_item, quantidade, unidade, categoria_item),
            )
            conn.commit()

    def alterar_quantidade_geladeira(self, id_item: int, delta: int) -> None:
        with self._conectar() as conn:
            row = conn.execute("SELECT quantidade FROM itens_geladeira WHERE id = ?", (id_item,)).fetchone()
            if not row:
                return
            nova_qtd = int(row["quantidade"]) + delta
            if nova_qtd <= 0:
                conn.execute("DELETE FROM itens_geladeira WHERE id = ?", (id_item,))
            else:
                conn.execute("UPDATE itens_geladeira SET quantidade = ? WHERE id = ?", (nova_qtd, id_item))
            conn.commit()

    def registrar_log(self, usuario: str, perfil: str, acao: str) -> None:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with self._conectar() as conn:
            conn.execute(
                "INSERT INTO historico_eventos (data_hora, usuario, perfil, acao) VALUES (?, ?, ?, ?)",
                (agora, usuario, perfil, acao),
            )
            conn.commit()

    def listar_logs(self, limite: int = 12) -> List[Dict[str, object]]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT id, data_hora, usuario, perfil, acao FROM historico_eventos ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
            return [dict(r) for r in rows]


BancoNavBot = BancoSmartHome
