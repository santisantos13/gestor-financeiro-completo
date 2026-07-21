@echo off
REM Wrapper para permitir dar duplo clique: arquivos .ps1 nao executam com
REM duplo clique no Windows por padrao (abrem no Bloco de Notas por seguranca).
REM -ExecutionPolicy Bypass so vale para esta execucao, nao muda nenhuma
REM configuracao permanente do sistema.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
pause
