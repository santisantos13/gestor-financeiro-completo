<#
  Inicia o backend (uvicorn, sem --reload) e o frontend (build de producao
  servido por `vite preview`) em segundo plano, sem nenhuma janela de
  terminal visivel. Cada processo grava seu PID num arquivo (.backend.pid /
  .frontend.pid) para o parar.ps1 conseguir encerra-los depois.

  IMPORTANTE: este script serve o ULTIMO build gerado por `npm run build`
  dentro de frontend/ - ele NAO le o codigo-fonte ao vivo (diferente de
  `npm run dev`). Sempre que o codigo do frontend mudar, rode de novo:

      cd frontend
      npm run build

  antes de reiniciar (ou simplesmente rode parar.ps1 seguido de iniciar.ps1
  depois de gerar o novo build).
#>

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Backend -------------------------------------------------------------
$uvicornExe = Join-Path $raiz "backend\.venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicornExe)) {
    Write-Host "ERRO: nao encontrei $uvicornExe - o ambiente virtual do backend existe?"
    exit 1
}

$backend = Start-Process -FilePath $uvicornExe `
    -ArgumentList "app.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory (Join-Path $raiz "backend") `
    -WindowStyle Hidden -PassThru
$backend.Id | Out-File (Join-Path $raiz ".backend.pid")

# --- Frontend (build de producao, nao o servidor de desenvolvimento) -----
$viteExe = Join-Path $raiz "frontend\node_modules\.bin\vite.cmd"
if (-not (Test-Path $viteExe)) {
    Write-Host "ERRO: nao encontrei $viteExe - rode 'npm install' dentro de frontend/ primeiro."
    exit 1
}
$distDir = Join-Path $raiz "frontend\dist"
if (-not (Test-Path $distDir)) {
    Write-Host "AVISO: frontend/dist nao existe ainda - rode 'npm run build' dentro de frontend/ antes."
}

$frontend = Start-Process -FilePath $viteExe `
    -ArgumentList "preview --port 5173 --strictPort" `
    -WorkingDirectory (Join-Path $raiz "frontend") `
    -WindowStyle Hidden -PassThru
$frontend.Id | Out-File (Join-Path $raiz ".frontend.pid")

Write-Host "Financas Pessoais iniciado."
Write-Host "  Backend:  http://localhost:8000 (PID $($backend.Id))"
Write-Host "  Frontend: http://localhost:5173 (PID $($frontend.Id))"
Write-Host ""
Write-Host "Abra http://localhost:5173 no navegador. Para parar, rode parar.ps1."
