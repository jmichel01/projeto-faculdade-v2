# Arquitetura e Diagramas UML — Smart Home 2050

Este documento apresenta o **Diagrama de Classes**, o **Diagrama de Sequência** e a **Modelagem do Banco de Dados (DER / SQLite3)** implementados no código do projeto.

---

## 1. Diagrama de Classes (UML)

Representa a hierarquia de Orientação a Objetos em `navbot/modelos.py`, as estruturas de dados em `navbot/estruturas.py` (`FilaAutomacao` e `PilhaComandos`) e a camada de persistência `BancoSmartHome` em `navbot/banco.py`.

```mermaid
classDiagram
    class DispositivoCasa {
        -int _id_disp
        -str _comodo_codigo
        -str _nome
        -str _categoria
        -bool _ligado
        -float _valor_num
        -str _modo_atual
        -str _detalhe_extra
        -bool _restrito_admin
        +id_disp() int
        +comodo_codigo() str
        +nome() str
        +categoria() str
        +ligado() bool
        +valor_num() float
        +modo_atual() str
        +detalhe_extra() str
        +restrito_admin() bool
        +consumo_watts() int
        +resumo_estado() str
    }

    class ArCondicionado {
        +consumo_watts() int
        +resumo_estado() str
    }

    class SmartTV {
        +consumo_watts() int
        +resumo_estado() str
    }

    class GeladeiraSmart {
        +consumo_watts() int
        +resumo_estado() str
    }

    class SistemaSom {
        +consumo_watts() int
        +resumo_estado() str
    }

    class Iluminacao {
        +consumo_watts() int
        +resumo_estado() str
    }

    class FechaduraPorta {
        +consumo_watts() int
        +resumo_estado() str
    }

    class CameraSeguranca {
        +consumo_watts() int
        +resumo_estado() str
    }

    DispositivoCasa <|-- ArCondicionado
    DispositivoCasa <|-- SmartTV
    DispositivoCasa <|-- GeladeiraSmart
    DispositivoCasa <|-- SistemaSom
    DispositivoCasa <|-- Iluminacao
    DispositivoCasa <|-- FechaduraPorta
    DispositivoCasa <|-- CameraSeguranca

    class FilaAutomacao {
        -List _fila
        +enfileirar(comando) void
        +desenfileirar() Any
        +esta_vazia() bool
        +tamanho() int
    }

    class PilhaComandos {
        -List _itens
        -int _capacidade
        +empilhar(estado_anterior) void
        +desempilhar() Dict
        +esta_vazia() bool
        +listar_historico() List
        +tamanho() int
    }

    class BancoSmartHome {
        +Path caminho_banco
        +inicializar_tabelas() void
        +autenticar(username, senha) Dict
        +autenticar_perfil_demo(username) Dict
        +listar_comodos() List
        +listar_dispositivos(comodo_codigo) List~DispositivoCasa~
        +listar_por_categoria(categoria) List~DispositivoCasa~
        +buscar_dispositivo(id_disp) DispositivoCasa
        +atualizar_dispositivo(id_disp, ligado, valor_num, modo_atual) void
        +listar_itens_geladeira() List
        +adicionar_item_geladeira(nome_item, quantidade, unidade, categoria_item) void
        +alterar_quantidade_geladeira(id_item, delta) void
        +registrar_log(usuario, perfil, acao) void
        +listar_logs(limite) List
    }

    BancoSmartHome ..> DispositivoCasa : instancia via instanciar_dispositivo()
```

---

## 2. Diagrama de Sequência (UML)

Representa o fluxo completo de execução quando o morador utiliza um comando no painel, passando pela validação (`navbot/validadores.py`), pela **Fila FIFO (`FilaAutomacao`)**, pela **Pilha LIFO (`PilhaComandos`)** e pela persistência no **SQLite (`BancoSmartHome`)**.

