package com.javaspider.downloader;

import com.javaspider.core.Request;
import com.javaspider.core.Site;
import com.javaspider.core.Page;

/**
 * 下载器接口
 */
public interface Downloader {
    Page download(Request request, Site site);
}
