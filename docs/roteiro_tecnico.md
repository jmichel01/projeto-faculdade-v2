# Roteiro Técnico de Apresentação — Central da Casa Inteligente 2050

## 1. Visão Geral da Arquitetura
O sistema implementa uma **Central de Controle de Casa Inteligente (Smart Home 2050)** dividida em 5 módulos Python desacoplados:
- `navbot/modelos.py`: Hierarquia de classes POO representando os dispositivos residenciais.
- `navbot/estruturas.py`: Estruturas clássicas de dados em memória (`PilhaComandos` LIFO e `FilaAutomacao` FIFO).
- `navbot/validadores.py`: Validação defensiva contra tipos inválidos e limites operacionais.
- `navbot/banco.py`: Persistência relacional em SQLite3 com 5 tabelas.
- `navbot/app.py`: Controlador web Flask com controle de sessão e autorização por perfil.

## 2. Demonstração Prática para a Banca
1. **Autenticação e Controle de Acesso (RBAC):**
   - Entrar como `convidado` e tentar destrancar uma porta ou alterar uma câmera de segurança -> o sistema bloqueia a operação e grava o alerta na tabela `historico_eventos`.
   - Entrar como `admin` -> controle total liberado.
2. **Comandos Gerais via Fila FIFO (`FilaAutomacao`):**
   - Clicar em **"Colocar Todos em 20°C"** -> o sistema enfileira todos os aparelhos da categoria `ar` na `FilaAutomacao`, desenfileira um a um aplicando `20°C` e registra cada estado anterior na `PilhaComandos`.
3. **Desfazer Alteração via Pilha LIFO (`PilhaComandos`):**
   - Clicar em **"Desfazer Última Ação"** -> desempilha o último estado salvo no topo da pilha e restaura o dispositivo no SQLite.
4. **Controle por Cômodo e Geladeira Inteligente:**
   - Navegar entre `Sala`, `Cozinha`, `Suíte`, `Quarto de Hóspedes` e `Segurança & Garagem`.
   - Na `Cozinha`, demonstrar o controle de estoque interno da Geladeira Inteligente e a validação de entrada numérica.
