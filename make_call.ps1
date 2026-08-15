$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== INITIATING CALL ==="
$result = cmd /c curl -s -X POST http://localhost:8000/api/v1/telephony/initiate-call -H Content-Type:application/json -H "$auth" -d @C:\Users\USER\call.json
Write-Host $result
