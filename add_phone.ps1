$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

$result = cmd /c curl -s -X POST "http://localhost:8000/api/v1/organizations/telephony-configs/2/phone-numbers" -H "Content-Type:application/json" -H "$auth" -d @C:\Users\USER\add_phone_body.json
Write-Host $result
