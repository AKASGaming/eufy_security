# Home Assistant integration fork (T85D0 / T85L0)

This fork adds a Home Assistant **lock** entity for Eufy smart locks that report state via `lockStatus` (MQTT), including **T85D0** and **T85L0**, while keeping upstream behavior for other locks.

## Prerequisites

- **Eufy Security WS** add-on (or dev add-on) connected to your account, with a client build that supports T85D0 MQTT (see [bropat/eufy-security-client PR #797](https://github.com/bropat/eufy-security-client/pull/797) or your fork on `feat/t85d0-smart-lock-c30`).
- **HACS** installed in Home Assistant.

## Install via HACS (custom repository)

1. In Home Assistant, open **HACS** → **Integrations** → **⋮** (menu) → **Custom repositories**.
2. Add repository:
   - **Repository:** `https://github.com/AKASGaming/eufy_security`
   - **Category:** Integration
3. Search for **Eufy Security**, open it, choose branch **`feat/t85d0-smart-lock-c30`**, and **Download**.
4. **Restart** Home Assistant.
5. **Settings** → **Devices & services** → **Add integration** → **Eufy Security** → point at your WebSocket bridge (default port `3000`).

## Version

Integration version in this branch: **8.2.5-t85d0.1**.

## Upstream

Based on [fuatakgun/eufy_security](https://github.com/fuatakgun/eufy_security). Report T85D0-specific lock issues on this fork; general integration bugs may still belong upstream.

## Related workspace docs

If you use the dev add-on + client fork workflow, see your project `docs/HOME-ASSISTANT-SETUP.md` for the full stack (client, WS add-on, HACS).
