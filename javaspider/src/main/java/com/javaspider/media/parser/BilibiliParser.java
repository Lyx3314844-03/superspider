package com.javaspider.media.parser;

public class BilibiliParser implements VideoParser {
    private final GenericParser genericParser = new GenericParser();

    @Override
    public boolean supports(String url) {
        String lower = url.toLowerCase();
        return lower.contains("bilibili.com") || lower.contains("b23.tv");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = genericParser.parse(url);
        info.setPlatform("Bilibili");
        return info;
    }
}
