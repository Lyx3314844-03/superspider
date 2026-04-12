const DEFAULT_STEALTH_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br',
  'Connection': 'keep-alive',
  'Upgrade-Insecure-Requests': '1',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-User': '?1',
  'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
  'Sec-Ch-Ua-Mobile': '?0',
  'Sec-Ch-Ua-Platform': '"Windows"'
};

const DEFAULT_FINGERPRINTS = {
  chrome_windows: {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    platform: 'Win32',
    vendor: 'Google Inc.',
    languages: ['zh-CN', 'zh', 'en-US', 'en'],
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0,
    screen: { width: 1920, height: 1080, colorDepth: 24 },
    timezone: 'Asia/Shanghai',
    plugins: ['Chrome PDF Plugin', 'Native Client'],
    fonts: ['Microsoft YaHei', 'Arial', 'Times New Roman']
  },
  chrome_mac: {
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    platform: 'MacIntel',
    vendor: 'Google Inc.',
    languages: ['zh-CN', 'zh', 'en-US', 'en'],
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0,
    screen: { width: 2560, height: 1600, colorDepth: 24 },
    timezone: 'Asia/Shanghai'
  },
  firefox_windows: {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    platform: 'Win32',
    vendor: '',
    languages: ['zh-CN', 'zh', 'en-US', 'en'],
    hardwareConcurrency: 8,
    deviceMemory: 8,
    maxTouchPoints: 0,
    doNotTrack: '1'
  }
};

const DEFAULT_TLS_FINGERPRINTS = {
  chrome: {
    cipherSuites: [
      'TLS_AES_128_GCM_SHA256',
      'TLS_AES_256_GCM_SHA384',
      'TLS_CHACHA20_POLY1305_SHA256',
      'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256',
      'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256',
      'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384',
      'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
      'TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256',
      'TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256'
    ],
    extensions: [
      'server_name',
      'extended_master_secret',
      'renegotiation_info',
      'supported_groups',
      'ec_point_formats',
      'session_ticket',
      'application_layer_protocol_negotiation',
      'status_request',
      'signature_algorithms',
      'signed_certificate_timestamp',
      'key_share',
      'psk_key_exchange_modes',
      'supported_versions',
      'compress_certificate',
      'application_settings',
      'encrypted_client_hello'
    ],
    curves: ['X25519', 'secp256r1', 'secp384r1', 'secp521r1'],
    signatureAlgorithms: [
      'ecdsa_secp256r1_sha256',
      'rsa_pss_rsae_sha256',
      'rsa_pkcs1_sha256',
      'ecdsa_secp384r1_sha384',
      'rsa_pss_rsae_sha384',
      'rsa_pkcs1_sha384',
      'rsa_pss_rsae_sha512',
      'rsa_pkcs1_sha512'
    ],
    ja3: '771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-41-21-65037-5-171-11-0-13-23-43-65281-18-16-30032-27-51,29-23-24,0'
  },
  firefox: {
    ja3: '771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21-65037-5-11-0-13-23-43-65281-18-16-30032-27-51,29-23-24,0'
  },
  safari: {
    ja3: '771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21-65037-5-11-0-13-23-43-65281-18-16-30032-27-51,29-23-24,0'
  }
};

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeText(value) {
  if (value === undefined || value === null) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (error) {
      return String(value);
    }
  }
  return String(value);
}

function normalizeHeaders(headers = {}) {
  if (!headers || typeof headers !== 'object' || Array.isArray(headers)) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(headers).map(([key, value]) => [String(key).toLowerCase(), normalizeText(value)])
  );
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function getSpoofedFingerprintProfile(browser = 'chrome', platform = 'windows') {
  const key = `${browser}_${platform}`;
  return deepClone(DEFAULT_FINGERPRINTS[key] || DEFAULT_FINGERPRINTS.chrome_windows);
}

function getTLSFingerprintProfile(browser = 'chrome', version = '120') {
  return {
    ...deepClone(DEFAULT_TLS_FINGERPRINTS[browser] || DEFAULT_TLS_FINGERPRINTS.chrome),
    browser,
    version
  };
}

function getStealthHeaders(headers = {}) {
  return {
    ...DEFAULT_STEALTH_HEADERS,
    ...headers
  };
}

function getRateLimitStrategy(level = 'medium') {
  const strategies = {
    low: { minDelayMs: 800, maxDelayMs: 2000, proxyRotation: 'every 25-50 requests' },
    medium: { minDelayMs: 1500, maxDelayMs: 4000, proxyRotation: 'every 10-25 requests' },
    high: { minDelayMs: 3000, maxDelayMs: 8000, proxyRotation: 'every 3-10 requests' },
    very_high: { minDelayMs: 5000, maxDelayMs: 12000, proxyRotation: 'every request or every 1-3 requests' }
  };
  return strategies[level] || strategies.medium;
}

