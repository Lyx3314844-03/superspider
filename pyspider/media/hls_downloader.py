"""
HLS/DASH 视频流下载器
支持 M3U8 播放列表解析、TS 分片下载、视频合并
"""

import os
import re
import math
import time
import threading
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from urllib.parse import urljoin, urlparse

from pyspider.media.ffmpeg_tools import FFmpegExecutor, FFmpegNotFoundError


logger = logging.getLogger(__name__)


@dataclass
class MediaSegment:
    """媒体分片"""
    url: str
    duration: float
    title: Optional[str] = None
    sequence: int = 0
    key_uri: Optional[str] = None
    key_iv: Optional[str] = None
    byte_range: Optional[str] = None


@dataclass
class MediaPlaylist:
    """媒体播放列表"""
    target_duration: float
    media_sequence: int
    segments: List[MediaSegment] = field(default_factory=list)
    endlist: bool = False
    version: int = 3
    total_duration: float = 0.0


@dataclass
class StreamInfo:
    """流信息（用于主播放列表）"""
    bandwidth: int
    resolution: Optional[Tuple[int, int]] = None
    codecs: Optional[str] = None
    uri: Optional[str] = None
    frame_rate: Optional[float] = None


class HLSParser:
    """HLS 播放列表解析器"""
    
    def parse_master_playlist(self, content: str) -> List[StreamInfo]:
        """解析主播放列表"""
        streams = []
        current_stream = None
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('#EXT-X-STREAM-INF:'):
                current_stream = self._parse_stream_inf(line)
            elif line and not line.startswith('#') and current_stream:
                current_stream.uri = line
                streams.append(current_stream)
                current_stream = None
        
        return streams
    
    def _parse_stream_inf(self, line: str) -> StreamInfo:
        """解析流信息标签"""
        stream = StreamInfo(bandwidth=0)
        
        # 提取带宽
        match = re.search(r'BANDWIDTH=(\d+)', line)
        if match:
            stream.bandwidth = int(match.group(1))
        
        # 提取分辨率
        match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
        if match:
            stream.resolution = (int(match.group(1)), int(match.group(2)))
        
        # 提取编解码器
        match = re.search(r'CODECS="([^"]+)"', line)
        if match:
            stream.codecs = match.group(1)
        
        # 提取帧率
        match = re.search(r'FRAME-RATE=([\d.]+)', line)
        if match:
            stream.frame_rate = float(match.group(1))
        
        return stream
    
    def parse_media_playlist(self, content: str, base_url: str = '') -> MediaPlaylist:
        """解析媒体播放列表"""
        playlist = MediaPlaylist(
            target_duration=0,
            media_sequence=0,
            segments=[]
        )
        
        current_segment = None
        segment_sequence = 0
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('#EXT-X-TARGETDURATION:'):
                playlist.target_duration = float(line.split(':')[1])
            
            elif line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                playlist.media_sequence = int(line.split(':')[1])
            
            elif line.startswith('#EXT-X-VERSION:'):
                playlist.version = int(line.split(':')[1])
            
            elif line.startswith('#EXT-X-ENDLIST'):
                playlist.endlist = True
            
            elif line.startswith('#EXTINF:'):
                # 解析分片信息
                match = re.match(r'#EXTINF:([\d.]+),\s*(.*)', line)
                if match:
                    current_segment = MediaSegment(
                        url='',
                        duration=float(match.group(1)),
                        title=match.group(2) if match.group(2) else None,
                        sequence=segment_sequence
                    )
                    segment_sequence += 1
            
            elif line.startswith('#EXT-X-KEY:'):
                # 解析加密密钥
                if current_segment:
                    key_info = self._parse_key(line)
                    current_segment.key_uri = key_info.get('URI')
                    current_segment.key_iv = key_info.get('IV')
            
            elif line.startswith('#EXT-X-BYTERANGE:'):
                # 解析字节范围
                if current_segment:
                    current_segment.byte_range = line.split(':')[1]
            
            elif line and not line.startswith('#'):
                # 分片 URL
                if current_segment:
                    current_segment.url = urljoin(base_url, line)
                    playlist.segments.append(current_segment)
                    playlist.total_duration += current_segment.duration
                    current_segment = None
        
        return playlist
    
    def _parse_key(self, line: str) -> Dict:
        """解析密钥信息"""
        key_info = {}
        
        match = re.search(r'METHOD=([^,\s]+)', line)
        if match:
            key_info['METHOD'] = match.group(1)
        
        match = re.search(r'URI="([^"]+)"', line)
        if match:
            key_info['URI'] = match.group(1)
        
        match = re.search(r'IV=([^,\s]+)', line)
        if match:
            key_info['IV'] = match.group(1)
        
        return key_info


