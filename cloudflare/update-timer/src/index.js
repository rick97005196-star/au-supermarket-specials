// Cloudflare Worker "au-specials-timer": starts the GitHub update on time.
// All rules are in timer.js. Only the Worker itself may be exported from this file.
import { tick } from './timer.js';

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(tick(event.scheduledTime, env));
  },
};