```mermaid
sequenceDiagram
    autonumber
    actor Morador as Morador (Navegador)
    participant Flask as Controlador Web (app.py)
    participant Val as Validador (validadores.py)
    participant Fila as FilaAutomacao (FIFO)
    participant Pilha as PilhaComandos (LIFO)
    participant DB as BancoSmartHome (SQLite)

    Morador->>Flask: POST /geral/ar (temperatura_geral = "20")
    Flask->>Val: validar_numero_inteiro("20", "Temperatura", 16, 28)
    Val-->>Flask: Retorna int(20)
    Flask->>DB: listar_por_categoria("ar")
    DB-->>Flask: Lista objetos ArCondicionado

    loop Para cada ArCondicionado da casa
        Flask->>Fila: enfileirar(ar, temp=20, ligado=True)
    end

    loop Enquanto Fila não está vazia (FIFO)
        Flask->>Fila: desenfileirar()
        Flask->>Pilha: empilhar(estado_antigo do aparelho)
        Flask->>DB: atualizar_dispositivo(id_disp, True, 20.0, "Frio")
    end

    Flask->>DB: registrar_log(usuario, perfil, "Sincronizou todos os Ar em 20°C")
    Flask-->>Morador: Renderiza Painel atualizado (HTTP 200)

    Note over Morador,DB: Fluxo de Reversão — Botão "Reverter Alteração (LIFO)"
    Morador->>Flask: POST /pilha/desfazer
    Flask->>Pilha: desempilhar()
    Pilha-->>Flask: Retorna último estado salvo no topo
    Flask->>DB: atualizar_dispositivo(id_disp, ligado_antigo, valor_antigo, modo_antigo)
    Flask->>DB: registrar_log(usuario, perfil, "DESFEZ AÇÃO (Pilha LIFO)")
    Flask-->>Morador: Restaura estado anterior na tela
```

---

## 3. Banco de Dados Relacional (DER — SQLite3)

O banco de dados `smarthome2050.db` é gerenciado pela classe `BancoSmartHome` (`navbot/banco.py`) e possui **5 tabelas relacionais**:

```mermaid
erDiagram
    COMODOS ||--o{ DISPOSITIVOS : "possui (comodo_codigo)"
    USUARIOS ||--o{ HISTORICO_EVENTOS : "registra (usuario)"

    USUARIOS {
        INTEGER id PK
        TEXT username UK
        TEXT nome_exibicao
        TEXT senha_hash
        TEXT perfil
    }

    COMODOS {
        TEXT codigo PK
        TEXT nome
        TEXT descricao
        INTEGER ordem
    }

    DISPOSITIVOS {
        INTEGER id PK
        TEXT comodo_codigo FK
        TEXT nome
        TEXT categoria
        INTEGER ligado
        REAL valor_num
        TEXT modo_atual
        TEXT detalhe_extra
        INTEGER restrito_admin
    }

    ITENS_GELADEIRA {
        INTEGER id PK
        TEXT nome_item
        INTEGER quantidade
        TEXT unidade
        TEXT categoria_item
        TEXT validade_status
    }

    HISTORICO_EVENTOS {
        INTEGER id PK
        TEXT data_hora
        TEXT usuario
        TEXT perfil
        TEXT acao
    }
```

### Estrutura DDL (SQL) das Tabelas no Código (`navbot/banco.py`):

```sql
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    nome_exibicao TEXT NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comodos (
    codigo TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL,
    ordem INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dispositivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comodo_codigo TEXT NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    ligado INTEGER NOT NULL DEFAULT 1,
    valor_num REAL NOT NULL DEFAULT 20.0,
    modo_atual TEXT NOT NULL DEFAULT '',
    detalhe_extra TEXT NOT NULL DEFAULT '',
    restrito_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS itens_geladeira (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_item TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    unidade TEXT NOT NULL,
    categoria_item TEXT NOT NULL,
    validade_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historico_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_hora TEXT NOT NULL,
    usuario TEXT NOT NULL,
    perfil TEXT NOT NULL,
    acao TEXT NOT NULL
);
```
