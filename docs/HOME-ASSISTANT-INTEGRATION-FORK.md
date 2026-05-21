# Home Assistant integration fork (T85D0 / T85L0)

This fork adds a Home Assistant **lock** entity for Eufy smart locks that report state via `lockStatus` (MQTT), including **T85D0** and **T85L0**.

## Prerequisites

- **Eufy Security WS** add-on running (dev add-on with T85D0 client fork recommended).
- **HACS** installed in Home Assistant.
- **FFmpeg** and **Stream** integrations (dependencies — usually already present on HA OS).

## Install via HACS

1. **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. Add:
   - **Repository:** `https://github.com/AKASGaming/eufy_security`
   - **Category:** Integration
3. **HACS** → **Integrations** → search **Eufy Security** → **Download**
4. **Restart Home Assistant** (full restart, not quick reload)

## Add the integration (important)

Custom integrations **do not always appear as a tile** on the main “Add integration” screen.

1. **Settings** → **Devices & services**
2. **Add integration** (bottom right)
3. In the **search box**, type: **`Eufy Security`** (exact name from manifest)
4. Select **Eufy Security** → enter WebSocket host/port (`127.0.0.1` / `3000` if the WS add-on runs on the same HA host)

Alternative: **HACS** → **Integrations** → **Eufy Security** → **⋮** → **Open integration** / **Configure** (if shown after download).

## Version

**8.2.50** on branch **`main`** (only branch on this fork).

## Not in the integration list?

Work through this list in order:

### 1. Confirm HACS actually installed the files

Check that this folder exists on your HA config volume:

```text
config/custom_components/eufy_security/manifest.json
```

(File editor, Samba, or SSH.) If the folder is missing, use HACS → **Redownload** → **Restart HA**.

### 2. Check for load errors

**Settings** → **System** → **Logs** → search for `eufy_security`.

Common failures:

- **Invalid manifest version** — use this fork **8.2.50** or newer (not `8.2.5-t85d0.1`).
- **Missing dependency** — install **FFmpeg** and **Stream** from **Settings** → **Devices & services** → **Add integration** (search those names).
- **Import error** — remove `custom_components/eufy_security`, redownload from HACS, restart.

### 3. Remove a broken or duplicate install

If you switched from official **fuatakgun** to **AKASGaming**:

1. **Settings** → **Devices & services** → remove any **Eufy Security** config entry (⋮ → Delete).
2. **HACS** → remove old **Eufy Security** if two entries exist.
3. Ensure only **one** folder: `custom_components/eufy_security` (not a nested copy).
4. Redownload from `AKASGaming/eufy_security`, restart, then add via search again.

### 4. HACS custom repository still registered?

**HACS** → **Integrations** → **⋮** → **Custom repositories** → `AKASGaming/eufy_security` must be listed.

### 5. Already configured?

This integration allows **one** config entry. If one exists (even broken), use **Reload** or **Delete** on that entry instead of adding a second time.

## Upstream

Based on [fuatakgun/eufy_security](https://github.com/fuatakgun/eufy_security). T85D0 lock issues: [AKASGaming/eufy_security issues](https://github.com/AKASGaming/eufy_security/issues).
