package com.javaspider.media.parser;

public class DouyinParser implements VideoParser {
    private final GenericParser genericParser = new GenericParser();

    @Override
    public boolean supports(String url) {
        String lower = url.toLowerCase();
        return lower.contains("douyin.com");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = genericParser.parse(url);
        info.setPlatform("Douyin");
        return info;
    }
}
