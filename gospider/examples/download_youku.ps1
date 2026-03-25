# 优酷视频下载脚本

$outputDir = "C:\Users\Administrator\spider\gospider\downloads\youku_video"
if (!(Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

# 视频链接（使用之前捕获的链接）
$videoUrls = @(
    "https://valipl.cp31.ott.cibntv.net/67756D6080932713CFC02204E/0500CC000065D318F1EDD14ABB79034128B118-8E42-4F91-82DE-5F16F31C41CB_video_init.mp4?ccode=0597&duration=4805&expire=18000&psid=482d1ca2ef30d94c8ab9533e3d39e50741346&ups_client_netip=75bc0d1d&ups_ts=1774012224&ups_userid=&apscid=&mnid=&operate_type=1&umt=1&type=cmfv4hd2&utid=HjVEIgjFZWQCAS2H5F6%2FvvAz&vid=XNTk4Mjg1MjEzMg%3D%3D&s=cfeb97262f9f4d29b86b&t=a14c06ab5bbec39&cug=2&bc=2&si=774&eo=1&ckt=5&m_onoff=0&fms=dbd407cee631b819&tr=4805&le=3d264632e6fc2ca3b5e45b931581cbf9&app_key=34300712&app_ver=9.8.2&vkey=Bac84e069d0d13e1e4503d81dd57371eb",
    "https://valipl.cp31.ott.cibntv.net/67756D6080932713CFC02204E/0500CC000065D318F1EDD14ABB79034128B118-8E42-4F91-82DE-5F16F31C41CB_video_00001.mp4?ccode=0597&duration=4805&expire=18000&psid=482d1ca2ef30d94c8ab9533e3d39e50741346&ups_client_netip=75bc0d1d&ups_ts=1774012224&ups_userid=&apscid=&mnid=&rid=200000004292910304B3C8DE6274B22A81F33C4602000000&operate_type=1&umt=1&type=cmfv4hd2&utid=HjVEIgjFZWQCAS2H5F6%2FvvAz&vid=XNTk4Mjg1MjEzMg%3D%3D&s=cfeb97262f9f4d29b86b&t=a14c06ab5bbec39&cug=2&bc=2&si=774&eo=1&ckt=5&m_onoff=0&fms=dbd407cee631b819&tr=4805&le=3d264632e6fc2ca3b5e45b931581cbf9&app_key=34300712&app_ver=9.8.2&vkey=B6a22a938fea08e05abd83c6c873fe855",
    "https://valipl.cp31.ott.cibntv.net/67756D6080932713CFC02204E/0500CC000065D318F1EDD14ABB79034128B118-8E42-4F91-82DE-5F16F31C41CB_video_00002.mp4?ccode=0597&duration=4805&expire=18000&psid=482d1ca2ef30d94c8ab9533e3d39e50741346&ups_client_netip=75bc0d1d&ups_ts=1774012224&ups_userid=&apscid=&mnid=&rid=200000004292910304B3C8DE6274B22A81F33C4602000000&operate_type=1&umt=1&type=cmfv4hd2&utid=HjVEIgjFZWQCAS2H5F6%2FvvAz&vid=XNTk4Mjg1MjEzMg%3D%3D&s=cfeb97262f9f4d29b86b&t=a14c06ab5bbec39&cug=2&bc=2&si=774&eo=1&ckt=5&m_onoff=0&fms=dbd407cee631b819&tr=4805&le=3d264632e6fc2ca3b5e45b931581cbf9&app_key=34300712&app_ver=9.8.2&vkey=Beb1b1c133ab2b1ddfe405e84f11b6a77",
    "https://valipl.cp31.ott.cibntv.net/67756D6080932713CFC02204E/0500CC000065D318F1EDD14ABB79034128B118-8E42-4F91-82DE-5F16F31C41CB_video_00003.mp4?ccode=0597&duration=4805&expire=18000&psid=482d1ca2ef30d94c8ab9533e3d39e50741346&ups_client_netip=75bc0d1d&ups_ts=1774012224&ups_userid=&apscid=&mnid=&rid=200000004292910304B3C8DE6274B22A81F33C4602000000&operate_type=1&umt=1&type=cmfv4hd2&utid=HjVEIgjFZWQCAS2H5F6%2FvvAz&vid=XNTk4Mjg1MjEzMg%3D%3D&s=cfeb97262f9f4d29b86b&t=a14c06ab5bbec39&cug=2&bc=2&si=774&eo=1&ckt=5&m_onoff=0&fms=dbd407cee631b819&tr=4805&le=3d264632e6fc2ca3b5e45b931581cbf9&app_key=34300712&app_ver=9.8.2&vkey=Bab3de624d9bacf70139095e3de6a7efc"
)

Write-Host "=== 优酷视频下载器 ===" -ForegroundColor Cyan
Write-Host "下载目录：$outputDir" -ForegroundColor Yellow
Write-Host ""

# 下载视频分段
for ($i = 0; $i -lt $videoUrls.Count; $i++) {
    $url = $videoUrls[$i]
    $outputFile = Join-Path $outputDir "video_segment_$($i.ToString("D3")).mp4"
    
    Write-Host "正在下载分段 $($i+1)/$($videoUrls.Count)..." -NoNewline
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $outputFile -UseBasicParsing
        Write-Host " 完成！" -ForegroundColor Green
    }
    catch {
        Write-Host " 失败：$_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== 下载完成 ===" -ForegroundColor Cyan
Write-Host "视频分段已保存到：$outputDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示：使用 ffmpeg 合并视频：" -ForegroundColor Yellow
Write-Host "  ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4" -ForegroundColor White
