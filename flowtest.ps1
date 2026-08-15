$login = cmd /c curl -s -X POST http://localhost:3011/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== CREATING SESSION ==="
$session = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/1/text-chat/sessions" -H Content-Type:application/json -H "$auth" -d '{}'
$session | ConvertFrom-Json -Depth 2 | ConvertTo-Json -Depth 2
$runId = ($session | ConvertFrom-Json).workflow_run_id
Write-Host "`nRun ID: $runId"

Write-Host "`n=== SENDING MESSAGE ==="
$reply = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/1/text-chat/sessions/$runId/messages" -H Content-Type:application/json -H "$auth" -d @C:\Users\USER\msg.json
$reply | ConvertFrom-Json -Depth 3 | ConvertTo-Json -Depth 3
