$login = cmd /c curl -s -X POST http://localhost:3011/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token

$result = cmd /c curl -s -X POST "http://localhost:3011/api/v1/workflow/6/text-chat/sessions/6/messages" -H Content-Type:application/json -H "Authorization:Bearer $token" -d @C:\Users\USER\msg.json
$result | ConvertFrom-Json | ConvertTo-Json -Depth 5
