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

**8.2.54** on branch **`master`** (default). Branch **`main`** is kept in sync.

## Not in the brands / integration list?

### UTF-8 BOM in manifest (fixed in 8.2.50+)

If there are **no** `eufy_security` lines in HA logs and the integration vanished from **Add integration** search, `manifest.json` likely has a **UTF-8 BOM** (`EF BB BF` before `{`). Home Assistant then **ignores** the integration entirely (no brands tile, no search hit). **Redownload 8.2.54+** from this repo, or use [MANUAL-INSTALL.md](MANUAL-INSTALL.md). On Windows, verify the file starts with `{` not invisible BOM (see MANUAL-INSTALL).

### HACS branch / master

If this stopped after a GitHub branch cleanup: HACS may have cached the deleted **`master`** branch. This fork uses **`master`** as default again (same as [fuatakgun/eufy_security](https://github.com/fuatakgun/eufy_security)).

**Fix in HACS:**

1. **HACS** → **Integrations** → **Eufy Security** → if present, **Remove** (HACS side only).
2. **HACS** → **⋮** → **Custom repositories** → remove `AKASGaming/eufy_security`, save.
3. Re-add custom repository: `https://github.com/AKASGaming/eufy_security` (Integration).
4. **Download** / **Update** Eufy Security → **Restart Home Assistant**.
5. **Add integration** → search **`Eufy Security`**.

Work through this list if it still does not appear:

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
