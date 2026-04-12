package com.javaspider.antibot;

import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.image.ConvolveOp;
import java.awt.image.Kernel;
import java.io.*;
import java.lang.reflect.Type;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * 验证码识别器
 * 支持多种验证码识别方式和第三方打码平台
 */
public class CaptchaSolver {
    private static final Logger logger = LoggerFactory.getLogger(CaptchaSolver.class);

    private final CaptchaSolverType type;
    private final String apiKey;
    private final String apiSecret;

    public enum CaptchaSolverType {
        LOCAL_OCR,           // 本地 OCR
        LOCAL_TESSERACT,     // Tesseract OCR
        TWOCAPTCHA,          // 2Captcha
        ANTICAPTCHA,         // Anti-Captcha
        CAPMONSTER,          // CapMonster
        DEATHBYCAPTCHA,      // DeathByCaptcha
        CUSTOM               // 自定义 API
    }

    public CaptchaSolver(CaptchaSolverType type) {
        this(type, null, null);
    }

    public CaptchaSolver(CaptchaSolverType type, String apiKey, String apiSecret) {
        this.type = type;
        this.apiKey = apiKey;
        this.apiSecret = apiSecret;
    }

    /**
     * 识别验证码
     * @param imageBytes 验证码图片字节数组
     * @return 识别结果
     */
    public String solve(byte[] imageBytes) {
        switch (type) {
            case LOCAL_OCR:
                return solveLocalOCR(imageBytes);
            case LOCAL_TESSERACT:
                return solveTesseract(imageBytes);
            case TWOCAPTCHA:
                return solveTwoCaptcha(imageBytes);
            case ANTICAPTCHA:
                return solveAntiCaptcha(imageBytes);
            case CAPMONSTER:
                return solveCapMonster(imageBytes);
            case DEATHBYCAPTCHA:
                return solveDeathByCaptcha(imageBytes);
            case CUSTOM:
                return solveCustom(imageBytes);
            default:
                throw new UnsupportedOperationException("Unsupported solver type: " + type);
        }
    }

    /**
     * 识别验证码（从 URL）
     */
    public String solveFromUrl(String imageUrl) {
        try {
            byte[] imageBytes = downloadImage(imageUrl);
            return solve(imageBytes);
        } catch (IOException e) {
            logger.error("Failed to download captcha image", e);
            return null;
        }
    }

    /**
     * 识别验证码（从文件）
     */
    public String solveFromFile(String imagePath) {
        try {
            BufferedImage image = ImageIO.read(new java.io.File(imagePath));
            return solve(bufferedImageToBytes(image));
        } catch (IOException e) {
            logger.error("Failed to read captcha image", e);
            return null;
        }
    }

    /**
     * 本地简单 OCR 识别
     */
    private String solveLocalOCR(byte[] imageBytes) {
        try {
            BufferedImage image = ImageIO.read(new ByteArrayInputStream(imageBytes));
            
            // 图像预处理
            image = preprocessImage(image);
            
            // 简单字符识别
            return recognizeCharacters(image);
        } catch (IOException e) {
            logger.error("Failed to perform OCR", e);
            return null;
        }
    }

    /**
     * 本地 Tesseract OCR 识别
     */
    private String solveTesseract(byte[] imageBytes) {
        File imageFile = null;
        try {
            imageFile = File.createTempFile("javaspider-captcha-", ".png");
            try (OutputStream os = new FileOutputStream(imageFile)) {
                os.write(imageBytes);
            }

            Process process = new ProcessBuilder(
                "tesseract",
                imageFile.getAbsolutePath(),
                "stdout",
                "--psm",
                "8"
            ).redirectErrorStream(true).start();

            String output;
            try (InputStream is = process.getInputStream()) {
                output = new String(is.readAllBytes(), StandardCharsets.UTF_8);
            }
            int exitCode = process.waitFor();
            String solved = normalizeSolvedText(output);
            if (exitCode == 0 && solved != null && !solved.isBlank()) {
                return solved;
            }
            logger.warn("Tesseract OCR returned no usable result, falling back to local OCR");
        } catch (Exception e) {
            logger.warn("Tesseract OCR failed, falling back to local OCR: {}", e.getMessage());
        } finally {
            if (imageFile != null && imageFile.exists() && !imageFile.delete()) {
                logger.debug("Failed to delete temp captcha image: {}", imageFile.getAbsolutePath());
            }
        }
        return solveLocalOCR(imageBytes);
    }

