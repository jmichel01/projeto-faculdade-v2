# 🤖 NavBot 2050 — Explicação do Projeto para o Grupo

**Curso:** Ciência da Computação — 4º Semestre (Categoria INTELLIGENCE — ExpoTech 2026.2)  
**Tema:** Simulador de Navegação em Grafo (Pathfinding Dijkstra) e Missões de um Robô Doméstico para a Smart Home 2050  
**Tecnologias:** Python + Flask + SQLite + Algoritmo de Dijkstra + POO + Fila de Prioridade + Pilha LIFO  
**Link Online (Vercel):** https://navbot-2050.vercel.app

---

## 1. Qual é a Ideia do Projeto?

Em vez de fazermos um painel simples de ligar e desligar lâmpadas (que quase todos os grupos vão fazer), criamos o **sistema de navegação e controle de um robô doméstico autônomo (Unidade R-2050)** que opera dentro da casa do futuro.

A planta da casa é modelada como um **Grafo Ponderado**, onde:
- **Os Nós (Vértices)** são os 8 ambientes da residência (`BASE`, `SALA`, `COZ`, `Q1`, `Q2`, `LAB`, `GAR`, `JAR`).
- **As Arestas** são os corredores que ligam os cômodos, cada um com sua **distância real em metros** (`3.5m`, `4.0m`, `5.5m`, etc.).

Quando o morador pede para o robô realizar uma tarefa (levar um item da Cozinha até o Quarto de Hóspedes, fazer limpeza UV na Sala ou inspecionar sensores no Servidor), o sistema roda o **Algoritmo de Dijkstra** em Python para descobrir o **menor caminho possível**, desviando automaticamente de cômodos que estejam **bloqueados/interditados**!

---

## 2. O que o Site Faz na Prática?

1. **Mapa Visual Interativo da Planta em Grafo (SVG Animado):**
   - Mostra todos os cômodos, as conexões em metros, a posição atual do robô e destaca em **azul elétrico tracejado** a última rota calculada pelo algoritmo de Dijkstra, animando o deslocamento do robô pelos nós.
2. **Simulação de Obstáculos / Interdição de Cômodos em Tempo Real:**
   - O Administrador pode clicar em **"Bloquear"** em qualquer cômodo (ex.: interditar a `SALA` porque está em limpeza). Se você mandar o robô ir para um local que antes passava pela Sala, o algoritmo de **Dijkstra recalcula na hora uma rota alternativa** pelos outros cômodos!
3. **Fila de Prioridade de Missões:**
   - As missões cadastradas entram numa **Fila Ordenada por Prioridade (P5 até P1)**. Ao clicar em *"Executar Próxima da Fila"*, o robô atende primeiro a missão mais urgente, calcula o menor caminho e desconta a bateria.
4. **Pilha LIFO para Desfazer Rota / Retornar Passo:**
   - Cada movimento do robô é salvo em uma **Pilha (LIFO)**. O botão *"↩ Desfazer Rota (Pilha LIFO)"* desempilha o último deslocamento e faz o robô voltar imediatamente ao cômodo anterior.
5. **Programação Orientada a Objetos (Polimorfismo Real):**
   - Temos a classe base `MissaoRobo` e 4 subclasses (`MissaoEntrega`, `MissaoLimpeza`, `MissaoPatrulha`, `MissaoEmergencia`). Cada classe calcula o gasto de bateria de um jeito diferente (considerando peso da carga em kg, uso de lâmpada UV, etc.).
6. **Dois Perfis de Usuário no Login (`admin` vs `convidado`):**
   - **Administrador (`admin` / `1234`):** Controle total. Pode bloquear/liberar cômodos no grafo, enviar o robô para áreas restritas (`LAB - Servidor IA` e `GAR - Oficina`), criar missões de patrulha/emergência e excluir registros.
   - **Visitante / Usuário Comum (`convidado` / `1234`):** Acesso limitado. Pode enviar o robô apenas para áreas sociais (`SALA`, `COZ`, `Q2`, `JAR`). Se tentar mandar o robô para o `LAB` ou `GAR`, ou tentar bloquear um cômodo no mapa, o sistema barra a ação na hora e grava tentativa de violação no log!

---

## 3. Como Utilizar e Testar o Site (Passo a Passo)

### Passo 1 — Fazer Login
- Abra o site e clique no botão rápido **"Perfil Administrador (`admin` / `1234`)"** (ou digite manualmente).

### Passo 2 — Testar o Algoritmo de Dijkstra no Mapa
- Na coluna da direita (*"Controle de Nós & Obstáculos"*), clique em **"Ir (Dijkstra)"** no cômodo **Q2 (Quarto de Hóspedes)** ou **JAR (Jardim)**.
- Veja o mapa no centro iluminar o caminho mais curto e o marcador azul do robô se mover pelos cômodos!

### Passo 3 — Testar Desvio de Obstáculos (O Ponto Alto da Apresentação!)
1. Clique em **"Bloquear"** no cômodo **SALA** (ele ficará vermelho no mapa do grafo).
2. Agora mande o robô ir para o **JAR (Jardim)**.
3. Observe como o algoritmo de **Dijkstra** desvia automaticamente da Sala bloqueada e encontra o caminho alternativo passando pela Cozinha (`BASE -> COZ -> JAR`)!

### Passo 4 — Testar a Fila de Prioridade e a Pilha LIFO
- Na seção **"Fila de Prioridade de Missões"**, clique em **"Enfileirar Pendentes"** e depois em **"Executar Próxima da Fila"**: o robô executará primeiro a missão de Prioridade P5.
- No topo do mapa, clique em **"↩ Desfazer Rota (Pilha LIFO)"** para ver o robô voltar ao estado anterior usando a estrutura de Pilha.

### Passo 5 — Testar o Bloqueio do Perfil Visitante e a Validação de Dados
- Clique em **"Trocar Conta"** no canto superior direito e entre como **"Perfil Visitante (`convidado` / `1234`)"**.
- Tente clicar em **"Ir (Dijkstra)"** para o cômodo **LAB (Servidor IA)**: o site bloqueará o acesso exibindo o alerta vermelho de segurança!
- No formulário de **"Nova Missão"**, tente digitar letras (`abc`) no campo **Peso da Carga (kg)** para ver a validação de dados impedindo o erro.

---

## 4. Como Rodar Localmente no PC

```bash
pip install -r requirements.txt
python run.py
```
Depois acesse: **http://127.0.0.1:8000**
