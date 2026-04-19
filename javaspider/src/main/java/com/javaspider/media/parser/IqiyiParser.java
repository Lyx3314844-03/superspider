package com.javaspider.media.parser;

public class IqiyiParser implements VideoParser {
    private final GenericParser genericParser = new GenericParser();

    @Override
    public boolean supports(String url) {
        return url.toLowerCase().contains("iqiyi.com");
    }

    @Override
    public VideoInfo parse(String url) throws Exception {
        VideoInfo info = genericParser.parse(url);
        info.setPlatform("IQIYI");
        return info;
    }
}
