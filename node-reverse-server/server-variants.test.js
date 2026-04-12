const legacy = require('./server');
const enhanced = require('./server-enhanced');

function routePaths(expressApp) {
  return expressApp._router.stack
    .filter((layer) => layer.route)
    .map((layer) => layer.route.path);
}

describe('node reverse server variants', () => {
  test('legacy server exposes anti-bot profile routes', () => {
    const paths = routePaths(legacy.app);
    expect(paths).toEqual(expect.arrayContaining([
      '/api/anti-bot/detect',
      '/api/anti-bot/profile',
      '/api/tls/fingerprint',
      '/api/fingerprint/spoof',
      '/api/http/stealth'
    ]));
  });

  test('enhanced server exposes anti-bot profile routes', () => {
    const paths = routePaths(enhanced.app);
    expect(paths).toEqual(expect.arrayContaining([
      '/api/anti-bot/detect',
      '/api/anti-bot/profile',
      '/api/tls/fingerprint',
      '/api/fingerprint/spoof',
      '/api/http/stealth'
    ]));
  });
});
