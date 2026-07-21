@echo off
REM Wrapper para dar duplo clique. Rode parar.bat ANTES deste (na raiz do
REM projeto) para garantir que o backend nao esta com o banco aberto.
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0apagar_usuarios_teste.py"
pause
