$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
Write-Host "TOKEN: $token"
$result = cmd /c curl -s -X POST http://localhost:8000/api/v1/telephony/initiate-call -H Content-Type:application/json -H "Authorization:Bearer $token" -d @C:\Users\USER\call.json
Write-Host "RESULT: $result"
