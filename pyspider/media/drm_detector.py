"""
DRM 检测和处理模块
支持 Widevine、FairPlay、PlayReady 等 DRM 检测
"""

import re
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import base64
import struct


logger = logging.getLogger(__name__)


class DRMType(Enum):
    """DRM 类型"""
    WIDEVINE = "widevine"
    FAIRPLAY = "fairplay"
    PLAYREADY = "playready"
    CLEARKEY = "clearkey"
    AES_128 = "aes-128"
    SAMPLE_AES = "sample-aes"
    UNKNOWN = "unknown"
    NONE = "none"


@dataclass
class DRMInfo:
    """DRM 信息"""
    drm_type: DRMType = DRMType.NONE
    is_drm_protected: bool = False
    key_uri: Optional[str] = None
    key_id: Optional[str] = None
    pssh_boxes: List[bytes] = field(default_factory=list)
    license_url: Optional[str] = None
    encryption_scheme: Optional[str] = None
    kid: Optional[str] = None  # Key ID
    iv: Optional[str] = None  # Initialization Vector
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'drm_type': self.drm_type.value,
            'is_drm_protected': self.is_drm_protected,
            'key_uri': self.key_uri,
            'key_id': self.key_id,
            'license_url': self.license_url,
            'encryption_scheme': self.encryption_scheme,
            'kid': self.kid,
            'iv': self.iv,
            'custom_data': self.custom_data,
        }


