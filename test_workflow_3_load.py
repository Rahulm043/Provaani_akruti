import asyncio
from api.database import get_db_context
from api.services.workflow.service import WorkflowService

async def test():
    async with get_db_context() as db:
        wf = await WorkflowService.get_workflow_with_definition(db, workflow_id=3)
        print("WORKFLOW_3_LOAD_SUCCESS:")
        print("  Name:", wf.name)
        print("  Status:", wf.status)
        print("  Definition ID:", wf.released_definition_id)
        print("  Realtime Provider:", wf.workflow_configurations.get("model_configuration_v2_override", {}).get("byok", {}).get("realtime", {}).get("realtime", {}).get("provider"))
        print("  Realtime Model:", wf.workflow_configurations.get("model_configuration_v2_override", {}).get("byok", {}).get("realtime", {}).get("realtime", {}).get("model"))

if __name__ == "__main__":
    asyncio.run(test())
