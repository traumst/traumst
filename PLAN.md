# GitHub Profile Arkanoid ("Vaus Breakout") — Implementation Plan

This document serves as the cross-session architectural and implementation guide for building a **100% self-contained, 3-level retro Arkanoid game** playable directly on the GitHub Profile page (`https://github.com/traumst`) inside [`README.md`](./README.md) with **zero page reloads, zero external servers, and zero multi-file state clutter**.

---

## 1. Downsides of the Current Solution & Prior Draft

### A. Downsides in [`README.md`](./README.md) & [`custom-card.svg`](./custom-card.svg)
1. **Multi-File Link Hopping Leaves the Profile Page (`README.md:66-74`, `README.md:112-119`, `README.md:195-197`):**
   - The DoomMe-style pattern in `README.md:66-74` and `README.md:195-197` navigates to separate `.md` files on every click. When clicked from `https://github.com/traumst`, `<a href="...">` links kick the visitor **off the profile page** into the repository file viewer (`/blob/main/...`), trigger full page reloads, lose scroll position, and bloat the repo with hundreds or thousands of `.md` files.
   - Similarly, the webhook / GitHub Actions approach in `README.md:112-119` and `README.md:184-185` suffers from 15–30s runner latency or requires external hosting.
2. **Static Demo Table Instead of Functional Game HUD (`README.md:20-53`):**
   - The HTML `<table>`, `<kbd>`, `<ruby>`, `<ins>`/`<del>`, and `<mark>` elements in `README.md:20-53` only render static documentation examples rather than acting as an interactive arcade cabinet control deck and HUD.
3. **Redundant `<picture>` Sources & Static Single-Element SVG (`README.md:84-88`, `README.md:96-100`, `custom-card.svg:1-62`):**
   - Both `<source>` tags in `README.md:84-88` point to the same `./custom-card.svg`, which hardcodes dark colors (`custom-card.svg:5-17`) and only animates a single pulsing circle via `@keyframes glow` (`custom-card.svg:39-50`) inside a `680x140` box (`custom-card.svg:1`).
4. **Disconnected Diagram & Formatting Blocks (`README.md:104-193`):**
   - The `mermaid` diagram (`README.md:112-119`), `geojson` map (`README.md:125-139`), `stl` tetrahedron (`README.md:145-176`), GFM alert (`README.md:184-185`), and `diff` block (`README.md:189-193`) are isolated tech demos rather than integrated game systems.

### B. Downsides Eliminated from the Previous Plan (`PLAN.md:28-81`)
1. **Removed `states/*.md` File Generation (`PLAN.md:40-41`, `PLAN.md:57-60`, `PLAN.md:71-81`):**
   - Generating 60–90 `states/*.md` files carried over DoomMe's repository clutter and page-reload navigation penalty. Everything now lives inside the root `README.md`.
2. **Replaced Fragile One-Shot `loading="lazy"` Animations (`PLAN.md:31-39`):**
   - Relying on one-shot `animation-fill-mode: forwards` + `loading="lazy"` (`PLAN.md:31-39`) breaks when browsers or GitHub's Camo proxy pre-decode images inside closed `<details>` tags on page load (causing the animation to finish before the player expands the turn).
3. **Eliminated Duplicate Dark/Light Frame Files (`PLAN.md:63-64`, `PLAN.md:76-77`):**
   - Generating separate `_dark.svg` and `_light.svg` files for every rally doubled the asset count unnecessarily when `@media (prefers-color-scheme)` inside each `.svg` handles theme adaptation natively.

---

## 2. Improved Architecture: 100% In-Profile Zero-Reload Engine

