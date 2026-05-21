# Manual install (if HACS does not show Eufy Security)

Use this when the integration never appears in the brands list and there are **no** `eufy_security` log lines (files not installed or manifest invalid).

## Option A — Home Assistant Terminal / SSH

```bash
cd /config
rm -rf custom_components/eufy_security
mkdir -p custom_components
cd custom_components
wget -qO- https://github.com/AKASGaming/eufy_security/archive/refs/heads/master.tar.gz | tar xz
mv eufy_security-master/eufy_security .
rm -rf eufy_security-master
```

Restart Home Assistant, then **Settings** → **Devices & services** → **Add integration** → search **Eufy Security**.

## Option B — Samba / File editor

1. Download https://github.com/AKASGaming/eufy_security/archive/refs/heads/master.zip
2. Extract `custom_components/eufy_security` from the zip.
3. Copy that folder to `config/custom_components/eufy_security` on your HA config drive.
4. Restart Home Assistant.

## Verify before restart

Open `config/custom_components/eufy_security/manifest.json` in a hex editor or check the file starts with `{` (byte `7B`), **not** UTF-8 BOM bytes `EF BB BF`.

## After restart

**Developer tools** → **Info** → **Custom integrations** should list **Eufy Security** version **8.2.50**.