    /**
     * 2Captcha API 识别
     */
    private String solveTwoCaptcha(byte[] imageBytes) {
        try {
            String base64Image = Base64.getEncoder().encodeToString(imageBytes);
            
            // 提交验证码
            String submitUrl = "https://2captcha.com/in.php";
            String response = postRequest(submitUrl, 
                "key=" + apiKey +
                "&method=base64" +
                "&body=" + URLEncoder.encode(base64Image, "UTF-8") +
                "&json=1");
            
            Map<String, Object> submitResult = parseJson(response);
            if (!"1".equals(String.valueOf(submitResult.get("status")))) {
                throw new RuntimeException("Failed to submit captcha: " + submitResult.get("request"));
            }
            
            String captchaId = String.valueOf(submitResult.get("request"));
            
            // 轮询获取结果
            return pollTwoCaptchaResult(captchaId);
        } catch (Exception e) {
            logger.error("Failed to solve captcha with 2Captcha", e);
            return null;
        }
    }

    /**
     * Anti-Captcha API 识别
     */
    private String solveAntiCaptcha(byte[] imageBytes) {
        try {
            String base64Image = Base64.getEncoder().encodeToString(imageBytes);
            
            // 创建任务
            String createTaskUrl = "https://api.anti-captcha.com/createTask";
            Map<String, Object> taskData = new HashMap<>();
            taskData.put("clientKey", apiKey);
            
            Map<String, Object> task = new HashMap<>();
            task.put("type", "ImageToTextTask");
            task.put("body", base64Image);
            
            taskData.put("task", task);
            
            String response = postJsonRequest(createTaskUrl, toJson(taskData));
            Map<String, Object> result = parseJson(response);
            
            if (result.containsKey("errorId") && !Integer.valueOf(0).equals(result.get("errorId"))) {
                throw new RuntimeException("Failed to create task: " + result.get("errorDescription"));
            }
            
            Integer taskId = (Integer) result.get("taskId");
            
            // 轮询获取结果
            return pollAntiCaptchaResult(taskId);
        } catch (Exception e) {
            logger.error("Failed to solve captcha with Anti-Captcha", e);
            return null;
        }
    }

    /**
     * CapMonster API 识别
     */
    private String solveCapMonster(byte[] imageBytes) {
        try {
            String base64Image = Base64.getEncoder().encodeToString(imageBytes);
            
            // CapMonster 本地服务 API
            String createTaskUrl = "http://localhost:24999/createTask";
            Map<String, Object> taskData = new HashMap<>();
            
            Map<String, Object> task = new HashMap<>();
            task.put("type", "ImageToTextTask");
            task.put("body", base64Image);
            
            taskData.put("task", task);
            
            String response = postJsonRequest(createTaskUrl, toJson(taskData));
            Map<String, Object> result = parseJson(response);
            
            Integer taskId = (Integer) result.get("taskId");
            
            // 轮询获取结果
            return pollCapMonsterResult(taskId);
        } catch (Exception e) {
            logger.error("Failed to solve captcha with CapMonster", e);
            return null;
        }
    }

    /**
     * DeathByCaptcha 识别
     */
    private String solveDeathByCaptcha(byte[] imageBytes) {
        if (apiKey == null || apiKey.isBlank() || apiSecret == null || apiSecret.isBlank()) {
            logger.warn("DeathByCaptcha credentials missing, falling back to local OCR");
            return solveLocalOCR(imageBytes);
        }

        try {
            String boundary = "----JavaSpiderCaptcha" + System.nanoTime();
            Map<String, String> fields = new HashMap<>();
            fields.put("username", apiKey);
            fields.put("password", apiSecret);

            String response = postMultipartRequest(
                "http://api.dbcapi.me/api/captcha",
                boundary,
                fields,
                "captchafile",
                "captcha.png",
                imageBytes
            );
            Map<String, Object> result = parseJson(response);

            String directText = extractTextResult(result);
            if (directText != null && !directText.isBlank()) {
                return directText;
            }

            Object captchaId = result.get("captcha");
            if (captchaId == null) {
                captchaId = result.get("id");
            }
            if (captchaId != null) {
                return pollDeathByCaptchaResult(String.valueOf(captchaId));
            }
        } catch (Exception e) {
            logger.error("Failed to solve captcha with DeathByCaptcha", e);
        }
        return solveLocalOCR(imageBytes);
    }

