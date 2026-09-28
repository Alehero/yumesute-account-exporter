# Yumesute Account Exporter

[日本語](README.md) | **English**

[Download ZIP](https://github.com/Alehero/yumesute-account-exporter/archive/refs/heads/main.zip) · [Report a problem](https://github.com/Alehero/yumesute-account-exporter/issues)

Save your own **World Dai Star: Yume no Stellarium** account locally while the official service is still reachable. No private server installation, jailbreak, Apple ID password, purchases, or in-game resource spending is required.

**Do this before shutdown. Reaching home is not enough: wait for `ACCOUNT SAVED` in the computer terminal.** Keep the resulting ZIP private. This project does not upload it anywhere.

The exporter preserves the full `/api/data/user` response, including owned actors, posters, upgrades, inventory, and other records returned by the game. It is a snapshot at login, not an ongoing save-file synchronizer. It does not include game media, every separate API's data, or a guarantee that every feature can already be restored by a private server.

## What you need

- An iPad/iPhone with the working game installed and your account still accessible.
- A Mac or Windows PC and the device on the **same Wi-Fi**. USB alone does not capture the traffic; no cable is required.
- The official [WireGuard app](https://www.wireguard.com/install/) on the device.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) on the computer. It installs the required Python/runtime dependencies automatically on first run.

Mac with Homebrew: `brew install uv`. Windows: `winget install --id=astral-sh.uv -e`, then open a new terminal. If you do not use Homebrew, follow uv's official installation page.

**Verification status:** The standalone Mac → iPad workflow was verified end to end on September 28, 2026: an official login produced a ZIP with a valid checksum, account records, and login association. Tested with macOS 26.2 and an M1 iPad Pro on iPadOS 26.6.1. Seven automated tests pass. Windows instructions are available but have not been device-tested; iPhone is also unverified. This is an early community preview, not a guarantee for every device/network.

## Start

1. Download this repository with **Code → Download ZIP**, and extract it to a folder you own.
2. On Mac, open Terminal, type `cd `, drag the extracted folder into Terminal, press Enter, then run:

   ```sh
   uv run --locked --python 3.12 python launcher.py
   ```

   `Start-Mac.command` is an alternative launcher if executable permissions are retained. If macOS blocks the downloaded launcher, use the Terminal command above after reviewing the source.

   On Windows, double-click `Start-Windows.cmd` after extracting. Keep its terminal window open.
3. A **local setup page** opens with a private QR code. If it does not open, double-click `private/setup.html` in Finder or File Explorer. Its English instructions correspond to the steps below. Follow its instructions:
   - Set the iPad's Wi-Fi HTTP Proxy to **Off**.
   - Import the QR code in WireGuard and enable the tunnel.
   - Open the certificate address shown on the page in iPad Safari.
   - Install the downloaded profile under **Settings → General → VPN & Device Management**.
   - Enable its full trust under **Settings → General → About → Certificate Trust Settings**. Installing the profile alone is insufficient.
4. Fully close the game, launch it again, and reach home.
5. Check the computer terminal for **ACCOUNT SAVED**, actor/poster counts, and a ZIP filename. The file is inside **`exports/`** in this folder. If no success message appears, do not assume your account is saved.
6. Copy the ZIP to a second safe location. After further gameplay, fully close and reopen the game to save a new snapshot. Existing snapshots are never overwritten.
7. Turn WireGuard **off**, press **Control+C** in the terminal, and remove the export certificate profile and WireGuard tunnel when finished. Your ordinary connection should work again.

Do not run this while routed to a private game server: the intended source is the official service. Don't uninstall the game, clear its data, or switch accounts just to use the exporter.

## What gets saved

Each ZIP contains:

- `user-data.response.bin`: the exact decoded HTTP response body, preserving the game's MessagePack types and timestamps.
- `manifest.json`: versioned format, account ID, UTC capture time, record counts, and SHA-256 checksum.
- `account-bridge.json`, when login was observed: account ID plus a SHA-256 digest of the game's installation login token. This lets a future compatible local server recognize the same installation without storing the raw token.

**The ZIP contains private account data and is not encrypted.** Do not attach it to public GitHub issues, social posts, or bug reports. A token hash is still private linking information. On Windows, files inherit your user folder's permissions; use a private user-owned folder.

No raw login tokens, session tokens, request headers, packet logs, WireGuard keys, or certificate signing keys are included in exports. No telemetry or automatic uploads are implemented. Login/session hashes are correlated in memory; a different account cannot accidentally inherit the previous account's bridge.

The `private/` folder contains the local tunnel keys, setup QR, and certificate authority. Do not share it. Only the public certificate is downloadable from the small LAN certificate server. There is no file browser or export-download endpoint.

## Verify an export later, even offline

From this folder, after dependencies are installed:

```sh
uv run --locked --python 3.12 python exporter.py /path/to/your-account.zip
```

Windows paths can be quoted, for example `"C:\Users\You\Documents\your-account.zip"`.

A successful checksum/structure check means the snapshot is intact. It does not prove all game features can be restored. Keep the original ZIP until an importer is released. See [FORMAT.md](FORMAT.md) for implementers.

## Troubleshooting

- **Wrong computer address:** find your Wi-Fi IPv4 address in OS network settings, then run `uv run --locked --python 3.12 python launcher.py --host 192.168.1.23` (replace the example). Re-import the new QR/config after changing address or ports.
- **No certificate download:** check that both devices are on the same network, the computer is awake, the tunnel is on, and guest-network isolation is off. Allow Python on the **private/home** network when the firewall prompts. The defaults are **UDP 51821** for WireGuard and **TCP 8765** for the public certificate. Do not expose these ports to the internet or disable the whole firewall.
- **Port conflict:** use `--wg-port 51822 --cert-port 8766`, then use the updated setup page.
- **Game connection fails:** verify full certificate trust, HTTP Proxy Off, and the export tunnel On. Other VPNs can conflict. Stop the tunnel to restore the ordinary connection.
- **No ACCOUNT SAVED:** fully close/reopen the game. The app may still be using a previous connection. IPv6/network-specific routing can also bypass capture; never infer success from home loading. This preview does not claim every network works.
- **Saved without login matching:** the account inventory is preserved. Fully close/reopen once with capture running to observe login; a new export with its bridge will be written when available. Older ZIPs remain valid inventory backups.
- **Export validation error:** the official response may be a maintenance/fault response or a changed format. The exporter refuses to label these as successful backups. Do not post account files to diagnose it; first report only OS, client version, and the generic error class.
- **Official service already unavailable:** this tool cannot fetch a new account snapshot from an offline server. It cannot recover an account from screenshots or the app's cached media.

## Development

```sh
uv run --locked --python 3.12 python -m unittest discover -v
```

The capture is passive: it does not alter, replay, or create game API calls. Only the game's API host is selected for TLS interception, and only authentication correlation plus `/api/data/user` are processed by the exporter. Other tunnel traffic is forwarded without being exported. Each installation generates its own keys.

Built using [mitmproxy](https://docs.mitmproxy.org/stable/concepts/modes/#wireguard), MessagePack, LZ4, and qrcode. See [Apple's certificate-trust instructions](https://support.apple.com/102390). This is an unofficial community preservation tool, not affiliated with the game's operators. No official game assets or other players' accounts are distributed here.


## Getting help

Open an issue in Japanese or English with your computer/device OS versions, the step that failed, whether `ACCOUNT SAVED` appeared, and the generic error message. Do not upload your account ZIP, `private/` folder, setup QR, tokens, or screenshots containing them. No donation of account data is required to use this tool.

[Changelog](CHANGELOG.md) · [Export format](FORMAT.md) · [Dependency notices](THIRD_PARTY.md)
