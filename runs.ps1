$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== LAST 3 RUNS ==="
$runs = cmd /c curl -s "http://localhost:8000/api/v1/workflow/1/runs" -H "$auth"
Write-Host $runs
