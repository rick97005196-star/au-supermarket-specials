// The update timer's rules (used by index.js, checked by test/timer.test.js).
//
// GitHub's own schedule skips most runs when GitHub is busy (only 4-6 of ~48 a day ran in the week
// of 5 Oct 2026), so this small Worker starts the "Weekly Specials Auto Update & Deploy" workflow
// on time instead. GitHub's own schedule stays switched on as a backup.
//
// Safety:
//   * No public web address: it only runs on its timer (workers_dev / preview_urls are off).
//   * The GitHub key it uses (secret GH_DISPATCH_TOKEN) is a fine-grained token for this one
//     repository with only "Actions: Read and write": it can start and list update runs, but it
//     cannot read or change the code, the data or any other secret.
//   * If an update is already waiting in the queue, it does not add another one.
//
// Plan (Brisbane time, the same as the GitHub schedule):
//   Mon 00:00 - Wed 23:59   every 30 minutes, at :17 and :47
//   Wed 00:01               the weekly switch-over to next week's specials
//   Thu - Sun               twice a day, 10:17 and 22:17
// The Cloudflare timer fires at minutes 1, 17 and 47 of every hour; shouldRun() picks the times above.

export const REPO = 'rick97005196-star/au-supermarket-specials';
export const WORKFLOW = 'auto_update.yml';

export function brisbaneTime(ms) {
  const t = new Date(ms + 10 * 3600 * 1000);     // Queensland has no daylight saving: always UTC+10
  return { day: t.getUTCDay(), hour: t.getUTCHours(), minute: t.getUTCMinutes() };
}

/** Why an update should start at this moment ('' = not now). */
export function shouldRun(ms) {
  const { day, hour, minute } = brisbaneTime(ms);
  if (day === 3 && hour === 0 && minute === 1) return 'Wednesday 00:01 weekly switch-over';
  if (day >= 1 && day <= 3) return (minute === 17 || minute === 47) ? 'Mon-Wed every 30 minutes' : '';
  return (minute === 17 && (hour === 10 || hour === 22)) ? 'Thu-Sun twice a day' : '';
}

const WAITING = new Set(['queued', 'pending', 'waiting', 'requested']);

function github(env, fetchImpl, path, init = {}) {
  return fetchImpl(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'au-specials-timer',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
    },
  });
}

/** One timer tick. Returns what happened (also written to the Worker log). */
export async function tick(ms, env, fetchImpl = fetch, retryWaitMs = 5000) {
  const reason = shouldRun(ms);
  if (!reason) return 'not a run time';
  if (!env.GH_DISPATCH_TOKEN) {
    console.log('GitHub key (GH_DISPATCH_TOKEN) not set yet - nothing started');
    return 'no key';
  }

  // Already an update waiting? Then that one will run with the newest data anyway.
  try {
    const r = await github(env, fetchImpl, `/actions/workflows/${WORKFLOW}/runs?per_page=10`);
    if (r.status === 401 || r.status === 403) {
      throw new Error(`GitHub refused the key (${r.status}) - it may have expired; make a new one`);
    }
    if (r.ok) {
      const runs = (await r.json()).workflow_runs || [];
      if (runs.some((run) => WAITING.has(run.status))) {
        console.log(`${reason}: an update is already waiting in the queue - not adding another`);
        return 'already queued';
      }
    }
  } catch (e) {
    if (String(e.message).startsWith('GitHub refused')) throw e;
    console.log(`could not check the queue (${e.message}) - starting the update anyway`);
  }

  let last = '';
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const r = await github(env, fetchImpl, `/actions/workflows/${WORKFLOW}/dispatches`, {
        method: 'POST',
        body: JSON.stringify({ ref: 'main', inputs: { source: 'cloudflare' } }),
      });
      if (r.status === 204) {
        console.log(`${reason}: update started`);
        return 'started';
      }
      last = `GitHub answered ${r.status}: ${(await r.text()).slice(0, 300)}`;
      if (r.status < 500) break;                  // 4xx: trying again will not help
    } catch (e) {
      last = `network problem: ${e.message}`;
    }
    if (attempt === 1) await new Promise((res) => setTimeout(res, retryWaitMs));
  }
  throw new Error(`${reason}: could not start the update - ${last}`);
}
