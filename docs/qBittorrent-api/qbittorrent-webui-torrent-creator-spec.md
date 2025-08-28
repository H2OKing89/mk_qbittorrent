# qBittorrent WebUI — Torrent Creator Spec & Reference

**Purpose:** Recreate qBittorrent’s desktop “Torrent Creator” as a modern Web UI component (Alpine.js + Tailwind), tuned for private trackers and cross-seeding.

**Status:** Draft (ready for implementation)

**Audience:** Frontend/Backend devs (and Future You at 2 AM)

---

## Table of Contents
- [Goals](#goals)
- [Non-Goals](#non-goals)
- [Tech Stack & Assumptions](#tech-stack--assumptions)
- [UX Overview](#ux-overview)
- [Functional Spec](#functional-spec)
  - [1) Select file/folder to share](#1-select-filefolder-to-share)
  - [2) Settings](#2-settings)
  - [3) Fields](#3-fields)
  - [4) Progress + Actions](#4-progress--actions)
- [Under the Hood (Behavioral Notes)](#under-the-hood-behavioral-notes)
- [Web UI Blueprint (Alpine.js)](#web-ui-blueprint-alpinejs)
  - [Data Model](#data-model)
  - [Component Anatomy](#component-anatomy)
  - [State & Methods (Skeleton)](#state--methods-skeleton)
- [Backend API (Sketch)](#backend-api-sketch)
- [Validation & UX Niceties](#validation--ux-niceties)
- [Opinionated Defaults](#opinionated-defaults)
- [Edge Cases](#edge-cases)
- [Security & Privacy](#security--privacy)
- [Performance Targets](#performance-targets)
- [Tracker Profiles (Optional)](#tracker-profiles-optional)
- [Acceptance Criteria Checklist](#acceptance-criteria-checklist)
- [Testing Plan](#testing-plan)
- [Future Enhancements](#future-enhancements)

---

## Goals
- Match desktop creator parity for the common flow: **pick path → add tracker(s) → create** in < 10s.
- Stay **private-tracker friendly** (default private, v1 torrents).
- Enable **tiered trackers** and sane piece-size heuristics.
- Stream **scan/hash progress** with reconnection resilience.
- Keep the UI **predictable, fast, and boring** (in the best way).

## Non-Goals
- Browser-side hashing of server files (not feasible).
- Managing client-wide settings (ratio rules, categories, etc.) outside per-torrent toggles.
- Tracker-specific automation beyond simple “profiles.”

## Tech Stack & Assumptions
- **Frontend:** Alpine.js + Tailwind.
- **Backend:** Any (Node/Python/Go) that can:
  - Read server filesystem (stat/scan).
  - Build .torrent metadata (libtorrent or equivalent).
  - Optionally talk to qBittorrent Web API to add & start seeding.
- **Environment:** Server has access to the target files/folders. Browsers do **not** upload content for this workflow.

---

## UX Overview
Four stacked cards:
1. **Path Picker**  
2. **Settings** (Piece Size, Private/Seeding, Alignment)  
3. **Fields** (Trackers, Web Seeds, Comment, Source)  
4. **Summary & Progress** (Stats, Create/Cancel)

> **Rule of thumb:** Minimal ceremony—defaults get you a valid private-tracker torrent without surprises.

---

## Functional Spec

### 1) Select file/folder to share
- **Path**: Choose a single file *or* a directory.
  - **File mode** → one payload, no internal tree.
  - **Folder mode** → recursive tree with preserved subpaths.
- **Select file / Select folder**: Server-side picker modal.
- **Drag & Drop**: Optional; disabled for non-upload flow.
- **Behavior:** Dependent fields (size, piece count) invalidate on change.

**Under the hood**
- Scan size + file list before hashing.
- Folder mode uses **stable, canonical sorting** for reproducible infohashes.
- Alignment (if enabled) may inject **pad files** (see Alignment).

### 2) Settings

#### Piece size
- **Auto** (default): Pick a power-of-two piece size so **piece count** lands in a sane range.
- **Manual**: 16 KiB → 16 MiB.

**Auto heuristic (practical)**
- Start 64 KiB; double until `total_size / piece_size ≤ target_piece_count`.
- Target **1,500–4,000** pieces. Cap at **16 MiB** unless policy says smaller.

#### “Calculate number of pieces”
- Recomputes using current path + piece size.
- In Auto, show **chosen piece size** *and* resulting **piece count**.
- Disabled until a valid path exists.

#### Private torrent
- **ON** disables DHT/PEX/LPD in metadata.  
- Default **checked** (private trackers require this).  
- If off, warn that many private trackers will reject the torrent.

#### Start seeding immediately
- If enabled, after creation:
  1. Add torrent to client,
  2. Set content path,
  3. Start seeding.
- **Interlock:** If unchecked → **Ignore share ratio** disabled.

#### Ignore share ratio limits
- Only meaningful when “Start seeding” is on; allows bypassing global ratio rules.

#### Optimize alignment
- Inserts **pad files** so files larger than a threshold begin on piece boundaries.
- Dropdown: **Disabled** (default), 32 MiB, 64 MiB, 128 MiB…
- **Why:** Disk I/O benefits; prevents multi-file spanning per piece.
- **Caveat:** Some trackers forbid pad files → default **Disabled** + tooltip.

### 3) Fields

#### Tracker URLs
- Multiline textarea.
- **Each line** = one announce URL.
- **Tiers:** Blank line separates tiers (Tier 1 block, then Tier 2…).
- Validate scheme (`http(s)://` or `udp://`); warn if missing `/announce` on HTTP(S).

**Example (two tiers):**
```

[https://t.example.org/announce](https://t.example.org/announce)
udp\://tracker.example.net:6969/announce

[https://backup.example.org/announce](https://backup.example.org/announce)

````

#### Web seed URLs
- HTTP/FTP seeds (BEP-19). Often forbidden on private sites.
- Multiline; URL-validate; show “Private trackers often prohibit this” warning if Private is on.

#### Comments
- Free-text metadata; useful for notes or signature.

#### Source
- Optional tag some trackers read (e.g., site acronym).  
- Leave blank for cross-seeding unless a tracker mandates it.

### 4) Progress + Actions
- **Progress bar**: Two phases—(1) scan, (2) hash. Show file-level progress + ETA on large sets.
- **Create Torrent**: Validate → build metainfo → write `.torrent` → (optional) add to client & start seeding.
- **Cancel**: Abort cleanly.

---

## Under the Hood (Behavioral Notes)
- Stable file ordering → reproducible infohashes.
- Alignment → pad files included in metadata (no on-disk writes required).
- v1 vs v2 vs hybrid:
  - Default **v1** (private trackers).
  - v2/hybrid behind an “Advanced” toggle with policy warning.

---

## Web UI Blueprint (Alpine.js)

### Data Model
```ts
type Tier = string[]; // announce URLs in one tier

interface CreatorForm {
  mode: 'file' | 'folder';
  path: string;
  totalBytes: number | null;
  fileCount: number | null;

  pieceSizeMode: 'auto' | 'manual';
  pieceSizeBytes: number | null;
  targetPieces: number;

  privateTorrent: boolean;
  startSeeding: boolean;
  ignoreShareRatio: boolean;

  optimizeAlignment: boolean;
  alignThresholdBytes: number | null;

  announceTiers: Tier[];  // [[url1, url2], [url3]]
  webSeeds: string[];
  comment: string;
  source: string;

  v2Mode: 'v1' | 'v2' | 'hybrid';
}
````

### Component Anatomy

* **Path Picker**

  * Path input + “Browse File/Folder” (server modal)
  * On change → `scanPath(path)` → `{ totalBytes, fileCount }`
* **Settings**

  * Piece Size: Auto (target slider 1000–5000) / Manual (16 KiB…16 MiB)
  * Calculate Pieces → backend
  * Toggles: Private, Start Seeding, Ignore Ratio (gated)
  * Alignment: checkbox + threshold dropdown + tooltip
* **Fields**

  * Trackers: one textarea → split into tiers by **double newline**; per-line validate; “+ Tier” inserts blank line
  * Web seeds (with private warning)
  * Comment & Source (show char counts)
* **Summary & Actions**

  * Stat chips: size, file count, piece size, estimated pieces, v1/v2, alignment
  * Progress bar + status (“Hashing 37/732… ETA 02:41”)
  * Create / Cancel

### State & Methods (Skeleton)

```html
<form x-data="torrentCreator()" @submit.prevent="create()">
  <!-- path picker, settings, fields, summary -->
</form>

<script>
function torrentCreator() {
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

    get canCalcPieces(){ return !!this.form.path && (this.form.totalBytes ?? 0) > 0; },
    get canCreate(){ return this.validate().ok; },

    async scanPath(){
      if (!this.form.path) return;
      const res = await fetch('/api/scan', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({path: this.form.path})
      });
      const data = await res.json();
      this.form.totalBytes = data.totalBytes;
      this.form.fileCount = data.fileCount;
    },

    async calcPieces(){
      if (!this.canCalcPieces) return;
      const desired = this.form.pieceSizeMode === 'auto' ? null : this.form.pieceSizeBytes;
      const res = await fetch('/api/pieces', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          totalBytes: this.form.totalBytes,
          desiredPieceSize: desired,
          target: this.form.targetPieces
        })
      });
      const data = await res.json(); // { pieceSizeBytes, pieceCount }
      this.form.pieceSizeBytes = data.pieceSizeBytes;
      this.pieceCount = data.pieceCount;
    },

    validate(){
      const errors = [];
      if (!this.form.path) errors.push('Select a file or folder.');
      if (!this.form.announceTiers.flat().length) errors.push('Add at least one tracker URL.');
      if (this.form.optimizeAlignment && !this.form.alignThresholdBytes)
        errors.push('Choose an alignment threshold or disable alignment.');
      if (!this.form.startSeeding) this.form.ignoreShareRatio = false;
      return { ok: errors.length === 0, errors };
    },

    async create(){
      const v = this.validate();
      if (!v.ok) { alert(v.errors.join('\n')); return; }

      const res = await fetch('/api/create', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(this.form)
      });

      const out = await res.json(); // { torrentPath, added, warnings }
      // Render link to .torrent; toast any warnings
    }
  }
}
</script>
```

---

## Backend API (Sketch)

* `POST /api/scan` → `{ totalBytes, fileCount }`
  Recursively stat the path (configurable ignores: hidden files, temp files).
* `POST /api/pieces` → `{ pieceSizeBytes, pieceCount }`
  Auto or manual computation; may consider v1/v2 differences.
* `POST /api/create` → streams progress; returns
  `{ torrentPath, added: boolean, warnings: string[] }`

  * Build **v1** by default (warn if user picked v2/hybrid).
  * If `startSeeding`, add to qBittorrent via Web API and **force recheck**.

---

## Validation & UX Niceties

* **Path exists** (server-side): differentiate “not found” vs “no permission.”
* **Tracker validation**: scheme + `/announce` hint for HTTP(S).
* **Tier visualization**: headers “Tier 1 / Tier 2 …” from blank-line grouping.
* **Private + Web seeds**: info badge warning.
* **Alignment**: plain-language tooltip; emphasize pad-file metadata implication.
* **Estimated .torrent size**: rough `20–80 KB + 2×piece_count` (v1).
* **Reproducibility**: “Stable file order (bytewise lexicographic)” advanced toggle.
* **Cross-seed guardrails**: default v1; avoid `source` unless required; ensure save path = content path.
* **Accessibility**: keyboard nav everywhere; aria for tooltips/messages.

---

## Opinionated Defaults

* **Private:** ON
* **Piece Size:** Auto (target ≈ **2500** pieces)
* **Start Seeding:** OFF (remember last choice)
* **Alignment:** Disabled
* **Torrent Mode:** v1
* **Tracker Profiles:** optional presets (e.g., “MAM”) to preload announce URL

---

## Edge Cases

1. **Multi-TB payloads:** stream progress; durable job IDs; tolerate web reconnects.
2. **Sparse files / symlinks / devices:** define policy (dereference symlinks; error on devices).
3. **Mid-scan permission errors:** show per-file failures; allow “exclude unreadable.”
4. **Pad files + policy:** explicit, reversible choice with a clear warning.
5. **v2/hybrid:** prominent warning that many private trackers reject them.

---

## Security & Privacy

* Do **not** log full absolute paths beyond what’s needed for debugging (redact home dirs if public logs).
* Sanitize tracker URLs in logs (strip passkeys/tokens).
* CSRF-protect create endpoint; auth-gate all APIs.
* Validate path traversal (no `..` escapes outside allowed roots).

---

## Performance Targets

* **Initial scan time:** < 2s per 100k files (server-dependent; parallel stat).
* **Hash throughput:** bounded by disk; show ETA after first 3–5% sampled.
* **UI idle cost:** minimal; Alpine state updates O(1) per user action.

---

## Tracker Profiles (Optional)

Example config snippet:

```json
{
  "profiles": {
    "MAM": {
      "private": true,
      "announceTiers": [["https://t.example.net/announce"]],
      "source": "",
      "v2Mode": "v1",
      "alignment": { "enabled": false }
    }
  }
}
```

---

## Acceptance Criteria Checklist

* [ ] Path can be selected via server picker; scan shows size & file count.
* [ ] Auto piece size picks a sensible value; manual overrides work.
* [ ] “Calculate pieces” displays both size and count.
* [ ] Private torrent defaults ON; disabling shows a tracker warning.
* [ ] Start seeding toggles “Ignore share ratio.”
* [ ] Alignment disabled by default; enabling requires threshold and warns about pad files.
* [ ] Trackers support tiers via blank lines; invalid URLs are highlighted.
* [ ] Web seeds allowed but warned under “Private.”
* [ ] Create shows streaming progress, handles cancel, and returns a `.torrent`.
* [ ] (Optional) Adds torrent to qBittorrent and starts seeding when requested.
* [ ] v1/v2/hybrid exposed only under “Advanced” with clear policy warnings.
* [ ] All inputs keyboard accessible; ARIA labels present.

---

## Testing Plan

**Unit**

* Piece size heuristic → expected piece counts across sizes.
* Tracker parsing → tier splits on blank lines.
* Validation → each failure path returns useful messages.

**Integration**

* Scan huge folders (mock file trees); ensure robust progress & no UI freezes.
* Create v1 torrents and verify infohash reproducibility (stable sort).
* Start seeding → verify client loads and rechecks existing data.

**Manual**

* Private on/off + web seeds warning behavior.
* Alignment on common thresholds; verify pad files appear in metadata.
* Tiered trackers with failover (network-simulated).

---

## Future Enhancements

* **Profile Manager:** Save/load per-tracker presets (announce/source/flags).
* **Category & Tags:** Pre-set qBittorrent category on add.
* **Post-create Hooks:** e.g., copy `.torrent` to “seedvault” path.
* **.torrent Inspector:** Show parsed metainfo for sanity checks.
* **Dark Mode:** because of course.

```
```