    /**
     * 自定义 API 识别
     */
    private String solveCustom(byte[] imageBytes) {
        if (apiKey == null || apiKey.isBlank()) {
            logger.warn("Custom captcha endpoint missing, falling back to local OCR");
            return solveLocalOCR(imageBytes);
        }

        try {
            String response = postJsonRequest(
                apiKey,
                toJson(Map.of(
                    "image", Base64.getEncoder().encodeToString(imageBytes),
                    "image_base64", Base64.getEncoder().encodeToString(imageBytes)
                )),
                apiSecret
            );
            String solved = extractTextResult(parseJson(response));
            if (solved != null && !solved.isBlank()) {
                return solved;
            }
        } catch (Exception e) {
            logger.error("Failed to solve captcha with custom endpoint", e);
        }
        return solveLocalOCR(imageBytes);
    }

    /**
     * 轮询 2Captcha 结果
     */
    private String pollTwoCaptchaResult(String captchaId) throws Exception {
        String resultUrl = "https://2captcha.com/res.php";
        int maxAttempts = 30;
        
        for (int i = 0; i < maxAttempts; i++) {
            Thread.sleep(2000);
            
            String response = getRequest(resultUrl + 
                "?key=" + apiKey +
                "&action=get" +
                "&id=" + captchaId +
                "&json=1");
            
            Map<String, Object> result = parseJson(response);
            
            if ("1".equals(String.valueOf(result.get("status")))) {
                return String.valueOf(result.get("request"));
            }
            
            if (!"CAPCHA_NOT_READY".equals(String.valueOf(result.get("request")))) {
                throw new RuntimeException("Error: " + result.get("request"));
            }
        }
        
        throw new RuntimeException("Captcha solving timeout");
    }

    /**
     * 轮询 Anti-Captcha 结果
     */
    private String pollAntiCaptchaResult(Integer taskId) throws Exception {
        String getTaskResultUrl = "https://api.anti-captcha.com/getTaskResult";
        int maxAttempts = 30;
        
        for (int i = 0; i < maxAttempts; i++) {
            Thread.sleep(2000);
            
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("clientKey", apiKey);
            requestData.put("taskId", taskId);
            
            String response = postJsonRequest(getTaskResultUrl, toJson(requestData));
            Map<String, Object> result = parseJson(response);
            
            if (result.containsKey("errorId") && !Integer.valueOf(0).equals(result.get("errorId"))) {
                throw new RuntimeException("Error: " + result.get("errorDescription"));
            }
            
            if ("ready".equals(String.valueOf(result.get("status")))) {
                Map<String, Object> solution = asObjectMap(result.get("solution"));
                return String.valueOf(solution.get("text"));
            }
        }
        
        throw new RuntimeException("Captcha solving timeout");
    }

    /**
     * 轮询 CapMonster 结果
     */
    private String pollCapMonsterResult(Integer taskId) throws Exception {
        String getTaskResultUrl = "http://localhost:24999/getTaskResult";
        int maxAttempts = 30;
        
        for (int i = 0; i < maxAttempts; i++) {
            Thread.sleep(2000);
            
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("taskId", taskId);
            
            String response = postJsonRequest(getTaskResultUrl, toJson(requestData));
            Map<String, Object> result = parseJson(response);
            
            if ("ready".equals(String.valueOf(result.get("status")))) {
                Map<String, Object> solution = asObjectMap(result.get("solution"));
                return String.valueOf(solution.get("text"));
            }
        }
        
        throw new RuntimeException("Captcha solving timeout");
    }

