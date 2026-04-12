from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

FETCHER_PATH = (
    Path(__file__).resolve().parents[1] / "pyspider" / "node_reverse" / "fetcher.py"
)
SPEC = spec_from_file_location("pyspider_node_reverse_fetcher", FETCHER_PATH)
fetcher_module = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(fetcher_module)
NodeReverseFetcher = fetcher_module.NodeReverseFetcher


def test_pre_process_task_uses_sync_decrypt(monkeypatch):
    fetcher = NodeReverseFetcher()

    def fake_decrypt(self, algorithm, data, key, iv=None, mode=None):
        return {"success": True, "decrypted": f"plain:{data}"}

    monkeypatch.setattr(fetcher_module.NodeReverseClient, "decrypt", fake_decrypt)

    task = {
        "url": "https://example.com",
        "fetch": {
            "encrypt_params": {
                "algorithm": "AES",
                "encrypted_data": "cipher",
                "key": "secret",
            }
        },
    }

    processed = fetcher._pre_process_task(task)
    assert processed["decrypted_data"] == "plain:cipher"


def test_post_process_response_records_crypto_analysis(monkeypatch):
    fetcher = NodeReverseFetcher()

    def fake_analyze_crypto(self, code):
        return {
            "success": True,
            "analysis": {"hasKeyDerivation": True},
            "cryptoTypes": ["AES"],
        }

    monkeypatch.setattr(
        fetcher_module.NodeReverseClient, "analyze_crypto", fake_analyze_crypto
    )

    result = fetcher._post_process_response(
        {
            "content": "function sign(){return 'ok'}",
            "content_type": "application/javascript",
            "headers": {"Content-Type": "application/javascript"},
            "orig_url": "https://example.com/app.js",
        }
    )

    assert result["crypto_analysis"]["hasKeyDerivation"] is True


def test_extract_js_crypto_falls_back_to_ast_analysis(monkeypatch):
    fetcher = NodeReverseFetcher()

    def fake_analyze_ast(self, code, analysis):
        return {
            "success": True,
            "results": {"crypto": [{"name": "AES"}], "analysis": analysis},
        }

    monkeypatch.setattr(
        fetcher_module.NodeReverseClient, "analyze_ast", fake_analyze_ast
    )

    result = fetcher.extract_js_crypto("const secret = encrypt(data)")
    assert result["success"] is True
    assert result["results"]["analysis"] == ["crypto", "obfuscation", "anti-debug"]
