$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

Write-Host "=== WORKFLOW FETCH ==="
$wf = cmd /c curl -s "http://localhost:8000/api/v1/workflow/fetch" -H "$auth"
Write-Host $wf

Write-Host "`n=== TELEPHONY CONFIGS ==="
$tc = cmd /c curl -s "http://localhost:8000/api/v1/organizations/telephony-configs" -H "$auth"
Write-Host $tc

Write-Host "`n=== MODEL CONFIGS ==="
$mc = cmd /c curl -s "http://localhost:8000/api/v1/organizations/model-configurations/v2" -H "$auth"
Write-Host $mc

Write-Host "`n=== ORG CONTEXT ==="
$ctx = cmd /c curl -s "http://localhost:8000/api/v1/organizations/context" -H "$auth"
Write-Host $ctx
