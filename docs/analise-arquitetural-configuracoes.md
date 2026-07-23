# Análise arquitetural — Configurações

Pedido do usuário (2026-07-23): fechar as três funcionalidades "Pendentes" do
dashboard de projeto (Alertas, Relatórios, Configurações), começando pela
mais rápida de implementar. Configurações não tinha NENHUM código ainda
(0% real, apesar do rótulo "10%" no tracker) — nem página no frontend, nem
endpoint de perfil no backend. Duas fatias entregues até agora: **Perfil**
(editar nome/e-mail, trocar senha) e **Preferências** (formato de data,
tema). Notificações e Temas personalizáveis (mais paletas) chegam em
entregas seguintes — ver seção 6.

## 1. Onde a página vive

`UserMenu.tsx` já documentava, desde a etapa de Organização da Sidebar, ser
a "âncora deliberada" para crescimento futuro de personalização (tema,
densidade de tabela, cor de acento). Isso não significa que TODA
configuração deve virar um item de dropdown: editar nome/e-mail e trocar
senha exigem formulário com validação e feedback de erro por campo — uma
UX que não cabe bem num popover efêmero (fecha ao clicar fora, sem espaço
para mensagens de erro longas). Por isso: `/configuracoes` é uma página de
verdade (mesmo padrão de rota lazy do resto do app), acessada por um item
novo "Configurações" dentro do `UserMenu` (não pela `Sidebar` — mesmo
tratamento de `/novidades`, que também não está em `NAV_ITEMS`: é uma
página "sobre o app/usuário", não uma entidade financeira). O `ThemeToggle`
("Aparência") continua exatamente onde estava, sem duplicar lógica —
quando a aba "Temas" for implementada, ela reaproveita o mesmo
`ThemeContext`, só expondo mais opções no mesmo lugar.

## 2. Backend: dois endpoints novos em `/auth`, não uma entidade `Usuario` CRUD

`PATCH /auth/me` e `POST /auth/trocar-senha` foram adicionados a
`app/api/routes/auth.py` (não a um router `usuarios.py` novo) porque ambos
operam exclusivamente sobre o usuário JÁ AUTENTICADO (`CurrentUser`, nunca
um `usuario_id` de path) — mesma característica de `GET /auth/me`, que já
existia. Um CRUD genérico de Usuário (listar/editar QUALQUER usuário) está
fora de escopo: não existe um segundo papel (`TipoPapel` só tem `USER` hoje)
que justificasse um admin gerenciando outras contas.

`PerfilUpdate` (nome/email, ambos opcionais via `exclude_unset`) e
`TrocarSenhaRequest` (senha_atual/senha_nova) são schemas separados —
misturar os dois exigiria decidir o que fazer quando só um dos dois grupos
de campos vem preenchido, e trocar senha tem uma regra que perfil não tem
(exigir a senha atual). `AuthService.atualizar_perfil()` reaproveita a mesma
checagem de e-mail duplicado já usada em `registrar()` (`ConflictError`,
409) — exceto quando o e-mail novo é igual ao atual (reenviar o próprio
e-mail não deveria colidir consigo mesmo).
`AuthService.trocar_senha()` reaproveita `security.verificar_senha()` /
`security.hash_senha()`, os mesmos dois pontos de baixo nível já usados por
login/registro — nenhuma lógica de criptografia nova. Trocar a senha NÃO
revoga sessões existentes (decisão deliberada): esse já é um botão separado
("Sair de todos os dispositivos", `logout_todas`), e forçar os dois juntos
surpreenderia quem só queria atualizar a senha.

## 3. Frontend: dois formulários independentes, um só cache atualizado otimisticamente

A página tem dois cards/dois `useForm` (Perfil e Senha), não um formulário
único — ver comentário no topo de `ConfiguracoesPage.tsx`. `AuthContext`
ganhou `atualizarPerfil`/`trocarSenha`: a mutation de perfil usa
`queryClient.setQueryData(queryKeys.auth.me, usuarioAtualizado)` em vez de
só invalidar — o `Header`/`UserMenu` (que já leem `usuario` do mesmo
`meQuery`) refletem nome/e-mail novos no mesmo instante, sem esperar um
refetch de rede.

