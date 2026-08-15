$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== Create Text Chat Session ==="
$chatSession = cmd /c curl -s -X POST "http://localhost:8000/api/v1/workflow/1/text-chat/sessions" -H "$auth" -H Content-Type:application/json -d '{}'
Write-Host $chatSession

Write-Host "`n=== Workflow Status ==="
$wf = cmd /c curl -s "http://localhost:8000/api/v1/workflow/1/status" -H "$auth"
Write-Host $wf

Write-Host "`n=== Workflow Versions ==="
$ver = cmd /c curl -s "http://localhost:8000/api/v1/workflow/1/versions" -H "$auth"
Write-Host $ver

Write-Host "`n=== User Defaults ==="
$defaults = cmd /c curl -s "http://localhost:8000/api/v1/user/configurations/defaults" -H "$auth"
Write-Host $defaults
