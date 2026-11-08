from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Set
from werkzeug.security import check_password_hash, generate_password_hash
from navbot.modelos import MissaoRobo, instanciar_missao


def obter_caminho_banco() -> Path:
    if os.environ.get("VERCEL"):
        return Path("/tmp/robo2050.db")
    return Path(__file__).parent.parent / "robo2050.db"


class BancoNavBot:
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
                "CREATE TABLE IF NOT EXISTS comodos_grafo ("
                "codigo TEXT PRIMARY KEY, "
                "nome TEXT NOT NULL, "
                "pos_x INTEGER NOT NULL, "
                "pos_y INTEGER NOT NULL, "
                "bloqueado INTEGER NOT NULL DEFAULT 0, "
                "restrito_admin INTEGER NOT NULL DEFAULT 0)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS estado_robo ("
                "id INTEGER PRIMARY KEY CHECK (id = 1), "
                "nome_robo TEXT NOT NULL, "
                "no_atual TEXT NOT NULL, "
                "bateria_pct REAL NOT NULL, "
                "ultima_rota TEXT NOT NULL, "
                "distancia_acumulada_m REAL NOT NULL)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS missoes ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "titulo TEXT NOT NULL, "
                "tipo TEXT NOT NULL, "
                "origem TEXT NOT NULL, "
                "destino TEXT NOT NULL, "
                "prioridade INTEGER NOT NULL, "
                "carga_kg REAL NOT NULL DEFAULT 0.0, "
                "status TEXT NOT NULL DEFAULT 'pendente', "
                "rota_calculada TEXT NOT NULL DEFAULT '', "
                "distancia_metros REAL NOT NULL DEFAULT 0.0)"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS telemetria_logs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "data_hora TEXT NOT NULL, "
                "usuario TEXT NOT NULL, "
                "perfil TEXT NOT NULL, "
                "evento TEXT NOT NULL)"
            )
            conn.commit()
            self._popular_dados_iniciais(conn)

    def _popular_dados_iniciais(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        if cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            admin_user = os.environ.get("NAVBOT_ADMIN_USER", "admin")
            admin_pass = os.environ.get("NAVBOT_ADMIN_PASS", "1234")
            guest_user = os.environ.get("NAVBOT_GUEST_USER", "convidado")
            guest_pass = os.environ.get("NAVBOT_GUEST_PASS", "1234")
            usuarios = [
                (admin_user, "Engenheiro / Morador Admin", generate_password_hash(admin_pass), "administrador"),
                (guest_user, "Visitante / Morador Comum", generate_password_hash(guest_pass), "comum"),
            ]
            cursor.executemany(
                "INSERT INTO usuarios (username, nome_exibicao, senha_hash, perfil) VALUES (?, ?, ?, ?)",
                usuarios,
            )

        if cursor.execute("SELECT COUNT(*) FROM comodos_grafo").fetchone()[0] == 0:
            comodos = [
                ("BASE", "Base de Recarga Central", 380, 210, 0, 0),
                ("SALA", "Sala de Estar", 200, 120, 0, 0),
                ("COZ", "Cozinha Automatizada", 200, 300, 0, 0),
                ("Q1", "Suíte Principal", 560, 110, 0, 0),
                ("Q2", "Quarto de Hóspedes", 380, 70, 0, 0),
                ("LAB", "Servidor IA & Escritório", 600, 240, 0, 1),
                ("GAR", "Oficina & Garagem V2X", 450, 340, 0, 1),
                ("JAR", "Jardim & Domo Solar", 80, 210, 0, 0),
            ]
            cursor.executemany(
                "INSERT INTO comodos_grafo (codigo, nome, pos_x, pos_y, bloqueado, restrito_admin) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                comodos,
            )

        if cursor.execute("SELECT COUNT(*) FROM estado_robo").fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO estado_robo (id, nome_robo, no_atual, bateria_pct, ultima_rota, distancia_acumulada_m) "
                "VALUES (1, 'Unidade Autônoma R-2050', 'BASE', 94.0, 'BASE -> SALA -> COZ', 28.5)"
            )

        if cursor.execute("SELECT COUNT(*) FROM missoes").fetchone()[0] == 0:
            missoes = [
                ("Levar bandeja de café para Hóspedes", "entrega", "COZ", "Q2", 3, 2.5, "pendente", "", 0.0),
                ("Higienização UV na Sala de Estar", "limpeza", "BASE", "SALA", 2, 0.0, "pendente", "", 0.0),
                ("Inspeção de Sensores no Servidor IA", "patrulha", "BASE", "LAB", 5, 0.0, "pendente", "", 0.0),
            ]
            cursor.executemany(
                "INSERT INTO missoes "
                "(titulo, tipo, origem, destino, prioridade, carga_kg, status, rota_calculada, distancia_metros) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                missoes,
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

    def listar_comodos(self) -> List[Dict[str, object]]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT codigo, nome, pos_x, pos_y, bloqueado, restrito_admin FROM comodos_grafo ORDER BY codigo"
            ).fetchall()
            return [dict(r) for r in rows]

    def buscar_comodo(self, codigo: str) -> Optional[Dict[str, object]]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT codigo, nome, pos_x, pos_y, bloqueado, restrito_admin FROM comodos_grafo WHERE codigo = ?",
                (codigo,),
            ).fetchone()
            return dict(row) if row else None

    def obter_conjunto_bloqueados(self) -> Set[str]:
        with self._conectar() as conn:
            rows = conn.execute("SELECT codigo FROM comodos_grafo WHERE bloqueado = 1").fetchall()
            return {str(r["codigo"]) for r in rows}

    def alternar_bloqueio_comodo(self, codigo: str) -> bool:
        with self._conectar() as conn:
            row = conn.execute("SELECT bloqueado FROM comodos_grafo WHERE codigo = ?", (codigo,)).fetchone()
            if not row:
                return False
            novo = 0 if row["bloqueado"] else 1
            conn.execute("UPDATE comodos_grafo SET bloqueado = ? WHERE codigo = ?", (novo, codigo))
            conn.commit()
            return bool(novo)

    def obter_estado_robo(self) -> Dict[str, object]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT nome_robo, no_atual, bateria_pct, ultima_rota, distancia_acumulada_m FROM estado_robo WHERE id = 1"
            ).fetchone()
            return dict(row)

    def atualizar_estado_robo(
        self,
        no_atual: str,
        bateria_pct: float,
        ultima_rota: str,
        distancia_adicional: float,
    ) -> None:
        with self._conectar() as conn:
            conn.execute(
                "UPDATE estado_robo SET no_atual = ?, bateria_pct = ?, ultima_rota = ?, "
                "distancia_acumulada_m = ROUND(distancia_acumulada_m + ?, 2) WHERE id = 1",
                (no_atual, round(max(0.0, min(100.0, bateria_pct)), 1), ultima_rota, distancia_adicional),
            )
            conn.commit()

    def listar_missoes(self) -> List[MissaoRobo]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT id, titulo, tipo, origem, destino, prioridade, carga_kg, status, rota_calculada, distancia_metros "
                "FROM missoes ORDER BY prioridade DESC, id DESC"
            ).fetchall()
            return [instanciar_missao(dict(r)) for r in rows]

    def buscar_missao(self, id_missao: int) -> Optional[MissaoRobo]:
        with self._conectar() as conn:
            row = conn.execute(
                "SELECT id, titulo, tipo, origem, destino, prioridade, carga_kg, status, rota_calculada, distancia_metros "
                "FROM missoes WHERE id = ?",
                (id_missao,),
            ).fetchone()
            return instanciar_missao(dict(row)) if row else None

    def cadastrar_missao(
        self,
        titulo: str,
        tipo: str,
        origem: str,
        destino: str,
        prioridade: int,
        carga_kg: float,
    ) -> int:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO missoes (titulo, tipo, origem, destino, prioridade, carga_kg, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pendente')",
                (titulo, tipo, origem, destino, prioridade, carga_kg),
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def concluir_missao(self, id_missao: int, rota_str: str, distancia: float) -> None:
        with self._conectar() as conn:
            conn.execute(
                "UPDATE missoes SET status = 'concluida', rota_calculada = ?, distancia_metros = ? WHERE id = ?",
                (rota_str, distancia, id_missao),
            )
            conn.commit()

    def excluir_missao(self, id_missao: int) -> None:
        with self._conectar() as conn:
            conn.execute("DELETE FROM missoes WHERE id = ?", (id_missao,))
            conn.commit()

    def registrar_log(self, usuario: str, perfil: str, evento: str) -> None:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with self._conectar() as conn:
            conn.execute(
                "INSERT INTO telemetria_logs (data_hora, usuario, perfil, evento) VALUES (?, ?, ?, ?)",
                (agora, usuario, perfil, evento),
            )
            conn.commit()

    def listar_logs(self, limite: int = 12) -> List[Dict[str, object]]:
        with self._conectar() as conn:
            rows = conn.execute(
                "SELECT id, data_hora, usuario, perfil, evento FROM telemetria_logs ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
            return [dict(r) for r in rows]
