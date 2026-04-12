package com.javaspider.workflow;

import com.javaspider.antibot.CaptchaSolver;
import com.javaspider.browser.BrowserManager;
import com.javaspider.antibot.UserAgentRotator;
import com.javaspider.antibot.AntiBotHandler;
import com.javaspider.antibot.ProxyPool;
import com.javaspider.dynamic.interaction.FormInteractor;
import com.javaspider.dynamic.render.ScrollLoader;
import com.javaspider.dynamic.wait.DynamicWait;
import com.javaspider.session.SessionProfile;
import org.openqa.selenium.By;
import org.openqa.selenium.Cookie;
import org.openqa.selenium.Keys;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.WebElement;

import java.io.IOException;
import java.net.URL;
import java.net.URI;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class SeleniumWorkflowExecutionContext implements WorkflowExecutionContext {
    private static final List<String> DEFAULT_CAPTCHA_IMAGE_SELECTORS = List.of(
        "img[alt*='captcha' i]",
        "img[src*='captcha' i]",
        "img.captcha",
        ".captcha img",
        ".captcha-image img",
        "#captcha img",
        "#captcha"
    );
    private static final List<String> DEFAULT_CAPTCHA_INPUT_SELECTORS = List.of(
        "input[name*='captcha' i]",
        "input[id*='captcha' i]",
        "input[placeholder*='验证码']",
        "input[name*='verify' i]",
        "input[id*='verify' i]",
        "input[name*='code' i]",
        "input[id*='code' i]"
    );
    private static final List<String> DEFAULT_CAPTCHA_SUBMIT_SELECTORS = List.of(
        "button[type='submit']",
        "input[type='submit']",
        "button[id*='submit' i]",
        "button[class*='submit' i]",
        "button[id*='verify' i]",
        "button[class*='verify' i]"
    );

    private final BrowserManager browser;
    private final FormInteractor formInteractor;
    private final DynamicWait dynamicWait;
    @SuppressWarnings("unused")
    private final ScrollLoader scrollLoader;
    private final SessionProfile sessionProfile;
    private boolean cookiesApplied;
    private final AntiBotHandler antiBotHandler;
    private final ProxyPool proxyPool;
    private final ProxyPool.ProxyInfo configuredProxy;
    private final boolean proxyHealthy;
    private boolean networkObserverInstalled;

    public SeleniumWorkflowExecutionContext(SessionProfile sessionProfile) {
        this.sessionProfile = sessionProfile;
        this.antiBotHandler = new AntiBotHandler();
        this.proxyPool = new ProxyPool();
        this.configuredProxy = buildProxyInfo(sessionProfile);
        this.proxyHealthy = configuredProxy == null || proxyPool.checkProxyHealth(configuredProxy);
        this.browser = new BrowserManager(
            BrowserManager.BrowserType.CHROME,
            true,
            false,
            resolveUserAgent(sessionProfile),
            resolveProxy(sessionProfile)
        );
        this.browser.init();
        this.formInteractor = new FormInteractor(browser);
        this.dynamicWait = new DynamicWait(browser);
        this.scrollLoader = new ScrollLoader(browser);
        this.cookiesApplied = false;
        this.networkObserverInstalled = false;
    }

    @Override
    public void gotoUrl(String url) {
        browser.navigate(url);
        applyCookiesIfNeeded(url);
        browser.waitForPageLoad();
        ensureNetworkObserverInstalled();
    }

    @Override
    public void waitFor(long timeoutMillis) {
        dynamicWait.waitForPageLoad(timeoutMillis <= 0 ? 500L : timeoutMillis);
    }

    @Override
    public void click(String selector) {
        if (!formInteractor.click(selector)) {
            browser.click(selector, By.cssSelector(selector));
        }
    }

    @Override
    public void type(String selector, String value) {
        if (!formInteractor.inputText(selector, value)) {
            browser.type(selector, By.cssSelector(selector), value);
        }
    }

    @Override
    public void select(String selector, String value, Map<String, Object> options) {
        String mode = optionString(options, "select_by");
        if (mode.isBlank()) {
            mode = optionString(options, "mode");
        }
        if ("index".equalsIgnoreCase(mode)) {
            try {
                int index = Integer.parseInt(value);
                if (formInteractor.selectByIndex(selector, index)) {
                    return;
                }
            } catch (NumberFormatException ignored) {
                // Fall through to string-based selection when index is malformed.
            }
        }
        if ("text".equalsIgnoreCase(mode)) {
            if (formInteractor.selectByText(selector, value)) {
                return;
            }
        } else {
            if (formInteractor.selectByValue(selector, value) || formInteractor.selectByText(selector, value)) {
                return;
            }
        }
        browser.executeScript(
            "var select = document.querySelector(arguments[0]);" +
                "if (select) {" +
                "  for (var i = 0; i < select.options.length; i++) {" +
                "    if (select.options[i].value === arguments[1] || select.options[i].text === arguments[1]) {" +
                "      select.selectedIndex = i;" +
                "      select.dispatchEvent(new Event('change'));" +
                "      return true;" +
                "    }" +
                "  }" +
                "}" +
                "return false;",
            selector,
            value
        );
    }

    @Override
    public void hover(String selector) {
        if (!formInteractor.hover(selector)) {
            browser.executeScript(
                "var el = document.querySelector(arguments[0]);" +
                    "if (el) { el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true})); }",
                selector
            );
        }
    }

    @Override
    public void scroll(String selector, Map<String, Object> options) {
        String mode = optionString(options, "mode");
        int maxScrolls = (int) optionLong(options, "max_scrolls", 1L);
        if (selector != null && !selector.isBlank()) {
            scrollLoader.scrollToElement(selector);
            return;
        }
        if ("top".equalsIgnoreCase(mode)) {
            browser.scrollToTop();
            return;
        }
        if (maxScrolls > 1) {
            scrollLoader.scrollToBottom(50, maxScrolls, 2);
            return;
        }
        browser.scrollToBottom();
    }

    @Override
    public Object evaluate(String script) {
        return browser.executeScript(script);
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listenNetwork(Map<String, Object> options) {
        ensureNetworkObserverInstalled();
        dynamicWait.waitForNetworkIdle(optionLong(options, "timeout_ms", 1_000L));
        Object result = browser.executeScript(
            "var resourceEntries = window.performance.getEntriesByType('resource').map(function(r) {" +
                "return {" +
                "name: r.name," +
                "type: r.initiatorType," +
                "duration: r.duration," +
                "startTime: r.startTime," +
                "responseEnd: r.responseEnd || 0," +
                "transferSize: r.transferSize || 0" +
                "};" +
            "});" +
            "var hooked = Array.isArray(window.__javaspiderNetworkEvents) ? window.__javaspiderNetworkEvents : [];" +
            "return resourceEntries.concat(hooked);"
        );
        if (result instanceof List<?> list) {
            List<Map<String, Object>> entries = new ArrayList<>();
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    entries.add((Map<String, Object>) map);
                }
            }
            return entries;
        }
        return List.of();
    }

    private void ensureNetworkObserverInstalled() {
        if (networkObserverInstalled) {
            return;
        }
        browser.executeScript(
            "if (!window.__javaspiderNetworkRecorderInstalled) {" +
                "window.__javaspiderNetworkRecorderInstalled = true;" +
                "window.__javaspiderNetworkEvents = window.__javaspiderNetworkEvents || [];" +
                "var pushEvent = function(evt) { window.__javaspiderNetworkEvents.push(evt); };" +
                "if (!window.__javaspiderOriginalFetch && window.fetch) {" +
                    "window.__javaspiderOriginalFetch = window.fetch.bind(window);" +
                    "window.fetch = function(input, init) {" +
                        "var started = Date.now();" +
                        "var method = (init && init.method) || 'GET';" +
                        "var url = typeof input === 'string' ? input : (input && input.url) || '';" +
                        "return window.__javaspiderOriginalFetch(input, init).then(function(response) {" +
                            "pushEvent({name: url, type: 'fetch', method: method, status: response.status || 0, duration: Date.now() - started, startTime: started, transferSize: 0});" +
                            "return response;" +
                        "}).catch(function(error) {" +
                            "pushEvent({name: url, type: 'fetch', method: method, status: 0, duration: Date.now() - started, startTime: started, error: String(error)});" +
                            "throw error;" +
                        "});" +
                    "};" +
                "}" +
                "if (!window.__javaspiderOriginalXHROpen && window.XMLHttpRequest) {" +
                    "window.__javaspiderOriginalXHROpen = XMLHttpRequest.prototype.open;" +
                    "window.__javaspiderOriginalXHRSend = XMLHttpRequest.prototype.send;" +
                    "XMLHttpRequest.prototype.open = function(method, url) { this.__javaspiderMethod = method; this.__javaspiderUrl = url; return window.__javaspiderOriginalXHROpen.apply(this, arguments); };" +
                    "XMLHttpRequest.prototype.send = function() {" +
                        "var xhr = this;" +
                        "var started = Date.now();" +
                        "xhr.addEventListener('loadend', function() {" +
                            "pushEvent({name: xhr.__javaspiderUrl || '', type: 'xhr', method: xhr.__javaspiderMethod || 'GET', status: xhr.status || 0, duration: Date.now() - started, startTime: started, transferSize: 0});" +
                        "});" +
                        "return window.__javaspiderOriginalXHRSend.apply(this, arguments);" +
                    "};" +
                "}" +
            "}"
        );
        networkObserverInstalled = true;
    }

    @Override
    public String captureHtml() {
        return browser.getPageSource();
    }

    @Override
    public void captureScreenshot(String artifactPath) {
        browser.screenshotToFile(artifactPath);
    }

    @Override
    public String currentUrl() {
        return browser.getCurrentUrl();
    }

    @Override
    public String title() {
        return browser.getTitle();
    }

    @Override
    public void close() {
        browser.close();
        proxyPool.close();
    }

    @Override
    public boolean challengeDetected() {
        return antiBotHandler.isBlocked(captureHtml(), 200);
    }

    @Override
    public boolean captchaDetected() {
        String html = captureHtml().toLowerCase(Locale.ROOT);
        return html.contains("captcha") || html.contains("验证码");
    }

    @Override
    public CaptchaRecoveryResult recoverCaptcha(Map<String, Object> options) {
        String mockSolution = optionString(options, "mock_solution");
        String solverName = resolveSolverName(options, mockSolution);

        String solution = mockSolution;
        if (solution.isBlank()) {
            CaptchaSolver solver = createCaptchaSolver(solverName, options);
            if (solver == null) {
                return CaptchaRecoveryResult.failed(solverName, "captcha solver is not configured");
            }

            byte[] imageBytes = loadCaptchaImage(options);
            if (imageBytes == null || imageBytes.length == 0) {
                return CaptchaRecoveryResult.failed(solverName, "captcha image could not be captured");
            }

            solution = solver.solve(imageBytes);
            if (solution == null || solution.isBlank()) {
                return CaptchaRecoveryResult.failed(solverName, "captcha solver returned an empty result");
            }
        }

        String inputSelector = resolveInputSelector(options);
        if (inputSelector.isBlank()) {
            return CaptchaRecoveryResult.failed(solverName, "captcha input field was not found");
        }

        type(inputSelector, solution);
        boolean continued = continueAfterCaptcha(options, inputSelector);
        return CaptchaRecoveryResult.solved(solverName, continued, solution.length());
    }

    @Override
    public String proxyHealth() {
        if (configuredProxy == null) {
            return "not-configured";
        }
        return proxyHealthy ? "healthy" : "unhealthy";
    }

    static String resolveUserAgent(SessionProfile sessionProfile) {
        String override = System.getProperty("javaspider.user_agent", "").trim();
        if (!override.isBlank()) {
            return override;
        }
        String preset = sessionProfile == null ? "" : sessionProfile.getFingerprintPreset();
        UserAgentRotator rotator = new UserAgentRotator();
        if (preset == null) {
            return rotator.getLeastUsedUserAgent();
        }
        String normalized = preset.toLowerCase(Locale.ROOT);
        if (normalized.contains("mobile")) {
            return rotator.getBrowserUserAgent("mobile");
        }
        if (normalized.contains("firefox")) {
            return rotator.getBrowserUserAgent("firefox");
        }
        if (normalized.contains("safari")) {
            return rotator.getBrowserUserAgent("safari");
        }
        if (normalized.contains("edge")) {
            return rotator.getBrowserUserAgent("edge");
        }
        return rotator.getBrowserUserAgent("chrome");
    }

    static String resolveProxy(SessionProfile sessionProfile) {
        String globalProxy = System.getProperty("javaspider.proxy.url", "").trim();
        if (!globalProxy.isBlank()) {
            return globalProxy;
        }
        if (sessionProfile == null || sessionProfile.getProxyGroup() == null) {
            return "";
        }
        String key = "javaspider.proxy.group." + sessionProfile.getProxyGroup().replace('-', '_');
        return System.getProperty(key, "").trim();
    }

    private void applyCookiesIfNeeded(String url) {
        if (cookiesApplied || sessionProfile == null) {
            return;
        }
        Map<String, String> cookies = sessionProfile.getCookies();
        if (cookies == null || cookies.isEmpty()) {
            return;
        }
        String domain = URI.create(url).getHost();
        if (domain == null || domain.isBlank()) {
            return;
        }
        for (Map.Entry<String, String> entry : cookies.entrySet()) {
            browser.getDriver().manage().addCookie(new Cookie.Builder(entry.getKey(), entry.getValue())
                .domain(domain)
                .path("/")
                .build());
        }
        cookiesApplied = true;
        browser.navigate(url);
    }

    private ProxyPool.ProxyInfo buildProxyInfo(SessionProfile sessionProfile) {
        String proxy = resolveProxy(sessionProfile);
        if (proxy.isBlank()) {
            return null;
        }
        try {
            URI uri = URI.create(proxy);
            String scheme = uri.getScheme() == null ? "http" : uri.getScheme();
            String host = uri.getHost();
            int port = uri.getPort() > 0 ? uri.getPort() : 80;
            return new ProxyPool.ProxyInfo(host, port, scheme);
        } catch (Exception ignored) {
            return null;
        }
    }

    private String resolveSolverName(Map<String, Object> options, String mockSolution) {
        if (mockSolution != null && !mockSolution.isBlank()) {
            return "mock";
        }
        String configured = optionString(options, "solver");
        if (!configured.isBlank()) {
            return configured.toLowerCase(Locale.ROOT);
        }
        String systemSolver = System.getProperty("javaspider.captcha.solver", "").trim();
        if (!systemSolver.isBlank()) {
            return systemSolver.toLowerCase(Locale.ROOT);
        }
        return "local_ocr";
    }

    private CaptchaSolver createCaptchaSolver(String solverName, Map<String, Object> options) {
        String normalized = solverName == null ? "" : solverName.toLowerCase(Locale.ROOT);
        String apiKey = optionString(options, "api_key");
        if (apiKey.isBlank()) {
            apiKey = System.getProperty("javaspider.captcha.api_key", "").trim();
        }
        return switch (normalized) {
            case "", "local", "ocr", "local_ocr" ->
                CaptchaSolver.create(CaptchaSolver.CaptchaSolverType.LOCAL_OCR);
            case "2captcha", "twocaptcha" ->
                apiKey.isBlank() ? null : CaptchaSolver.twoCaptcha(apiKey);
            case "anticaptcha", "anti_captcha" ->
                apiKey.isBlank() ? null : CaptchaSolver.antiCaptcha(apiKey);
            case "capmonster" -> CaptchaSolver.capMonster();
            default -> null;
        };
    }

    private byte[] loadCaptchaImage(Map<String, Object> options) {
        String imageBase64 = optionString(options, "image_base64");
        if (!imageBase64.isBlank()) {
            return decodeBase64Image(imageBase64);
        }

        String imageURL = optionString(options, "image_url");
        if (!imageURL.isBlank()) {
            try {
                return new URL(imageURL).openStream().readAllBytes();
            } catch (IOException ignored) {
                return null;
            }
        }

        String selector = optionString(options, "image_selector");
        if (selector.isBlank()) {
            selector = firstPresentSelector(DEFAULT_CAPTCHA_IMAGE_SELECTORS);
        }
        if (selector.isBlank()) {
            return null;
        }

        WebElement element = findElement(selector);
        if (element == null) {
            return null;
        }

        try {
            return element.getScreenshotAs(OutputType.BYTES);
        } catch (Exception ignored) {
            String src = element.getAttribute("src");
            if (src != null && src.startsWith("data:image")) {
                return decodeBase64Image(src);
            }
            if (src != null && !src.isBlank()) {
                try {
                    return new URL(src).openStream().readAllBytes();
                } catch (IOException suppressed) {
                    return null;
                }
            }
            return null;
        }
    }

    private byte[] decodeBase64Image(String value) {
        String payload = value;
        int prefix = payload.indexOf("base64,");
        if (prefix >= 0) {
            payload = payload.substring(prefix + "base64,".length());
        }
        try {
            return Base64.getDecoder().decode(payload);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private String resolveInputSelector(Map<String, Object> options) {
        String selector = optionString(options, "input_selector");
        if (!selector.isBlank() && findElement(selector) != null) {
            return selector;
        }
        return firstPresentSelector(DEFAULT_CAPTCHA_INPUT_SELECTORS);
    }

    private boolean continueAfterCaptcha(Map<String, Object> options, String inputSelector) {
        long waitAfterSubmitMillis = optionLong(options, "wait_after_submit_ms", 1_000L);
        String submitSelector = optionString(options, "submit_selector");
        if (submitSelector.isBlank()) {
            submitSelector = optionString(options, "continue_selector");
        }
        if (submitSelector.isBlank()) {
            submitSelector = firstPresentSelector(DEFAULT_CAPTCHA_SUBMIT_SELECTORS);
        }

        if (!submitSelector.isBlank() && findElement(submitSelector) != null) {
            click(submitSelector);
            waitFor(waitAfterSubmitMillis);
            return true;
        }

        WebElement input = findElement(inputSelector);
        if (input != null) {
            input.sendKeys(Keys.ENTER);
            waitFor(waitAfterSubmitMillis);
            return true;
        }
        return false;
    }

    private String firstPresentSelector(List<String> selectors) {
        for (String selector : selectors) {
            if (findElement(selector) != null) {
                return selector;
            }
        }
        return "";
    }

    private WebElement findElement(String selector) {
        List<By> locators = List.of(By.cssSelector(selector), By.xpath(selector), By.id(selector));
        for (By locator : locators) {
            try {
                List<WebElement> elements = browser.getDriver().findElements(locator);
                if (!elements.isEmpty()) {
                    return elements.get(0);
                }
            } catch (Exception ignored) {
                // Ignore invalid selectors and continue through the fallback list.
            }
        }
        return null;
    }

    private String optionString(Map<String, Object> options, String key) {
        if (options == null) {
            return "";
        }
        Object value = options.get(key);
        if (value == null) {
            return "";
        }
        String text = String.valueOf(value).trim();
        return text;
    }

    private long optionLong(Map<String, Object> options, String key, long fallback) {
        if (options == null) {
            return fallback;
        }
        Object value = options.get(key);
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value == null) {
            return fallback;
        }
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }
}
