@echo off
REM Inicia um servidor local para o painel (necessario para o fetch() do
REM project-status.json funcionar — abrir o index.html direto com duplo
REM clique nao funciona por restricao de seguranca do navegador).
cd /d "%~dp0"
echo Iniciando painel em http://localhost:8642 ...
start "" http://localhost:8642
python -m http.server 8642
