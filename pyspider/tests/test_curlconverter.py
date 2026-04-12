from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pyspider.core.curlconverter import CurlToPythonConverter


def test_convert_to_aiohttp_generates_get_request():
    converter = CurlToPythonConverter()

    code = converter.convert_to_aiohttp(
        'curl "https://example.com/api" -H "Accept: application/json"'
    )

    assert "async with session.request(" in code
    assert "'GET'" in code
    assert "'https://example.com/api'" in code
    assert '"Accept": "application/json"' in code
    assert "response.raise_for_status()" in code


def test_convert_to_aiohttp_generates_post_request_with_data():
    converter = CurlToPythonConverter()

    code = converter.convert_to_aiohttp(
        'curl -X POST "https://example.com/login" -H "Content-Type: application/json" --data \'{"user":"alice"}\''
    )

    assert "'POST'" in code
    assert "'https://example.com/login'" in code
    assert '"Content-Type": "application/json"' in code
    assert 'data = "{\\"user\\":\\"alice\\"}"' in code
