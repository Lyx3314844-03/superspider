"""
FFmpeg 深度集成模块
支持视频转换、合并、压缩、截图、音频提取等
"""

import os
import subprocess
import json
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import logging
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """视频信息"""

    filename: str
    duration: float
    size: int
    format: str
    video_codec: str
    audio_codec: str
    resolution: Tuple[int, int]
    bitrate: int
    frame_rate: float
    has_audio: bool
    has_video: bool


@dataclass
class FFmpegProgress:
    """FFmpeg 进度"""

    time: float
    frame: int
    fps: float
    speed: float
    percent: float


class FFmpegNotFoundError(Exception):
    """FFmpeg 未找到"""

    pass


class FFmpegExecutor:
    """FFmpeg 执行器"""

    def __init__(
        self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None
    ):
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()

        if not self.ffmpeg_path:
            raise FFmpegNotFoundError(
                "未找到 ffmpeg，请安装或指定路径。\n"
                "Windows: choco install ffmpeg\n"
                "Linux: sudo apt install ffmpeg\n"
                "macOS: brew install ffmpeg"
            )

        if not self.ffprobe_path:
            logger.warning("未找到 ffprobe，部分功能可能不可用")

    def _find_ffmpeg(self) -> Optional[str]:
        """查找 ffmpeg"""
        # 尝试 PATH
        path = self._which("ffmpeg")
        if path:
            return path

        # 尝试常见路径
        common_paths = [
            r"C:\ffmpeg\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Users\Administrator\ffmpeg\bin\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
        ]

        for p in common_paths:
            if os.path.exists(p):
                return p

        return None

    def _find_ffprobe(self) -> Optional[str]:
        """查找 ffprobe"""
        path = self._which("ffprobe")
        if path:
            return path

        # 尝试与 ffmpeg 同目录
        if self.ffmpeg_path:
            ffprobe = os.path.join(
                os.path.dirname(self.ffmpeg_path),
                "ffprobe.exe" if os.name == "nt" else "ffprobe",
            )
            if os.path.exists(ffprobe):
                return ffprobe

        return None

    def _which(self, name: str) -> Optional[str]:
        """在 PATH 中查找可执行文件"""
        for path in os.environ.get("PATH", "").split(os.pathsep):
            exe = os.path.join(path, f"{name}.exe" if os.name == "nt" else name)
            if os.path.isfile(exe) and os.access(exe, os.X_OK):
                return exe
        return None

    def run(
        self,
        args: List[str],
        input_file: Optional[str] = None,
        output_file: Optional[str] = None,
        overwrite: bool = True,
        capture_progress: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> bool:
        """
        运行 FFmpeg

        Args:
            args: FFmpeg 参数列表
            input_file: 输入文件
            output_file: 输出文件
            overwrite: 是否覆盖已存在文件
            capture_progress: 是否捕获进度
            progress_callback: 进度回调函数

        Returns:
            是否成功
        """
        cmd = [self.ffmpeg_path]

        if overwrite:
            cmd.append("-y")

        if input_file:
            cmd.extend(["-i", input_file])

        cmd.extend(args)

        if output_file:
            cmd.append(output_file)

        logger.info(f"执行：{' '.join(cmd)}")

        try:
            if capture_progress:
                return self._run_with_progress(cmd, progress_callback)
            else:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=3600  # 1 小时超时
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg 错误：{result.stderr}")
                    return False

                logger.info("FFmpeg 执行完成")
                return True

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg 执行超时")
            return False
        except Exception as e:
            logger.error(f"FFmpeg 执行失败：{e}")
            return False

    def _run_with_progress(
        self, cmd: List[str], callback: Optional[callable] = None
    ) -> bool:
        """带进度捕获的运行"""
        # 添加进度报告参数
        cmd.extend(["-progress", "pipe:1", "-nostats"])

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )

        total_duration = (
            self.get_duration(cmd[cmd.index("-i") + 1]) if "-i" in cmd else 0
        )

        try:
            for line in process.stdout:
                line = line.strip()

                if line.startswith("out_time_ms="):
                    time_ms = int(line.split("=")[1])
                    current_time = time_ms / 1_000_000

                    progress = FFmpegProgress(
                        time=current_time,
                        frame=0,
                        fps=0,
                        speed=0,
                        percent=(
                            (current_time / total_duration * 100)
                            if total_duration > 0
                            else 0
                        ),
                    )

                    if callback:
                        callback(progress)
                    else:
                        logger.debug(f"进度：{progress.percent:.1f}%")

            process.wait()
            return process.returncode == 0

        except Exception as e:
            logger.error(f"进度捕获失败：{e}")
            return False

    def get_duration(self, input_file: str) -> float:
        """获取视频时长"""
        info = self.probe(input_file)
        return info.get("duration", 0) if info else 0

    def probe(self, input_file: str) -> Optional[Dict]:
        """使用 ffprobe 探测媒体信息"""
        if not self.ffprobe_path:
            return None

        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            input_file,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"ffprobe 错误：{result.stderr}")
                return None

        except Exception as e:
            logger.error(f"ffprobe 失败：{e}")
            return None

    def get_video_info(self, input_file: str) -> Optional[VideoInfo]:
        """获取视频详细信息"""
        data = self.probe(input_file)
        if not data:
            return None

        format_info = data.get("format", {})
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None
        )

        return VideoInfo(
            filename=os.path.basename(input_file),
            duration=float(format_info.get("duration", 0)),
            size=int(format_info.get("size", 0)),
            format=format_info.get("format_name", ""),
            video_codec=video_stream.get("codec_name", "") if video_stream else "",
            audio_codec=audio_stream.get("codec_name", "") if audio_stream else "",
            resolution=(
                (video_stream.get("width", 0), video_stream.get("height", 0))
                if video_stream
                else (0, 0)
            ),
            bitrate=int(format_info.get("bit_rate", 0)),
            frame_rate=(
                self._parse_frame_rate(video_stream.get("r_frame_rate", "0/1"))
                if video_stream
                else 0
            ),
            has_video=video_stream is not None,
            has_audio=audio_stream is not None,
        )

    def _parse_frame_rate(self, value: str) -> float:
        """解析 ffprobe 返回的帧率字符串"""
        if value is None:
            return 0.0

        rate = str(value).strip()
        if not rate or rate.upper() == "N/A":
            return 0.0

        if "/" in rate:
            numerator, denominator = rate.split("/", 1)
            try:
                numerator_value = float(numerator)
                denominator_value = float(denominator)
            except (TypeError, ValueError):
                return 0.0

            if denominator_value == 0:
                return 0.0

            return numerator_value / denominator_value

        try:
            return float(rate)
        except (TypeError, ValueError):
            return 0.0


