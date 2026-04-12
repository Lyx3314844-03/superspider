const {
  app,
  detectAntiBotProfile,
  getSpoofedFingerprintProfile,
  getTLSFingerprintProfile,
  getStealthHeaders
} = require('./server-maximum');
const fs = require('fs');
const path = require('path');

const FIXTURE_DIR = path.join(__dirname, 'fixtures', 'anti-bot');

function listRoutes(expressApp) {
  return expressApp._router.stack
    .filter((layer) => layer.route)
    .map((layer) => ({
      path: layer.route.path,
      methods: Object.keys(layer.route.methods)
    }));
}

describe('node reverse anti-bot profiling', () => {
  test('registers the anti-bot profile endpoint', () => {
    const routes = listRoutes(app);
    expect(routes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          path: '/api/anti-bot/profile',
          methods: expect.arrayContaining(['post'])
        })
      ])
    );
  });

  test('builds a vendor-aware anti-bot profile for challenge pages', () => {
    const html = fs.readFileSync(path.join(FIXTURE_DIR, 'cloudflare-challenge.html'), 'utf8');
    const js = fs.readFileSync(path.join(FIXTURE_DIR, 'cloudflare-challenge.js'), 'utf8');
    const profile = detectAntiBotProfile({
      url: 'https://target.example/challenge',
      statusCode: 429,
      html,
      js,
      headers: {
        'cf-ray': '1234',
        'retry-after': '10',
        'set-cookie': '__cf_bm=token; path=/; HttpOnly'
      }
    });

    expect(profile.success).toBe(true);
    expect(profile.level).toBe('very_high');
    expect(profile.vendors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: 'Cloudflare' })
      ])
    );
    expect(profile.signals).toEqual(
      expect.arrayContaining([
        'managed-browser-challenge',
        'javascript-challenge',
        'high-entropy-fingerprint',
        'requires-paced-requests'
      ])
    );
    expect(profile.requestBlueprint.headers['User-Agent']).toContain('Chrome/120');
    expect(profile.requestBlueprint.session.bootstrapRequired).toBe(true);
  });

  test('profiles datadome-style blocks from fixtures', () => {
    const html = fs.readFileSync(path.join(FIXTURE_DIR, 'datadome-block.html'), 'utf8');
    const js = fs.readFileSync(path.join(FIXTURE_DIR, 'datadome-block.js'), 'utf8');

    const profile = detectAntiBotProfile({
      url: 'https://shop.example/protected',
      statusCode: 403,
      html,
      js,
      headers: {
        'x-datadome': '1'
      },
      cookies: 'datadome=token'
    });

    expect(profile.success).toBe(true);
    expect(profile.level).toBe('very_high');
    expect(profile.vendors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: 'DataDome' })
      ])
    );
    expect(profile.challenges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: 'captcha' }),
        expect.objectContaining({ type: 'audio-fingerprint' })
      ])
    );
  });

  test('shares consistent spoofed fingerprint and stealth header defaults', () => {
    const fingerprint = getSpoofedFingerprintProfile('chrome', 'windows');
    const tls = getTLSFingerprintProfile('chrome', '120');
    const headers = getStealthHeaders({ 'X-Test': '1' });

    expect(fingerprint.userAgent).toContain('Chrome/120');
    expect(tls.browser).toBe('chrome');
    expect(tls.ja3).toBeTruthy();
    expect(headers['Sec-Ch-Ua']).toContain('Chromium');
    expect(headers['X-Test']).toBe('1');
  });
});
