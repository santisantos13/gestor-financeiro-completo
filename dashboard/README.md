# Painel do Projeto — Finanças Pessoais

Página interna para acompanhar o progresso real do desenvolvimento. Não faz parte do app (`backend/`, `frontend/`) — é uma ferramenta separada, só para consulta.

## Como abrir

O painel precisa ser servido por um servidor HTTP local (não funciona com duplo clique direto no `index.html`, por restrição de segurança dos navegadores ao ler arquivos locais via `fetch`).

**Opção mais simples (Windows):** dê duplo clique em `start-dashboard.bat`. Ele abre `http://localhost:8642` no navegador automaticamente.

**Alternativa manual**, a partir desta pasta:

```
python -m http.server 8642
```

e acesse `http://localhost:8642`.

## Como atualizar os dados

Edite **apenas** `project-status.json`. Nunca é necessário editar `index.html`, `style.css` ou `app.js` para refletir o progresso — eles só leem o JSON.

O painel recarrega os dados automaticamente a cada 30 segundos enquanto estiver aberto. Basta salvar o JSON e a página se atualiza sozinha (não precisa dar F5).

### Estrutura do `project-status.json`

| Campo | O que é |
|---|---|
| `project` | Nome, status geral, `overallPercent` (0-100) e `updatedAt` (ISO 8601) |
| `areas[]` | Cards de progresso por área (`key`, `label`, `percent`, `done`, `inProgress`, `pending`) |
| `roadmap[]` | Fases do projeto (`status`: `done` \| `in-progress` \| `pending`, `items[]`) |
| `features[]` | Linhas da tabela de funcionalidades (`status`: `done` \| `in-progress` \| `pending` \| `blocked`, `progress` 0-100, `priority`: `Alta` \| `Média` \| `Baixa`) |
| `kanban` | Objeto com `backlog`, `in-development`, `review`, `done` — cada um é uma lista de tarefas (`title`, `description`, `category`, `priority`, `date`) |
| `changelog[]` | Histórico, mais recente primeiro (`date` ISO ou `dateLabel` quando a data exata não é conhecida, `type`, `title`) |
| `architecture` | Camadas do sistema e tecnologias por camada |
| `quality` | Indicadores: cobertura de testes, débitos técnicos, proporção de funcionalidades prontas, % de documentação, % de segurança |

Qualquer editor de texto serve para editar o JSON — é só um arquivo de dados.

## Por que essa arquitetura

- **Sem build step**: HTML + CSS + JS puros, sem dependências, sem npm install. Abre em segundos.
- **Fonte de dados separada**: `project-status.json` é a única coisa editada no dia a dia.
- **Visual alinhado ao design system do produto** (`docs/design-system.md`): mesma paleta escura e tokens, para manter consistência entre o app e a ferramenta que o acompanha.
