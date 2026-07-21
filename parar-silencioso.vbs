' Dispara parar.ps1 sem NENHUMA janela visivel (nem o console do
' PowerShell aparece por um instante). Use este arquivo (em vez de
' parar.ps1 diretamente) para parar o app com um duplo-clique.
' Irmao de iniciar-silencioso.vbs - a mesma lacuna que ele resolve para
' iniciar.ps1 valia tambem para parar.ps1 (arquivos .ps1 nao rodam com
' duplo-clique no Windows por padrao, so abrem num editor de texto).
Dim shell, pasta
Set shell = CreateObject("WScript.Shell")
pasta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & pasta & "\parar.ps1""", 0, False
