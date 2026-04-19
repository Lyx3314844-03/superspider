package com.javaspider.media.parser;

public class TencentParser implements VideoParser {
    private final GenericParser genericParser = new GenericParser();

    @Override
    public boolean supports(String url) {
        String lower = url.toLowerCase();
        return lower.contains("v.qq.com") || lower.contains("qq.com");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = genericParser.parse(url);
        info.setPlatform("Tencent");
        return info;
    }
}
