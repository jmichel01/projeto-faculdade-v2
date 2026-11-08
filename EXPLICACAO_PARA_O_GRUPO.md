# Central da Casa Inteligente 2050 — Resumo para o Grupo

**Link do site funcionando (Vercel):** https://navbot-2050.vercel.app  
**Repositório no GitHub:** https://github.com/jmichel01/projeto-faculdade-v2

---

## 1. Qual é a ideia do projeto e como se encaixa na ExpoTech?

Nosso projeto para a **Missão 2050 (Categoria INTELLIGENCE — 4º Semestre de Ciência da Computação)** é uma **Central de Controle da Casa Inteligente (Smart Home)**.

Pelo site, o morador entra na central da casa, escolhe o cômodo e controla todos os aparelhos daquele ambiente ou da casa inteira:
- **Por Cômodo (`Sala de Estar`, `Cozinha`, `Suíte Principal`, `Quarto de Hóspedes`, `Segurança & Garagem`):**
  - **Smart TV:** Ligar/desligar, escolher o canal ou aplicativo (`Netflix`, `YouTube`, `HBO Max`, `Globo`, `ESPN`, `PlayStation 6`) e ajustar o volume (`0% a 100%`).
  - **Ar-Condicionado:** Ligar/desligar, escolher a temperatura (`16°C a 28°C`) e o modo (`Frio`, `Eco`, `Sono Silencioso`, `Ventilar`).
  - **Geladeira Inteligente (na Cozinha):** Ver tudo o que tem dentro da geladeira (lista de alimentos e bebidas com quantidade, categoria e validade), retirar itens consumidos (`-1`), repor (`+1`), cadastrar novos produtos e ajustar a temperatura interna (`-2°C a 8°C`).
  - **Som Ambiente:** Ligar/desligar, escolher a playlist (`Spotify`, `Lo-Fi`, `Som de Chuva`, `Rádio`) e regular o volume.
  - **Iluminação:** Ligar/desligar, regular a intensidade do brilho (`0% a 100%`) e a cor/tonalidade da luz.
  - **Portas e Portão Eletrônico:** Trancar e destrancar fechaduras biométricas (exclusivo para o perfil **Administrador**).
  - **Câmeras de Segurança:** Acompanhar o status ao vivo das câmeras da rua, garagem, quintal, sala e cozinha.
- **Comandos Gerais da Casa (No topo do site):**
  - **Colocar todos os Ar-Condicionados em 20°C** (ou qualquer outra temperatura) de uma só vez.
  - **Apagar ou acender todas as lâmpadas** da casa com um clique.
  - **Trancar todas as portas e o portão** simultaneamente.
  - **Desfazer Última Ação** (volta o aparelho exatamente para o estado anterior).

---

## 2. Como usar o site

1. Abra o link https://navbot-2050.vercel.app
2. Na tela de login, clique em **"Entrar como Morador Principal (Admin)"** (acesso total, inclusive portas e câmeras) ou **"Entrar como Visitante / Convidado"** (pode mexer em TV, ar, som e luzes, mas é bloqueado nas fechaduras e câmeras).
3. Use a barra **"Comandos Gerais da Residência"** no topo para testar colocar todos os ar-condicionados em `20°C` ou apagar todas as luzes.
4. Clique nas abas dos cômodos (**Sala de Estar**, **Cozinha**, **Suíte Principal**, **Quarto de Hóspedes**, **Segurança & Garagem**) para controlar cada aparelho individualmente.
5. Clique na aba **Cozinha** para ver o **Interior da Geladeira Inteligente** e adicionar ou retirar alimentos.

---

## 3. Como cada disciplina do semestre foi aplicada no código

- **Programação Orientada a Objetos (`navbot/modelos.py`):**
  - Classe base `DispositivoCasa` com atributos privados (`_ligado`, `_valor_num`, `_modo_atual`) encapsulados com `@property`.
  - 7 subclasses com **Herança e Polimorfismo** (`ArCondicionado`, `SmartTV`, `GeladeiraSmart`, `SistemaSom`, `Iluminacao`, `FechaduraPorta`, `CameraSeguranca`), cada uma sobrescrevendo `consumo_watts()` e `resumo_estado()`.
- **Estruturas de Dados (`navbot/estruturas.py`):**
  - **Fila (`FilaAutomacao` — FIFO):** Processa em sequência os comandos gerais da casa (ex.: colocar todos os ar-condicionados em 20°C ou apagar todas as luzes).
  - **Pilha (`PilhaComandos` — LIFO):** Guarda o estado anterior de cada aparelho alterado para permitir o botão **"Desfazer Última Ação"**.
- **Banco de Dados Relacional (`navbot/banco.py`):**
  - Banco **SQLite** (`smarthome2050.db`) com 5 tabelas (`usuarios`, `comodos`, `dispositivos`, `itens_geladeira`, `historico_eventos`).
- **Segurança, Testes e Validação (`navbot/validadores.py` e `tests/test_navbot.py`):**
  - Senhas com hash criptográfico (`Werkzeug`), controle de acesso por perfil (`administrador` vs `comum`), validação que impede texto em campos numéricos de temperatura/volume/quantidade e testes automatizados com `pytest`.