class HLSDownloader:
    """HLS 下载器"""
    
    def __init__(
        self,
        output_dir: str = "downloads",
        max_workers: int = 10,
        chunk_size: int = 8192,
        timeout: int = 30,
        retry_times: int = 3
    ):
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.retry_times = retry_times
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.youku.com/',
        })
        
        self.parser = HLSParser()
        self._downloaded_count = 0
        self._failed_count = 0
        self._lock = threading.Lock()
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, m3u8_url: str, output_name: Optional[str] = None) -> bool:
        """
        下载 HLS 视频
        
        Args:
            m3u8_url: M3U8 播放列表 URL
            output_name: 输出文件名
            
        Returns:
            是否成功
        """
        logger.info(f"开始下载：{m3u8_url}")
        
        try:
            # 1. 下载播放列表
            playlist_content = self._fetch_m3u8(m3u8_url)
            if not playlist_content:
                return False
            
            # 2. 解析播放列表
            base_url = self._get_base_url(m3u8_url)
            playlist = self.parser.parse_media_playlist(playlist_content, base_url)
            
            logger.info(f"解析到 {len(playlist.segments)} 个分片，总时长 {playlist.total_duration:.1f}秒")
            
            # 3. 检查是否需要选择最佳流
            if '#EXT-X-STREAM-INF' in playlist_content:
                return self._download_best_stream(m3u8_url, output_name)
            
            # 4. 下载分片
            output_name = output_name or f"video_{int(time.time())}"
            temp_dir = self.output_dir / f"{output_name}_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            success = self._download_segments(playlist.segments, temp_dir)
            
            if success:
                # 5. 合并分片
                output_file = self.output_dir / f"{output_name}.ts"
                self._merge_segments(playlist.segments, temp_dir, output_file)
                
                # 6. 清理临时文件
                self._cleanup_temp(temp_dir)
                
                logger.info(f"下载完成：{output_file}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"下载失败：{e}")
            return False
    
    def _fetch_m3u8(self, url: str) -> Optional[str]:
        """获取 M3U8 内容"""
        for attempt in range(self.retry_times):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                logger.warning(f"获取 M3U8 失败 (尝试 {attempt+1}/{self.retry_times}): {e}")
                time.sleep(2 ** attempt)
        return None
    
    def _get_base_url(self, url: str) -> str:
        """获取基础 URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/', 1)[0]}/"
    
    def _download_best_stream(self, master_url: str, output_name: Optional[str] = None) -> bool:
        """下载最佳流"""
        content = self._fetch_m3u8(master_url)
        if not content:
            return False
        
        streams = self.parser.parse_master_playlist(content)
        if not streams:
            # 可能是媒体播放列表，直接下载
            return self.download(master_url, output_name)
        
        # 选择带宽最高的流
        best_stream = max(streams, key=lambda s: s.bandwidth)
        
        logger.info(f"选择最佳流：带宽 {best_stream.bandwidth}, 分辨率 {best_stream.resolution}")
        
        if best_stream.uri:
            stream_url = urljoin(master_url, best_stream.uri)
            return self.download(stream_url, output_name)
        
        return False
    
    def _download_segments(
        self,
        segments: List[MediaSegment],
        output_dir: Path
    ) -> bool:
        """下载所有分片"""
        self._downloaded_count = 0
        self._failed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_segment, seg, output_dir): seg
                for seg in segments
            }
            
            for future in as_completed(futures):
                segment = futures[future]
                try:
                    success = future.result()
                    if not success:
                        logger.warning(f"分片下载失败：{segment.url}")
                except Exception as e:
                    logger.error(f"分片下载异常：{e}")
        
        success_rate = self._downloaded_count / max(len(segments), 1)
        logger.info(f"分片下载完成：成功 {self._downloaded_count}, 失败 {self._failed_count}, 成功率 {success_rate:.1%}")
        
        return success_rate > 0.9
    
    def _download_segment(
        self,
        segment: MediaSegment,
        output_dir: Path
    ) -> bool:
        """下载单个分片"""
        filename = output_dir / f"{segment.sequence:06d}.ts"
        
        for attempt in range(self.retry_times):
            try:
                resp = self.session.get(segment.url, timeout=self.timeout, stream=True)
                resp.raise_for_status()
                
                with open(filename, 'wb') as f:
                    for chunk in resp.iter_content(self.chunk_size):
                        if chunk:
                            f.write(chunk)
                
                with self._lock:
                    self._downloaded_count += 1
                
                return True
                
            except Exception as e:
                logger.debug(f"分片下载失败 (尝试 {attempt+1}/{self.retry_times}): {e}")
                time.sleep(2 ** attempt)
        
        with self._lock:
            self._failed_count += 1
        
        return False
    
    def _merge_segments(
        self,
        segments: List[MediaSegment],
        temp_dir: Path,
        output_file: Path
    ):
        """合并分片"""
        logger.info(f"合并 {len(segments)} 个分片...")
        
        with open(output_file, 'wb') as outfile:
            for segment in sorted(segments, key=lambda s: s.sequence):
                filename = temp_dir / f"{segment.sequence:06d}.ts"
                if filename.exists():
                    with open(filename, 'rb') as infile:
                        outfile.write(infile.read())
        
        logger.info(f"合并完成：{output_file}")
    
    def _cleanup_temp(self, temp_dir: Path):
        """清理临时文件"""
        import shutil
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"清理临时目录：{temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败：{e}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'downloaded': self._downloaded_count,
            'failed': self._failed_count,
            'success_rate': self._downloaded_count / max(self._downloaded_count + self._failed_count, 1)
        }


class DASHParser:
    """DASH 播放列表解析器"""
    
    def parse_mpd(self, content: str, base_url: str = '') -> Dict:
        """解析 MPD 文件"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(content)
            ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
            
            result = {
                'type': root.get('type', 'static'),
                'media_presentation_duration': root.get('mediaPresentationDuration'),
                'min_buffer_time': root.get('minBufferTime'),
                'periods': []
            }
            
            # 解析 Period
            for period in root.findall('.//mpd:Period', ns):
                period_info = {
                    'duration': period.get('duration'),
                    'adaptations': []
                }
                
                # 解析 AdaptationSet
                for adaptation in period.findall('.//mpd:AdaptationSet', ns):
                    mime_type = adaptation.get('mimeType')
                    if not mime_type:
                        content_type = adaptation.get('contentType')
                        if content_type:
                            mime_type = f"{content_type}/mp4"

                    adaptation_info = {
                        'mimeType': mime_type,
                        'representations': []
                    }
                    
                    # 解析 Representation
                    for rep in adaptation.findall('.//mpd:Representation', ns):
                        rep_info = {
                            'id': rep.get('id'),
                            'bandwidth': rep.get('bandwidth'),
                            'width': rep.get('width'),
                            'height': rep.get('height'),
                            'segments': []
                        }
                        
                        # 解析 SegmentTemplate
                        seg_template = rep.find('mpd:SegmentTemplate', ns)
                        if seg_template is not None:
                            rep_info['initialization'] = seg_template.get('initialization')
                            rep_info['segment_template'] = {
                                'media': seg_template.get('media'),
                                'initialization': seg_template.get('initialization'),
                                'start_number': seg_template.get('startNumber', '1'),
                                'timescale': seg_template.get('timescale', '1'),
                                'duration': seg_template.get('duration'),
                            }

                        rep_info['period_duration'] = period.get('duration')
                        rep_info['mpd_type'] = result['type']
                        
                        # 解析 SegmentList
                        seg_list = rep.find('mpd:SegmentList', ns)
                        if seg_list is not None:
                            initialization = seg_list.find('mpd:Initialization', ns)
                            if initialization is not None:
                                rep_info['initialization'] = initialization.get('sourceURL')

                            for seg_url in seg_list.findall('.//mpd:SegmentURL', ns):
                                rep_info['segments'].append({
                                    'media': seg_url.get('media'),
                                    'media_range': seg_url.get('mediaRange'),
                                })
                        
                        adaptation_info['representations'].append(rep_info)
                    
                    period_info['adaptations'].append(adaptation_info)
                
                result['periods'].append(period_info)
            
            return result
            
        except Exception as e:
            logger.error(f"解析 MPD 失败：{e}")
            return {}


class DASHDownloader:
    """DASH 下载器"""
    
    def __init__(
        self,
        output_dir: str = "downloads",
        max_workers: int = 10,
        timeout: int = 30
    ):
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.timeout = timeout
        
        self.session = requests.Session()
        self.parser = DASHParser()
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, mpd_url: str, output_name: Optional[str] = None) -> bool:
        """下载 DASH 视频"""
        logger.info(f"开始下载 DASH: {mpd_url}")
        
        try:
            # 1. 下载 MPD
            resp = self.session.get(mpd_url, timeout=self.timeout)
            resp.raise_for_status()
            
            # 2. 解析 MPD
            base_url = self._get_base_url(mpd_url)
            mpd = self.parser.parse_mpd(resp.text, base_url)
            
            if not mpd or not mpd.get('periods'):
                logger.error("无法解析 MPD")
                return False
            
            # 3. 选择最佳音视频流
            video_rep = self._select_best_representation(mpd, "video/")
            audio_rep = self._select_best_representation(mpd, "audio/")

            if not video_rep and not audio_rep:
                return False
            
            # 4. 下载分片
            output_name = output_name or f"dash_video_{int(time.time())}"
            temp_dir = self.output_dir / f"{output_name}_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            output_file = self.output_dir / f"{output_name}.mp4"
            video_file = None
            audio_file = None

            if video_rep:
                video_dir = temp_dir / "video"
                if not self._download_dash_segments(video_rep, base_url, video_dir):
                    self._cleanup_temp(temp_dir)
                    return False
                video_file = temp_dir / "video.mp4"
                self._merge_dash_segments(video_rep, video_dir, video_file)

            if audio_rep:
                audio_dir = temp_dir / "audio"
                if not self._download_dash_segments(audio_rep, base_url, audio_dir):
                    self._cleanup_temp(temp_dir)
                    return False
                audio_file = temp_dir / "audio.mp4"
                self._merge_dash_segments(audio_rep, audio_dir, audio_file)

            success = False
            if video_file and audio_file:
                success = self._mux_dash_tracks(video_file, audio_file, output_file)
            elif video_file:
                os.replace(video_file, output_file)
                success = True
            elif audio_file:
                os.replace(audio_file, output_file)
                success = True

            if not success and output_file.exists():
                output_file.unlink()

            self._cleanup_temp(temp_dir)

            if success:
                logger.info(f"DASH 下载完成：{output_file}")
                return True

            return False
            
        except Exception as e:
            logger.error(f"DASH 下载失败：{e}")
            return False
    
    def _select_best_representation(self, mpd: Dict, mime_prefix: str) -> Optional[Dict]:
        """选择最佳表示"""
        best_bandwidth = 0
        best_rep = None
        
        for period in mpd.get('periods', []):
            for adaptation in period.get('adaptations', []):
                mime_type = adaptation.get('mimeType') or ''
                if mime_type.startswith(mime_prefix):
                    for rep in adaptation.get('representations', []):
                        bandwidth = int(rep.get('bandwidth', 0))
                        if bandwidth > best_bandwidth:
                            best_bandwidth = bandwidth
                            best_rep = rep
        
        return best_rep
    
    def _download_dash_segments(
        self,
        representation: Dict,
        base_url: str,
        output_dir: Path
    ) -> bool:
        """下载 DASH 分片"""
        output_dir.mkdir(parents=True, exist_ok=True)

        initialization = representation.get('initialization')
        segments = representation.get('segments', [])
        seg_template = representation.get('segment_template', {})

        if initialization and seg_template:
            initialization = self._resolve_segment_template_value(
                initialization,
                representation,
                int(seg_template.get('start_number') or 1),
                0,
            )
            representation['initialization'] = initialization

        if initialization:
            init_url = urljoin(base_url, initialization)
            init_file = output_dir / "init.mp4"

            try:
                resp = self.session.get(init_url, timeout=self.timeout)
                resp.raise_for_status()

                with open(init_file, 'wb') as f:
                    f.write(resp.content)
            except Exception as e:
                logger.warning(f"初始化分片下载失败：{e}")
                return False
        
        if not segments:
            # 使用 SegmentTemplate 生成 URLs
            if seg_template:
                segments = self._build_segments_from_template(representation, seg_template)
                if not segments:
                    logger.warning("SegmentTemplate 下载失败：无法生成分片 URL")
                    return False
                representation['segments'] = segments
        
        # 下载分片
        downloaded = 0
        for i, segment in enumerate(segments):
            media_url = urljoin(base_url, segment.get('media', ''))
            filename = output_dir / f"{i:06d}.m4s"
            
            try:
                resp = self.session.get(media_url, timeout=self.timeout)
                resp.raise_for_status()
                
                with open(filename, 'wb') as f:
                    f.write(resp.content)
                
                downloaded += 1
            except Exception as e:
                logger.warning(f"分片下载失败：{e}")
        
        logger.info(f"DASH 分片下载完成：{downloaded}/{len(segments)}")
        return downloaded == len(segments)

    def _build_segments_from_template(
        self,
        representation: Dict,
        seg_template: Dict
    ) -> List[Dict]:
        """从 SegmentTemplate 生成静态 MPD 的分片 URL"""
        media_template = seg_template.get('media')
        if not media_template:
            return []

        try:
            timescale = int(seg_template.get('timescale') or 1)
            start_number = int(seg_template.get('start_number') or 1)
            segment_duration = int(seg_template.get('duration') or 0)
        except (TypeError, ValueError):
            return []

        if timescale <= 0 or segment_duration <= 0:
            return []

        mpd_type = representation.get('mpd_type', 'static')
        if mpd_type != 'static':
            logger.warning("动态 MPD 的 SegmentTemplate 仍未支持")
            return []

        period_duration = self._parse_iso8601_duration(representation.get('period_duration'))
        if period_duration <= 0:
            return []

        segment_seconds = segment_duration / timescale
        segment_count = max(1, math.ceil(period_duration / segment_seconds))
        generated = []

        for i in range(segment_count):
            number = start_number + i
            time_value = i * segment_duration
            media = self._resolve_segment_template_value(
                media_template,
                representation,
                number,
                time_value,
            )
            generated.append({"media": media, "media_range": None})

        return generated

    def _resolve_segment_template_value(
        self,
        template: str,
        representation: Dict,
        number: int,
        time_value: int,
    ) -> str:
        """替换 SegmentTemplate 中常见占位符"""
        value = template or ""
        value = value.replace("$RepresentationID$", str(representation.get('id', '')))
        value = value.replace("$Number%04d$", f"{number:04d}")
        value = value.replace("$Number$", str(number))
        value = value.replace("$Time$", str(time_value))
        return value

    def _parse_iso8601_duration(self, value: Optional[str]) -> float:
        """解析简单 ISO 8601 时长，例如 PT6S / PT1M30S"""
        if not value:
            return 0.0

        match = re.fullmatch(
            r'P(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?(?:(?P<minutes>\d+(?:\.\d+)?)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?)',
            value,
        )
        if not match:
            return 0.0

        hours = float(match.group('hours') or 0)
        minutes = float(match.group('minutes') or 0)
        seconds = float(match.group('seconds') or 0)
        return hours * 3600 + minutes * 60 + seconds

    def _merge_dash_segments(
        self,
        representation: Dict,
        temp_dir: Path,
        output_file: Path
    ):
        """合并 DASH 初始化片段和媒体分片"""
        with open(output_file, 'wb') as outfile:
            init_file = temp_dir / "init.mp4"
            if representation.get('initialization') and init_file.exists():
                with open(init_file, 'rb') as infile:
                    outfile.write(infile.read())

            for i, _ in enumerate(representation.get('segments', [])):
                segment_file = temp_dir / f"{i:06d}.m4s"
                if segment_file.exists():
                    with open(segment_file, 'rb') as infile:
                        outfile.write(infile.read())

    def _mux_dash_tracks(self, video_file: Path, audio_file: Path, output_file: Path) -> bool:
        """使用 FFmpeg 合并 DASH 音视频轨"""
        try:
            executor = FFmpegExecutor()
        except FFmpegNotFoundError as e:
            logger.error(f"DASH 音视频合并失败：{e}")
            return False

        success = executor.run(
            ["-i", str(audio_file), "-c", "copy"],
            input_file=str(video_file),
            output_file=str(output_file),
        )
        if not success:
            logger.error("DASH 音视频合并失败")
        return success

    def _cleanup_temp(self, temp_dir: Path):
        """清理临时文件"""
        import shutil

        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"清理临时目录失败：{e}")
    
    def _get_base_url(self, url: str) -> str:
        """获取基础 URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rsplit('/', 1)[0]}/"


# 使用示例
if __name__ == "__main__":
    import sys
    
    # HLS 下载示例
    if len(sys.argv) > 1:
        m3u8_url = sys.argv[1]
        
        downloader = HLSDownloader(
            output_dir="downloads",
            max_workers=10,
            retry_times=3
        )
        
        success = downloader.download(m3u8_url, "output_video")
        
        if success:
            print(f"✓ 下载完成")
            print(f"统计：{downloader.get_stats()}")
        else:
            print("✗ 下载失败")
    else:
        print("用法：python hls_downloader.py <m3u8_url>")
