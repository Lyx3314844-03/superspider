#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i];
    if (!current.startsWith('--')) continue;
    const key = current.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function ensureParent(filePath) {
  if (!filePath) return;
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

async function runFetch(args) {
  const browser = await chromium.launch({ headless: !!args.headless });
  const context = await browser.newContext(args['user-agent'] ? { userAgent: args['user-agent'] } : {});
  const page = await context.newPage();
  await page.goto(args.url, { waitUntil: 'networkidle', timeout: Number(args['timeout-seconds'] || 30) * 1000 });
  const html = await page.content();
  const title = await page.title();
  const resolvedUrl = page.url();
  if (args.html) {
    ensureParent(args.html);
    fs.writeFileSync(args.html, html, 'utf8');
  }
  if (args.screenshot) {
    ensureParent(args.screenshot);
    await page.screenshot({ path: args.screenshot, fullPage: true });
  }
  if (args['save-storage-state']) {
    ensureParent(args['save-storage-state']);
    await context.storageState({ path: args['save-storage-state'] });
  }
  if (args['save-cookies-file']) {
    ensureParent(args['save-cookies-file']);
    fs.writeFileSync(args['save-cookies-file'], JSON.stringify(await context.cookies(), null, 2), 'utf8');
  }
  await browser.close();
  console.log(JSON.stringify({ title, url: resolvedUrl, html_path: args.html || '', screenshot_path: args.screenshot || '' }));
}

async function runJob(args) {
  const job = JSON.parse(fs.readFileSync(args['job-file'], 'utf8'));
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  const consoleMessages = [];
  const networkEvents = [];
  page.on('console', message => consoleMessages.push(message.text()));
  page.on('response', response => {
    networkEvents.push({ url: response.url(), status: response.status(), method: response.request().method() });
  });
  await page.goto(job.target.url, { waitUntil: 'networkidle', timeout: 30000 });
  const title = await page.title();
  const extract = {};
  for (const field of job.extract || []) {
    if (field.field === 'title') {
      extract[field.field] = title;
    }
  }
  for (const action of (job.browser && job.browser.actions) || []) {
    if (action.type === 'eval') {
      const result = await page.evaluate(action.value);
      if (action.save_as) extract[action.save_as] = result;
    } else if (action.type === 'listen_network' && action.save_as) {
      extract[action.save_as] = networkEvents;
    }
  }
  const outputPath = job.output && job.output.path ? job.output.path : '';
  const artifactDir = outputPath ? path.dirname(outputPath) : process.cwd();
  const htmlPath = path.join(artifactDir, 'playwright-page.html');
  const screenshotPath = path.join(artifactDir, 'playwright-page.png');
  ensureParent(htmlPath);
  fs.writeFileSync(htmlPath, await page.content(), 'utf8');
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await browser.close();
  console.log(JSON.stringify({
    title,
    url: page.url(),
    extract,
    artifacts: [htmlPath, screenshotPath],
    console_messages: consoleMessages,
    network_events: networkEvents,
    warnings: ['browser runtime executed via native Playwright process']
  }));
}

const args = parseArgs(process.argv.slice(2));
if (args['job-file']) {
  await runJob(args);
} else {
  await runFetch(args);
}
