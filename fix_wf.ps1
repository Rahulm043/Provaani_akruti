$login = cmd /c curl -s -X POST http://localhost:8000/api/v1/auth/login -H Content-Type:application/json -d @C:\Users\USER\login.json
$token = ($login | ConvertFrom-Json).token
$auth = "Authorization:Bearer $token"

# Get current version
$ver = cmd /c curl -s "http://localhost:8000/api/v1/workflow/fetch/1" -H "$auth"
$current = $ver | ConvertFrom-Json

# Get the workflow definition
$def = $current.workflow_definition

# Remove node 1 (Greeting as startCall) and make node 2 the start node
# Update node 2 prompt to include greeting at the beginning
$node2 = $def.nodes | Where-Object {$_.id -eq '2'}
$node2.data.is_start = $true
$node2.data.delayed_start = $false

# Prepend greeting to node 2's prompt
$greeting = "## First Turn (Opening)\nStart the conversation with: \"Namaskar, ami Riya bolchhi. Provani AI theke calling korchhi. Aapni ki ektu kotha bolte parben?\" Wait for them to respond before saying anything else.\n\n"
$node2.data.prompt = $greeting + $node2.data.prompt

# Remove greeting node and its edge
$def.nodes = @($def.nodes | Where-Object {$_.id -ne '1'})
$def.edges = @($def.edges | Where-Object {$_.source -ne '1' -and $_.target -ne '1'})

# Update start node reference
$def.start_node_id = '2'

# Create new version
$updateBody = @{
    name = $current.name
    description = "Fixed - merged greeting into main conversation"
    workflow_definition = $def
} | ConvertTo-Json -Depth 10 -Compress

$updateBody | Out-File C:\Users\USER\update_wf.json -Encoding UTF8
Write-Host "Updated workflow written to update_wf.json"
