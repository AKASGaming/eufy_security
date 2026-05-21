"""Rewrite manifest.json as UTF-8 without BOM (HA ignores integrations with BOM)."""
import json
import pathlib

MANIFEST = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "eufy_security" / "manifest.json"

data = {
    "domain": "eufy_security",
    "name": "Eufy Security",
    "codeowners": ["@fuatakgun", "@AKASGaming"],
    "config_flow": True,
    "dependencies": ["ffmpeg", "stream"],
    "documentation": "https://github.com/AKASGaming/eufy_security",
    "integration_type": "hub",
    "iot_class": "cloud_push",
    "issue_tracker": "https://github.com/AKASGaming/eufy_security/issues",
    "requirements": ["websocket-client==1.8.0", "aiortsp==1.4.0"],
    "version": "8.2.55",
}

text = json.dumps(data, indent=2) + "\n"
MANIFEST.write_bytes(text.encode("utf-8"))
raw = MANIFEST.read_bytes()
assert raw[0] == ord("{"), f"manifest must start with '{{', got {raw[:4]!r}"
assert not raw.startswith(b"\xef\xbb\xbf"), "manifest must not have UTF-8 BOM"
print(f"OK: {MANIFEST} ({len(raw)} bytes, no BOM)")
