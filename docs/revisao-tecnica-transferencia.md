# Revisão técnica — CRUD de Transferência

Revisão crítica da implementação entregue, mesmo formato das revisões anteriores: pontos
priorizados, sem filtro de cortesia. **Status: fechada.** Diferente das entidades
anteriores, esta implementação começou com uma decisão arquitetural explícita do usuário
que reverteu a instrução inicial do pedido — registrada aqui porque muda o resto da
análise.

## A decisão que define toda a implementação

O pedido original especificava: "a transferência deve gerar automaticamente duas
Transações vinculadas". Isso conflita diretamente com uma decisão já registrada no
docstring de `Transferencia` desde antes desta etapa: "fica FORA de Transacao de
propósito... se fosse modelada como duas Transacoes, relatórios de 'quanto eu gastei no
mês' ficariam inflados/errados". Gerar as duas Transacoes também quebraria, silenciosamente,
o cálculo de `saldo_atual` (`saldo_inicial + Σ(Transacao paga) + Σ(Transferencia líquida)`
— duas somas hoje independentes; gerar Transacao a partir de Transferencia faria o mesmo
movimento ser contado duas vezes).

Apresentei o conflito antes de escrever qualquer código. O usuário decidiu manter a
modelagem original: **Transferencia continua fora de Transacao, nenhuma Transacao é gerada,
nenhum dado é duplicado.** O restante desta revisão avalia a implementação sob essa
decisão, não sob o pedido original — as regras de negócio pedidas (mesma posse, origem
distinta de destino, atomicidade, sem edição estrutural, cancelamento que preserva
histórico) continuam todas atendidas, só que pelo mecanismo já estabelecido no projeto em
vez de gerar duplicatas em Transacao.

## Resumo

Segue `Router → Service → Repository`. Única mudança de modelagem: `Transferencia.ativo`
(soft delete, mesmo padrão de `Conta`/`Cartão`/`Tag`), que é o que torna "cancelar"
possível sem apagar a linha. `ContaRepository.somar_transferencias` passou a filtrar
`ativo=True` — é a única mudança fora do módulo novo de Transferência em si; nada em
`ContaService`, `TransacaoService`, `ParcelamentoService` ou qualquer outro Service
precisou mudar, confirmando que a premissa "toda movimentação financeira passa por
Transação" nunca esteve codificada em nenhum lugar além de Conta (que já tratava
Transacao e Transferencia como duas fontes paralelas desde a primeira versão). 431 testes
passam no total (17 unitários novos de `TransferenciaService`, 20 de integração novos,
mais os 394 pré-existentes).

## Atomicidade: resolvida pela própria decisão de modelagem, não por código novo

O pedido original pedia "nunca permitir que apenas um dos lados seja criado (operação
atômica)" — um requisito genuíno SE a estratégia fosse duas Transacoes. Como a estratégia
final é uma única linha (`Transferencia`), a atomicidade vem de graça da Unit of Work já
existente (`app/db/session.py`): um único `INSERT`, com `commit()` só no fim do request e
`rollback()` em qualquer exceção. Nenhum tratamento especial foi necessário. Testado
explicitamente (`test_criar_transferencia_invalida_nao_deixa_nenhum_registro_orfao`): uma
tentativa de criação rejeitada (conta de outro usuário) não deixa nenhuma linha na tabela
nem altera saldo de nenhuma conta.

## Cancelamento: mesma regra já adotada no projeto, não uma nova

O pedido explicitamente pediu para reaproveitar "a regra já adotada no projeto" para
desfazer efeitos financeiros preservando histórico. A regra já adotada é dupla: soft
delete (`ativo`, usado por Conta/Categoria/Tag/Cartão) para preservar a linha, e "saldo
nunca é armazenado, sempre calculado" (usado por Conta desde o primeiro CRUD) para o
efeito financeiro desaparecer automaticamente na próxima leitura, sem nenhum ajuste
manual de valor. `TransferenciaService.cancelar()` só marca `ativo=False` — não recalcula,
não ajusta saldo, não toca em nenhuma outra tabela; o "desfazer" acontece porque
`somar_transferencias` para de contar a linha, não porque alguém subtraiu manualmente o
valor de volta. Testado de ponta a ponta via HTTP
(`test_cancelar_transferencia_desfaz_o_saldo_das_duas_contas`): saldo das duas contas volta
exatamente ao valor anterior à transferência, e a linha continua visível via
`GET /transferencias/{id}` com `ativo=false`.

## Migração: sem drift, ciclo completo validado

`alembic upgrade head` → `downgrade -1` → `upgrade head` executado limpo num banco
descartável. `alembic revision --autogenerate` rodado contra o schema pós-migração não
detectou nenhuma diferença — modelo e migração em sincronia exata. A coluna `ativo` foi
adicionada com `server_default=sa.true()` (não só o `default` do Python) — mesmo cuidado já
usado na migração de `tags.ativo`: sem isso, adicionar uma coluna `NOT NULL` a uma tabela
que já tivesse linhas falharia (SQLite não erra nesse caso especificamente, mas o padrão
correto para bancos que erram foi seguido de qualquer forma, por consistência).

## Validação cruzada: mesmo padrão de Cartão, aplicado duas vezes

`TransferenciaService._validar_conta_do_usuario_ativa()` é chamado uma vez para
`conta_origem_id` e uma vez para `conta_destino_id` — mesma função, sem duplicar lógica
entre os dois casos. Mesma resposta 404 uniforme para "conta não existe" e "conta é de
outro usuário" (anti-enumeração, mesmo padrão de todo o projeto). Conta inativa é
rejeitada com 422 antes de qualquer escrita — não dá para abrir uma transferência
envolvendo uma conta que o usuário já desativou.

## O que foi deliberadamente NÃO alterado

`ContaService.desativar()` não verifica se a conta está envolvida em uma transferência
ativa antes de desativar — mesma lacuna já documentada e aceita para Cartão ("avaliar
bloqueio de desativação de Cartão com fatura em aberto", `docs/revisao-tecnica-cartao.md`).
Desativar uma conta não bloqueia NOVAS transferências envolvendo-a (isso já é impedido pela
validação de `ativo` em `criar()`), mas não reverte transferências passadas — comportamento
consistente com o resto do sistema (desativar uma Conta/Cartão nunca apaga ou invalida
histórico já lançado).

## Conclusão

A implementação atende integralmente as regras de negócio pedidas (mesma posse, contas
distintas, atomicidade, imutabilidade estrutural, cancelamento que preserva histórico),
mas por um caminho diferente do pedido originalmente: em vez de gerar duas Transacoes,
reaproveita a modelagem independente que já existia para Transferencia, evitando duplicar
dado financeiro e quebrar relatórios/cálculos que dependem de Transacao representar
estritamente receita ou despesa. Essa mudança de rota foi decidida explicitamente pelo
usuário antes de qualquer código ser escrito, não uma reinterpretação unilateral. Nenhum
problema de arquitetura, consistência, segurança ou regra de negócio foi encontrado nesta
revisão além do conflito já resolvido na decisão de modelagem.
