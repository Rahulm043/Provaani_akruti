$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$tokenObj = $login | ConvertFrom-Json
$token = $tokenObj.token
Write-Host "Token: $token"

$json = cmd /c curl -s http://localhost:8000/api/v1/openapi.json
$spec = $json | ConvertFrom-Json
$paths = $spec.paths.PSObject.Properties | ForEach-Object { $_.Name }
Write-Host "`n=== ALL ENDPOINTS ==="
$paths | ForEach-Object { Write-Host $_ }
