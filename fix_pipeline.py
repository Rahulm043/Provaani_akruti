"""Fix run_pipeline.py for base image compatibility."""

import re

path = "/app/api/services/pipecat/run_pipeline.py"
with open(path) as f:
    content = f.read()

# Remove the bad sed import we added earlier (if any)
content = content.replace(
    "from api.services.pipecat.event_handlers import (\n    TranscriptLogCoordinator as EventTranscriptLogCoordinator,\n",
    "from api.services.pipecat.event_handlers import (",
)

# Fix 1: Import TranscriptLogCoordinator
if (
    "from api.services.pipecat.transcript_log_coordinator import TranscriptLogCoordinator"
    not in content
):
    # Add import after the existing event_handlers import line
    content = content.replace(
        "from api.services.pipecat.event_handlers import (",
        "from api.services.pipecat.transcript_log_coordinator import TranscriptLogCoordinator\nfrom api.services.pipecat.event_handlers import (",
    )

# Fix 2: Add transcript_log_coordinator to register_event_handlers call
old = """    in_memory_audio_buffer = register_event_handlers(
        task,
        transport,
        workflow_run_id,
        engine=engine,
        audio_buffer=audio_buffer,
        in_memory_logs_buffer=in_memory_logs_buffer,
        pipeline_metrics_aggregator=pipeline_metrics_aggregator,"""

new = """    transcript_log_coordinator = TranscriptLogCoordinator(workflow_run_id=workflow_run_id)
    in_memory_audio_buffer = register_event_handlers(
        task,
        transport,
        workflow_run_id,
        engine=engine,
        audio_buffer=audio_buffer,
        in_memory_logs_buffer=in_memory_logs_buffer,
        transcript_log_coordinator=transcript_log_coordinator,
        pipeline_metrics_aggregator=pipeline_metrics_aggregator,"""

# Fix: remove any previous java/TempFile leftovers
content = content.replace(
    "    import tempfile\n    transcript_log_coordinator = EventTranscriptLogCoordinator.__new__(EventTranscriptLogCoordinator)\n    in_memory_audio_buffer",
    "    transcript_log_coordinator = TranscriptLogCoordinator(workflow_run_id=workflow_run_id)\n    in_memory_audio_buffer",
)

if old in content:
    content = content.replace(old, new)
    print("Fixed register_event_handlers call")
else:
    # Try with slightly different indentation
    print("Pattern not found in register_event_handlers call")

with open(path, "w") as f:
    f.write(content)
print("Done")
