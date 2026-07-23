# Análise arquitetural — Configurações

Pedido do usuário (2026-07-23): fechar as três funcionalidades "Pendentes" do
dashboard de projeto (Alertas, Relatórios, Configurações), começando pela
mais rápida de implementar. Configurações não tinha NENHUM código ainda
(0% real, apesar do rótulo "10%" no tracker) — nem página no frontend, nem
endpoint de perfil no backend. Esta entrega cobre a primeira fatia: **Perfil**
(editar nome/e-mail, trocar senha). Preferências, Notificações e Temas
personalizáveis chegam em entregas seguintes.

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

## 5. Não incluído nesta entrega

Preferências (moeda, formato de data, dia de início do mês — este último
exigiria revisar toda lógica de "mês" da Central Financeira, hoje sempre
calendário civil), Notificações (toggle por `TipoAlerta` — depende do
backend de Alertas, ainda não implementado) e Temas personalizáveis (mais
paletas além do claro/escuro atual). Cada uma ganha sua própria entrega,
citada em `dashboard/project-status.json`.
