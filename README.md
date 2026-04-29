# Nora — Permanent proof your files existed

**Drop a file in a watched folder. Nora timestamps it on the Bitcoin blockchain. Done.**

**You never know which files will matter later.** A contract, a draft, a photo, a spreadsheet — most likely you'll never need to prove anything about them. But for the few you do, having a tamper-proof record of when the file existed, in exactly that form, can be the difference between a clean resolution and an expensive one. Think of Nora as a safety net for your files: pay fractions of a cent to timestamp anything that *might* matter someday, and you'll have permanent proof if it ever does.

Nora is a desktop application that creates those records. It monitors a folder you choose, fingerprints each file with a SHA-256 hash, and permanently registers that fingerprint on the Bitcoin SV blockchain. The proof is yours forever, independent of Nora or any third party.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux | Windows | macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/ekseesse/nora/releases)

***

## Download

**[→ Download Nora from GitHub Releases](https://github.com/ekseesse/nora/releases)**

| Platform | File | Instructions |
|----------|------|--------------|
| **Linux** | `Nora-*.AppImage` | Download, run `chmod +x Nora-*.AppImage`, then double-click to launch |
| **Windows** | `Nora-*-Setup.exe` | Download and run executable |
| **macOS** | `Nora-*.dmg` | Open the DMG, drag Nora to Applications. See [macOS Gatekeeper](#macos-gatekeeper) below before first launch |


### macOS Gatekeeper

Nora is not signed with an Apple Developer ID. On first launch macOS will show:

> *"Nora" can't be opened because Apple cannot check it for malicious software.*

This is a **one-time** bypass. Pick whichever is easiest:

**Terminal** (fastest, works on all macOS versions):
```bash
xattr -dr com.apple.quarantine /Applications/Nora.app
```
Then launch Nora normally.

**System Settings** (macOS 13+):
1. Try to open Nora (you'll see the dialog above — click **OK**)
2. Open **System Settings → Privacy & Security**
3. Scroll to the bottom, find *"Nora was blocked..."*, click **Open Anyway**
4. Launch Nora again and click **Open** in the confirmation dialog


## Who is Nora for?

### 🎨 Artists & Musicians

Prove when you created a piece of work — before a dispute, before a pitch, before anyone else claims credit. Nora gives you a blockchain-stamped record of every file, version by version.

- Timestamp original artwork, compositions, and recordings
- Protect intellectual property without a lawyer or notary
- Build a documented creative history over time

### ⚖️ Legal Professionals

Establish an unalterable record of when a document existed. Blockchain timestamps are increasingly accepted as evidence in digital proceedings.

- Record when contracts were finalized or received
- Create audit trails for client files and case documents
- Verify document integrity at any future date

### 💼 Accountants & Tax Advisors

Prove that records were complete before a deadline. No more disputes about when a report was finished or when a file was received.

- Timestamp financial reports and tax documents
- Maintain permanent audit trails for regulatory purposes

### 📄 Anyone with Important Documents

Contracts, proposals, applications, communications — if it matters, timestamp it.

- Prove when you submitted a proposal or application
- Protect signed agreements from backdating disputes
- Create a permanent, verifiable record of important communications

***

## Features

- **Automatic folder watching** — Set a folder and walk away. Nora registers new files as they appear, with configurable recursion and file size limits.
- **Permanent proof** — SHA-256 fingerprints registered on the Bitcoin blockchain cannot be altered or deleted.
- **Private by design** — Your files never leave your computer. Only a cryptographic fingerprint is sent to the blockchain.
- **Verify anytime** — Anyone can verify a file's timestamp, even years later, using nothing but the file and the blockchain record.
- **Local trial mode** — Try Nora without a blockchain account using local simulation mode.
- **Dashboard** — Registration statistics and daily activity chart at a glance.
- **File database** — Searchable, paginated record of every registered file with CSV export.
- **Settings** — Configure your API key, project ID, automation level, and quiet hours.

***

## How it works

1. **Point Nora at a folder** — Choose a directory to watch. Nora monitors it continuously.
2. **Drop a file** — Add any document, image, audio, or other file to the watched folder.
3. **Automatic fingerprinting** — Nora computes a SHA-256 hash of the file — a unique digital fingerprint.
4. **Blockchain registration** — The fingerprint is permanently recorded on the Bitcoin blockchain with the current timestamp.
5. **Verify later** — Open any registered file in Nora's Verify panel to confirm it matches its blockchain record.

***

## Getting Started

1. [Download Nora](https://github.com/ekseesse/nora/releases) for your platform
2. Install and launch the application
3. Complete the one-time setup: add your MintBlue SDK token and project ID (see [Getting a MintBlue API key](#getting-a-mintblue-api-key) below), or enable local trial mode
4. Choose a folder to watch
5. Drop a file — Nora handles the rest

### Getting a MintBlue API key

Nora uses [MintBlue](https://mintblue.com) as the gateway to Bitcoin SV. You need a free account, a project, and an **SDK Access Token** (not the API Access Token — the SDK variant is what Nora needs). The steps below mirror [MintBlue's quick-start guide](https://docs.mintblue.com/quick-start).

1. **Sign up** at [console.mintblue.com/signup](https://console.mintblue.com/signup) and log in.
2. **Create a project**: in the left sidebar click **Projects → New Project**, give it a name (e.g. *"Nora"*), and save. Your **Project ID** is shown on the project overview page — copy it.
3. **Create an SDK token**: click the three dots next to your account name in the bottom-left of the console, then **Access Tokens → New Token**. Choose the **SDK Access Token** type, name it (e.g. *"Nora desktop"*), and save. **Copy the token immediately — it won't be shown again.**
    > **Copy the full string, including the `secret-token:` prefix.** The token is the entire value (e.g. `secret-token:abc123…`), not just the hex part. Nora will reject a token pasted without the prefix.
4. In Nora, open **Settings** and paste both values:
    - *MintBlue SDK Token* → the SDK token from step 3
    - *MintBlue Project ID* → the ID from step 2
5. Save. Nora will verify the credentials and switch from local trial mode to live blockchain mode.

> **Trying Nora first?** You can skip this setup and use **Local Trial Mode** (Settings → *Operating Mode* → *Local*). No blockchain, no account — just a local simulation to evaluate the workflow before committing to MintBlue.

***

## Technical Details

- **Blockchain**: Bitcoin SV via MintBlue API
- **Hashing**: SHA-256 per file
- **Database**: SQLite (stored at `~/.nora/nora.db`)
- **Backend**: Python with pywebview
- **Frontend**: React, TypeScript, Chakra UI
- **Packaging**: PyInstaller (Linux AppImage, Windows EXE, macOS bundle)

***

*Nora is open source. MIT licensed. [View on GitHub](https://github.com/ekseesse/nora)*