class DRMDetector:
    """DRM 检测器"""
    
    def __init__(self):
        # DRM 特征
        self.drm_patterns = {
            DRMType.WIDEVINE: [
                r'widevine',
                r'com\.widevine\.alphadigital',
                r'pssh.*widevine',
                r'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
            ],
            DRMType.FAIRPLAY: [
                r'fairplay',
                r'com\.apple\.fps',
                r'urn:uuid:94ce86fb-0790-4974-8fd1-3c54e7ef316f',
                r'fps-cert',
            ],
            DRMType.PLAYREADY: [
                r'playready',
                r'com\.microsoft\.playready',
                r'urn:uuid:9a04f079-9840-4286-ab92-e65be0885f95',
                r'<WRMHEADER',
            ],
            DRMType.CLEARKEY: [
                r'clearkey',
                r'urn:uuid:e2719d58-a985-b3c9-781a-b030af78d30e',
            ],
        }
    
    def detect_from_m3u8(self, m3u8_content: str) -> DRMInfo:
        """从 M3U8 内容检测 DRM"""
        info = DRMInfo()
        
        # 检查加密标签
        key_lines = re.findall(r'#EXT-X-KEY:(.+)', m3u8_content)
        
        for key_line in key_lines:
            # 提取 METHOD
            method_match = re.search(r'METHOD=([^,\s]+)', key_line)
            if method_match:
                method = method_match.group(1)
                
                if method == 'NONE':
                    info.drm_type = DRMType.NONE
                elif method == 'AES-128':
                    info.drm_type = DRMType.AES_128
                    info.is_drm_protected = True
                elif method in ['SAMPLE-AES', 'SAMPLE-AES-CTR']:
                    info.drm_type = DRMType.SAMPLE_AES
                    info.is_drm_protected = True
            
            # 提取 URI
            uri_match = re.search(r'URI="([^"]+)"', key_line)
            if uri_match:
                info.key_uri = uri_match.group(1)
            
            # 提取 IV
            iv_match = re.search(r'IV=([^,\s]+)', key_line)
            if iv_match:
                info.iv = iv_match.group(1)
            
            # 提取 KEYFORMAT
            format_match = re.search(r'KEYFORMAT="([^"]+)"', key_line)
            if format_match:
                key_format = format_match.group(1)
                self._detect_from_keyformat(info, key_format)
            
            # 提取 KEYID
            keyid_match = re.search(r'KEYID=([^,\s]+)', key_line)
            if keyid_match:
                info.key_id = keyid_match.group(1)
        
        # 检查是否有 DRM 特征字符串
        for drm_type, patterns in self.drm_patterns.items():
            for pattern in patterns:
                if re.search(pattern, m3u8_content, re.IGNORECASE):
                    if info.drm_type == DRMType.NONE:
                        info.drm_type = drm_type
                    info.is_drm_protected = True
                    break
        
        # 如果没有找到加密但有关键 URI，可能是 AES-128
        if info.key_uri and info.drm_type == DRMType.NONE:
            info.drm_type = DRMType.AES_128
            info.is_drm_protected = True
        
        return info
    
    def detect_from_mpd(self, mpd_content: str) -> DRMInfo:
        """从 DASH MPD 内容检测 DRM"""
        info = DRMInfo()
        
        # 检查 ContentProtection 元素
        protection_matches = re.findall(
            r'<ContentProtection[^>]*>(.*?)</ContentProtection>',
            mpd_content,
            re.DOTALL | re.IGNORECASE
        )
        
        for protection in protection_matches:
            # 检查 schemeIdUri
            scheme_match = re.search(r'schemeIdUri="([^"]+)"', protection)
            if scheme_match:
                scheme = scheme_match.group(1)
                self._detect_from_scheme(info, scheme)
            
            # 检查 PSSH
            pssh_match = re.search(r'<cenc:pssh[^>]*>([^<]+)</cenc:pssh>', protection)
            if pssh_match:
                try:
                    pssh_data = base64.b64decode(pssh_match.group(1))
                    info.pssh_boxes.append(pssh_data)
                    info.is_drm_protected = True
                    self._parse_pssh(info, pssh_data)
                except Exception as e:
                    logger.debug(f"解析 PSSH 失败：{e}")
            
            # 检查默认 KID
            kid_match = re.search(r'cenc:default_KID="([^"]+)"', protection)
            if kid_match:
                info.kid = kid_match.group(1)
                info.is_drm_protected = True
        
        # 检查 mspr:pro (PlayReady)
        mspr_match = re.search(r'<mspr:pro[^>]*>([^<]+)</mspr:pro>', mpd_content)
        if mspr_match:
            info.drm_type = DRMType.PLAYREADY
            info.is_drm_protected = True
            try:
                pro_data = base64.b64decode(mspr_match.group(1))
                info.custom_data['playready_pro'] = base64.b64encode(pro_data).decode()
            except:
                pass
        
        # 如果没有找到 DRM，检查是否有加密
        if not info.is_drm_protected:
            if 'value="cenc"' in mpd_content or 'value="cbcs"' in mpd_content:
                info.is_drm_protected = True
                if info.drm_type == DRMType.NONE:
                    info.drm_type = DRMType.UNKNOWN
        
        return info
    
    def detect_from_video_file(self, file_path: str) -> DRMInfo:
        """从视频文件检测 DRM"""
        info = DRMInfo()
        
        try:
            with open(file_path, 'rb') as f:
                # 读取文件头
                header = f.read(1024)
                
                # 检查文件类型
                if b'ftyp' in header:
                    # MP4 文件
                    info = self._detect_from_mp4(file_path, info)
                elif b'\x47' == header[0:1]:
                    # TS 文件
                    info = self._detect_from_ts(file_path, info)
            
            return info
            
        except Exception as e:
            logger.error(f"检测视频文件 DRM 失败：{e}")
            return info
    
    def _detect_from_mp4(self, file_path: str, info: DRMInfo) -> DRMInfo:
        """从 MP4 文件检测 DRM"""
        try:
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                position = 0
                
                while position < file_size:
                    # 读取 box header
                    f.seek(position)
                    header = f.read(8)
                    
                    if len(header) < 8:
                        break
                    
                    size = struct.unpack('>I', header[0:4])[0]
                    box_type = header[4:8].decode('ascii', errors='ignore')
                    
                    if size < 8:
                        break
                    
                    # 检查 pssh box
                    if box_type == 'pssh':
                        f.seek(position)
                        pssh_data = f.read(size)
                        info.pssh_boxes.append(pssh_data)
                        info.is_drm_protected = True
                        self._parse_pssh(info, pssh_data[8:])  # 跳过 header
                    
                    # 检查 schm box (scheme type)
                    elif box_type == 'schm':
                        f.seek(position + 4)
                        scheme_data = f.read(size - 4)
                        if len(scheme_data) >= 4:
                            scheme_type = scheme_data[0:4].decode('ascii', errors='ignore')
                            if scheme_type == 'wcbe':  # Widevine
                                info.drm_type = DRMType.WIDEVINE
                                info.is_drm_protected = True
                            elif scheme_type == 'cbcs':  # Common Encryption
                                info.drm_type = DRMType.CLEARKEY
                                info.is_drm_protected = True
                    
                    position += size
                    
        except Exception as e:
            logger.debug(f"解析 MP4 失败：{e}")
        
        return info
    
    def _detect_from_ts(self, file_path: str, info: DRMInfo) -> DRMInfo:
        """从 TS 文件检测 DRM"""
        # TS 文件通常使用 AES-128 加密
        # 检查是否有对应的 .key 文件
        key_file = file_path + '.key'
        if os.path.exists(key_file):
            info.drm_type = DRMType.AES_128
            info.is_drm_protected = True
            info.key_uri = key_file
        
        return info
    
    def _detect_from_keyformat(self, info: DRMInfo, key_format: str):
        """从 KEYFORMAT 检测 DRM"""
        key_format_lower = key_format.lower()
        
        if 'widevine' in key_format_lower:
            info.drm_type = DRMType.WIDEVINE
            info.is_drm_protected = True
        elif 'fairplay' in key_format_lower or 'fps' in key_format_lower:
            info.drm_type = DRMType.FAIRPLAY
            info.is_drm_protected = True
        elif 'playready' in key_format_lower:
            info.drm_type = DRMType.PLAYREADY
            info.is_drm_protected = True
        elif 'clearkey' in key_format_lower:
            info.drm_type = DRMType.CLEARKEY
            info.is_drm_protected = True
    
    def _detect_from_scheme(self, info: DRMInfo, scheme: str):
        """从 schemeIdUri 检测 DRM"""
        scheme_lower = scheme.lower()
        
        if 'widevine' in scheme_lower:
            info.drm_type = DRMType.WIDEVINE
            info.is_drm_protected = True
        elif 'fairplay' in scheme_lower or 'fps' in scheme_lower:
            info.drm_type = DRMType.FAIRPLAY
            info.is_drm_protected = True
        elif 'playready' in scheme_lower:
            info.drm_type = DRMType.PLAYREADY
            info.is_drm_protected = True
        elif 'clearkey' in scheme_lower:
            info.drm_type = DRMType.CLEARKEY
            info.is_drm_protected = True
    
    def _parse_pssh(self, info: DRMInfo, pssh_data: bytes):
        """解析 PSSH 数据"""
        if len(pssh_data) < 4:
            return
        
        # 读取 system ID
        system_id = pssh_data[0:16]
        
        # Widevine UUID: edef8ba9-79d6-4ace-a3c8-27dcd51d21ed
        widevine_uuid = bytes.fromhex('edef8ba979d64acea3c827dcd51d21ed')
        
        # PlayReady UUID: 9a04f079-9840-4286-ab92-e65be0885f95
        playready_uuid = bytes.fromhex('9a04f07998404286ab92e65be0885f95')
        
        # FairPlay UUID: 94ce86fb-0790-4974-8fd1-3c54e7ef316f
        fairplay_uuid = bytes.fromhex('94ce86fb079049748fd13c54e7ef316f')
        
        if system_id == widevine_uuid:
            info.drm_type = DRMType.WIDEVINE
            info.is_drm_protected = True
            
            # 尝试解析 Widevine PSSH
            try:
                pssh = self._parse_widevine_pssh(pssh_data)
                if pssh:
                    info.custom_data['widevine_pssh'] = pssh
            except:
                pass
                
        elif system_id == playready_uuid:
            info.drm_type = DRMType.PLAYREADY
            info.is_drm_protected = True
            
        elif system_id == fairplay_uuid:
            info.drm_type = DRMType.FAIRPLAY
            info.is_drm_protected = True
    
    def _parse_widevine_pssh(self, pssh_data: bytes) -> Optional[str]:
        """解析 Widevine PSSH"""
        try:
            # 跳过 version 和 flags
            data = pssh_data[4:]
            
            # 读取 data size
            data_size = struct.unpack('>I', data[0:4])[0]
            data_content = data[4:4+data_size]
            
            return base64.b64encode(data_content).decode()
        except:
            return None