Nenhum dos dois erros de negócio (409 e-mail duplicado, 401 senha atual
incorreta) chega como erro 422 de validação por campo (`getFieldErrors`
espera o formato de lista do FastAPI) — os dois são strings simples. Cada
formulário mapeia manualmente esse erro para o campo relevante
(`email`/`senha_atual`) via `form.setError(..., { type: "server" })`, além
do toast padrão — mesma UX de erro de campo que qualquer 422 já teria.

## 4. Testes

`test_auth_service.py` (unitário, `FakeUsuarioRepository` ganhou `update()`)
e `test_auth_flow.py` (integração, `TestClient` real) cobrem: troca de
nome/e-mail, e-mail já usado por outro usuário, e-mail igual ao próprio
(não deve conflitar), troca de senha com senha atual certa/errada, e que a
senha antiga para de funcionar após a troca. `ConfiguracoesPage.test.tsx`
(frontend, Vitest) cobre o pré-preenchimento assíncrono do formulário (nasce
vazio, é preenchido só depois de `usuario` resolver — testes usam
`findByDisplayValue`, não `findByLabelText`, porque o campo já existe no DOM
antes do preenchimento acontecer), salvar perfil com sucesso, o erro 409
mapeado pro campo, confirmação de senha divergente bloqueando o submit sem
chamar a API, troca de senha com sucesso (limpa os campos) e o erro 401
mapeado pro campo `senha_atual`.

## 5. Preferências: formato de data, moeda deliberadamente FORA

Segunda fatia (mesmo dia). Escopo pedido ao usuário incluía moeda, formato
de data, tema e "dia de início do mês" — os dois últimos já tinham sido
excluídos antes de começar (tema já existia via `ThemeToggle`/`UserMenu`;
"dia de início do mês" exigiria revisar toda lógica de "mês" da Central
Financeira, hoje sempre calendário civil). Perguntado especificamente sobre
moeda, o usuário escolheu deixá-la FORA também: um seletor de símbolo
(R$/US$/€) não converteria nenhum valor de verdade — só trocaria a
formatação de exibição, o número continuaria idêntico. Isso arrisca dar a
falsa impressão de que o saldo virou outra moeda de verdade, um risco real
demais para uma preferência cosmética num app financeiro. Resultado:
**moeda continua fixa em R$**, sem seletor algum.

"Formato de data" (DD/MM/AAAA, AAAA-MM-DD, MM/DD/AAAA) foi implementado.
Mecanismo: `lib/preferencesStore.ts` é uma ponte não-React (mesmo padrão de
`api/tokenStore.ts`) — `utils/date.ts` é chamado como função utilitária pura
por dezenas de componentes fora de qualquer árvore React, então não pode
`useContext`. `PreferenciasContext` (novo, ao lado de `ThemeContext` em
`App.tsx`) é o único escritor; `formatDate`/`formatDateTime` passaram a
montar a string manualmente a partir dos componentes dia/mês/ano (em vez de
um `Intl.DateTimeFormat` fixo em pt-BR), respeitando a preferência atual.

Diferente do tema (que reaplica instantaneamente via atributo `data-theme`
no `<html>`), mudar o formato de data exigiria que TODO consumidor de
`formatDate` reagisse a um contexto — refactor bem maior que o escopo desta
etapa. Solução mais simples, deliberada: `setFormatoData` grava a
preferência (store + localStorage) e chama `window.location.reload()` —
toda chamada futura de `formatDate` (já remontada do zero) usa o valor
novo, sem precisar de reatividade fina espalhada pelo app. Componente novo
`DateFormatToggle` (mesma mecânica visual de `ThemeToggle`, indicador que
desliza) mostra a data de HOJE já formatada em cada opção, em vez de um
rótulo genérico "Brasileiro"/"Americano" - elimina qualquer ambiguidade
sobre o que cada opção produz.

Testes: `utils/date.test.ts` (novo, unitário puro) prova os 3 formatos +
o fallback para ISO malformado. `ConfiguracoesPage.test.tsx` ganhou um
teste de renderização (3 opções, DD/MM/AAAA ativo por padrão) — sem clicar
de verdade, já que isso dispararia o reload real fora do escopo do teste.

## 6. Não incluído nesta entrega

Notificações (toggle por `TipoAlerta` — depende do backend de Alertas,
ainda não implementado) e Temas personalizáveis (mais paletas além do
claro/escuro atual). Cada uma ganha sua própria entrega, citada em
`dashboard/project-status.json`.