function detectAntiBotProfile(input = {}) {
  const html = normalizeText(input.html);
  const js = normalizeText(input.js);
  const body = normalizeText(input.body);
  const cookies = normalizeText(input.cookies);
  const headers = normalizeHeaders(input.headers);
  const headerText = JSON.stringify(headers);
  const statusCode = Number(input.statusCode || 0);
  const url = normalizeText(input.url);

  const combinedMarkup = [html, body].filter(Boolean).join('\n');
  const searchCorpus = [combinedMarkup, js, headerText, cookies, url].join('\n');

  const detection = {
    hasCloudflare: /cloudflare|cf-ray|cf-cache-status|cf-chl|__cf_bm|cf_clearance/i.test(searchCorpus),
    hasAkamai: /akamai|ak-bmsc|akavpau|akamai bot manager/i.test(searchCorpus),
    hasDataDome: /datadome|dd-protection|datadome cookie/i.test(searchCorpus),
    hasPerimeterX: /perimeterx|_px|px-captcha/i.test(searchCorpus),
    hasIncapsula: /incapsula|visid_incap|incap_ses/i.test(searchCorpus),
    hasF5: /\bbigip\b|f5[- ]?networks|x-wa-info/i.test(searchCorpus),
    hasKasada: /kasada|x-kpsdk|ips.js/i.test(searchCorpus),
    hasShape: /shape security|shape[-_]?api|f_sid/i.test(searchCorpus),
    hasCaptcha: /captcha|g-recaptcha|hcaptcha|turnstile|geetest/i.test(searchCorpus),
    hasManagedChallenge: /just a moment|checking your browser|attention required|challenge-platform/i.test(searchCorpus),
    hasJSLChallenge: /eval\(function|\.split\(|\.join\(|settimeout\(function\(\)\s*\{.*location/i.test(js),
    hasCanvasChallenge: /canvas|toDataURL|getContext\s*\(\s*['"]2d['"]\s*\)/i.test(js),
    hasWebGLChallenge: /webgl|getContext\s*\(\s*['"]webgl['"]\s*\)|webglrenderer/i.test(js),
    hasAudioChallenge: /audiocontext|createoscillator|offlineaudiocontext/i.test(js),
    hasFingerprinting: /fingerprint|navigator\.webdriver|canvas.*hash|webgl.*hash|audio.*hash/i.test(searchCorpus),
    hasCookieChallenge: /set-cookie|__cf_bm|cf_clearance|ak_bmsc|datadome|_px/i.test(searchCorpus),
    hasRateLimit: statusCode === 429 || /retry-after|too many requests|rate limit|slow down/i.test(searchCorpus),
    hasForbidden: statusCode === 403 || /access denied|request blocked|forbidden/i.test(searchCorpus)
  };

  const vendors = [];
  const addVendor = (name, triggered, reasons) => {
    if (!triggered) {
      return;
    }
    vendors.push({
      name,
      confidence: Math.min(0.99, 0.55 + reasons.length * 0.1),
      reasons
    });
  };

  addVendor('Cloudflare', detection.hasCloudflare, unique([
    /cf-ray/i.test(searchCorpus) && 'cf-ray header or marker',
    /cf_clearance|__cf_bm/i.test(searchCorpus) && 'Cloudflare session cookie',
    detection.hasManagedChallenge && 'managed browser challenge'
  ]));
  addVendor('Akamai', detection.hasAkamai, unique([
    /ak-bmsc|akavpau/i.test(searchCorpus) && 'Akamai cookie marker',
    /akamai/i.test(searchCorpus) && 'Akamai keyword'
  ]));
  addVendor('DataDome', detection.hasDataDome, unique([
    /datadome/i.test(searchCorpus) && 'DataDome marker'
  ]));
  addVendor('PerimeterX', detection.hasPerimeterX, unique([
    /_px|perimeterx/i.test(searchCorpus) && 'PerimeterX token or namespace'
  ]));
  addVendor('Incapsula', detection.hasIncapsula, unique([
    /visid_incap|incap_ses/i.test(searchCorpus) && 'Incapsula cookie marker'
  ]));
  addVendor('F5', detection.hasF5, unique([
    /\bbigip\b|x-wa-info/i.test(searchCorpus) && 'F5/BIG-IP marker'
  ]));
  addVendor('Kasada', detection.hasKasada, unique([
    /kasada|x-kpsdk|ips.js/i.test(searchCorpus) && 'Kasada fingerprint marker'
  ]));
  addVendor('Shape', detection.hasShape, unique([
    /shape security|shape[-_]api|f_sid/i.test(searchCorpus) && 'Shape marker'
  ]));

  const challenges = unique([
    detection.hasManagedChallenge && 'managed-browser-challenge',
    detection.hasCaptcha && 'captcha',
    detection.hasJSLChallenge && 'javascript-challenge',
    detection.hasCanvasChallenge && 'canvas-fingerprint',
    detection.hasWebGLChallenge && 'webgl-fingerprint',
    detection.hasAudioChallenge && 'audio-fingerprint',
    detection.hasFingerprinting && 'high-entropy-fingerprint',
    detection.hasCookieChallenge && 'cookie-bootstrap',
    detection.hasRateLimit && 'rate-limit',
    detection.hasForbidden && 'request-blocked'
  ]).map((type) => ({ type }));

  const weightedScore =
    vendors.length * 2 +
    challenges.length +
    Number(detection.hasRateLimit) +
    Number(detection.hasForbidden);

  const level = weightedScore >= 8
    ? 'very_high'
    : weightedScore >= 7
      ? 'high'
      : weightedScore >= 4
        ? 'medium'
        : weightedScore > 0
          ? 'low'
          : 'none';

  const preferredBrowser = vendors.some((vendor) => ['Cloudflare', 'DataDome', 'Kasada', 'PerimeterX'].includes(vendor.name))
    ? 'chrome'
    : 'firefox';
  const preferredPlatform = 'windows';
  const fingerprint = getSpoofedFingerprintProfile(preferredBrowser, preferredPlatform);
  const tls = getTLSFingerprintProfile(preferredBrowser, preferredBrowser === 'chrome' ? '120' : '120');
  const rateLimitStrategy = getRateLimitStrategy(level);
  const recommendedHeaders = getStealthHeaders({
    'User-Agent': fingerprint.userAgent || DEFAULT_STEALTH_HEADERS['User-Agent']
  });

  const signals = unique([
    vendors.map((vendor) => `vendor:${vendor.name.toLowerCase()}`),
    challenges.map((challenge) => challenge.type),
    detection.hasFingerprinting && 'requires-real-browser-fingerprint',
    detection.hasCookieChallenge && 'requires-cookie-bootstrap',
    detection.hasRateLimit && 'requires-paced-requests'
  ].flat());

  const recommendations = unique([
    vendors.some((vendor) => vendor.name === 'Cloudflare') && 'Prioritize a real Chrome fingerprint and JS execution chain',
    vendors.some((vendor) => vendor.name === 'Akamai') && 'Preserve Akamai cookies and send full client hints',
    vendors.some((vendor) => vendor.name === 'DataDome') && 'Keep the session cookie stable and avoid static HTTP fingerprints',
    detection.hasManagedChallenge && 'Pass the challenge in a browser context before replaying the session',
    detection.hasFingerprinting && 'Keep UA, client hints, Canvas, WebGL, and TLS fingerprints consistent',
    detection.hasRateLimit && 'Increase jitter and rotate proxies more aggressively',
    detection.hasCaptcha && 'Route captcha handling to an external solver or manual step',
    challenges.length === 0 && 'No obvious challenge detected; validate with a lightweight HTTP pass first'
  ]);

  return {
    success: true,
    url,
    statusCode,
    detection,
    vendors,
    challenges,
    signals,
    score: weightedScore,
    level,
    recommendations,
    fingerprintProfile: {
      browser: preferredBrowser,
      platform: preferredPlatform,
      fingerprint
    },
    requestBlueprint: {
      headers: recommendedHeaders,
      tls,
      session: {
        preserveCookies: detection.hasCookieChallenge || vendors.length > 0,
        bootstrapRequired: detection.hasManagedChallenge || detection.hasCookieChallenge
      },
      pacing: rateLimitStrategy
    },
    mitigationPlan: {
      immediate: unique([
        detection.hasManagedChallenge && 'Use a browser context to clear the challenge page first',
        detection.hasCaptcha && 'Move captcha handling to an external solver or manual lane',
        detection.hasForbidden && 'Rotate exit IPs and rebuild the session'
      ]),
      browser: unique([
        'Keep browser fingerprint, client hints, and TLS traits aligned',
        detection.hasCanvasChallenge && 'Stabilize Canvas output instead of randomizing it',
        detection.hasWebGLChallenge && 'Pin GPU/renderer exposure',
        detection.hasAudioChallenge && 'Pin AudioContext output'
      ]),
      network: unique([
        'Prefer session-level proxies over per-request random proxies',
        detection.hasRateLimit && `Keep request spacing between ${rateLimitStrategy.minDelayMs}-${rateLimitStrategy.maxDelayMs}ms`,
        `Proxy rotation strategy: ${rateLimitStrategy.proxyRotation}`
      ]),
      reverse: unique([
        detection.hasJSLChallenge && 'Feed challenge scripts into AST and executeJS analysis',
        vendors.length > 0 && 'Record vendor traits and build a site-specific anti-bot template',
        detection.hasCookieChallenge && 'Persist the initial Set-Cookie values as reverse inputs'
      ])
    }
  };
}

module.exports = {
  detectAntiBotProfile,
  getRateLimitStrategy,
  getSpoofedFingerprintProfile,
  getTLSFingerprintProfile,
  getStealthHeaders
};
