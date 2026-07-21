<#
  Encerra o backend (porta 8000) e o frontend (porta 5173).

  Antes so matava os PIDs salvos em .backend.pid/.frontend.pid por
  iniciar.ps1 - se esse arquivo estivesse desatualizado, ausente, ou o
  processo tivesse sido reiniciado/matado por fora (ex.: fechar o Windows,
  travar, etc.), o processo antigo continuava vivo e preso na porta, e
  iniciar.ps1 seguinte nao conseguia (ou nao devia) subir um novo processo
  no lugar dele - resultado pratico: o navegador continuava conversando
  com a versao antiga do backend/frontend mesmo depois de "reiniciar".

  Agora mata por PORTA (mais confiavel: sempre acerta quem estiver
  realmente ocupando 8000/5173, com ou sem PID salvo) e so usa os arquivos
  .pid como reforco/limpeza.
#>

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path

function Parar-Porta([int]$porta, [string]$nome) {
    $conexoes = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
    if (-not $conexoes) {
        Write-Host "$nome nao estava rodando (nada escutando na porta $porta)."
        return
    }
    $pids = $conexoes | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "$nome parado (PID $procId, porta $porta)."
    }
}

function Limpar-ArquivoPid([string]$arquivoPid) {
    $caminho = Join-Path $raiz $arquivoPid
    if (Test-Path $caminho) {
        Remove-Item $caminho -ErrorAction SilentlyContinue
    }
}

Parar-Porta 8000 "Backend"
Parar-Porta 5173 "Frontend"

Limpar-ArquivoPid ".backend.pid"
Limpar-ArquivoPid ".frontend.pid"
