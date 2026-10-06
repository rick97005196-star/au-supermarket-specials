// Cloudflare Worker "specials-update-trigger"
// GitHub's own schedule often skips runs (only every 4-7 hours), so this Worker starts the
// "Weekly Specials Auto Update & Deploy" workflow on time instead.
// Cron trigger in Cloudflare: 17,47 * * * *   (every 30 minutes, UTC)
// Secret in Cloudflare: GH_TOKEN = fine-grained GitHub token, this repo only, "Actions: Read and write"
const REPO = 'rick97005196-star/au-supermarket-specials';
const WORKFLOW = 'auto_update.yml';

export default {
  async scheduled(event, env, ctx) {
    const bne = new Date(event.scheduledTime + 10 * 3600 * 1000); // Brisbane time (UTC+10)
    const day = bne.getUTCDay();            // 0 Sun ... 6 Sat
    const hour = bne.getUTCHours(), min = bne.getUTCMinutes();
    const busyDays = day >= 1 && day <= 3;  // Mon-Wed: every 30 minutes (new specials appear)
    const twiceDaily = (hour === 10 || hour === 22) && min < 30; // Thu-Sun: 10:17 and 22:17
    if (!busyDays && !twiceDaily) return;
    ctx.waitUntil(dispatch(env));
  },
  async fetch() {
    return new Response('specials update trigger is running');
  },
};

async function dispatch(env) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'specials-update-trigger',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (r.status !== 204) throw new Error(`GitHub answered ${r.status}: ${await r.text()}`);
}
