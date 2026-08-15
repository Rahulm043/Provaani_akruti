"""Restore the Akruti TTS config (def 36) to the previous provider.

Restores the TTS block backed up by patch_akruti_rumik.py
(/tmp/akruti_tts_backup.json), which preserves the original provider, model,
voice, language, and api_key exactly. Use this as the fallback if Rumik needs
to be reverted.

Run on the VM from /root/dograh_test:

    python patch_akruti_tts_smallest.py

No restart needed.
"""

import json
import subprocess

BACKUP = "/tmp/akruti_tts_backup.json"

DB = [
    "sudo",
    "docker",
    "exec",
    "dograh_test-postgres-1",
    "psql",
    "-U",
    "postgres",
    "-d",
    "postgres",
    "-tA",
]

TTS_PATH = "{model_configuration_v2_override,byok,pipeline,tts}"


def psql(sql):
    res = subprocess.run(DB + ["-c", sql], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return res.stdout


def main():
    with open(BACKUP, encoding="utf-8") as fh:
        backup = json.load(fh)
    print("restoring tts block from", BACKUP)
    print("backup:", json.dumps(backup, ensure_ascii=False))

    payload = json.dumps(backup, ensure_ascii=False).replace("'", "''")
    psql(
        "UPDATE workflow_definitions SET workflow_configurations = jsonb_set("
        "workflow_configurations::jsonb, "
        f"'{TTS_PATH}'::text[], '{payload}'::jsonb, true) "
        "WHERE id = 36 RETURNING id;"
    )

    verify = psql(
        "SELECT workflow_configurations->'model_configuration_v2_override'->'byok'"
        "->'pipeline'->'tts' FROM workflow_definitions WHERE id = 36;"
    ).strip()
    v = json.loads(verify)
    print("VERIFY tts:", json.dumps(v, ensure_ascii=False))
    if v != backup:
        raise SystemExit("verification FAILED - restored value does not match backup")
    print("OK: original tts config restored (no restart needed)")


if __name__ == "__main__":
    main()
