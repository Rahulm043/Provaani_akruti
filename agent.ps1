$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== Embed Init Endpoint ==="
$embed = cmd /c curl -s -X POST "http://localhost:8000/api/v1/public/embed/init" -H "$auth" -H Content-Type:application/json -d '{}'
Write-Host $embed

Write-Host "`n=== Agent Test Workflow ==="
$agent = cmd /c curl -s -X POST "http://localhost:8000/api/v1/public/agent/test/workflow/93ad7275-de0a-4c29-b893-ac5d93327aa4" -H "$auth" -H Content-Type:application/json
Write-Host $agent

Write-Host "`n=== Workflow Text Chat Sessions ==="
$chat = cmd /c curl -s -X POST "http://localhost:8000/api/v1/workflow/1/text-chat/sessions" -H "$auth" -H Content-Type:application/json
Write-Host $chat

Write-Host "`n=== Auth Me ==="
$me = cmd /c curl -s "http://localhost:8000/api/v1/auth/me" -H "$auth"
Write-Host $me