class FFmpegTools:
    """FFmpeg 工具集"""

    def __init__(self, executor: Optional[FFmpegExecutor] = None):
        self.executor = executor or FFmpegExecutor()

    def convert_format(
        self,
        input_file: str,
        output_file: str,
        output_format: str = "mp4",
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        crf: int = 23,
        preset: str = "medium",
    ) -> bool:
        """
        转换视频格式

        Args:
            input_file: 输入文件
            output_file: 输出文件
            output_format: 输出格式
            video_codec: 视频编码器
            audio_codec: 音频编码器
            crf: 质量因子（0-51，越小质量越高）
            preset: 编码速度预设
        """
        args = [
            "-c:v",
            video_codec,
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-c:a",
            audio_codec,
            "-b:a",
            "192k",
        ]

        return self.executor.run(args, input_file, output_file)

    def compress(
        self,
        input_file: str,
        output_file: str,
        quality: str = "medium",
        max_width: int = 1920,
        max_height: int = 1080,
    ) -> bool:
        """
        压缩视频

        Args:
            input_file: 输入文件
            output_file: 输出文件
            quality: 质量（low, medium, high）
            max_width: 最大宽度
            max_height: 最大高度
        """
        crf_map = {"low": 28, "medium": 23, "high": 18}
        crf = crf_map.get(quality, 23)

        args = [
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            "slow",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-vf",
            f"scale='min({max_width},iw)':'min({max_height},ih)':force_original_aspect_ratio=decrease",
        ]

        return self.executor.run(args, input_file, output_file)

    def extract_audio(
        self,
        input_file: str,
        output_file: str,
        audio_format: str = "mp3",
        bitrate: str = "192k",
    ) -> bool:
        """
        提取音频

        Args:
            input_file: 输入文件
            output_file: 输出文件
            audio_format: 音频格式
            bitrate: 比特率
        """
        args = [
            "-vn",  # 无视频
            "-acodec",
            "libmp3lame" if audio_format == "mp3" else "copy",
            "-ab",
            bitrate,
        ]

        return self.executor.run(args, input_file, output_file)

    def merge_videos(self, input_files: List[str], output_file: str) -> bool:
        """
        合并视频

        Args:
            input_files: 输入文件列表
            output_file: 输出文件
        """
        if len(input_files) < 2:
            logger.error("至少需要 2 个视频文件")
            return False

        # 创建文件列表
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for file in input_files:
                f.write(f"file '{os.path.abspath(file)}'\n")
            list_file = f.name

        try:
            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c",
                "copy",
            ]

            return self.executor.run(args, output_file=output_file)

        finally:
            os.unlink(list_file)

    def take_screenshot(
        self,
        input_file: str,
        output_file: str,
        timestamp: str = "00:00:01",
        width: Optional[int] = None,
    ) -> bool:
        """
        截取截图

        Args:
            input_file: 输入文件
            output_file: 输出文件
            timestamp: 时间戳（HH:MM:SS 或秒数）
            width: 截图宽度（可选）
        """
        args = [
            "-ss",
            timestamp,
            "-vframes",
            "1",
        ]

        if width:
            args.extend(["-vf", f"scale={width}:-1"])

        return self.executor.run(args, input_file, output_file)

    def take_screenshots_batch(
        self, input_file: str, output_dir: str, interval: int = 60, width: int = 320
    ) -> List[str]:
        """
        批量截取截图

        Args:
            input_file: 输入文件
            output_dir: 输出目录
            interval: 截图间隔（秒）
            width: 截图宽度

        Returns:
            截图文件列表
        """
        os.makedirs(output_dir, exist_ok=True)

        duration = self.executor.get_duration(input_file)
        screenshots = []

        for i, timestamp in enumerate(range(0, int(duration), interval)):
            output_file = os.path.join(output_dir, f"screenshot_{i:04d}.jpg")

            if self.take_screenshot(
                input_file, output_file, self._format_timestamp(timestamp), width
            ):
                screenshots.append(output_file)

        return screenshots

    def _format_timestamp(self, total_seconds: int) -> str:
        """将秒数格式化为 HH:MM:SS"""
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def add_watermark(
        self,
        input_file: str,
        output_file: str,
        watermark_file: str,
        position: str = "topright",
        opacity: float = 0.7,
    ) -> bool:
        """
        添加水印

        Args:
            input_file: 输入文件
            output_file: 输出文件
            watermark_file: 水印文件
            position: 位置（topright, topleft, bottomright, bottomleft）
            opacity: 透明度（0-1）
        """
        positions = {
            "topright": "W-w-10:10",
            "topleft": "10:10",
            "bottomright": "W-w-10:H-h-10",
            "bottomleft": "10:H-h-10",
        }

        pos = positions.get(position, positions["topright"])

        args = [
            "-i",
            watermark_file,
            "-filter_complex",
            f"[0][1]overlay={pos}:format=auto:alpha={opacity}",
            "-c:a",
            "copy",
        ]

        return self.executor.run(args, input_file, output_file)

    def trim_video(
        self,
        input_file: str,
        output_file: str,
        start_time: str,
        end_time: Optional[str] = None,
        duration: Optional[str] = None,
    ) -> bool:
        """
        裁剪视频

        Args:
            input_file: 输入文件
            output_file: 输出文件
            start_time: 开始时间
            end_time: 结束时间
            duration: 持续时间（与 end_time 二选一）
        """
        if end_time:
            # 计算持续时间
            start_sec = self._parse_time(start_time)
            end_sec = self._parse_time(end_time)
            duration = f"{end_sec - start_sec:.3f}"

        args = [
            "-ss",
            start_time,
            "-t",
            duration if duration else "999999",
            "-c",
            "copy",
        ]

        return self.executor.run(args, input_file, output_file)

    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串为秒数"""
        parts = time_str.split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        else:
            return float(time_str)

    def change_resolution(
        self, input_file: str, output_file: str, resolution: str = "1920x1080"
    ) -> bool:
        """
        改变分辨率

        Args:
            input_file: 输入文件
            output_file: 输出文件
            resolution: 目标分辨率（如 1920x1080）
        """
        args = [
            "-c:v",
            "libx264",
            "-vf",
            f"scale={resolution}",
            "-c:a",
            "copy",
        ]

        return self.executor.run(args, input_file, output_file)

    def extract_frames(
        self, input_file: str, output_dir: str, frame_rate: float = 1.0
    ) -> List[str]:
        """
        提取视频帧

        Args:
            input_file: 输入文件
            output_dir: 输出目录
            frame_rate: 帧率（1.0=每秒 1 帧）

        Returns:
            帧文件列表
        """
        os.makedirs(output_dir, exist_ok=True)

        args = ["-vf", f"fps={frame_rate}", os.path.join(output_dir, "frame_%06d.jpg")]

        success = self.executor.run(args, input_file)

        if success:
            return sorted(
                [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.endswith(".jpg")
                ]
            )
        return []

    def create_gif(
        self,
        input_file: str,
        output_file: str,
        frame_rate: float = 10.0,
    ) -> bool:
        """
        生成 GIF

        Args:
            input_file: 输入文件
            output_file: 输出 GIF 文件
            frame_rate: 抽帧帧率
        """
        args = [
            "-vf",
            f"fps={frame_rate}",
            "-loop",
            "0",
        ]

        return self.executor.run(args, input_file, output_file)

    def get_thumbnail(
        self, input_file: str, output_file: str, size: Tuple[int, int] = (320, 180)
    ) -> bool:
        """
        生成缩略图

        Args:
            input_file: 输入文件
            output_file: 输出文件
            size: 缩略图尺寸
        """
        args = [
            "-vf",
            f"scale={size[0]}:{size[1]}",
            "-vframes",
            "1",
        ]

        return self.executor.run(args, input_file, output_file)


# 使用示例
if __name__ == "__main__":
    import sys

    try:
        # 创建执行器
        executor = FFmpegExecutor()
        tools = FFmpegTools(executor)

        if len(sys.argv) > 1:
            input_file = sys.argv[1]

            # 获取视频信息
            info = executor.get_video_info(input_file)
            if info:
                print("\n视频信息:")
                print(f"  文件名：{info.filename}")
                print(f"  时长：{info.duration:.2f}秒")
                print(f"  大小：{info.size / 1024 / 1024:.2f}MB")
                print(f"  格式：{info.format}")
                print(f"  分辨率：{info.resolution[0]}x{info.resolution[1]}")
                print(f"  视频编码：{info.video_codec}")
                print(f"  音频编码：{info.audio_codec}")
                print(f"  帧率：{info.frame_rate:.2f}fps")

            # 示例：转换为 MP4
            # tools.convert_format(input_file, "output.mp4")

            # 示例：压缩
            # tools.compress(input_file, "compressed.mp4", quality="medium")

            # 示例：提取音频
            # tools.extract_audio(input_file, "audio.mp3")

            # 示例：截图
            # tools.take_screenshot(input_file, "screenshot.jpg", "00:00:05")

        else:
            print("用法：python ffmpeg_tools.py <video_file>")

    except FFmpegNotFoundError as e:
        print(f"错误：{e}")
