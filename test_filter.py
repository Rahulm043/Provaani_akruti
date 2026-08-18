import subprocess
import json

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    '--command=python3 -c "import requests, json; tok=requests.post(\'http://localhost:8000/api/v1/auth/login\', json={\'email\':\'admin@provaani.xyz\',\'password\':\'Admin123!\'}).json()[\'token\']; print(json.dumps(requests.get(\'http://localhost:8000/api/v1/workflow/1/runs?limit=100\', headers={\'Authorization\': \'Bearer \' + str(tok)}).json()))"'
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
data = json.loads(proc.stdout)
runs = data.get("runs", [])
print(f"Total runs fetched from API: {len(runs)}")

with open("test_filter.js", "w") as f:
    f.write("""
const parseSafeDate = (isoString) => {
  if (!isoString) return null;
  if (isoString instanceof Date) return isNaN(isoString.getTime()) ? null : isoString;
  let str = String(isoString).trim();
  if (str.includes(' ') && !str.includes('T')) {
    str = str.replace(' ', 'T');
  }
  if (str.endsWith('+00')) {
    str = str + ':00';
  }
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
};

const BILLING_START_DATE_STR = '2026-08-18';

function getBillingPeriods(startStr) {
  const start = parseSafeDate(`${startStr}T00:00:00+05:30`) || new Date(startStr);
  const now = new Date();
  const periods = [];
  let currentStart = new Date(start);

  while (currentStart <= now) {
    const periodEnd = new Date(currentStart);
    periodEnd.setDate(periodEnd.getDate() + 29);
    periodEnd.setHours(23, 59, 59, 999);

    const isCurrent = now >= currentStart && now <= periodEnd;
    periods.push({
      start: new Date(currentStart),
      end: new Date(periodEnd),
      isCurrent,
      label: `${currentStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} - ${periodEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
    });

    currentStart = new Date(periodEnd);
    currentStart.setMilliseconds(currentStart.getMilliseconds() + 1);
  }

  periods.reverse();
  return periods;
}

const periods = getBillingPeriods(BILLING_START_DATE_STR);
const currentPeriod = periods.find(p => p.isCurrent) || periods[0];
const startDateCutoff = parseSafeDate(`${BILLING_START_DATE_STR}T00:00:00+05:30`);

const allRuns = """ + json.dumps(runs) + """;

const activeRuns = allRuns.filter(r => {
  if (r.name === 'WebCall') return false;
  const d = parseSafeDate(r.created_at);
  if (!d) return false;
  if (startDateCutoff && d < startDateCutoff) return false;
  return d >= currentPeriod.start && d <= currentPeriod.end;
});

console.log("Filtered activeRuns count:", activeRuns.length);
activeRuns.forEach(r => console.log("Run:", r.id, r.created_at, r.cost_info));
""")
