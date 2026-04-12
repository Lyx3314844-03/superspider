package com.javaspider.antibot;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.File;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class CaptchaSolverLiveSmokeTest {

    @Test
    void localTesseractCanReadGeneratedCaptchaWhenAvailable() throws Exception {
        assumeLiveCaptchaEnabled();
        Assumptions.assumeTrue(commandAvailable("tesseract"), "tesseract is not installed");

        CaptchaSolver solver = CaptchaSolver.create(CaptchaSolver.CaptchaSolverType.LOCAL_TESSERACT);
        String solved = solver.solve(renderCaptchaBytes("2468"));

        assertNotNull(solved);
        assertFalse(solved.isBlank(), "tesseract returned an empty result");
    }

    @Test
    void deathByCaptchaCanSolveCaptchaWithLiveCredentials() throws Exception {
        assumeLiveCaptchaEnabled();
        String username = System.getenv("DEATHBYCAPTCHA_USERNAME");
        String password = System.getenv("DEATHBYCAPTCHA_PASSWORD");
        Assumptions.assumeTrue(username != null && !username.isBlank(), "DeathByCaptcha username is missing");
        Assumptions.assumeTrue(password != null && !password.isBlank(), "DeathByCaptcha password is missing");

        CaptchaSolver solver = CaptchaSolver.deathByCaptcha(username, password);
        String solved = solver.solve(renderCaptchaBytes("3141"));

        assertNotNull(solved);
        assertFalse(solved.isBlank(), "DeathByCaptcha returned an empty result");
    }

    @Test
    void customCaptchaEndpointCanSolveCaptchaWhenConfigured() throws Exception {
        assumeLiveCaptchaEnabled();
        String endpoint = System.getenv("JAVASPIDER_CUSTOM_CAPTCHA_URL");
        String token = firstNonBlank(
            System.getenv("JAVASPIDER_CUSTOM_CAPTCHA_TOKEN"),
            System.getenv("JAVASPIDER_CUSTOM_CAPTCHA_BEARER")
        );
        Assumptions.assumeTrue(endpoint != null && !endpoint.isBlank(), "custom captcha endpoint is missing");

        CaptchaSolver solver = CaptchaSolver.custom(endpoint, token);
        String solved = solver.solve(renderCaptchaBytes("9876"));

        assertNotNull(solved);
        assertFalse(solved.isBlank(), "custom captcha endpoint returned an empty result");
    }

    private static void assumeLiveCaptchaEnabled() {
        String enabled = System.getenv("JAVASPIDER_LIVE_CAPTCHA_SMOKE");
        Assumptions.assumeTrue(
            enabled != null && (enabled.equals("1") || enabled.equalsIgnoreCase("true")),
            "live captcha smoke is disabled"
        );
    }

    private static boolean commandAvailable(String command) {
        String path = System.getenv("PATH");
        if (path == null || path.isBlank()) {
            return false;
        }
        String[] pathEntries = path.split(File.pathSeparator);
        String[] suffixes = isWindows() ? new String[]{"", ".exe", ".cmd", ".bat"} : new String[]{""};
        for (String entry : pathEntries) {
            if (entry == null || entry.isBlank()) {
                continue;
            }
            for (String suffix : suffixes) {
                File candidate = new File(entry, command + suffix);
                if (candidate.isFile() && candidate.canExecute()) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean isWindows() {
        String os = System.getProperty("os.name", "");
        return os.toLowerCase().contains("win");
    }

    private static byte[] renderCaptchaBytes(String text) throws Exception {
        BufferedImage image = new BufferedImage(220, 80, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = image.createGraphics();
        try {
            g.setColor(Color.WHITE);
            g.fillRect(0, 0, image.getWidth(), image.getHeight());
            g.setColor(Color.BLACK);
            g.setFont(new Font(Font.MONOSPACED, Font.BOLD, 42));
            g.drawString(text, 20, 55);
        } finally {
            g.dispose();
        }

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ImageIO.write(image, "png", baos);
        return baos.toByteArray();
    }

    private static String firstNonBlank(String first, String second) {
        if (first != null && !first.isBlank()) {
            return first;
        }
        if (second != null && !second.isBlank()) {
            return second;
        }
        return null;
    }
}