    /**
     * 图像预处理
     */
    private BufferedImage preprocessImage(BufferedImage image) {
        // 转换为灰度图像
        BufferedImage grayImage = new BufferedImage(image.getWidth(), image.getHeight(), BufferedImage.TYPE_BYTE_GRAY);
        Graphics2D g = grayImage.createGraphics();
        g.drawImage(image, 0, 0, null);
        g.dispose();
        
        // 二值化
        BufferedImage binaryImage = new BufferedImage(image.getWidth(), image.getHeight(), BufferedImage.TYPE_BYTE_BINARY);
        g = binaryImage.createGraphics();
        g.drawImage(grayImage, 0, 0, null);
        g.dispose();
        
        // 降噪
        return denoise(binaryImage);
    }

    /**
     * 图像降噪
     */
    private BufferedImage denoise(BufferedImage image) {
        Kernel kernel = new Kernel(3, 3, new float[]{
            1f/9f, 1f/9f, 1f/9f,
            1f/9f, 1f/9f, 1f/9f,
            1f/9f, 1f/9f, 1f/9f
        });
        ConvolveOp op = new ConvolveOp(kernel);
        return op.filter(image, null);
    }

    /**
     * 简单字符识别
     */
    private String recognizeCharacters(BufferedImage image) {
        // 这是一个简化的实现，实际应该使用更复杂的 OCR 算法
        // 建议使用 Tesseract-OCR 或其他专业 OCR 库
        StringBuilder result = new StringBuilder();
        
        // 简单的模板匹配或特征提取可以在这里实现
        // 这里仅作为示例
        
        int width = image.getWidth();
        int height = image.getHeight();
        
        // 简单的字符分割和识别逻辑
        // 实际应用中应该使用更复杂的算法
        
        logger.warn("Local OCR is basic, consider using Tesseract or third-party service");
        
        return result.toString();
    }

    /**
     * 下载图片
     */
    private byte[] downloadImage(String imageUrl) throws IOException {
        URL url = new URL(imageUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);
        
        try (java.io.InputStream is = conn.getInputStream()) {
            return is.readAllBytes();
        }
    }

    /**
     * BufferedImage 转字节数组
     */
    private byte[] bufferedImageToBytes(BufferedImage image) throws IOException {
        java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
        ImageIO.write(image, "png", baos);
        return baos.toByteArray();
    }

    /**
     * POST 请求
     */
    private String postRequest(String urlString, String data) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
        
        try (java.io.OutputStream os = conn.getOutputStream()) {
            os.write(data.getBytes(StandardCharsets.UTF_8));
        }
        
