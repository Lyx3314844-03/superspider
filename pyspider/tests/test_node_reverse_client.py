from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

CLIENT_PATH = (
    Path(__file__).resolve().parents[1] / "pyspider" / "node_reverse" / "client.py"
)
SPEC = spec_from_file_location("pyspider_node_reverse_client", CLIENT_PATH)
client_module = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(client_module)
NodeReverseClient = client_module.NodeReverseClient


def test_profile_anti_bot_uses_profile_endpoint(monkeypatch):
    captured = {}

    def fake_do_request(self, path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"success": True, "level": "high"}

    monkeypatch.setattr(NodeReverseClient, "_do_request", fake_do_request)

    client = NodeReverseClient("http://localhost:3000")
    response = client.profile_anti_bot(
        html="<title>Just a moment...</title>",
        headers={"cf-ray": "token"},
        status_code=429,
        url="https://target.example/challenge",
    )

    assert response["success"] is True
    assert captured["path"] == "/api/anti-bot/profile"
    assert captured["payload"]["statusCode"] == 429


def test_detect_anti_bot_uses_detect_endpoint(monkeypatch):
    captured = {}

    def fake_do_request(self, path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"success": True, "signals": ["vendor:cloudflare"]}

    monkeypatch.setattr(NodeReverseClient, "_do_request", fake_do_request)

    client = NodeReverseClient("http://localhost:3000")
    response = client.detect_anti_bot(headers={"cf-ray": "token"})

    assert response["success"] is True
    assert captured["path"] == "/api/anti-bot/detect"
    assert captured["payload"]["headers"]["cf-ray"] == "token"


def test_analyze_crypto_merges_local_multi_algorithm_heuristics(monkeypatch):
    def fake_do_request(self, path, payload):
        return {"success": False, "error": "offline"}

    monkeypatch.setattr(NodeReverseClient, "_do_request", fake_do_request)

    client = NodeReverseClient("http://localhost:3000")
    response = client.analyze_crypto(
        """
        const key = "secret-key-1234";
        const iv = "nonce-001";
        const token = CryptoJS.HmacSHA256(data, key).toString();
        const cipher = sm4.encrypt(data, key, { mode: "cbc" });
        const digest = CryptoJS.SHA256(data).toString();
        const derived = CryptoJS.PBKDF2(password, salt, { keySize: 8 });
        const sessionKey = localStorage.getItem("session-key");
        const derivedKey = sha256(sessionKey || key);
        window.crypto.subtle.encrypt({ name: "AES-GCM", iv }, derivedKey, data);
        """
    )

    names = {item["name"] for item in response["cryptoTypes"]}
    assert response["success"] is True
    assert {"AES", "SM4", "HMAC-SHA256", "SHA256", "PBKDF2"} <= names
    assert "secret-key-1234" in response["keys"]
    assert "nonce-001" in response["ivs"]
    assert "CryptoJS" in response["analysis"]["detectedLibraries"]
    assert "crypto.subtle.encrypt" in response["analysis"]["cryptoSinks"]
    assert "aes-gcm" in response["analysis"]["algorithmAliases"]["AES"]
    assert any(
        candidate["variable"] == "sessionKey"
        and "storage.localStorage" in candidate["sources"]
        for candidate in response["analysis"]["keyFlowCandidates"]
    )
    assert any(
        chain["variable"] == "sessionKey"
        and chain["source"]["kind"] == "storage.localStorage"
        and any(step["variable"] == "derivedKey" for step in chain["derivations"])
        and "crypto.subtle.encrypt" in chain["sinks"]
        for chain in response["analysis"]["keyFlowChains"]
    )
    assert response["analysis"]["reverseComplexity"] in {"medium", "high", "extreme"}
    assert "trace-key-materialization" in response["analysis"]["recommendedApproach"]
    assert response["analysis"]["requiresASTDataflow"] is True
