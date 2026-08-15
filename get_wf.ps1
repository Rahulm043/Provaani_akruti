$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

$wf = cmd /c curl -s "http://localhost:8000/api/v1/workflow/fetch/1" -H "$auth"
$wf | Out-File C:\Users\USER\wf.json -Encoding UTF8

$d = $wf | ConvertFrom-Json
$json = $d.workflow_definition | ConvertTo-Json -Depth 5
Set-Content C:\Users\USER\wf_pretty.json -Value $json -Encoding UTF8
