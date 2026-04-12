package com.spider.converter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/**
 * curlconverter 集成模块
 * 将 curl 命令转换为 Java 代码
 */
public class CurlToJavaConverter {
    
    private boolean useCLI = true;
    
    /**
     * 创建转换器
     */
    public CurlToJavaConverter() {
    }
    
    /**
     * 将 curl 命令转换为 Java 代码
     *
     * @param curlCommand curl 命令字符串
     * @return 转换后的 Java 代码
     * @throws IOException 如果转换失败
     */
    public String convert(String curlCommand) throws IOException {
        // 尝试直接使用 curlconverter
        String javaCode = runCurlconverter("curlconverter", curlCommand);
        
        // 如果失败，尝试使用 npx
        if (javaCode == null) {
            javaCode = runCurlconverter("npx", curlCommand);
        }
        
        if (javaCode != null) {
            return javaCode;
        }
        
        throw new IOException("curlconverter 执行失败，请检查安装");
    }
    
    /**
     * 运行 curlconverter 命令
     */
    private String runCurlconverter(String command, String curlCommand) throws IOException {
        ProcessBuilder pb;
        if ("npx".equals(command)) {
            pb = new ProcessBuilder("npx", "curlconverter", "--language", "java", "-");
        } else {
            pb = new ProcessBuilder("curlconverter", "--language", "java", "-");
        }
        pb.redirectErrorStream(true);

        Process process = pb.start();

        // 写入 curl 命令到 stdin
        try (OutputStream os = process.getOutputStream()) {
            os.write(curlCommand.getBytes(StandardCharsets.UTF_8));
            os.flush();
        }

        // 读取输出
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
        }

        try {
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                return null;  // 失败，返回 null
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("转换被中断", e);
        }

        return output.toString();
    }
    
    /**
     * 转换为使用 HttpURLConnection 的代码
     * 
     * @param curlCommand curl 命令字符串
     * @return Java 代码
     */
    public String convertToHttpURLConnection(String curlCommand) {
        try {
            String javaCode = convert(curlCommand);
            // 添加必要的 import
            if (!javaCode.contains("import")) {
                javaCode = "import java.net.HttpURLConnection;\n" +
                          "import java.net.URL;\n" +
                          "import java.io.BufferedReader;\n" +
                          "import java.io.InputStreamReader;\n" +
                          "import java.io.OutputStream;\n\n" + javaCode;
            }
            return javaCode;
        } catch (IOException e) {
            return "// 转换失败: " + e.getMessage();
        }
    }
    
    /**
     * 转换为使用 OkHttp 的代码
     * 
     * @param curlCommand curl 命令字符串
     * @return Java 代码
     */
    public String convertToOkHttp(String curlCommand) {
        // 提供 OkHttp 模板
        return String.format(
            "import okhttp3.*;\n" +
            "import java.io.IOException;\n" +
            "import java.util.concurrent.TimeUnit;\n\n" +
            "public class Main {\n" +
            "    private static final OkHttpClient client = new OkHttpClient.Builder()\n" +
            "        .connectTimeout(30, TimeUnit.SECONDS)\n" +
            "        .readTimeout(30, TimeUnit.SECONDS)\n" +
            "        .writeTimeout(30, TimeUnit.SECONDS)\n" +
            "        .build();\n\n" +
            "    public static void main(String[] args) throws IOException {\n" +
            "        // curl: %s\n" +
            "        \n" +
            "        Request request = new Request.Builder()\n" +
            "            .url(\"https://httpbin.org/get\")\n" +
            "            .get()\n" +
            "            .build();\n\n" +
            "        try (Response response = client.newCall(request).execute()) {\n" +
            "            System.out.println(response.body().string());\n" +
            "        }\n" +
            "    }\n" +
            "}\n",
            curlCommand
        );
    }
    
    /**
     * 转换为使用 Apache HttpClient 的代码
     * 
     * @param curlCommand curl 命令字符串
     * @return Java 代码
     */
    public String convertToApacheHttpClient(String curlCommand) {
        // 提供 Apache HttpClient 模板
        return String.format(
            "import org.apache.http.HttpResponse;\n" +
            "import org.apache.http.client.methods.HttpGet;\n" +
            "import org.apache.http.impl.client.CloseableHttpClient;\n" +
            "import org.apache.http.impl.client.HttpClients;\n" +
            "import org.apache.http.util.EntityUtils;\n" +
            "import java.io.IOException;\n\n" +
            "public class Main {\n" +
            "    public static void main(String[] args) throws IOException {\n" +
            "        // curl: %s\n" +
            "        \n" +
            "        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {\n" +
            "            HttpGet request = new HttpGet(\"https://httpbin.org/get\");\n" +
            "            request.addHeader(\"Accept\", \"application/json\");\n\n" +
            "            HttpResponse response = httpClient.execute(request);\n" +
            "            String result = EntityUtils.toString(response.getEntity());\n" +
            "            System.out.println(result);\n" +
            "        }\n" +
            "    }\n" +
            "}\n",
            curlCommand
        );
    }
    
    /**
     * 安装 curlconverter CLI 工具
     */
    public static void installCurlconverter() {
        try {
            System.out.println("正在安装 curlconverter...");
            
            ProcessBuilder pb = new ProcessBuilder("npm", "install", "-g", "curlconverter");
            pb.inheritIO();
            Process process = pb.start();
            int exitCode = process.waitFor();
            
            if (exitCode == 0) {
                System.out.println("✓ curlconverter 安装成功");
            } else {
                System.out.println("✗ curlconverter 安装失败，退出码: " + exitCode);
            }
        } catch (IOException | InterruptedException e) {
            System.err.println("安装失败: " + e.getMessage());
            Thread.currentThread().interrupt();
        }
    }
    
    /**
     * 便捷函数：将 curl 命令转换为 Java 代码
     * 
     * @param curlCommand curl 命令字符串
     * @return 转换后的 Java 代码
     */
    public static String curlToJava(String curlCommand) {
        CurlToJavaConverter converter = new CurlToJavaConverter();
        try {
            return converter.convert(curlCommand);
        } catch (IOException e) {
            return "// 转换失败: " + e.getMessage();
        }
    }
    
    /**
     * 主函数 - 测试
     */
    public static void main(String[] args) {
        String testCurl = "curl -X GET \"https://httpbin.org/get\" -H \"Accept: application/json\"";
        
        System.out.println("测试 curl 命令:");
        System.out.println(testCurl);
        System.out.println("\n转换后的 Java 代码 (OkHttp):");
        System.out.println(curlToJava(testCurl));
    }
}
