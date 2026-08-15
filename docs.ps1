$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== API DOCS ==="
$docs = cmd /c curl -s http://localhost:8000/openapi.json
Write-Host $docs | powershell -c "$input | ConvertFrom-Json | ConvertTo-Json -Depth 1"
