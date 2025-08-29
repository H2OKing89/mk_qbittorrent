# Torrent Creator Web UI — Functional & Implementation Spec

> Goal: Build a qBittorrent-style “Create Torrent” experience in the browser (Alpine.js front-end + server backend) with tracker-friendly defaults, strong validation, and reproducible outputs.

---

## Table of Contents
1. [Scope](#scope)
2. [Non-Goals](#non-goals)
3. [User Journey (Happy Path)](#user-journey-happy-path)
4. [Desktop Creator Parity — Behavior by Section](#desktop-creator-parity--behavior-by-section)
   - [Select file/folder to share](#1-select-filefolder-to-share)
   - [Settings](#2-settings)
   - [Fields](#3-fields)
   - [Progress & Actions](#4-progress--actions)
5. [Web UI Architecture](#web-ui-architecture)
   - [Client State Model](#client-state-model)
   - [Backend API Contract](#backend-api-contract)
   - [Piece Size Auto Heuristic](#piece-size-auto-heuristic)
   - [Tiered Tracker Parsing](#tiered-tracker-parsing)
   - [SSE/WebSocket Progress Streaming](#ssewebsocket-progress-streaming)
6. [Validation Matrix](#validation-matrix)
7. [Edge Cases & Recovery](#edge-cases--recovery)
8. [Defaults & Profiles](#defaults--profiles)
9. [Reproducibility & Cross-Seeding](#reproducibility--cross-seeding)
10. [Security & Privacy](#security--privacy)
11. [Accessibility & i18n](#accessibility--i18n)
12. [UX Details & Layout](#ux-details--layout)
13. [Logging, Telemetry, and Audit](#logging-telemetry-and-audit)
14. [Testing Strategy](#testing-strategy)
15. [Performance Targets](#performance-targets)
16. [Roadmap & Future Enhancements](#roadmap--future-enhancements)
17. [Glossary](#glossary)

---

## Scope
Deliver a browser UI that mirrors qBittorrent Desktop’s **Torrent Creator** with:
- File/folder selection (server-side paths),
- Piece sizing (auto/manual) and computed piece count,
- Private flag, start-seeding, ratio-ignore interlocks,
- Alignment (pad files) with thresholds,
- Trackers (tiered), Web Seeds, Comment, Source,
- Live progress (scan → hash → finalize),
- Output: `.torrent` file + optional immediate add/seed via qBittorrent Web API.

Supported metadata modes: **v1** (default). Optional **v2/hybrid** can be exposed behind an “advanced” toggle if backend supports it (see tracker caveats).

---

## Non-Goals
- Browser-side hashing of server files.
- Client-side file upload seeding (out of scope for private tracker workflows).
- Full file manager; we only need a minimal server-side browser.

---

## User Journey (Happy Path)
1. Open Creator → paste or browse to **server path** (file or directory).
2. App **scans** path → shows total bytes + file count.
3. Choose **Auto** piece size (default) → click “Calculate” → shows chosen size and piece count.
4. **Private** is ON by default. Start seeding OFF by default.
5. Paste **tracker** URL(s). (Optional: add more tiers.)
6. (Optional) Add **Comment**, **Source**, Web Seeds (discouraged with private).
7. Click **Create** → progress stream → download `.torrent`.  
   If _Start seeding_ is ON, torrent is added to qBittorrent and seeding begins.

---

## Desktop Creator Parity — Behavior by Section

### 1) Select file/folder to share
- **Path**: single file or directory; toggles mode internally.
- **Browse file / folder**: server-side picker modal.
- **Drag-and-drop**: disabled unless implementing upload flow (not required).
- **Invalidation**: change path ⇒ clear previous piece count, recompute size, disable “Create” until rescan.

**Under the hood**
- Folder scan builds a stable, sorted list (bytewise lexicographic) for deterministic infohashes.
- If alignment is later enabled, pad files may be inserted into metadata (not on disk).

### 2) Settings

#### Piece size
- **Auto**: choose power-of-two (64 KiB…16 MiB) to land near target piece count (default target ≈ **2500**).
- **Manual**: user picks from 16 KiB…16 MiB.
- Show **piece count** and **estimated .torrent size**.

**Recommended caps & targets**
- Target piece count: 1500–4000.
- Max piece size: 16 MiB (unless tracker dictates smaller).

#### “Calculate number of pieces”
- Disabled until path scanned.
- In **Auto**, display both the chosen size and resultant piece count.

#### Private torrent
- **ON by default**. Encodes “private” in metadata to disable DHT/PEX/LPD.
- If OFF, show warning: “Private trackers typically require this.”

#### Start seeding immediately
- If ON: after creation, add torrent to client, set save path = selected path, force recheck.

#### Ignore share ratio limits
- Enabled only if **Start seeding** is ON.

#### Optimize alignment
- OFF by default. If ON, provide **threshold** dropdown: Disabled / 32 MiB / 64 MiB / 128 MiB …
- Tooltip: “Adds pad files to align large files to piece boundaries; some trackers forbid pads.”

### 3) Fields

#### Tracker URLs
- Multiline; **one URL per line**.
- **Tiers**: separate by a **blank line**.  
  Tier 1 = first block, Tier 2 = second block, etc.
- Validate scheme (`http(s)://` or `udp://`); warn if `/announce` missing on private URLs.

**Example (two tiers):**
```

[https://t.example.org/announce](https://t.example.org/announce)
udp\://tracker.example.net:6969/announce

[https://backup.example.org/announce](https://backup.example.org/announce)

````

#### Web seed URLs
- Multiline; BEP-19. Show warning if Private is ON (“often forbidden”).

#### Comments
- Free text stored in metainfo. Good for your signature and build info.

#### Source
- Optional. Tracker-specific tag (e.g., site short name).  
  **Leave blank** if you plan to cross-seed unless the site mandates it.

### 4) Progress & Actions
- **Progress bar** with phases:
  1) Scanning files,
  2) Hashing pieces,
  3) Finalizing metadata.
- **Create**: validates, streams progress, returns `.torrent` and optional “added to client”.
- **Cancel**: aborts cleanly.

---

## Web UI Architecture

### Client State Model
```ts
type Tier = string[];

interface CreatorForm {
  mode: 'file' | 'folder';
  path: string;
  totalBytes: number | null;
  fileCount: number | null;

  pieceSizeMode: 'auto' | 'manual';
  pieceSizeBytes: number | null;   // null when auto until computed
  targetPieces: number;            // default 2500

  privateTorrent: boolean;         // default true
  startSeeding: boolean;           // default false
  ignoreShareRatio: boolean;       // gated by startSeeding

  optimizeAlignment: boolean;      // default false
  alignThresholdBytes: number | null;

  announceTiers: Tier[];           // [[url1, url2], [url3]]
  webSeeds: string[];

  comment: string;
  source: string;

  v2Mode: 'v1' | 'v2' | 'hybrid';  // default 'v1' for private trackers
}
````

### Backend API Contract

**POST `/api/scan`**
Request: `{ path: string }`
Response: `{ totalBytes: number, fileCount: number, exists: boolean, mode: 'file' | 'folder' }`

**POST `/api/pieces`**
Request: `{ totalBytes: number, desiredPieceSize?: number | null, target?: number }`
Response: `{ pieceSizeBytes: number, pieceCount: number }`

**POST `/api/create`**
Request: mirrors `CreatorForm` (server will rescan to avoid tampering).
Response (final):

```json
{
  "torrentPath": "/srv/torrents/MyFile.torrent",
  "infoHashV1": "abc123...",
  "infoHashV2": null,
  "added": true,
  "warnings": ["web seeds ignored for private"],
  "padFiles": 12,
  "pieceCount": 2476
}
```

**Progress:** stream via **SSE** at `/api/create/stream?jobId=...` or upgrade initial request to WebSocket.

### Piece Size Auto Heuristic

Pseudocode:

```text
size = 64 KiB
while (totalBytes / size) > targetPieces and size < 16 MiB:
    size *= 2
return size
```

* Recompute piece **count = ceil(totalBytes / size)**.
* For v2/hybrid (if enabled), consider more conservative targets (trees cost overhead).

### Tiered Tracker Parsing

* Split on `\n\n+` for tiers, then split each tier on `\n`.
* Trim whitespace; drop empty lines.
* Validate each URL; return per-line error map.

### SSE/WebSocket Progress Streaming

SSE event types:

* `scan` → `{ files: number, bytes: number }`
* `hash` → `{ currentFile: "path", fileIndex: n, files: N, bytesHashed: b, bytesTotal: B, etaSeconds: t }`
* `finalize` → `{ pieceCount: n }`
* `done` → `{ torrentPath, infoHashV1, infoHashV2, added }`
* `error` → `{ message }`

---

## Validation Matrix

| Field               | Rule                                          | Error Copy                                                                  |
| ------------------- | --------------------------------------------- | --------------------------------------------------------------------------- |
| Path                | Must exist and be readable server-side        | “Path not found or inaccessible.”                                           |
| Trackers            | ≥1 URL total; valid schemes; grouped by tiers | “Add at least one valid tracker URL.”                                       |
| Private + Web Seeds | Warn when both present                        | “Private trackers often forbid web seeds.”                                  |
| Piece Size (manual) | Must be power-of-two 16 KiB…16 MiB            | “Piece size must be a power-of-two between 16 KiB and 16 MiB.”              |
| Start Seeding       | If OFF ⇒ force Ignore Ratio = false           | (no inline error; auto-fix silently)                                        |
| Alignment           | If ON ⇒ threshold required                    | “Choose an alignment threshold or disable alignment.”                       |
| v2/hybrid           | If ON and Private ⇒ show visible warning      | “Many private trackers reject v2/hybrid torrents.”                          |
| Source              | If non-empty and profile forbids it           | “This tracker profile recommends leaving `source` blank for cross-seeding.” |

---

## Edge Cases & Recovery

1. **Multi-TB trees** — hashing can take hours: keep the job resumable (jobId token).
2. **Permission errors** — show per-file failures; allow “exclude unreadable files” checkbox.
3. **Symlinks, devices, sparse files** — decide policy: default to **dereference symlinks**, skip devices.
4. **Long paths / Unicode** — ensure normalization to NFC; avoid truncation.
5. **Pad files** — highlight count in summary; offer 1-click “Rebuild without pads”.
6. **Network drop** — SSE reconnect by `Last-Event-ID`, resume from last phase.

---

## Defaults & Profiles

* **Global defaults**

  * Private: **ON**
  * Piece size: **Auto** (target 2500)
  * Start seeding: **OFF**
  * Alignment: **Disabled**
  * v2Mode: **v1**
* **Tracker profiles** (JSON in `/config/tracker-profiles.json`)

```json
{
  "MAM": {
    "announce": ["https://t.myanonamouse.net/announce"],
    "allowWebSeeds": false,
    "requirePrivate": true,
    "setSource": false
  }
}
```

* UI “Profile” dropdown preloads `announce`, toggles warnings, and locks `Private` if required.

---

## Reproducibility & Cross-Seeding

* **Stable sort** of file list (bytewise lexicographic).
* **Line ending normalization** for text files is **not** performed; we hash raw bytes.
* Avoid setting **Source** unless mandated.
* Default to **v1** torrents for the broadest cross-seed compatibility.
* Keep **save path** identical across trackers to avoid mismatches.

---

## Security & Privacy

* Server validates paths against an **allowlist root** (e.g., `/mnt/user/media`).
* No arbitrary shell execution exposed via API.
* Rate-limit create operations; cap concurrent jobs.
* Don’t log full announce URLs if they contain **passkeys**; mask as `.../announce?passkey=****`.

---

## Accessibility & i18n

* All interactive elements reachable by keyboard; visible focus rings.
* Tooltips via `aria-describedby`.
* Copy is string-keyed for easy localization later.

---

## UX Details & Layout

* **Card 1**: Path Picker
  Small helper text: “Server path (not your browser’s).”
* **Card 2**: Settings
  3-column grid: Piece Size | Privacy/Seeding | Alignment.
* **Card 3**: Trackers
  Tier editor with `+ Add Tier` and per-line validation icons.
* **Card 4**: Extras
  Web Seeds, Comment, Source with live char counts.
* **Footer**: Summary chips (size, files, piece size, piece count, pads), progress bar, Create/Cancel.

---

## Logging, Telemetry, and Audit

* Server logs: `jobId`, path hash (not raw path), totals, chosen piece size, piece count, pad count, duration, result.
* Client logs only high-level events; redact passkeys.
* Optional: emit OpenTelemetry spans for scan/hash/finalize.

---

## Testing Strategy

**Unit**

* Tracker parsing (tiers), URL validation.
* Piece size heuristic across diverse `totalBytes`.
* Alignment threshold logic.

**Integration**

* `/api/scan` with real directory fixtures (empty, huge, mixed permissions).
* `/api/create` happy path + cancel + resume.

**E2E**

* Cypress/Playwright flow: select path → calculate → create → verify `.torrent` is downloadable and valid (decode info dictionary, assert piece count).

**Golden Files**

* Fixture trees with known, stable infohashes (v1) to catch regressions.

---

## Performance Targets

* Scan: ≥ 100k files/min on SSD trees.
* Hash throughput: close to disk read speed (don’t bottleneck CPU; enable multi-thread hashing if backend supports).
* UI time-to-interactive < 200 ms; progress updates ≥ 5 Hz.

---

## Roadmap & Future Enhancements

* **Profiles**: import/export, per-tracker rules (“forbid web seeds”, “force private”).
* **Template comments**: auto-inject build/version, H2OKing signature.
* **Batch mode**: queue multiple paths.
* **Verify-only**: compute infohash without writing `.torrent`.
* **Magnet preview**: generate magnet for quick tests (private trackers often disallow, keep behind dev flag).
* **v2/hybrid**: gated by tracker policy toggle.

---

## Glossary

* **Piece size**: Chunk size used for hashing content; determines piece count.
* **Tier**: Group of trackers tried in parallel before moving to the next group.
* **Pad file**: Zero-filled pseudo-file inserted to align file boundaries with piece boundaries.
* **Private flag**: Bit in metadata that disables DHT/PEX/LPD for that torrent.
* **Infohash**: SHA1 (v1) or Merkle root (v2) that uniquely identifies the torrent content.

---

## Appendix A — UI Pseudocode (Alpine.js)

```html
<form x-data="creator()" @submit.prevent="create()">
  <!-- cards and inputs omitted for brevity -->
</form>

<script>
function creator(){
  return {
    form: {
      mode: 'folder',
      path: '',
      totalBytes: null,
      fileCount: null,

      pieceSizeMode: 'auto',
      pieceSizeBytes: null,
      targetPieces: 2500,

      privateTorrent: true,
      startSeeding: false,
      ignoreShareRatio: false,

      optimizeAlignment: false,
      alignThresholdBytes: null,

      announceTiers: [['https://.../announce']],
      webSeeds: [],
      comment: '',
      source: '',
      v2Mode: 'v1',
    },

    pieceCount: null,
    jobId: null,

    get canCalcPieces(){ return !!this.form.path && (this.form.totalBytes ?? 0) > 0; },
    get canCreate(){ return this.validate().ok; },

    async scanPath(){
      const r = await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:this.form.path})});
      const d = await r.json();
      this.form.totalBytes = d.totalBytes; this.form.fileCount = d.fileCount;
    },

    async calcPieces(){
      const desired = this.form.pieceSizeMode === 'auto' ? null : this.form.pieceSizeBytes;
      const r = await fetch('/api/pieces',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ totalBytes:this.form.totalBytes, desiredPieceSize:desired, target:this.form.targetPieces })});
      const d = await r.json();
      this.form.pieceSizeBytes = d.pieceSizeBytes; this.pieceCount = d.pieceCount;
    },

    validate(){
      const e = [];
      if(!this.form.path) e.push('Select a file or folder.');
      if(!this.form.announceTiers.flat().length) e.push('Add at least one tracker URL.');
      if(this.form.optimizeAlignment && !this.form.alignThresholdBytes) e.push('Choose an alignment threshold or disable alignment.');
      if(!this.form.startSeeding) this.form.ignoreShareRatio = false;
      return { ok: e.length===0, errors: e };
    },

    async create(){
      const v = this.validate(); if(!v.ok){ alert(v.errors.join('\\n')); return; }
      const r = await fetch('/api/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(this.form)});
      const d = await r.json(); // or attach to SSE stream
      // render completion UI and link to d.torrentPath
    }
  }
}
</script>
```

---

## Appendix B — Heuristic Notes

**Estimated .torrent size (v1):**
`~(bencode overhead 20–80 KiB) + (20 bytes * pieceCount)`
Display this estimate under the piece count so users understand the trade-off.

**Alignment Guidance:**
Enable only when seeding very large, multi-GB files that benefit from boundary alignment. On private trackers, prefer **Disabled** unless policy allows pads.

```
```
