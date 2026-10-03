import json
import subprocess

def main():
    wf_config = {
        "model_configuration_v2_override": {
            "version": 2,
            "mode": "byok",
            "byok": {
                "mode": "realtime",
                "realtime": {
                    "realtime": {
                        "provider": "google_realtime",
                        "model": "models/gemini-3.8-live",
                        "voice": "Aoede",
                        "language": "bn",
                        "api_key": ["GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"]
                    },
                    "llm": {
                        "provider": "openai",
                        "model": "gpt-oss-120b",
                        "base_url": "https://api.cerebras.ai/v1",
                        "api_key": ["CEREBRAS_API_KEY_PLACEHOLDER"]
                    }
                }
            }
        },
        "dictionary": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan, whatsapp",
        "max_call_duration": 600,
        "max_user_idle_timeout": 30,
        "user_turn_stop_timeout": 0.8
    }

    config_json_str = json.dumps(wf_config)
    sql_escaped = config_json_str.replace("'", "''")
    sql = f"""UPDATE workflow_definitions SET workflow_configurations = '{sql_escaped}'::json WHERE workflow_id = 2;
SELECT id, workflow_id, workflow_configurations->'model_configuration_v2_override'->'byok'->'realtime'->'realtime'->>'model' AS model, workflow_configurations->'model_configuration_v2_override'->'byok'->'realtime'->'realtime'->>'voice' AS voice FROM workflow_definitions WHERE workflow_id = 2;
"""

    full_cmd = [
        "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
        "-o", "StrictHostKeyChecking=no",
        "rahul@34.131.238.156",
        "sudo docker exec -i provaani_akruti-postgres-1 psql -U postgres -d postgres"
    ]
    res = subprocess.run(full_cmd, input=sql, capture_output=True, text=True, errors="replace")
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)

if __name__ == "__main__":
    main()
