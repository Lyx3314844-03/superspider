package com.spider.javaspider.enhanced;

/**
 * 爬取统计信息
 */
public class CrawlStats {
    private int totalVideos;
    private int uniqueChannels;
    private long crawlTime;
    private String startTime;
    private String endTime;
    private String totalDuration;
    
    public CrawlStats() {}
    
    public CrawlStats(int totalVideos, int uniqueChannels, long crawlTime) {
        this.totalVideos = totalVideos;
        this.uniqueChannels = uniqueChannels;
        this.crawlTime = crawlTime;
    }
    
    /**
     * 转换为 JSON 字符串
     */
    public String toJson() {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"total_videos\":").append(totalVideos).append(",");
        json.append("\"unique_channels\":").append(uniqueChannels).append(",");
        json.append("\"crawl_time\":").append(crawlTime).append(",");
        json.append("\"start_time\":\"").append(startTime != null ? startTime : "").append("\",");
        json.append("\"end_time\":\"").append(endTime != null ? endTime : "").append("\"");
        json.append("}");
        return json.toString();
    }
    
    // Getters and Setters
    public int getTotalVideos() { return totalVideos; }
    public void setTotalVideos(int totalVideos) { this.totalVideos = totalVideos; }
    
    public int getUniqueChannels() { return uniqueChannels; }
    public void setUniqueChannels(int uniqueChannels) { this.uniqueChannels = uniqueChannels; }
    
    public long getCrawlTime() { return crawlTime; }
    public void setCrawlTime(long crawlTime) { this.crawlTime = crawlTime; }
    
    public String getStartTime() { return startTime; }
    public void setStartTime(String startTime) { this.startTime = startTime; }
    
    public String getEndTime() { return endTime; }
    public void setEndTime(String endTime) { this.endTime = endTime; }
    
    public String getTotalDuration() { return totalDuration; }
    public void setTotalDuration(String totalDuration) { this.totalDuration = totalDuration; }
    
    @Override
    public String toString() {
        return "CrawlStats{" +
            "totalVideos=" + totalVideos +
            ", uniqueChannels=" + uniqueChannels +
            ", crawlTime=" + crawlTime +
            ", startTime='" + startTime + '\'' +
            ", endTime='" + endTime + '\'' +
            '}';
    }
}
