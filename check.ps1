$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== WORKFLOWS ==="
$wf = cmd /c curl -s http://localhost:8000/api/v1/workflows -H "$auth"
Write-Host $wf

Write-Host "`n=== TELEPHONY CONFIGS ==="
$tc = cmd /c curl -s http://localhost:8000/api/v1/telephony/configurations -H "$auth"
Write-Host $tc

Write-Host "`n=== MODELS ==="
$ml = cmd /c curl -s http://localhost:8000/api/v1/models -H "$auth"
Write-Host $ml
