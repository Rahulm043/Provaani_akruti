$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== TELEPHONY CONFIG ==="
$tc = cmd /c curl -s "http://localhost:8000/api/v1/organizations/telephony-configs" -H "$auth"
$tc | ConvertFrom-Json | ConvertTo-Json -Depth 3
