$login = cmd /c curl -s -X POST http://localhost:3011/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== CREATE SESSION ==="
$session = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/1/text-chat/sessions" -H Content-Type:application/json -H "$auth" -d '{}'
Write-Host $session

# Extract run_id
$runId = ($session | ConvertFrom-Json).workflow_run_id
Write-Host "`nRun ID: $runId"

Write-Host "`n=== SEND MESSAGE ==="
$msgBody = '{"text":"ami ekta real estate developer. apnar somporke aro janbo."}'
$reply = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/1/text-chat/sessions/$runId/messages" -H Content-Type:application/json -H "$auth" -d $msgBody
Write-Host $reply
