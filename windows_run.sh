# Open two PowerShell windows to run messagesapp and client
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\adi\adintproject; .\messagesapp.exe"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\adi\adintproject; .\client.exe"
