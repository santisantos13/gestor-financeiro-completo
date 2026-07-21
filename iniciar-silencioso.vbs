' Dispara iniciar.ps1 sem NENHUMA janela visivel (nem o console do
' PowerShell aparece por um instante). Use este arquivo (em vez de
' iniciar.ps1 diretamente) para iniciar o app com um duplo-clique, ou
' coloque um atalho dele na pasta de Inicializacao do Windows
' (Win+R -> shell:startup) para o app subir sozinho a cada login.
Dim shell, pasta
Set shell = CreateObject("WScript.Shell")
pasta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & pasta & "\iniciar.ps1""", 0, False