class DRMHandler:
    """DRM 处理器"""
    
    def __init__(self):
        self.detector = DRMDetector()
    
    def analyze(self, url: str, content: str) -> DRMInfo:
        """分析内容的 DRM 信息"""
        if '.m3u8' in url or '#EXTM3U' in content:
            return self.detector.detect_from_m3u8(content)
        elif '.mpd' in url or '<MPD' in content:
            return self.detector.detect_from_mpd(content)
        else:
            return DRMInfo()
    
    def is_downloadable(self, drm_info: DRMInfo) -> Tuple[bool, str]:
        """检查是否可下载"""
        if not drm_info.is_drm_protected:
            return True, "无 DRM 保护，可直接下载"
        
        if drm_info.drm_type == DRMType.AES_128:
            if drm_info.key_uri:
                return True, f"AES-128 加密，密钥 URL: {drm_info.key_uri}"
            else:
                return False, "AES-128 加密但未找到密钥 URL"
        
        if drm_info.drm_type == DRMType.CLEARKEY:
            return True, "ClearKey 加密，可尝试获取密钥"
        
        # 商业 DRM
        if drm_info.drm_type in [DRMType.WIDEVINE, DRMType.FAIRPLAY, DRMType.PLAYREADY]:
            return False, f"受 {drm_info.drm_type.value} DRM 保护，需要授权"
        
        return False, f"未知 DRM 类型：{drm_info.drm_type.value}"
    
    def get_decrypt_command(self, drm_info: DRMInfo, input_file: str, output_file: str) -> Optional[str]:
        """获取解密命令"""
        if not drm_info.is_drm_protected:
            return None
        
        if drm_info.drm_type == DRMType.AES_128:
            if drm_info.key_uri and drm_info.iv:
                # ffmpeg AES-128 解密
                key = self._fetch_key(drm_info.key_uri)
                if key:
                    return (
                        f'ffmpeg -i "{input_file}" '
                        f'-decryption_key {key} '
                        f'-c copy "{output_file}"'
                    )
        
        return None
    
    def _fetch_key(self, key_uri: str) -> Optional[str]:
        """获取密钥"""
        try:
            import requests
            resp = requests.get(key_uri, timeout=10)
            resp.raise_for_status()
            return resp.content.hex()
        except Exception as e:
            logger.error(f"获取密钥失败：{e}")
            return None


