#!/usr/bin/env node
// Renders the site's Open Graph card (og/default.png, 1200x630) with Playwright.
// Not part of CI: run it by hand when the card's text changes, and commit the PNG.
//   node admin/build/make_og.js
'use strict';
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const ROOT = path.resolve(__dirname, '..', '..');
const HTML = `<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;width:1200px;height:630px;background:#faf9f5;font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial,sans-serif;color:#1c1d21;
  display:flex;flex-direction:column;justify-content:space-between;padding:72px 84px;box-sizing:border-box;border-top:14px solid #0f766e}
.brand{font-weight:800;font-size:34px;letter-spacing:-.02em}.brand span{color:#0f766e}
.eyebrow{font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#0f766e;font-size:19px;margin-bottom:22px}
h1{font-family:Georgia,"Times New Roman",serif;font-size:104px;margin:0 0 22px;line-height:1;color:#101114}
p{font-size:30px;line-height:1.4;color:#5c5f66;margin:0;max-width:1000px}
.foot{display:flex;justify-content:space-between;font-size:22px;color:#8a8d94}
</style></head><body>
<div class="brand">diniscruz<span>.ai</span></div>
<div><div class="eyebrow">AI · cyber security · semantic knowledge graphs · open source</div>
<h1>Dinis Cruz</h1>
<p>Founder of sgit.ai, MyFeeds.ai, The Cyber Boardroom and RiskMandate.ai. Former OWASP Board member. Essays and research, built in the open.</p></div>
<div class="foot"><span>diniscruz.ai</span><span>CC BY 4.0</span></div>
</body></html>`;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  await p.setContent(HTML);
  await p.screenshot({ path: path.join(ROOT, 'og/default.png') });
  await b.close();
  console.log('wrote og/default.png');
})();
