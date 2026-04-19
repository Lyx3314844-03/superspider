"""
Node.js 逆向服务客户端
为 Python Spider 提供统一的逆向能力
"""

import requests
import json
import re
from typing import Dict, List, Optional, Any


class NodeReverseClient:
    """Node.js 逆向服务客户端"""

    DEFAULT_BASE_URL = "http://localhost:3000"

    def __init__(self, base_url: str = None):
        """
        初始化客户端

        Args:
            base_url: 逆向服务地址
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.timeout = 30

    def health_check(self) -> bool:
        """健康检查"""
        try:
            resp = self.session.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except Exception:
            return False

    def analyze_crypto(self, code: str) -> Dict[str, Any]:
        """
        分析代码中的加密算法

        Args:
            code: JavaScript 代码

        Returns:
            分析结果
        """
        remote = self._do_request("/api/crypto/analyze", {"code": code})
        local = self._local_crypto_analysis(code)
        return self._merge_crypto_analysis(remote, local)

    def encrypt(
        self, algorithm: str, data: str, key: str, iv: str = None, mode: str = "CBC"
    ) -> Dict[str, Any]:
        """
        执行加密操作

        Args:
            algorithm: 加密算法 (AES, DES, RSA, MD5, SHA等)
            data: 待加密数据
            key: 密钥
            iv: 初始化向量
            mode: 加密模式

        Returns:
            加密结果
        """
        payload = {"algorithm": algorithm, "data": data, "key": key, "mode": mode}
        if iv:
            payload["iv"] = iv

        return self._do_request("/api/crypto/encrypt", payload)

    def decrypt(
        self, algorithm: str, data: str, key: str, iv: str = None, mode: str = "CBC"
    ) -> Dict[str, Any]:
        """
        执行解密操作

        Args:
            algorithm: 加密算法
            data: 待解密数据
            key: 密钥
            iv: 初始化向量
            mode: 加密模式

        Returns:
            解密结果
        """
        payload = {"algorithm": algorithm, "data": data, "key": key, "mode": mode}
        if iv:
            payload["iv"] = iv

        return self._do_request("/api/crypto/decrypt", payload)

    def execute_js(
        self, code: str, context: Dict = None, timeout: int = 5000
    ) -> Dict[str, Any]:
        """
        执行 JavaScript 代码

        Args:
            code: JavaScript 代码
            context: 上下文变量
            timeout: 超时时间(毫秒)

        Returns:
            执行结果
        """
        payload = {"code": code, "timeout": timeout}
        if context:
            payload["context"] = context

        return self._do_request("/api/js/execute", payload)

    def analyze_ast(self, code: str, analysis: List[str] = None) -> Dict[str, Any]:
        """
        AST 语法分析

        Args:
            code: JavaScript 代码
            analysis: 分析类型列表 ['crypto', 'obfuscation', 'anti-debug']

        Returns:
            分析结果
        """
        payload = {
            "code": code,
            "analysis": analysis or ["crypto", "obfuscation", "anti-debug"],
        }

        return self._do_request("/api/ast/analyze", payload)

    def analyze_webpack(self, code: str) -> Dict[str, Any]:
        """
        Webpack 打包分析

        Args:
            code: Webpack 打包后的代码

        Returns:
            分析结果
        """
        return self._do_request("/api/webpack/analyze", {"code": code})

    def call_function(
        self, function_name: str, args: List, code: str
    ) -> Dict[str, Any]:
        """
        调用 JavaScript 函数

        Args:
            function_name: 函数名
            args: 参数列表
            code: 函数定义代码

        Returns:
            函数返回值
        """
        payload = {"functionName": function_name, "args": args, "code": code}

        return self._do_request("/api/function/call", payload)

    def simulate_browser(
        self, code: str, browser_config: Dict = None
    ) -> Dict[str, Any]:
        """
        模拟浏览器环境

        Args:
            code: JavaScript 代码
            browser_config: 浏览器配置
                {
                    'userAgent': '...',
                    'language': 'zh-CN',
                    'platform': 'Win32'
                }

        Returns:
            执行结果和 cookies
        """
        payload = {"code": code}
        if browser_config:
            payload["browserConfig"] = browser_config

        return self._do_request("/api/browser/simulate", payload)

    def detect_anti_bot(
        self,
        html: str = "",
        js: str = "",
        headers: Optional[Dict[str, Any]] = None,
        cookies: str = "",
        status_code: Optional[int] = None,
        url: str = "",
    ) -> Dict[str, Any]:
        """
        检测页面中的反爬挑战特征
        """
        payload = {
            "html": html,
            "js": js,
            "headers": headers or {},
            "cookies": cookies,
            "url": url,
        }
        if status_code is not None:
            payload["statusCode"] = status_code
        return self._do_request("/api/anti-bot/detect", payload)

    def profile_anti_bot(
        self,
        html: str = "",
        js: str = "",
        headers: Optional[Dict[str, Any]] = None,
        cookies: str = "",
        status_code: Optional[int] = None,
        url: str = "",
    ) -> Dict[str, Any]:
        """
        生成完整的反爬画像、请求蓝图和规避计划
        """
        payload = {
            "html": html,
            "js": js,
            "headers": headers or {},
            "cookies": cookies,
            "url": url,
        }
        if status_code is not None:
            payload["statusCode"] = status_code
        return self._do_request("/api/anti-bot/profile", payload)

    def spoof_fingerprint(
        self,
        browser: str = "chrome",
        platform: str = "windows",
    ) -> Dict[str, Any]:
        """
        生成伪造浏览器指纹。
        """
        return self._do_request(
            "/api/fingerprint/spoof",
            {
                "browser": browser,
                "platform": platform,
            },
        )

    def generate_tls_fingerprint(
        self,
        browser: str = "chrome",
        version: str = "120",
    ) -> Dict[str, Any]:
        """
        生成 TLS 指纹配置。
        """
        return self._do_request(
            "/api/tls/fingerprint",
            {
                "browser": browser,
                "version": version,
            },
        )

    def canvas_fingerprint(self) -> Dict[str, Any]:
        """
        生成 Canvas 指纹。
        """
        return self._do_request("/api/canvas/fingerprint", {})

    def reverse_signature(
        self, code: str, input_data: str, expected_output: str
    ) -> Dict[str, Any]:
        """
        逆向签名算法

        Args:
            code: 签名代码
            input_data: 输入数据
            expected_output: 期望输出

        Returns:
            逆向结果
        """
        payload = {"code": code, "input": input_data, "expectedOutput": expected_output}

        return self._do_request("/api/signature/reverse", payload)

    def _do_request(self, path: str, payload: Dict) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        try:
            resp = self.session.post(
                f"{self.base_url}{path}", json=payload, timeout=self.session.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败: {e}"}

    @staticmethod
    def _local_crypto_analysis(code: str) -> Dict[str, Any]:
        lowered = (code or "").lower()
        libraries = {
            "CryptoJS": ["cryptojs."],
            "NodeCrypto": ["require('crypto')", 'require("crypto")', "createcipheriv", "createhmac", "createhash"],
            "WebCrypto": ["crypto.subtle", "subtle.encrypt", "subtle.decrypt", "subtle.digest", "subtle.sign"],
            "Forge": ["forge.", "node-forge"],
            "SJCL": ["sjcl."],
            "sm-crypto": ["sm2", "sm3", "sm4", "sm-crypto"],
            "JSEncrypt": ["jsencrypt", "node-rsa"],
            "jsrsasign": ["jsrsasign", "rsasign"],
            "tweetnacl": ["tweetnacl", "nacl.sign", "nacl.box"],
            "elliptic": ["secp256k1", "elliptic.ec", "ecdh", "ecdsa"],
            "sodium": ["libsodium", "sodium.", "xchacha20", "ed25519", "x25519"],
        }
        operations = {
            "encrypt": ["encrypt(", "subtle.encrypt", "createcipheriv", ".encrypt("],
            "decrypt": ["decrypt(", "subtle.decrypt", "createdecipheriv", ".decrypt("],
            "sign": ["sign(", "subtle.sign", "jsonwebtoken.sign", "jws.sign"],
            "verify": ["verify(", "subtle.verify", "jsonwebtoken.verify", "jws.verify"],
            "hash": ["createhash", "subtle.digest", "md5(", "sha1(", "sha256(", "sha512(", "sha3", "ripemd160"],
            "kdf": ["pbkdf2", "scrypt", "bcrypt", "hkdf"],
            "encode": ["btoa(", "atob(", "base64", ".toString('hex')", ".toString(\"hex\")", "base64url", "jwt"],
        }
        mode_markers = {
            "CBC": ["cbc"],
            "GCM": ["gcm"],
            "CTR": ["ctr"],
            "ECB": ["ecb"],
            "CFB": ["cfb"],
            "OFB": ["ofb"],
            "CCM": ["ccm"],
            "XTS": ["xts"],
        }
        algorithm_catalog = [
            ("AES", ["cryptojs.aes", "aes-gcm", "aes-cbc", "aes-ctr", "aes-ecb", "subtle.encrypt", "subtle.decrypt", "createcipheriv", "createdecipheriv"]),
            ("DES", ["cryptojs.des", "des-cbc", "des-ecb"]),
            ("TripleDES", ["cryptojs.tripledes", "des-ede3", "3des", "tripledes"]),
            ("RSA", ["jsencrypt", "node-rsa", "publicencrypt", "privatedecrypt", "rsa-oaep", "rsa-pss", "rsasign"]),
            ("ECDSA", ["ecdsa", "secp256k1", "elliptic.ec"]),
            ("Ed25519", ["ed25519"]),
            ("X25519", ["x25519"]),
            ("SM2", ["sm2"]),
            ("SM3", ["sm3"]),
            ("SM4", ["sm4"]),
            ("RC4", ["cryptojs.rc4", "rc4"]),
            ("Rabbit", ["cryptojs.rabbit", "rabbit"]),
            ("ChaCha20", ["chacha20", "xchacha20"]),
            ("Salsa20", ["salsa20"]),
            ("Blowfish", ["blowfish"]),
            ("Twofish", ["twofish"]),
            ("TEA", ["tea.encrypt", "tea.decrypt"]),
            ("XTEA", ["xtea"]),
            ("XXTEA", ["xxtea"]),
            ("HMAC-SHA1", ["hmacsha1", "createhmac('sha1", 'createhmac("sha1']),
            ("HMAC-SHA256", ["hmacsha256", "createhmac('sha256", 'createhmac("sha256']),
            ("HMAC-SHA512", ["hmacsha512", "createhmac('sha512", 'createhmac("sha512']),
            ("MD5", ["cryptojs.md5", "md5("]),
            ("SHA1", ["cryptojs.sha1", "sha1("]),
            ("SHA256", ["cryptojs.sha256", "sha256("]),
            ("SHA512", ["cryptojs.sha512", "sha512("]),
            ("SHA3", ["cryptojs.sha3", "sha3"]),
            ("RIPEMD160", ["ripemd160"]),
            ("PBKDF2", ["cryptojs.pbkdf2", "pbkdf2"]),
            ("scrypt", ["scrypt"]),
            ("bcrypt", ["bcrypt"]),
            ("HKDF", ["hkdf"]),
            ("Base64", ["btoa(", "atob(", "base64"]),
            ("JWT", ["jsonwebtoken.sign", "jsonwebtoken.verify", "jwt.sign", "jwt.verify", "jws.sign"]),
        ]

        def contains_any(markers: List[str]) -> int:
            return sum(1 for marker in markers if marker in lowered)

        detected_libraries = sorted(
            name for name, markers in libraries.items() if contains_any(markers) > 0
        )
        detected_operations = sorted(
            name for name, markers in operations.items() if contains_any(markers) > 0
        )
        detected_modes = sorted(
            name for name, markers in mode_markers.items() if contains_any(markers) > 0
        )
        dynamic_source_markers = {
            "storage": ["localstorage", "sessionstorage", "indexeddb"],
            "cookie": ["document.cookie"],
            "navigator": ["navigator."],
            "time": ["date.now", "new date(", "performance.now"],
            "random": ["math.random", "getrandomvalues", "randombytes"],
            "env": ["process.env", "import.meta.env"],
            "window_state": ["window.__", "globalthis.", "window["],
            "network": ["fetch(", "axios.", "xmlhttprequest", ".response", "await fetch"],
        }
        runtime_selector_markers = {
            "algorithm_variable": ["algorithm", "algo", "ciphername"],
            "mode_variable": ["mode =", "mode:", "ciphermode"],
            "switch_dispatch": ["switch(", "case 'aes", 'case "aes'],
            "computed_lookup": ["[algo]", "[algorithm]", "algorithms[", "ciphers["],
        }
        obfuscation_loader_markers = {
            "eval_packer": ["eval(function(p,a,c,k,e,d)"],
            "hex_array": ["_0x", "\\x"],
            "base64_loader": ["atob(", "buffer.from(", "base64"],
            "function_constructor": ["function(", "constructor(\"return this\")", "constructor('return this')"],
            "webpack_loader": ["__webpack_require__", "webpackjsonp", "webpackchunk"],
            "anti_debug": ["debugger", "devtools", "setinterval(function(){debugger"],
        }
        sink_catalog = {
            "CryptoJS.AES.encrypt": ["cryptojs.aes.encrypt"],
            "CryptoJS.AES.decrypt": ["cryptojs.aes.decrypt"],
            "CryptoJS.DES.encrypt": ["cryptojs.des.encrypt"],
            "CryptoJS.TripleDES.encrypt": ["cryptojs.tripledes.encrypt"],
            "CryptoJS.HmacSHA256": ["cryptojs.hmacsha256", "hmacsha256("],
            "CryptoJS.PBKDF2": ["cryptojs.pbkdf2", "pbkdf2("],
            "crypto.createCipheriv": ["createcipheriv"],
            "crypto.createDecipheriv": ["createdecipheriv"],
            "crypto.createHmac": ["createhmac"],
            "crypto.createHash": ["createhash"],
            "crypto.subtle.encrypt": ["subtle.encrypt"],
            "crypto.subtle.decrypt": ["subtle.decrypt"],
            "crypto.subtle.sign": ["subtle.sign"],
            "crypto.subtle.digest": ["subtle.digest"],
            "sm4.encrypt": ["sm4.encrypt"],
            "sm2.doSignature": ["sm2.dosignature"],
            "jwt.sign": ["jsonwebtoken.sign", "jwt.sign"],
            "jwt.verify": ["jsonwebtoken.verify", "jwt.verify"],
        }

        dynamic_key_sources = sorted(
            name
            for name, markers in dynamic_source_markers.items()
            if contains_any(markers) > 0
        )
        runtime_algorithm_selection = sorted(
            name
            for name, markers in runtime_selector_markers.items()
            if contains_any(markers) > 0
        )
        obfuscation_loaders = sorted(
            name
            for name, markers in obfuscation_loader_markers.items()
            if contains_any(markers) > 0
        )
        algorithm_aliases = {
            name: sorted({marker for marker in markers if marker in lowered})
            for name, markers in algorithm_catalog
            if contains_any(markers) > 0
        }
        crypto_sinks = sorted(
            name for name, markers in sink_catalog.items() if contains_any(markers) > 0
        )
        key_flow_candidates: List[Dict[str, Any]] = []
        assignment_regex = re.compile(
            r"(?:const|let|var)?\s*([A-Za-z_$][\w$]*(?:key|iv|nonce|salt|secret|token)[A-Za-z0-9_$]*)\s*[:=]\s*([^;\n]+)",
            re.IGNORECASE,
        )
        source_detail_tokens = {
            "storage.localStorage": ["localstorage"],
            "storage.sessionStorage": ["sessionstorage"],
            "storage.indexedDB": ["indexeddb"],
            "cookie.document": ["document.cookie"],
            "navigator": ["navigator."],
            "time.date": ["date.now", "new date("],
            "time.performance": ["performance.now"],
            "random.math": ["math.random"],
            "random.crypto": ["getrandomvalues", "randombytes"],
            "env.process": ["process.env"],
            "env.import_meta": ["import.meta.env"],
            "window.bootstrap": ["window.__", "globalthis.", "window["],
            "network.fetch": ["fetch(", "await fetch"],
            "network.xhr": ["xmlhttprequest", ".response"],
            "network.axios": ["axios."],
            "dom.querySelector": ["queryselector(", "queryselectorall("],
            "dom.getElementById": ["getelementbyid("],
            "url.searchParams": ["urlsearchparams", "searchparams.get("],
        }
        for match in assignment_regex.finditer(code or ""):
            variable = match.group(1).strip()
            expression = match.group(2).strip()
            expression_lower = expression.lower()
            matched_sources = [
                source
                for source, tokens in source_detail_tokens.items()
                if any(token in expression_lower for token in tokens)
            ]
            if not matched_sources:
                continue
            key_flow_candidates.append(
                {
                    "variable": variable,
                    "expression": expression[:160],
                    "sources": matched_sources,
                    "dynamic": True,
                }
            )
        key_flow_chains: List[Dict[str, Any]] = []
        derivation_tokens = {
            "hash": ["sha", "md5(", "ripemd", "digest("],
            "hmac": ["hmac"],
            "kdf": ["pbkdf2", "scrypt", "bcrypt", "hkdf"],
            "encode": ["btoa(", "atob(", "base64", "buffer.from", "tostring("],
            "concat": ["concat(", "+", "join("],
            "json": ["json.stringify", "json.parse"],
            "url": ["encodeuricomponent", "decodeuricomponent", "urlsearchparams"],
        }
        assignment_matches = list(assignment_regex.finditer(code or ""))
        for candidate in key_flow_candidates:
            tracked_vars = {str(candidate.get("variable") or "")}
            derivations: List[Dict[str, Any]] = []
            for match in assignment_matches:
                target_var = match.group(1).strip()
                expression = match.group(2).strip()
                expression_lower = expression.lower()
                if target_var in tracked_vars:
                    continue
                if not any(re.search(rf"\b{re.escape(var)}\b", expression) for var in tracked_vars if var):
                    continue
                kind = next(
                    (
                        name
                        for name, tokens in derivation_tokens.items()
                        if any(token in expression_lower for token in tokens)
                    ),
                    "propagate",
                )
                derivations.append(
                    {
                        "variable": target_var,
                        "kind": kind,
                        "expression": expression[:160],
                    }
                )
                tracked_vars.add(target_var)
            sink_hits: List[str] = []
            code_lines = (code or "").splitlines()
            for sink_name, markers in sink_catalog.items():
                matched = False
                for line in code_lines:
                    line_lower = line.lower()
                    if not any(marker in line_lower for marker in markers):
                        continue
                    if any(re.search(rf"\b{re.escape(var)}\b", line) for var in tracked_vars if var):
                        matched = True
                        break
                if matched:
                    sink_hits.append(sink_name)
            if not derivations and not sink_hits:
                continue
            source_kinds = list(candidate.get("sources") or [])
            confidence = min(
                0.99,
                0.55
                + (0.1 if sink_hits else 0.0)
                + min(0.18, len(derivations) * 0.06)
                + (0.06 if source_kinds else 0.0),
            )
            key_flow_chains.append(
                {
                    "variable": candidate.get("variable"),
                    "source": {
                        "kind": source_kinds[0] if source_kinds else "unknown",
                        "expression": candidate.get("expression", ""),
                    },
                    "derivations": derivations,
                    "sinks": sorted(set(sink_hits)),
                    "confidence": round(confidence, 2),
                }
            )
        crypto_types: List[Dict[str, Any]] = []
        for name, markers in algorithm_catalog:
            hits = contains_any(markers)
            if hits == 0:
                continue
            modes = [
                mode_name
                for mode_name, mode_tokens in mode_markers.items()
                if any(token in lowered for token in mode_tokens)
            ]
            confidence = round(min(0.99, 0.55 + 0.12 * min(hits, 3) + 0.03 * min(len(modes), 3)), 2)
            crypto_types.append({"name": name, "confidence": confidence, "modes": sorted(set(modes))})

        def extract_literals(patterns: List[str]) -> List[str]:
            values: List[str] = []
            for pattern in patterns:
                for match in re.findall(pattern, code or "", re.IGNORECASE):
                    if isinstance(match, tuple):
                        match = next((item for item in match if item), "")
                    match = str(match).strip()
                    if 4 <= len(match) <= 128 and match not in values:
                        values.append(match)
            return values[:8]

        keys = extract_literals(
            [
                r"(?:const|let|var)?\s*(?:appSecret|secret|privateKey|publicKey|aesKey|desKey|rsaKey|signKey|hmacKey|key)\w*\s*[:=]\s*['\"`]([^'\"`\n]{4,128})['\"`]",
            ]
        )
        ivs = extract_literals(
            [
                r"(?:const|let|var)?\s*(?:iv|nonce|salt)\w*\s*[:=]\s*['\"`]([^'\"`\n]{4,128})['\"`]",
            ]
        )

        normalized_algorithms = sorted(item["name"] for item in crypto_types)
        risk_score = min(
            100,
            (18 if normalized_algorithms else 0)
            + min(20, len(dynamic_key_sources) * 8)
            + min(18, len(runtime_algorithm_selection) * 6)
            + min(24, len(obfuscation_loaders) * 8)
            + min(16, len(key_flow_candidates) * 4)
            + min(12, len(crypto_sinks) * 2)
            + (8 if any(name in normalized_algorithms for name in ["RSA", "ECDSA", "Ed25519", "X25519", "SM2"]) else 0)
            + (6 if any(name in detected_libraries for name in ["WebCrypto", "NodeCrypto", "sodium"]) else 0)
            + (6 if any(name in normalized_algorithms for name in ["PBKDF2", "scrypt", "bcrypt", "HKDF"]) else 0),
        )
        reverse_complexity = (
            "extreme"
            if risk_score >= 80
            else "high"
            if risk_score >= 55
            else "medium"
            if risk_score >= 30
            else "low"
        )
        recommended_approach: List[str] = []
        if obfuscation_loaders:
            recommended_approach.append("unpack-loader-first")
        if dynamic_key_sources:
            recommended_approach.append("trace-key-materialization")
        if runtime_algorithm_selection:
            recommended_approach.append("trace-algorithm-branch")
        if "WebCrypto" in detected_libraries:
            recommended_approach.append("hook-webcrypto")
        if any(name in normalized_algorithms for name in ["JWT", "HMAC-SHA1", "HMAC-SHA256", "HMAC-SHA512"]):
            recommended_approach.append("rebuild-signing-canonicalization")
        if any(name in normalized_algorithms for name in ["RSA", "ECDSA", "Ed25519", "X25519", "SM2"]):
            recommended_approach.append("capture-key-import-and-padding")
        if not recommended_approach:
            recommended_approach.append("static-analysis-sufficient")

        return {
            "success": bool(crypto_types),
            "cryptoTypes": crypto_types,
            "keys": keys,
            "ivs": ivs,
            "analysis": {
                "hasKeyDerivation": any(token in lowered for token in ["pbkdf2", "scrypt", "bcrypt", "hkdf"]),
                "hasRandomIV": any(token in lowered for token in ["wordarray.random", "randombytes", "getrandomvalues", "nonce", "iv"]),
                "detectedLibraries": detected_libraries,
                "detectedOperations": detected_operations,
                "detectedModes": detected_modes,
                "normalizedAlgorithms": normalized_algorithms,
                "algorithmAliases": algorithm_aliases,
                "dynamicKeySources": dynamic_key_sources,
                "keyFlowCandidates": key_flow_candidates,
                "keyFlowChains": key_flow_chains,
                "runtimeAlgorithmSelection": runtime_algorithm_selection,
                "obfuscationLoaders": obfuscation_loaders,
                "cryptoSinks": crypto_sinks,
                "reverseComplexity": reverse_complexity,
                "riskScore": risk_score,
                "recommendedApproach": recommended_approach,
                "requiresASTDataflow": bool(dynamic_key_sources or runtime_algorithm_selection or obfuscation_loaders or key_flow_candidates),
                "requiresRuntimeExecution": bool(dynamic_key_sources or obfuscation_loaders or "WebCrypto" in detected_libraries or crypto_sinks),
                "requiresLoaderUnpack": bool(obfuscation_loaders),
            },
        }

    @staticmethod
    def _merge_crypto_analysis(remote: Dict[str, Any], local: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(remote or {})
        remote_types = merged.get("cryptoTypes")
        if not isinstance(remote_types, list):
            remote_types = []

        types_by_name: Dict[str, Dict[str, Any]] = {}
        for item in [*remote_types, *(local.get("cryptoTypes") or [])]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            current = types_by_name.get(name, {"name": name, "confidence": 0.0, "modes": []})
            current["confidence"] = max(float(current.get("confidence") or 0.0), float(item.get("confidence") or 0.0))
            current["modes"] = sorted(set(list(current.get("modes") or []) + list(item.get("modes") or [])))
            types_by_name[name] = current

        merged["cryptoTypes"] = sorted(types_by_name.values(), key=lambda item: (-float(item.get("confidence") or 0.0), item["name"]))
        merged["keys"] = list(dict.fromkeys(list(merged.get("keys") or []) + list(local.get("keys") or [])))[:8]
        merged["ivs"] = list(dict.fromkeys(list(merged.get("ivs") or []) + list(local.get("ivs") or [])))[:8]

        analysis = dict(merged.get("analysis") or {})
        local_analysis = dict(local.get("analysis") or {})
        for key in ("detectedLibraries", "detectedOperations", "detectedModes", "normalizedAlgorithms", "dynamicKeySources", "runtimeAlgorithmSelection", "obfuscationLoaders", "recommendedApproach", "cryptoSinks"):
            analysis[key] = sorted(set(list(analysis.get(key) or []) + list(local_analysis.get(key) or [])))
        merged_aliases = dict(analysis.get("algorithmAliases") or {})
        for name, aliases in dict(local_analysis.get("algorithmAliases") or {}).items():
            merged_aliases[name] = sorted(set(list(merged_aliases.get(name) or []) + list(aliases or [])))
        analysis["algorithmAliases"] = merged_aliases
        existing_flows = list(analysis.get("keyFlowCandidates") or [])
        seen_flows = {
            (str(item.get("variable")), str(item.get("expression")))
            for item in existing_flows
            if isinstance(item, dict)
        }
        for item in list(local_analysis.get("keyFlowCandidates") or []):
            if not isinstance(item, dict):
                continue
            key = (str(item.get("variable")), str(item.get("expression")))
            if key in seen_flows:
                continue
            existing_flows.append(item)
            seen_flows.add(key)
        analysis["keyFlowCandidates"] = existing_flows
        existing_chains = list(analysis.get("keyFlowChains") or [])
        seen_chains = {
            (
                str(item.get("variable")),
                str((item.get("source") or {}).get("kind")),
                tuple(item.get("sinks") or []),
            )
            for item in existing_chains
            if isinstance(item, dict)
        }
        for item in list(local_analysis.get("keyFlowChains") or []):
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("variable")),
                str((item.get("source") or {}).get("kind")),
                tuple(item.get("sinks") or []),
            )
            if key in seen_chains:
                continue
            existing_chains.append(item)
            seen_chains.add(key)
        analysis["keyFlowChains"] = existing_chains
        analysis["hasKeyDerivation"] = bool(analysis.get("hasKeyDerivation")) or bool(local_analysis.get("hasKeyDerivation"))
        analysis["hasRandomIV"] = bool(analysis.get("hasRandomIV")) or bool(local_analysis.get("hasRandomIV"))
        analysis["requiresASTDataflow"] = bool(analysis.get("requiresASTDataflow")) or bool(local_analysis.get("requiresASTDataflow"))
        analysis["requiresRuntimeExecution"] = bool(analysis.get("requiresRuntimeExecution")) or bool(local_analysis.get("requiresRuntimeExecution"))
        analysis["requiresLoaderUnpack"] = bool(analysis.get("requiresLoaderUnpack")) or bool(local_analysis.get("requiresLoaderUnpack"))
        analysis["riskScore"] = max(int(analysis.get("riskScore") or 0), int(local_analysis.get("riskScore") or 0))
        analysis["reverseComplexity"] = (
            "extreme"
            if analysis["riskScore"] >= 80
            else "high"
            if analysis["riskScore"] >= 55
            else "medium"
            if analysis["riskScore"] >= 30
            else "low"
        )
        merged["analysis"] = analysis

        if merged["cryptoTypes"] and not merged.get("success"):
            merged["success"] = True
        return merged


# 便捷函数
def create_client(base_url: str = None) -> NodeReverseClient:
    """创建逆向客户端"""
    return NodeReverseClient(base_url)
