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

console.log("Current Period Start:", currentPeriod.start.toISOString());
console.log("Current Period End:", currentPeriod.end.toISOString());

const sampleRunDate = parseSafeDate("2026-08-18T11:35:10.129678Z");
console.log("Sample Run Date:", sampleRunDate.toISOString());

const startDateCutoff = parseSafeDate(`${BILLING_START_DATE_STR}T00:00:00+05:30`);
console.log("Start Date Cutoff:", startDateCutoff.toISOString());

console.log("Is run >= startDateCutoff?", sampleRunDate >= startDateCutoff);
console.log("Is run >= currentPeriod.start?", sampleRunDate >= currentPeriod.start);
console.log("Is run <= currentPeriod.end?", sampleRunDate <= currentPeriod.end);
