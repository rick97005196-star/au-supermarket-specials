// Checks for the update timer: run with  node --test cloudflare/update-timer/test/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { shouldRun, tick, brisbaneTime, REPO, WORKFLOW } from '../src/timer.js';

const MIN = 60 * 1000;
// Brisbane time -> UTC milliseconds
const bne = (y, mo, d, h, mi) => Date.UTC(y, mo - 1, d, h, mi) - 10 * 3600 * 1000;

test('Brisbane time is UTC+10 all year (no daylight saving)', () => {
  assert.deepEqual(brisbaneTime(bne(2026, 10, 7, 0, 1)), { day: 3, hour: 0, minute: 1 });
  assert.deepEqual(brisbaneTime(bne(2026, 1, 15, 23, 59)), { day: 4, hour: 23, minute: 59 });
});

test('the plan for a whole week (Mon 5 Oct - Sun 11 Oct 2026, Brisbane)', () => {
  const perDay = {};
  const times = [];
  for (let t = bne(2026, 10, 5, 0, 0); t < bne(2026, 10, 12, 0, 0); t += MIN) {
    if (!shouldRun(t)) continue;
    const b = new Date(t + 10 * 3600 * 1000);
    const key = b.toISOString().slice(0, 10);
    perDay[key] = (perDay[key] || 0) + 1;
    times.push(b.toISOString().slice(0, 16));
  }
  assert.deepEqual(perDay, {
    '2026-10-05': 48, '2026-10-06': 48, '2026-10-07': 49,   // Mon, Tue, Wed (+ 00:01 switch-over)
    '2026-10-08': 2, '2026-10-09': 2, '2026-10-10': 2, '2026-10-11': 2,
  });
  assert.ok(times.includes('2026-10-07T00:01'), 'Wednesday 00:01 switch-over');
  assert.ok(times.includes('2026-10-05T00:17'), 'Monday starts at 00:17');
  assert.ok(times.includes('2026-10-07T23:47'), 'Wednesday ends at 23:47');
  assert.ok(!times.includes('2026-10-08T00:17'), 'Thursday is not every 30 minutes');
  assert.deepEqual(times.filter((x) => x.startsWith('2026-10-09')), ['2026-10-09T10:17', '2026-10-09T22:17']);
  assert.ok(!times.includes('2026-10-06T00:01') && !times.includes('2026-10-08T00:01'), '00:01 only on Wednesday');
});

test('every run time is a minute the Cloudflare timer actually fires (1, 17, 47)', () => {
  const cfg = readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8');
  assert.match(cfg, /"crons":\s*\["1,17,47 \* \* \* \*"\]/);
  for (let t = bne(2026, 10, 5, 0, 0); t < bne(2026, 10, 12, 0, 0); t += MIN) {
    if (shouldRun(t)) assert.ok([1, 17, 47].includes(new Date(t).getUTCMinutes()));
  }
});

test('index.js exports only the Worker (Cloudflare refuses to start otherwise)', () => {
  const src = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
  assert.equal((src.match(/^export\b/gm) || []).length, 1);
  assert.match(src, /^export default \{/m);
  assert.match(src, /async scheduled\(event, env, ctx\)/);
  assert.doesNotMatch(src, /async fetch\(/, 'no web page handler');
});

test('the Worker has no public web address', () => {
  const cfg = readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8');
  assert.match(cfg, /"workers_dev":\s*false/);
  assert.match(cfg, /"preview_urls":\s*false/);
  assert.doesNotMatch(cfg, /"routes?"\s*:/);
});

// ---- tick() with a pretend GitHub ----
const RUN_TIME = bne(2026, 10, 6, 9, 17);            // Tuesday 09:17 -> a run time
function fakeGitHub(answers) {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url, init });
    const a = answers.shift();
    if (a instanceof Error) throw a;
    return new Response(a.body === undefined ? null : JSON.stringify(a.body), { status: a.status });
  };
  return { calls, fetchImpl };
}
const env = { GH_DISPATCH_TOKEN: 'test-key' };
const quiet = (fn) => async () => {
  const log = console.log; console.log = () => {};
  try { await fn(); } finally { console.log = log; }
};

test('not a run time: GitHub is not contacted', quiet(async () => {
  const g = fakeGitHub([]);
  assert.equal(await tick(bne(2026, 10, 6, 9, 30), env, g.fetchImpl), 'not a run time');
  assert.equal(g.calls.length, 0);
}));

test('no key yet: nothing is started', quiet(async () => {
  const g = fakeGitHub([]);
  assert.equal(await tick(RUN_TIME, {}, g.fetchImpl), 'no key');
  assert.equal(g.calls.length, 0);
}));

test('starts the update on the main branch, marked as coming from the timer', quiet(async () => {
  const g = fakeGitHub([
    { status: 200, body: { workflow_runs: [{ status: 'completed' }, { status: 'in_progress' }] } },
    { status: 204 },
  ]);
  assert.equal(await tick(RUN_TIME, env, g.fetchImpl), 'started');
  assert.equal(g.calls.length, 2);
  const post = g.calls[1];
  assert.equal(post.url, `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`);
  assert.equal(post.init.method, 'POST');
  assert.deepEqual(JSON.parse(post.init.body), { ref: 'main', inputs: { source: 'cloudflare' } });
  assert.equal(post.init.headers.Authorization, 'Bearer test-key');
}));

test('an update already waiting: no second one is added', quiet(async () => {
  for (const status of ['queued', 'pending', 'waiting', 'requested']) {
    const g = fakeGitHub([{ status: 200, body: { workflow_runs: [{ status: 'in_progress' }, { status }] } }]);
    assert.equal(await tick(RUN_TIME, env, g.fetchImpl), 'already queued');
    assert.equal(g.calls.length, 1);
  }
}));

test('expired or wrong key: reported as an error, nothing started', quiet(async () => {
  const g = fakeGitHub([{ status: 401, body: { message: 'Bad credentials' } }]);
  await assert.rejects(tick(RUN_TIME, env, g.fetchImpl), /refused the key \(401\)/);
  assert.equal(g.calls.length, 1);
}));

test('GitHub hiccup: tries once more, then succeeds', quiet(async () => {
  const g = fakeGitHub([
    { status: 200, body: { workflow_runs: [] } },
    { status: 502, body: { message: 'Bad gateway' } },
    { status: 204 },
  ]);
  assert.equal(await tick(RUN_TIME, env, g.fetchImpl, 1), 'started');
  assert.equal(g.calls.length, 3);
}));

test('queue check fails (network): still starts the update', quiet(async () => {
  const g = fakeGitHub([new Error('timeout'), { status: 204 }]);
  assert.equal(await tick(RUN_TIME, env, g.fetchImpl, 1), 'started');
}));

test('GitHub keeps failing: reported as an error after two tries', quiet(async () => {
  const g = fakeGitHub([
    { status: 200, body: { workflow_runs: [] } },
    { status: 500, body: {} },
    new Error('connection reset'),
  ]);
  await assert.rejects(tick(RUN_TIME, env, g.fetchImpl, 1), /could not start the update - network problem/);
}));

test('a rejected request (422) is not repeated', quiet(async () => {
  const g = fakeGitHub([
    { status: 200, body: { workflow_runs: [] } },
    { status: 422, body: { message: 'Unexpected inputs provided' } },
  ]);
  await assert.rejects(tick(RUN_TIME, env, g.fetchImpl, 1), /GitHub answered 422/);
  assert.equal(g.calls.length, 2);
}));
