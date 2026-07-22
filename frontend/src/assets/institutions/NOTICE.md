# Logos de instituições financeiras — proveniência

Estes 15 arquivos SVG foram copiados do repositório
[`rzmt/logos-bancos-br`](https://github.com/rzmt/logos-bancos-br) (licença MIT do código;
os logos em si **não** são cobertos pela licença MIT — ver `DISCLAIMER.md` do repositório).

Cada logo é a arte oficial publicada pela própria instituição no
[diretório público de participantes do Open Finance Brasil](https://data.directory.openbankingbrasil.org.br/participants)
(cadastro regulado pelo Banco Central, criado exatamente para permitir que terceiros
identifiquem visualmente as instituições). Uso nominativo: só para identificar visualmente a
instituição em `InstitutionBadge`/`CartaoVisual`/listas de Conta e Cartão — nunca para sugerir
parceria, patrocínio ou endosso.

Projeto de uso pessoal, nunca publicado — mesmo raciocínio já registrado em
`CartaoVisual.tsx`/`lib/bandeiras.ts` sobre reproduzir marca real de forma descritiva.

**Modificação local**: `c6.svg` teve sua única cor de preenchimento trocada de `#242424`
(quase preto) para branco (`#FFFFFF`) — o traço original não tem nenhuma forma de fundo (é só o
texto "C6" sobre transparência), o que ficava ilegível sobre o tema escuro do app depois que os
selos deixaram de ter uma caixa branca sólida atrás (pedido do usuário). Mesmo critério aplicado a
`VisaLogo` em `components/ui/brandLogos.tsx` (variante branca do wordmark). Nenhum outro arquivo
foi alterado.

## Arquivos e origem (ISPB, fonte, hash no momento da cópia)

- `bb.svg` — Banco do Brasil S.A. (ISPB 00000000) — https://www.bb.com.br/docs/pub/inst/img/LogoBB.svg — sha256 `8bd7640e0e08e49c…`
- `santander.svg` — Banco Santander (Brasil) S.A. (ISPB 90400888) — https://cms.santander.com.br/sites/WPS/imagem/santander_chama/23-10-31_194829_P_santander_chama.svg — sha256 `3db65acca8651f09…`
- `bradesco.svg` — Banco Bradesco S.A. (ISPB 60746948) — https://banco.bradesco/open-finance/logo/icones_vetorial-pf.svg — sha256 `eab31731175c5229…`
- `inter.svg` — Banco Inter S.A. (ISPB 00416968) — https://marketing.bancointer.com.br/arquivos/images/app-icon.svg — sha256 `09b8e88439fd0106…`
- `caixa.svg` — Caixa Econômica Federal (ISPB 00360305) — https://consentimento.openbanking.caixa.gov.br/assets/images/logomarca_caixa.svg — sha256 `3073827b49f87a32…`
- `neon.svg` — Neon Pagamentos S.A. (ISPB 20855875) — https://opbk-brasil.s3.sa-east-1.amazonaws.com/neon/logo.svg — sha256 `6fcb82100b54c355…`
- `picpay.svg` — PicPay Instituição de Pagamento S.A. (ISPB 22896431) — https://picpay.s3.sa-east-1.amazonaws.com/openbanking/picpay-logo-icon-pf.svg — sha256 `5dda49002fc6d9b3…`
- `xp.svg` — Banco XP S.A. (ISPB 33264668) — https://openbanking-redirect.xpi.com.br/assets/xpi.svg — sha256 `7f75762e82f828eb…`
- `btg.svg` — Banco BTG Pactual S.A. (ISPB 30306294) — https://banking-public-prd.s3.sa-east-1.amazonaws.com/open-finance/logo/btginvestimentos/btginvestimentos.svg — sha256 `ac521163417436f9…`
- `c6.svg` — Banco C6 S.A. (ISPB 31872495) — https://cdn.c6bank.com.br/open-banking/c6bank-logo.svg — sha256 `deb2fd2d220ad110…`
- `nubank.svg` — Nu Pagamentos S.A. (ISPB 18236120) — https://nuapp.nubank.com.br/open-banking/logo.svg — sha256 `a4a63bd7d76bd7f3…`
- `mercadopago.svg` — Mercado Pago Instituição de Pagamento Ltda. (ISPB 10573521) — https://http2.mlstatic.com/open-banking/assets/logo.svg — sha256 `a1dbab9a3efb581b…`
- `sicredi.svg` — Banco Cooperativo Sicredi S.A. (ISPB 01181521) — https://www.sicredi.com.br/openbanking/app/assets/images/shared/logo/logo_sicredi_512.svg — sha256 `046e1c6e7cd6c285…`
- `sicoob.svg` — Banco Cooperativo Sicoob S.A. (ISPB 02038232) — https://sicoob-openbanking.s3.sa-east-1.amazonaws.com/icone-sicoob.svg — sha256 `8d4b418f1c75262a…`
- `itau.svg` — Itaú Unibanco S.A. (ISPB 60701190) — https://www.itau.com.br/media/dam/m/4ee2c952e1fa91a2/original/Novo_itau.svg — sha256 `9b2cadfb4ec44d8a…`

Wise e PayPal continuam sem logo real (instituições internacionais, fora do escopo do
Open Finance Brasil) — `InstitutionBadge` cai no monograma de sempre para as duas.

## Agibank, Stone, BRB (2026-07-22) — PNG, não SVG

Mesma fonte (`rzmt/logos-bancos-br`, versão atualizada com 152 logos/470 instituições),
mas capturados de um jeito diferente dos 15 acima: as ferramentas de busca web
disponíveis nesta sessão só conseguem extrair texto de página, nunca bytes
binários/vetoriais brutos — toda tentativa de baixar o SVG original (do repositório ou
direto do domínio oficial de cada instituição) voltou vazia. Contornado navegando até a
URL do logo oficial via o navegador Chrome do usuário (mesmo domínio de origem de cada
instituição, nunca um agregador), tirando um screenshot e recortando a área do logo —
resultado é PNG (raster), não SVG (vetor), mas o componente (`InstitutionBadge`, via
`object-contain`) trata os dois formatos da mesma forma.

- `agibank.png` — Agibank S.A. (ISPB 10664513) — fonte:
  https://agibank.com.br/logo.svg (capturado via navegador, recortado, fundo removido)
- `stone.png` — Stone Pagamentos S.A. (ISPB 16501555) — fonte:
  https://public-assets.stone.com.br/openfinance/stone-logo.svg (idem)
- `brb.png` — BRB - Banco de Brasília S.A. (ISPB 00000208) — fonte:
  https://novo.brb.com.br/wp-content/uploads/2025/07/brb-preto-1.svg (idem). O arquivo
  original é a versão "preto" (traço preto sobre transparente) — mesmo problema já
  documentado para `c6.svg` acima (ilegível no tema escuro do app sem fundo sólido
  atrás). Cores invertidas (preto → branco) durante o recorte, mesmo critério já usado
  para o C6.
- `pagbank.png` — PagSeguro Internet Instituição de Pagamento S.A. / PagBank (ISPB
  08561701) — fonte: https://openfinance.api.pagseguro.uol.com.br/img/logo_pagbank.svg
  (capturado via navegador, recortado, fundo removido). Pedido do usuário (2026-07-22),
  faltava na lista.

Nenhuma proveniência por SHA-256 aqui (diferente dos 15 acima, que vieram do arquivo
original bit-a-bit) — o processo de screenshot+recorte não preserva hash do arquivo
fonte. Se uma versão vetorial ficar disponível no futuro (nova ferramenta, ou o próprio
usuário baixando manualmente), trocar por SVG segue sendo preferível.

Correção/remoção: ver processo de "Remoção de marca" no repositório de origem.