        try (java.io.InputStream is = conn.getInputStream()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    /**
     * POST JSON 请求
     */
    private String postJsonRequest(String urlString, String json) throws IOException {
        return postJsonRequest(urlString, json, null);
    }

    private String postJsonRequest(String urlString, String json, String bearerToken) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/json");
        if (bearerToken != null && !bearerToken.isBlank()) {
            conn.setRequestProperty("Authorization", "Bearer " + bearerToken);
        }
        
        try (java.io.OutputStream os = conn.getOutputStream()) {
            os.write(json.getBytes(StandardCharsets.UTF_8));
        }
        
        try (java.io.InputStream is = conn.getInputStream()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private String postMultipartRequest(
        String urlString,
        String boundary,
        Map<String, String> fields,
        String fileField,
        String fileName,
        byte[] fileBytes
    ) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

        try (OutputStream os = conn.getOutputStream()) {
            for (Map.Entry<String, String> entry : fields.entrySet()) {
                os.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
                os.write(("Content-Disposition: form-data; name=\"" + entry.getKey() + "\"\r\n\r\n")
                    .getBytes(StandardCharsets.UTF_8));
                os.write(entry.getValue().getBytes(StandardCharsets.UTF_8));
                os.write("\r\n".getBytes(StandardCharsets.UTF_8));
            }

            os.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
            os.write(("Content-Disposition: form-data; name=\"" + fileField + "\"; filename=\"" + fileName + "\"\r\n")
                .getBytes(StandardCharsets.UTF_8));
            os.write("Content-Type: application/octet-stream\r\n\r\n".getBytes(StandardCharsets.UTF_8));
            os.write(fileBytes);
            os.write("\r\n".getBytes(StandardCharsets.UTF_8));
            os.write(("--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
        }

        try (InputStream is = conn.getInputStream()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    /**
     * GET 请求
     */
    private String getRequest(String urlString) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        
        try (java.io.InputStream is = conn.getInputStream()) {
            return new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private String pollDeathByCaptchaResult(String captchaId) throws Exception {
        String resultUrl = "http://api.dbcapi.me/api/captcha/" + captchaId;
        for (int i = 0; i < 15; i++) {
            Thread.sleep(2000);
            String response = getRequest(resultUrl);
            String solved = extractTextResult(parseJson(response));
            if (solved != null && !solved.isBlank()) {
                return solved;
            }
        }
        throw new RuntimeException("DeathByCaptcha solving timeout");
    }

    private String extractTextResult(Map<String, Object> result) {
        if (result == null || result.isEmpty()) {
            return null;
        }
        for (String key : new String[]{"text", "result", "solution"}) {
            Object value = result.get(key);
            if (value != null) {
                String normalized = normalizeSolvedText(String.valueOf(value));
                if (normalized != null && !normalized.isBlank()) {
                    return normalized;
                }
            }
        }

        Object dataValue = result.get("data");
        if (dataValue instanceof Map<?, ?> nestedRaw) {
            Map<String, Object> nested = new HashMap<>();
            for (Map.Entry<?, ?> entry : nestedRaw.entrySet()) {
                nested.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return extractTextResult(nested);
        }
        return null;
    }

    private String normalizeSolvedText(String rawText) {
        if (rawText == null) {
            return null;
        }
        String normalized = rawText
            .replace("\uFEFF", "")
            .replaceAll("\\s+", " ")
            .trim();
        return normalized.isEmpty() ? null : normalized;
    }

    /**
     * 解析 JSON
     */
    private Map<String, Object> parseJson(String json) {
        com.google.gson.Gson gson = new com.google.gson.Gson();
        Type type = new TypeToken<Map<String, Object>>() {}.getType();
        return gson.fromJson(json, type);
    }

    private Map<String, Object> asObjectMap(Object value) {
        if (value instanceof Map<?, ?> rawMap) {
            Map<String, Object> typed = new HashMap<>();
            for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                typed.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return typed;
        }
        return Map.of();
    }

    /**
     * 对象转 JSON
     */
    private String toJson(Object obj) {
        com.google.gson.Gson gson = new com.google.gson.Gson();
        return gson.toJson(obj);
    }

    /**
     * 报告验证码识别错误（用于第三方平台）
     */
    public void reportBad(String captchaId) {
        if (type == CaptchaSolverType.TWOCAPTCHA) {
            try {
                getRequest("https://2captcha.com/res.php" +
                    "?key=" + apiKey +
                    "&action=reportbad" +
                    "&id=" + captchaId);
            } catch (IOException e) {
                logger.error("Failed to report bad captcha", e);
            }
        }
    }

    /**
     * 创建 CaptchaSolver
     */
    public static CaptchaSolver create(CaptchaSolverType type) {
        return new CaptchaSolver(type);
    }

    /**
     * 创建 2Captcha 求解器
     */
    public static CaptchaSolver twoCaptcha(String apiKey) {
        return new CaptchaSolver(CaptchaSolverType.TWOCAPTCHA, apiKey, null);
    }

    /**
     * 创建 Anti-Captcha 求解器
     */
    public static CaptchaSolver antiCaptcha(String apiKey) {
        return new CaptchaSolver(CaptchaSolverType.ANTICAPTCHA, apiKey, null);
    }

    /**
     * 创建 CapMonster 求解器
     */
    public static CaptchaSolver capMonster() {
        return new CaptchaSolver(CaptchaSolverType.CAPMONSTER, null, null);
    }

    /**
     * 创建 DeathByCaptcha 求解器
     */
    public static CaptchaSolver deathByCaptcha(String username, String password) {
        return new CaptchaSolver(CaptchaSolverType.DEATHBYCAPTCHA, username, password);
    }

    /**
     * 创建自定义 API 求解器
     */
    public static CaptchaSolver custom(String endpoint, String bearerToken) {
        return new CaptchaSolver(CaptchaSolverType.CUSTOM, endpoint, bearerToken);
    }
}
