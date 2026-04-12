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
