"""Flip the Akruti TTS config (def 36) to Rumik silk mulberry.

Backs up the current TTS block to /tmp/akruti_tts_backup.json before switching,
so patch_akruti_tts_smallest.py can restore it exactly (including the original
api_key, which is not stored in .env).

Run on the VM from /root/dograh_test:

    python patch_akruti_rumik.py

Requires RUMIK_API_KEY in ./.env (already added on the VM). No restart needed.
"""

import json
import os
import subprocess

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

RUMIK_TTS = {
    "provider": "rumik",
    "model": "mulberry",
    "description": (
        "a female 30s Hindi voice, smooth timbre, warm and reassuring, "
        "conversational pacing, natural casual register, like a friendly clinic receptionist"
    ),
    "voice": "",
    "language": "hi",
    "base_url": "https://silk-api.rumik.ai",
}


def load_env_key(path=".env", key="RUMIK_API_KEY"):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip().strip('"').strip("'")
    raise SystemExit(f"{key} not found in {path}")


def psql(sql):
    res = subprocess.run(DB + ["-c", sql], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return res.stdout


def main():
    api_key = load_env_key()
    if not api_key:
        raise SystemExit("RUMIK_API_KEY is empty in .env")
    if not api_key.startswith("rk_"):
        print(
            f"WARNING: RUMIK_API_KEY does not look like 'rk_...' (got {api_key[:4]}...)"
        )

    current = psql(
        "SELECT workflow_configurations->'model_configuration_v2_override'->'byok'"
        "->'pipeline'->'tts' FROM workflow_definitions WHERE id = 36;"
    ).strip()
    if not current or current == "":
        raise SystemExit("no tts block found on def 36")
    cur = json.loads(current)
    if cur.get("provider") == "rumik":
        raise SystemExit(
            f"def 36 already on rumik: {json.dumps(cur, ensure_ascii=False)}"
        )

    with open("/tmp/akruti_tts_backup.json", "w", encoding="utf-8") as fh:
        json.dump(cur, fh, ensure_ascii=False, indent=2)
    print("backed up current tts -> /tmp/akruti_tts_backup.json")

    rumik: dict = dict(RUMIK_TTS)
    rumik["api_key"] = [api_key]
    payload = json.dumps(rumik, ensure_ascii=False).replace("'", "''")

    psql(
        "UPDATE workflow_definitions SET workflow_configurations = jsonb_set("
        "workflow_configurations::jsonb, "
        f"'{TTS_PATH}'::text[], '{payload}'::jsonb, true) "
        "WHERE id = 36 RETURNING id;"
    )
    print("flipped def 36 tts -> rumik")

    verify = psql(
        "SELECT workflow_configurations->'model_configuration_v2_override'->'byok'"
        "->'pipeline'->'tts' FROM workflow_definitions WHERE id = 36;"
    ).strip()
    v = json.loads(verify)
    print("VERIFY tts:", json.dumps(v, ensure_ascii=False))
    ok = (
        v.get("provider") == "rumik"
        and v.get("model") == "mulberry"
        and v.get("api_key") == [api_key]
        and v.get("voice") == ""
    )
    if not ok:
        raise SystemExit("verification FAILED - rollback needed")
    print("OK: rumik config live (no restart needed)")


if __name__ == "__main__":
    main()
