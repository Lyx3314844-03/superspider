package com.javaspider.antibot;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;

class CaptchaSolverTest {

    @Test
    @DisplayName("LOCAL_TESSERACT 不应抛异常")
    void localTesseractFallbackDoesNotThrow() {
        byte[] imageBytes = sampleImage();
        CaptchaSolver solver = CaptchaSolver.create(CaptchaSolver.CaptchaSolverType.LOCAL_TESSERACT);
        assertDoesNotThrow(() -> solver.solve(imageBytes));
    }

    @Test
    @DisplayName("DEATHBYCAPTCHA 在缺失凭据时回退本地 OCR")
    void deathByCaptchaFallbackDoesNotThrow() {
        byte[] imageBytes = sampleImage();
        CaptchaSolver solver = CaptchaSolver.deathByCaptcha("", "");
        assertDoesNotThrow(() -> solver.solve(imageBytes));
    }

    @Test
    @DisplayName("CUSTOM 在缺失端点时回退本地 OCR")
    void customFallbackDoesNotThrow() {
        byte[] imageBytes = sampleImage();
        CaptchaSolver solver = CaptchaSolver.custom("", "");
        assertDoesNotThrow(() -> solver.solve(imageBytes));
    }

    private byte[] sampleImage() {
        try {
            BufferedImage image = new BufferedImage(8, 8, BufferedImage.TYPE_INT_RGB);
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ImageIO.write(image, "png", baos);
            return baos.toByteArray();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
