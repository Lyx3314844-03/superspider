package com.javaspider.downloader;

import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClients;

import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Page;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.apache.http.HttpEntity;
import org.apache.http.util.EntityUtils;

/**
 * HTTP 客户端下载器
 */
public class HttpClientDownloader implements Downloader {
    
    @Override
    public Page download(Request request, Site site) {
        Page page = new Page();
        page.setRequest(request);
        page.setUrl(request.getUrl());
        
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpGet httpGet = new HttpGet(request.getUrl());
            
            // 设置请求头
            if (request.getHeaders() != null) {
                for (String key : request.getHeaders().keySet()) {
                    httpGet.addHeader(key, request.getHeaders().get(key));
                }
            }
            
            // 设置 User-Agent
            if (site != null && site.getUserAgent() != null) {
                httpGet.addHeader("User-Agent", site.getUserAgent());
            }
            
            try (CloseableHttpResponse response = httpClient.execute(httpGet)) {
                page.setStatusCode(response.getStatusLine().getStatusCode());
                
                HttpEntity entity = response.getEntity();
                if (entity != null) {
                    String content = EntityUtils.toString(entity, StandardCharsets.UTF_8);
                    page.setRawText(content);
                    page.setDownloadDuration(System.currentTimeMillis());
                }
            }
        } catch (IOException e) {
            page.setSkip(true);
        }
        
        return page;
    }
}
