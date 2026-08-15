$login = cmd /c curl -s -X POST http://localhost:3011/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== CREATE SMALLWEBRTC RUN ==="
$result = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/1/runs" -H Content-Type:application/json -H "$auth" -d @C:\Users\USER\run_body.json
$result | ConvertFrom-Json | ConvertTo-Json -Depth 3