### A. Single-File In-Profile State Progression via `<details>` & `<summary>`
- All 3 levels and every playable turn live directly inside `README.md` using nested HTML5 `<details>` and `<summary>` accordions (building on `README.md:57-76`).
- Clicking a `<summary><kbd>...</kbd></summary>` paddle control toggles the next rally open **instantly in the browser (0ms latency) without ever leaving `https://github.com/traumst`**.
- To keep `README.md` compact (~30 KB, <6% of GitHub's 512 KB sanitizer limit), each stage is structured as a **3-Rally Tactical Arcade Sequence** where each decision node offers 3 paddle actions:
  1. **Optimal Angle Intercept:** Catches the ball on the Vaus paddle's angled edge, triggering a multi-brick combo shatter and unlocking the next rally `<details>` block.
  2. **Center Bank Deflection:** Catches the ball flat, clearing a subset of bricks and opening a compact **Bank Recovery Sub-Rally** that merges back into the main stage progression.
  3. **Misjudged Sector (Whiff):** Moves the paddle to the wrong sector, expanding an inline **Ball Lost / Shield Breach** SVG animation with a `[!CAUTION]` alert (`[-1 VAUS LIFE]`) and an immediate inline re-serve toggle.

### B. Preload-Immune Synchronized SVG Rally Loops (`assets/*.svg`)
Instead of a one-shot animation that can expire while hidden, every rally SVG (`assets/s{1..3}_r{1..3}_{branch}.svg`) runs a **seamless 4-second CSS `@keyframes` tactical cycle** inside `<foreignObject>` (upgrading `custom-card.svg:1-62`):
- **`0% – 12%` (Paddle Intercept):** The Vaus spacecraft slides into the chosen sector and strikes the incoming energy ball with a neon impact flash.
- **`12% – 75%` (Raycast Ricochet & Brick Shatter):** The ball travels along its exact deterministic multi-bounce trajectory; each struck brick flashes white, bursts into pixel fragments, and spawns a floating `+100` / `+250` score popup at its exact collision keyframe while the CRT HUD score ticks upward.
- **`75% – 100%` (Resulting Board & Threat Radar):** The surviving bricks remain visible while the ball descends toward its new landing column (`SECTOR 1`..`5`) with a pulsing target reticle showing the player where to aim next.
- Because the 4s tactical cycle loops cleanly, the player **always sees the full animated shot, brick destruction, and incoming radar** regardless of when the browser decoded the SVG.

---

## 3. 3-Level Campaign Design (Self-Contained in `README.md`)

| Stage | Title | Playfield & Brick Mechanics | Tactical Rallies & Boss/Clear Condition |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **Neon Wall** | $5 \times 2$ grid of 1-hit Cyan & Magenta bricks (`800 PTS`). | **3 Rallies:** Left-edge slice $\rightarrow$ Top-wall ricochet sweep $\rightarrow$ Final corner snipe. Unlocks Stage 2 drawer. |
| **Stage 2** | **Fortress Bunker** | $5 \times 3$ diamond fortress with **2-Hit Silver Armor Bricks** and **Indestructible Gold Bumpers** (`1,800 PTS`). | **3 Rallies:** Thread the gap between Gold Bumpers $\rightarrow$ Upper pocket pinball combo $\rightarrow$ Armor-breaker finisher. Unlocks Stage 3 drawer. |
| **Stage 3** | **DOH Core (Boss)** | Armored **DOH Boss Core (3 HP)** guarded by regenerating laser barriers and narrow return lanes (`5,000 PTS`). | **3 Rallies:** Breach left shield array $\rightarrow$ Direct Laser/Plasma Vaus strike on DOH Core $\rightarrow$ Final core overload & **3D Victory Vault**. |

---

## 4. Implementation Roadmap & File Checklist

### Phase 1: Deterministic SVG Scene Generator (`scripts/generate_assets.py`)
- [x] Create a single, dependency-free Python script (`scripts/generate_assets.py`) that computes exact 2D raycast bounce waypoints and outputs the ~16 self-contained `.svg` files into `assets/`:
  - `assets/marquee-dark.svg` & `assets/marquee-light.svg`: Dual-theme cabinet header for `<picture>` (`README.md:84-88`).
  - `assets/s{1..3}_r{1..3}_hit.svg`, `assets/s{1..3}_r{1..3}_bank.svg`, `assets/s{1..3}_miss.svg`, and `assets/victory.svg`: `680x420` animated CRT viewports (upgrading `custom-card.svg:1-62`) with embedded `@media (prefers-color-scheme: light/dark)` palettes, scanline overlays, HUD score/lives counters, multi-stop `@keyframes` ball paths, and brick shatter animations.

### Phase 2: Self-Contained Playable Profile (`README.md`)
- [x] **Arcade Cabinet Header & Marquee (refactoring `README.md:1-9`, `README.md:80-100`):**
  - Use `<picture>` (`README.md:84-88`) with `assets/marquee-dark.svg` and `assets/marquee-light.svg` so the cabinet header genuinely adapts to GitHub Light and Dark themes.
- [x] **Cabinet Control Deck & Telemetry Table (refactoring `README.md:20-53`):**
  - Use HTML `<table>` (`colspan`, `align="center"`, `README.md:20-53`) for the arcade frame.
  - Use `<ruby>` and `<rt>` (`README.md:39-43`) for telemetry badges (`<ruby>STAGE 01<rt>SECTOR</rt></ruby>`, `<ruby>00,800<rt>SCORE</rt></ruby>`, `<ruby>♥♥♥<rt>VAUS</rt></ruby>`).
  - Use `<del>`, `<ins>`, and `<mark>` (`README.md:34-38`, `README.md:44-48`) to track destroyed vs. active bricks per rally.
- [x] **3-Level In-Page `<details>` Game Tree (refactoring `README.md:57-76`):**
  - Replace the external DoomMe links (`README.md:70-72`) with nested `<details>` & `<summary><kbd>...</kbd></summary>` controls for Stages 1, 2, and 3 so every rally, bank shot, miss recovery, and stage transition happens inline on the profile page.
- [x] **Integrated Telemetry Diffs, Alerts, Mermaid Map & 3D Trophy (refactoring `README.md:104-197`):**
  - **`diff` Combat Logs (`README.md:189-193`):** Colorized rally readouts (`+ COMBO: 4x Neon Bricks Shattered (+400 PTS)`, `! RICOCHET: Gold Bumper Deflection`, `- BREACH: Ball Missed in Sector 4`).
  - **GFM Alerts (`README.md:182-185`):** Stage briefings (`[!NOTE]`), Vaus power-up notifications (`[!TIP] ENLARGED VAUS / LASER ACTIVE`), and miss warnings (`[!CAUTION]`).
  - **Tactical Sector Map (`mermaid`, `README.md:112-119`):** Visualizes the 3-stage campaign flow and deflection angles ($\theta_{\text{out}} = \theta_{\text{in}} + \Delta\theta_{\text{paddle}}$, replacing `README.md:195-197`).
  - **3D Vaus Spacecraft & Victory Trophy (`stl`, `README.md:145-176`):** Replaces the sample tetrahedron (`README.md:145-176`) with an interactive 3D ASCII `stl` model of the Vaus paddle inside the Stage 3 Victory Vault.
- [x] **Remove Legacy `custom-card.svg` (`custom-card.svg:1-62`):**
  - Replace the standalone demo `custom-card.svg` once the new `assets/*.svg` arcade frames are wired into `README.md`.

---

## 5. Verification Checklist

- [x] **100% In-Profile Playability:** Verify that every `<details>` / `<summary>` path across Stages 1, 2, and 3 expands inline without any `<a href>` navigation away from `README.md`.
- [x] **SVG Animation & Sanitizer Compliance:** Confirm all `assets/*.svg` files declare valid `xmlns="http://www.w3.org/2000/svg"` and `xmlns="http://www.w3.org/1999/xhtml"` (`custom-card.svg:1-3`), contain zero `<script>` tags or external URLs, and loop their 4s rally animations smoothly in both light and dark modes.
- [x] **Size Budget Check:** Ensure `README.md` stays under 50 KB (well below GitHub's 512 KB truncation limit) and total repo assets stay clean and self-contained.
