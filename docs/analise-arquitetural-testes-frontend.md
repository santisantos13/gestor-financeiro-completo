# Análise arquitetural — Testes automatizados de frontend

Primeira suíte de testes do frontend (hoje zero — só o backend tem suíte automatizada,
1087 testes). Pedido do backlog (`t7`, prioridade Média): "ao menos o fluxo crítico:
autenticação, submissão de formulário, tabela".

## Stack: Vitest + Testing Library, não Jest

Vite já é o build tool do projeto — Vitest reaproveita a mesma configuração (resolve de
módulos, plugins, aliases) sem precisar de um segundo bundler/transformer (Jest exigiria
`babel-jest`/`ts-jest` reconfigurando do zero algo que o Vite já resolve). `@testing-library/react`
+ `@testing-library/user-event` (interação por evento real, não `fireEvent` cru) +
`@testing-library/jest-dom` (matchers de asserção tipo `toBeInTheDocument`) é o padrão de
facto para testar componentes React por comportamento (o que o usuário vê/faz), não
detalhe de implementação.

## Onde a config de teste vive: `test` dentro de `vite.config.ts`, não um arquivo à parte

Depois dos dois incidentes de produção desta sessão (`docs/versionamento.md` — injeção de
versão via `vite.config.ts` quebrando em produção), qualquer mudança em `vite.config.ts` é
tratada com cautela redobrada. O campo `test: {...}` do Vitest é **inerte para
`vite build`/`vite dev`** — só é lido pelo processo do Vitest (`vitest run`), nunca pelo
build de produção. Adicionar esse campo não tem o mesmo risco das mudanças anteriores
(que injetavam uma constante em tempo de build, executada em todo carregamento da
aplicação); ainda assim, o build de produção foi revalidado (`npm run build`) depois da
mudança, por precaução.

## `tsc -b` (usado por `npm run build`) nunca vê arquivos de teste

`tsconfig.json` (raiz, o que o `build` usa) ganhou `"exclude": ["src/**/*.test.ts",
"src/**/*.test.tsx", "src/test/**"]` — arquivos de teste są **excluídos do type-check de
produção**, mesmo raciocínio de isolamento já usado para `vite.config.ts`
(`tsconfig.node.json`, projeto composite à parte). Um erro de tipo num teste nunca pode
quebrar `npm run build`.

Para type-check/autocomplete de teste no editor, `tsconfig.vitest.json` (novo, estende o
`tsconfig.json` raiz, inclui os arquivos de teste, adiciona `"types": ["vitest/globals",
"@testing-library/jest-dom"]`) — **não é referenciado pelo `tsconfig.json` raiz** (ao
contrário de `tsconfig.node.json`), de propósito: se fosse, `tsc -b` tentaria
buildá-lo também, reabrindo o mesmo risco que acabamos de isolar.

## Sem globals do Vitest — import explícito em todo arquivo de teste

`test.globals` fica `false` (não `true`). Cada arquivo de teste importa
`describe`/`it`/`expect`/`vi` de `"vitest"` explicitamente, em vez de depender de globals
injetados. Motivo: `globals: true` exigiria adicionar `"types": ["vitest/globals"]` ao
`tsconfig.json` **raiz** (o que o build usa) para o editor não reclamar em todo arquivo de
produção que nunca importou nada de teste — import explícito evita tocar no tsconfig de
produção de novo.

## Mock de rede: mockar o módulo de serviço, não `fetch`/`httpClient`

Todo teste desta etapa mocka a camada de `services/*Service.ts` (`vi.mock(...)`), nunca
`fetch` global nem `httpClient.ts` diretamente. Motivo: `httpClient.ts` tem lógica própria
não-trivial (refresh automático em 401 com mutex, parse dual-format de erro do FastAPI)
que não faz parte do "fluxo crítico" pedido agora e exigiria simular objetos `Response`
inteiros; mockar o service isola exatamente a camada que o componente sob teste realmente
consome. Testar `httpClient.ts` em si (a lógica de refresh/401) é candidato a uma etapa
futura, fora do escopo desta.

## Escopo desta etapa (3 áreas, mínimo pedido)

1. **Autenticação**: `LoginPage` — validação Zod inline, submit chamando
   `AuthContext.login` (mockado via `authService`), erro de credencial exibido via
   `ErrorMessage`, navegação em sucesso.
2. **Formulário**: `TagFormDialog` (schema mais simples do projeto — `nome`/`cor`, sem
   `CategorySelect`/`IconPicker`/hierarquia) — validação, submit chamando
   `useCriarTag`/`useAtualizarTag` (mockado via `tagService`), erro 422 mapeado campo-a-campo.
3. **Tabela**: `DataTable` isolado — busca textual, ordenação de coluna, paginação
   client-side. Escolhido de propósito por não ter NENHUMA dependência de rede (`data` é
   uma prop estática) — o teste roda 100% em memória, sem mock nenhum.

`renderWithProviders` (novo, `src/test/renderWithProviders.tsx`) envolve
`QueryClientProvider` (client novo por teste, `retry: false` para não atrasar) +
`AuthProvider` + `ToastProvider` + `MemoryRouter` (`initialEntries` configurável) — o
mínimo de providers que os 3 alvos acima realmente precisam (confirmado por leitura direta
do código antes de escrever qualquer teste).

## Fora de escopo desta etapa

Cobertura de CI (`t8`, item separado do backlog), testes de outras entidades/formulários
além de Tag, testes de `httpClient.ts` em si, testes de e2e (Playwright/Cypress) —
nenhum desses foi pedido nesta etapa ("ao menos o fluxo crítico").