# 工具函数
def check_drm_status(content: str, url: str = "") -> Dict:
    """快速检查 DRM 状态"""
    detector = DRMDetector()
    handler = DRMHandler()
    
    drm_info = handler.analyze(url, content)
    downloadable, message = handler.is_downloadable(drm_info)
    
    return {
        'drm_info': drm_info.to_dict(),
        'downloadable': downloadable,
        'message': message,
    }


# 导入 os（用于文件检测）
import os


# 使用示例
if __name__ == "__main__":
    # 示例 M3U8 内容
    test_m3u8 = """
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-KEY:METHOD=AES-128,URI="https://example.com/key.key",IV=0x1234567890abcdef
#EXTINF:10.0,
segment0.ts
#EXTINF:10.0,
segment1.ts
#EXT-X-ENDLIST
"""
    
    detector = DRMDetector()
    info = detector.detect_from_m3u8(test_m3u8)
    
    print(f"DRM 类型：{info.drm_type.value}")
    print(f"是否加密：{info.is_drm_protected}")
    print(f"密钥 URI: {info.key_uri}")
    print(f"IV: {info.iv}")
    
    handler = DRMHandler()
    downloadable, message = handler.is_downloadable(info)
    print(f"是否可下载：{downloadable}")
    print(f"说明：{message}")
