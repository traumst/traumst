#!/usr/bin/env python3
"""Deterministic 2D Raycast & SVG Scene Generator for GitHub Profile Arkanoid ("Vaus Breakout").

Generates self-contained, sanitizer-safe animated SVG files inside `assets/` using
`<foreignObject>` HTML/CSS keyframes, dual-theme CSS variables (`color-scheme: light dark`,
`@media (prefers-color-scheme: dark)`, and `light-dark()`), and deterministic 2D raycast
bounce trajectories.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

VIEWPORT_W = 680
VIEWPORT_H = 420
PLAYFIELD_LEFT = 30
PLAYFIELD_RIGHT = 650
PLAYFIELD_TOP = 58
PLAYFIELD_BOTTOM = 356
PADDLE_Y = 356

SECTOR_CENTERS = {
    1: 92,
    2: 216,
    3: 340,
    4: 464,
    5: 588,
}


@dataclass(frozen=True)
class BrickSpec:
    brick_id: str
    row: int
    col: int
    kind: str  # "cyan", "magenta", "silver", "emerald", "gold", "shield", "pylon", "boss"
    label: str
    points: int = 100
    hit_pct: float | None = None  # Keyframe % (12..75) when struck in this rally
    destroyed_before: bool = False
    indestructible: bool = False
    custom_rect: tuple[int, int, int, int] | None = None  # (x, y, w, h)


@dataclass(frozen=True)
class Waypoint:
    pct: float
    x: float
    y: float


@dataclass(frozen=True)
class RallySpec:
    filename: str
    stage: int
    stage_title: str
    rally_label: str
    status_badge: str
    score_start: int
    score_end: int
    lives: int
    paddle_start_sector: int
    paddle_hit_sector: int
    next_target_sector: int | None
    vaus_mode: str  # "STANDARD", "ENLARGED", "LASER", "BREACH"
    is_miss: bool
    boss_hp_start: int | None
    boss_hp_end: int | None
    bricks: Sequence[BrickSpec]
    waypoints: Sequence[Waypoint]
    banner_title: str
    banner_subtitle: str


def brick_rect(brick: BrickSpec) -> tuple[int, int, int, int]:
    """Return (x, y, width, height) for a brick on the 5-column playfield grid."""
    if brick.custom_rect is not None:
        return brick.custom_rect
    col_w = 116
    gap_x = 6
    x = 40 + brick.col * (col_w + gap_x)
    y = 78 + brick.row * 34
    return (x, y, col_w, 24)


def compute_raycast_schedule(points: Sequence[tuple[float, float]], start_pct: float = 12.0, end_pct: float = 75.0) -> list[Waypoint]:
    """Compute arc-length-parameterized keyframe percentages along a 2D raycast polyline."""
    if len(points) < 2:
        raise ValueError("Raycast polyline requires at least 2 points.")
    segment_lengths: list[float] = []
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        segment_lengths.append(math.hypot(x1 - x0, y1 - y0))
    total_len = sum(segment_lengths) or 1.0
    waypoints = [Waypoint(round(start_pct, 2), points[0][0], points[0][1])]
    elapsed = 0.0
    for (x1, y1), seg_len in zip(points[1:], segment_lengths):
        elapsed += seg_len
        pct = start_pct + (end_pct - start_pct) * (elapsed / total_len)
        waypoints.append(Waypoint(round(pct, 2), x1, y1))
    return waypoints


def build_rally_waypoints(
    serve_xy: tuple[float, float],
    paddle_sector: int,
    ricochet_points: Sequence[tuple[float, float]],
    next_sector: int | None,
    is_miss: bool = False,
) -> list[Waypoint]:
    """Build the full 0%..100% 4-second loop trajectory."""
    px = float(SECTOR_CENTERS[paddle_sector])
    if is_miss:
        # Ball descends past the paddle into the floor breach zone
        miss_x = serve_xy[0] + 40.0
        return [
            Waypoint(0.0, serve_xy[0], serve_xy[1]),
            Waypoint(12.0, miss_x, PADDLE_Y - 6),
            Waypoint(32.0, miss_x + 18.0, 408.0),
            Waypoint(75.0, miss_x + 18.0, 408.0),
            Waypoint(100.0, serve_xy[0], serve_xy[1]),
        ]

    intercept_pt = (px, float(PADDLE_Y - 8))
    core_points = [intercept_pt, *ricochet_points]
    mid_waypoints = compute_raycast_schedule(core_points, start_pct=12.0, end_pct=75.0)
    end_x = float(SECTOR_CENTERS[next_sector]) if next_sector else 340.0
    end_y = 316.0 if next_sector else 230.0
    return [
        Waypoint(0.0, serve_xy[0], serve_xy[1]),
        *mid_waypoints,
        Waypoint(90.0, end_x, end_y),
        Waypoint(100.0, end_x, end_y + 12.0),
    ]


def render_common_css() -> str:
    """Return shared CRT & dual-theme CSS rules."""
    return """
        :root {
          --bg-outer-light: #eef2f9;
          --bg-outer-dark: #070b14;
          --bg-crt-light: #f8faff;
          --bg-crt-dark: #0b1020;
          --text-main-light: #0f172a;
          --text-main-dark: #e2e8f0;
          --text-muted-light: #475569;
          --text-muted-dark: #94a3b8;
          --border-frame-light: #cbd5e1;
          --border-frame-dark: #1e293b;
          --grid-line-light: rgba(15, 23, 42, 0.06);
          --grid-line-dark: rgba(56, 189, 248, 0.08);
          --cyan-accent-light: #0284c7;
          --cyan-accent-dark: #38bdf8;
          --magenta-accent-light: #c026d3;
          --magenta-accent-dark: #f472b6;
          --amber-accent-light: #d97706;
          --amber-accent-dark: #fbbf24;
          --danger-accent-light: #dc2626;
          --danger-accent-dark: #f87171;
          --emerald-accent-light: #059669;
          --emerald-accent-dark: #34d399;

          --bg-outer: var(--bg-outer-light);
          --bg-crt: var(--bg-crt-light);
          --text-main: var(--text-main-light);
          --text-muted: var(--text-muted-light);
          --border-frame: var(--border-frame-light);
          --grid-line: var(--grid-line-light);
          --cyan-accent: var(--cyan-accent-light);
          --magenta-accent: var(--magenta-accent-light);
          --amber-accent: var(--amber-accent-light);
          --danger-accent: var(--danger-accent-light);
          --emerald-accent: var(--emerald-accent-light);

          color-scheme: light dark;
        }
        @media (prefers-color-scheme: dark) {
          :root {
            --bg-outer: var(--bg-outer-dark);
            --bg-crt: var(--bg-crt-dark);
            --text-main: var(--text-main-dark);
            --text-muted: var(--text-muted-dark);
            --border-frame: var(--border-frame-dark);
            --grid-line: var(--grid-line-dark);
            --cyan-accent: var(--cyan-accent-dark);
            --magenta-accent: var(--magenta-accent-dark);
            --amber-accent: var(--amber-accent-dark);
            --danger-accent: var(--danger-accent-dark);
            --emerald-accent: var(--emerald-accent-dark);
          }
        }
        @supports (color: light-dark(white, black)) {
          :root {
            --bg-outer: light-dark(var(--bg-outer-light), var(--bg-outer-dark));
            --bg-crt: light-dark(var(--bg-crt-light), var(--bg-crt-dark));
            --text-main: light-dark(var(--text-main-light), var(--text-main-dark));
            --text-muted: light-dark(var(--text-muted-light), var(--text-muted-dark));
            --border-frame: light-dark(var(--border-frame-light), var(--border-frame-dark));
            --cyan-accent: light-dark(var(--cyan-accent-light), var(--cyan-accent-dark));
            --magenta-accent: light-dark(var(--magenta-accent-light), var(--magenta-accent-dark));
            --amber-accent: light-dark(var(--amber-accent-light), var(--amber-accent-dark));
            --danger-accent: light-dark(var(--danger-accent-light), var(--danger-accent-dark));
            --emerald-accent: light-dark(var(--emerald-accent-light), var(--emerald-accent-dark));
          }
        }
        @media (forced-colors: active) {
          .cabinet, .brick, .paddle, .ball, .hud-pill {
            forced-color-adjust: none;
          }
        }
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        .cabinet {
          width: 680px;
          height: 420px;
          background: var(--bg-outer);
          color: var(--text-main);
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
          border: 2px solid var(--border-frame);
          border-radius: 14px;
          position: relative;
          overflow: hidden;
          user-select: none;
        }
        .crt {
          position: absolute;
          inset: 8px;
          background:
            linear-gradient(to right, var(--grid-line) 1px, transparent 1px) 0 0 / 24px 24px,
            linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px) 0 0 / 24px 24px,
            var(--bg-crt);
          border: 1px solid var(--border-frame);
          border-radius: 10px;
          overflow: hidden;
        }
        .scanlines {
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            to bottom,
            transparent 0px,
            transparent 2px,
            rgba(0, 0, 0, 0.07) 3px,
            rgba(0, 0, 0, 0.07) 4px
          );
          pointer-events: none;
          z-index: 30;
        }
        .hud {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 16px;
          border-bottom: 1px solid var(--border-frame);
          background: rgba(15, 23, 42, 0.06);
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.06em;
          z-index: 20;
        }
        .hud-group {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .hud-pill {
          padding: 3px 8px;
          border-radius: 6px;
          border: 1px solid var(--border-frame);
          background: var(--bg-outer);
          color: var(--text-main);
        }
        .hud-score-wrap {
          position: relative;
          display: inline-block;
          min-width: 112px;
          height: 22px;
          vertical-align: middle;
        }
        .score-before, .score-after {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 800;
          color: var(--cyan-accent);
        }
        .score-before {
          animation: scoreSwapBefore 4s infinite steps(1, end);
        }
        .score-after {
          animation: scoreSwapAfter 4s infinite steps(1, end);
        }
        @keyframes scoreSwapBefore {
          0%, 42% { opacity: 1; }
          42.01%, 100% { opacity: 0; }
        }
        @keyframes scoreSwapAfter {
          0%, 42% { opacity: 0; }
          42.01%, 100% { opacity: 1; }
        }
        .wall-left, .wall-right {
          position: absolute;
          top: 44px;
          bottom: 28px;
          width: 6px;
          background: linear-gradient(180deg, var(--cyan-accent), var(--magenta-accent));
          opacity: 0.45;
        }
        .wall-left { left: 16px; border-radius: 3px; }
        .wall-right { right: 16px; border-radius: 3px; }
        .brick {
          position: absolute;
          border-radius: 5px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.05em;
          border: 1.5px solid rgba(255, 255, 255, 0.35);
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
          z-index: 8;
        }
        .brick-cyan {
          background: linear-gradient(135deg, #0ea5e9, #0284c7);
          color: #ffffff;
        }
        .brick-magenta {
          background: linear-gradient(135deg, #e879f9, #c026d3);
          color: #ffffff;
        }
        .brick-silver {
          background: linear-gradient(135deg, #94a3b8, #475569);
          color: #ffffff;
          border-color: #e2e8f0;
        }
        .brick-emerald {
          background: linear-gradient(135deg, #10b981, #047857);
          color: #ffffff;
        }
        .brick-gold {
          background: linear-gradient(135deg, #f59e0b, #b45309);
          color: #fffbeb;
          border: 2px solid #fde68a;
        }
        .brick-shield {
          background: linear-gradient(135deg, #6366f1, #4338ca);
          color: #e0e7ff;
        }
        .brick-pylon {
          background: linear-gradient(135deg, #ec4899, #be185d);
          color: #fce7f3;
        }
        .brick-boss {
          background: linear-gradient(135deg, #ef4444, #7f1d1d);
          color: #fef2f2;
          border: 2px solid #fca5a5;
          flex-direction: column;
          gap: 3px;
          font-size: 12px;
          box-shadow: 0 0 18px rgba(239, 68, 68, 0.45);
        }
        .popup {
          position: absolute;
          font-size: 11px;
          font-weight: 900;
          color: var(--amber-accent);
          pointer-events: none;
          z-index: 18;
          opacity: 0;
        }
        .paddle {
          position: absolute;
          top: 348px;
          left: 0;
          height: 14px;
          border-radius: 7px;
          background: linear-gradient(90deg, var(--magenta-accent), var(--cyan-accent), var(--magenta-accent));
          border: 1.5px solid #ffffff;
          box-shadow: 0 0 12px rgba(56, 189, 248, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 8px;
          font-weight: 800;
          color: #ffffff;
          z-index: 15;
          animation: paddleMove 4s infinite ease-in-out;
        }
        .ball {
          position: absolute;
          top: 0;
          left: 0;
          width: 12px;
          height: 12px;
          margin-left: -6px;
          margin-top: -6px;
          border-radius: 50%;
          background: #ffffff;
          border: 2.5px solid var(--cyan-accent);
          box-shadow: 0 0 10px var(--cyan-accent);
          z-index: 16;
          animation: ballPath 4s infinite linear;
        }
        .impact-flash {
          position: absolute;
          width: 28px;
          height: 28px;
          margin-left: -14px;
          margin-top: -14px;
          border-radius: 50%;
          border: 2px solid var(--amber-accent);
          background: rgba(251, 191, 36, 0.35);
          z-index: 14;
          animation: impactPulse 4s infinite ease-out;
        }
        @keyframes impactPulse {
          0%, 10% { transform: scale(0.2); opacity: 0; }
          12% { transform: scale(1.35); opacity: 1; }
          20%, 100% { transform: scale(2.1); opacity: 0; }
        }
        .radar-target {
          position: absolute;
          top: 300px;
          width: 112px;
          margin-left: -56px;
          padding: 4px 6px;
          border-radius: 6px;
          border: 1.5px dashed var(--amber-accent);
          background: rgba(245, 158, 11, 0.12);
          color: var(--amber-accent);
          font-size: 9px;
          font-weight: 800;
          text-align: center;
          z-index: 12;
          animation: radarPulse 4s infinite ease-in-out;
        }
        @keyframes radarPulse {
          0%, 68% { opacity: 0; transform: translateY(-6px); }
          75%, 95% { opacity: 1; transform: translateY(0); }
          100% { opacity: 0; transform: translateY(4px); }
        }
        .banner {
          position: absolute;
          left: 50%;
          top: 238px;
          transform: translateX(-50%);
          padding: 7px 16px;
          border-radius: 8px;
          border: 1px solid var(--border-frame);
          background: var(--bg-outer);
          text-align: center;
          z-index: 19;
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
          animation: bannerFade 4s infinite ease-in-out;
        }
        .banner-title {
          font-size: 11px;
          font-weight: 900;
          letter-spacing: 0.06em;
          color: var(--cyan-accent);
        }
        .banner-sub {
          font-size: 9px;
          color: var(--text-muted);
          margin-top: 2px;
        }
        @keyframes bannerFade {
          0%, 62% { opacity: 0; transform: translate(-50%, 6px); }
          72%, 96% { opacity: 0.96; transform: translate(-50%, 0); }
          100% { opacity: 0; transform: translate(-50%, -4px); }
        }
        .sector-bar {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 26px;
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          border-top: 1px solid var(--border-frame);
          background: rgba(15, 23, 42, 0.05);
          font-size: 9px;
          font-weight: 700;
          z-index: 20;
        }
        .sector-cell {
          display: flex;
          align-items: center;
          justify-content: center;
          border-right: 1px solid var(--border-frame);
          color: var(--text-muted);
        }
        .sector-cell:last-child {
          border-right: none;
        }
        .sector-active {
          color: var(--amber-accent);
          font-weight: 900;
          background: rgba(245, 158, 11, 0.12);
        }
        .laser-beam {
          position: absolute;
          width: 3px;
          height: 180px;
          background: linear-gradient(180deg, #fbbf24, #ef4444, transparent);
          z-index: 13;
          animation: laserFire 4s infinite ease-out;
        }
        @keyframes laserFire {
          0%, 14% { opacity: 0; transform: translateY(80px) scaleY(0.2); }
          18%, 36% { opacity: 1; transform: translateY(-90px) scaleY(1); }
          45%, 100% { opacity: 0; transform: translateY(-160px) scaleY(0.1); }
        }
    """


def render_rally_svg(spec: RallySpec) -> str:
    """Render a complete 680x420 animated SVG for a single rally state."""
    paddle_w = 112 if spec.vaus_mode == "ENLARGED" else 88
    start_x = SECTOR_CENTERS[spec.paddle_start_sector] - paddle_w / 2
    hit_x = SECTOR_CENTERS[spec.paddle_hit_sector] - paddle_w / 2
    end_x = (
        SECTOR_CENTERS[spec.next_target_sector] - paddle_w / 2
        if spec.next_target_sector
        else hit_x
    )

    paddle_kf = f"""
        @keyframes paddleMove {{
          0% {{ transform: translateX({start_x:.1f}px); }}
          10%, 68% {{ transform: translateX({hit_x:.1f}px); }}
          92%, 100% {{ transform: translateX({end_x:.1f}px); }}
        }}
    """

    ball_kf_lines = ["        @keyframes ballPath {"]
    for wp in spec.waypoints:
        ball_kf_lines.append(
            f"          {wp.pct:.2f}% {{ transform: translate({wp.x:.1f}px, {wp.y:.1f}px); }}"
        )
    ball_kf_lines.append("        }")
    ball_kf = "\n".join(ball_kf_lines)

    brick_styles: list[str] = []
    brick_elements: list[str] = []
    popup_elements: list[str] = []

    # Build polyline SVG path for subtle trajectory preview
    poly_pts = " ".join(f"{wp.x:.1f},{wp.y:.1f}" for wp in spec.waypoints if 12.0 <= wp.pct <= 90.0)

    for idx, b in enumerate(spec.bricks):
        if b.destroyed_before:
            continue
        x, y, w, h = brick_rect(b)
        cls_id = f"b-{idx}"
        pop_id = f"p-{idx}"

        if b.hit_pct is not None and not b.indestructible:
            hp = b.hit_pct
            flash_p = max(12.5, hp - 1.2)
            gone_p = min(98.0, hp + 5.5)
            pop_end = min(99.0, hp + 18.0)
            if b.kind == "boss" and (spec.boss_hp_end or 0) > 0:
                # Boss takes damage flash but survives until HP == 0
                brick_styles.append(
                    f"""
        .{cls_id} {{ animation: bossHit_{idx} 4s infinite; }}
        @keyframes bossHit_{idx} {{
          0%, {flash_p:.1f}% {{ transform: scale(1); filter: brightness(1); }}
          {hp:.1f}% {{ transform: scale(1.06); filter: brightness(2.2); }}
          {gone_p:.1f}%, 100% {{ transform: scale(1); filter: brightness(1); }}
        }}
                    """
                )
            else:
                brick_styles.append(
                    f"""
        .{cls_id} {{ animation: shatter_{idx} 4s infinite ease-out; }}
        @keyframes shatter_{idx} {{
          0%, {flash_p:.1f}% {{ opacity: 1; transform: scale(1); filter: brightness(1); }}
          {hp:.1f}% {{ opacity: 1; transform: scale(1.12); filter: brightness(2.5); }}
          {gone_p:.1f}%, 100% {{ opacity: 0; transform: scale(0.15) translateY(-10px); }}
        }}
                    """
                )
            brick_styles.append(
                f"""
        .{pop_id} {{ animation: popup_{idx} 4s infinite ease-out; }}
        @keyframes popup_{idx} {{
          0%, {flash_p:.1f}% {{ opacity: 0; transform: translateY(4px); }}
          {hp + 1.5:.1f}% {{ opacity: 1; transform: translateY(-6px); }}
          {pop_end:.1f}%, 100% {{ opacity: 0; transform: translateY(-18px); }}
        }}
                """
            )
            popup_text = f"+{b.points}" if b.points > 0 else "RICOCHET!"
            popup_elements.append(
                f'        <div class="popup {pop_id}" style="left:{x + w/2 - 18:.0f}px;top:{y - 6}px;">{popup_text}</div>'
            )
        elif b.hit_pct is not None and b.indestructible:
            hp = b.hit_pct
            brick_styles.append(
                f"""
        .{cls_id} {{ animation: spark_{idx} 4s infinite; }}
        @keyframes spark_{idx} {{
          0%, {hp - 1.0:.1f}% {{ transform: scale(1); filter: brightness(1); }}
          {hp:.1f}% {{ transform: scale(1.09); filter: brightness(2.2); }}
          {hp + 5.0:.1f}%, 100% {{ transform: scale(1); filter: brightness(1); }}
        }}
                """
            )

        brick_elements.append(
            f'        <div class="brick brick-{b.kind} {cls_id}" '
            f'style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;">{html.escape(b.label)}</div>'
        )

    hearts = "♥" * spec.lives + "♡" * max(0, 3 - spec.lives)
    impact_x = SECTOR_CENTERS[spec.paddle_hit_sector]
    impact_y = PADDLE_Y - 6

    radar_html = ""
    if spec.next_target_sector is not None:
        rx = SECTOR_CENTERS[spec.next_target_sector]
        radar_html = (
            f'        <div class="radar-target" style="left:{rx}px;">'
            f"▼ NEXT AIM: SECTOR {spec.next_target_sector} ▼</div>"
        )

    laser_html = ""
    if spec.vaus_mode == "LASER":
        lx1 = hit_x + 14
        lx2 = hit_x + paddle_w - 17
        laser_html = (
            f'        <div class="laser-beam" style="left:{lx1:.0f}px;top:170px;"></div>\n'
            f'        <div class="laser-beam" style="left:{lx2:.0f}px;top:170px;"></div>'
        )

    sector_cells = []
    for s in range(1, 6):
        active_cls = " sector-active" if s == spec.next_target_sector else ""
        marker = " ★" if s == spec.next_target_sector else ""
        sector_cells.append(f'          <div class="sector-cell{active_cls}">SECTOR {s}{marker}</div>')

    return f"""<svg fill="none" viewBox="0 0 {VIEWPORT_W} {VIEWPORT_H}" width="{VIEWPORT_W}" height="{VIEWPORT_H}" xmlns="http://www.w3.org/2000/svg">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>
{render_common_css()}
{paddle_kf}
{ball_kf}
{"".join(brick_styles)}
      </style>
      <div class="cabinet">
        <div class="crt">
          <div class="scanlines"></div>
          <div class="hud">
            <div class="hud-group">
              <span class="hud-pill">STAGE 0{spec.stage}: {html.escape(spec.stage_title)}</span>
              <span class="hud-pill">{html.escape(spec.rally_label)}</span>
            </div>
            <div class="hud-group">
              <span>SCORE</span>
              <span class="hud-pill hud-score-wrap">
                <span class="score-before">{spec.score_start:06d}</span>
                <span class="score-after">{spec.score_end:06d}</span>
              </span>
              <span class="hud-pill">VAUS: {hearts} ({html.escape(spec.vaus_mode)})</span>
            </div>
          </div>
          <div class="wall-left"></div>
          <div class="wall-right"></div>
          <svg width="664" height="404" viewBox="0 0 664 404" style="position:absolute;inset:0;pointer-events:none;z-index:4;">
            <polyline points="{poly_pts}" fill="none" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="5 5" opacity="0.32" />
          </svg>
{chr(10).join(brick_elements)}
{chr(10).join(popup_elements)}
{laser_html}
          <div class="impact-flash" style="left:{impact_x}px;top:{impact_y}px;"></div>
          <div class="paddle" style="width:{paddle_w}px;">VAUS [{html.escape(spec.vaus_mode)}]</div>
          <div class="ball"></div>
{radar_html}
          <div class="banner">
            <div class="banner-title">{html.escape(spec.banner_title)}</div>
            <div class="banner-sub">{html.escape(spec.banner_subtitle)}</div>
          </div>
          <div class="sector-bar">
{chr(10).join(sector_cells)}
          </div>
        </div>
      </div>
    </div>
  </foreignObject>
</svg>
"""


def render_marquee_svg(theme: str) -> str:
    """Render `assets/marquee-dark.svg` or `assets/marquee-light.svg` (680x210)."""
    is_dark = theme == "dark"
    bg_grad = (
        "linear-gradient(135deg, #060913 0%, #0f172a 55%, #1e1b4b 100%)"
        if is_dark
        else "linear-gradient(135deg, #f8fafc 0%, #e0f2fe 55%, #fae8ff 100%)"
    )
    text_primary = "#f8fafc" if is_dark else "#0f172a"
    text_secondary = "#94a3b8" if is_dark else "#334155"
    border_col = "#38bdf8" if is_dark else "#0284c7"
    badge_bg = "rgba(56, 189, 248, 0.14)" if is_dark else "rgba(2, 132, 199, 0.12)"
    title_glow = "0 0 18px rgba(56, 189, 248, 0.55)" if is_dark else "none"
    theme_badge = "DARK CRT CABINET MODE" if is_dark else "LIGHT DAYLIGHT CABINET MODE"

    return f"""<svg fill="none" viewBox="0 0 680 210" width="680" height="210" xmlns="http://www.w3.org/2000/svg">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        .marquee {{
          width: 680px;
          height: 210px;
          background: {bg_grad};
          color: {text_primary};
          border: 2px solid {border_col};
          border-radius: 14px;
          padding: 18px 24px;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          position: relative;
          overflow: hidden;
        }}
        .top-row {{
          display: flex;
          align-items: center;
          justify-content: space-between;
        }}
        .pill {{
          display: inline-block;
          background: {badge_bg};
          color: {border_col};
          border: 1px solid {border_col};
          border-radius: 999px;
          padding: 4px 12px;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.06em;
        }}
        .title {{
          font-size: 25px;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-shadow: {title_glow};
          margin-top: 4px;
        }}
        .subtitle {{
          font-size: 12px;
          color: {text_secondary};
          margin-top: 4px;
        }}
        .demo-strip {{
          height: 54px;
          border-radius: 10px;
          border: 1px solid {border_col};
          background: rgba(15, 23, 42, {0.48 if is_dark else 0.06});
          position: relative;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 16px;
        }}
        .demo-bricks {{
          display: flex;
          gap: 6px;
        }}
        .mini-brick {{
          width: 34px;
          height: 14px;
          border-radius: 3px;
          background: linear-gradient(135deg, #38bdf8, #0284c7);
          animation: brickPulse 2.4s infinite ease-in-out;
        }}
        .mini-brick.alt {{
          background: linear-gradient(135deg, #f472b6, #c026d3);
          animation-delay: 0.6s;
        }}
        .mini-ball {{
          position: absolute;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #fbbf24;
          box-shadow: 0 0 8px #fbbf24;
          animation: attractBall 3.2s infinite ease-in-out;
        }}
        .radar-call {{
          font-size: 11px;
          font-weight: 800;
          color: #f59e0b;
          letter-spacing: 0.04em;
        }}
        @keyframes brickPulse {{
          0%, 100% {{ transform: scale(1); opacity: 0.9; }}
          50% {{ transform: scale(1.06); opacity: 1; }}
        }}
        @keyframes attractBall {{
          0%, 100% {{ left: 195px; top: 22px; }}
          50% {{ left: 365px; top: 14px; }}
        }}
      </style>
      <div class="marquee">
        <div>
          <div class="top-row">
            <span class="pill">🕹️ ZERO-RELOAD IN-PROFILE ARCADE ENGINE</span>
            <span class="pill">{theme_badge}</span>
          </div>
          <div class="title">ARKANOID // VAUS BREAKOUT</div>
          <div class="subtitle">100% Self-Contained 3-Stage Campaign Inside README.md — Zero Page Reloads, Zero External Servers</div>
        </div>
        <div class="demo-strip">
          <div class="demo-bricks">
            <div class="mini-brick"></div>
            <div class="mini-brick alt"></div>
            <div class="mini-brick"></div>
            <div class="mini-brick alt"></div>
          </div>
          <div class="mini-ball"></div>
          <div class="radar-call">⚡ STAGE 01 SERVE LOCKED: AIM AT SECTOR 2 BELOW ▼</div>
        </div>
      </div>
    </div>
  </foreignObject>
</svg>
"""


def render_victory_svg() -> str:
    """Render `assets/victory.svg` (680x420) celebratory clear screen."""
    return f"""<svg fill="none" viewBox="0 0 {VIEWPORT_W} {VIEWPORT_H}" width="{VIEWPORT_W}" height="{VIEWPORT_H}" xmlns="http://www.w3.org/2000/svg">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>
{render_common_css()}
        .victory-wrap {{
          position: absolute;
          inset: 56px 24px 36px 24px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          gap: 14px;
        }}
        .trophy-orb {{
          width: 84px;
          height: 84px;
          border-radius: 50%;
          background: radial-gradient(circle at 35% 35%, #fef08a, #f59e0b 65%, #b45309 100%);
          border: 3px solid #ffffff;
          box-shadow: 0 0 28px rgba(245, 158, 11, 0.65);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 32px;
          font-weight: 900;
          color: #451a03;
          animation: trophyFloat 3s infinite ease-in-out;
        }}
        @keyframes trophyFloat {{
          0%, 100% {{ transform: translateY(0) scale(1); }}
          50% {{ transform: translateY(-8px) scale(1.06); }}
        }}
        .vic-title {{
          font-size: 24px;
          font-weight: 900;
          letter-spacing: 0.08em;
          color: var(--amber-accent);
        }}
        .vic-sub {{
          font-size: 13px;
          color: var(--text-main);
          max-width: 520px;
          line-height: 1.45;
        }}
        .stats-grid {{
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          width: 100%;
          max-width: 540px;
          margin-top: 6px;
        }}
        .stat-card {{
          padding: 10px 12px;
          border-radius: 8px;
          border: 1px solid var(--border-frame);
          background: var(--bg-outer);
        }}
        .stat-label {{
          font-size: 10px;
          color: var(--text-muted);
          letter-spacing: 0.06em;
        }}
        .stat-val {{
          font-size: 16px;
          font-weight: 900;
          color: var(--cyan-accent);
          margin-top: 4px;
        }}
      </style>
      <div class="cabinet">
        <div class="crt">
          <div class="scanlines"></div>
          <div class="hud">
            <div class="hud-group">
              <span class="hud-pill">CAMPAIGN COMPLETE</span>
              <span class="hud-pill">ALL 3 SECTORS LIBERATED</span>
            </div>
            <div class="hud-group">
              <span class="hud-pill">FINAL SCORE: 007600</span>
              <span class="hud-pill">VAUS: ♥♥♥ (FLAWLESS)</span>
            </div>
          </div>
          <div class="victory-wrap">
            <div class="trophy-orb">★</div>
            <div class="vic-title">DOH CORE OBLITERATED // VICTORY!</div>
            <div class="vic-sub">
              The Vaus spacecraft has shattered the Neon Wall, breached the Fortress Bunker,
              and overloaded the DOH Dimension Core without leaving your GitHub Profile.
            </div>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-label">FINAL SCORE</div>
                <div class="stat-val">7,600 PTS</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">BRICKS &amp; CORES</div>
                <div class="stat-val">26 / 26 CLEARED</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">PILOT RATING</div>
                <div class="stat-val">S+ ACE VAUS</div>
              </div>
            </div>
          </div>
          <div class="sector-bar">
            <div class="sector-cell sector-active">★ STAGE 1 CLEAR</div>
            <div class="sector-cell sector-active">★ STAGE 2 CLEAR</div>
            <div class="sector-cell sector-active">★ STAGE 3 CLEAR</div>
            <div class="sector-cell sector-active">★ 0 RELOADS</div>
            <div class="sector-cell sector-active">★ 3D VAULT BELOW</div>
          </div>
        </div>
      </div>
    </div>
  </foreignObject>
</svg>
"""


def stage1_bricks(
    hit_map: dict[str, float],
    destroyed_set: set[str],
) -> list[BrickSpec]:
    """Return the 5x2 Stage 1 Neon Wall brick grid (800 PTS total)."""
    bricks: list[BrickSpec] = []
    for col in range(5):
        cid = f"C{col + 1}"
        bricks.append(
            BrickSpec(
                brick_id=cid,
                row=0,
                col=col,
                kind="cyan",
                label=f"CYAN-{col + 1} [100]",
                points=100,
                hit_pct=hit_map.get(cid),
                destroyed_before=cid in destroyed_set,
            )
        )
    for col in range(5):
        mid = f"M{col + 1}"
        bricks.append(
            BrickSpec(
                brick_id=mid,
                row=1,
                col=col,
                kind="magenta",
                label=f"NEON-{col + 1} [60]",
                points=60,
                hit_pct=hit_map.get(mid),
                destroyed_before=mid in destroyed_set,
            )
        )
    return bricks


def stage2_bricks(
    hit_map: dict[str, float],
    destroyed_set: set[str],
) -> list[BrickSpec]:
    """Return the Stage 2 Fortress Bunker layout (8 Silver + 2 Emerald + 2 Gold Bumpers = 1,800 PTS)."""
    bricks: list[BrickSpec] = []
    # Row 0: S1..S5 (200 PTS each = 1000 PTS)
    for col in range(5):
        sid = f"S{col + 1}"
        bricks.append(
            BrickSpec(
                brick_id=sid,
                row=0,
                col=col,
                kind="silver",
                label=f"ARMOR-{col + 1} [200]",
                points=200,
                hit_pct=hit_map.get(sid),
                destroyed_before=sid in destroyed_set,
            )
        )
    # Row 1: S6 (col 0), E1 (col 1), S7 (col 2), E2 (col 3), S8 (col 4)
    row1_defs = [
        ("S6", 0, "silver", "ARMOR-6 [200]", 200),
        ("E1", 1, "emerald", "CORE-1 [100]", 100),
        ("S7", 2, "silver", "ARMOR-7 [200]", 200),
        ("E2", 3, "emerald", "CORE-2 [100]", 100),
        ("S8", 4, "silver", "ARMOR-8 [200]", 200),
    ]
    for bid, col, kind, lbl, pts in row1_defs:
        bricks.append(
            BrickSpec(
                brick_id=bid,
                row=1,
                col=col,
                kind=kind,
                label=lbl,
                points=pts,
                hit_pct=hit_map.get(bid),
                destroyed_before=bid in destroyed_set,
            )
        )
    # Row 2: Indestructible Gold Bumpers at col 1 and col 3
    for gid, col, lbl in [("G1", 1, "◆ GOLD BUMPER L ◆"), ("G2", 3, "◆ GOLD BUMPER R ◆")]:
        bricks.append(
            BrickSpec(
                brick_id=gid,
                row=2,
                col=col,
                kind="gold",
                label=lbl,
                points=0,
                hit_pct=hit_map.get(gid),
                indestructible=True,
            )
        )
    return bricks


def stage3_bricks(
    hit_map: dict[str, float],
    destroyed_set: set[str],
    boss_hp_end: int,
    boss_hit_pts: int,
) -> list[BrickSpec]:
    """Return Stage 3 DOH Core boss chamber & shield arrays (5,000 PTS total)."""
    boss_label = (
        f"👁️ DOH CORE [HP: {boss_hp_end}/3]"
        if boss_hp_end > 0
        else "💥 DOH CORE [OVERLOADED]"
    )
    items: list[BrickSpec] = [
        BrickSpec(
            brick_id="DOH",
            row=0,
            col=2,
            kind="boss",
            label=boss_label,
            points=boss_hit_pts,
            hit_pct=hit_map.get("DOH"),
            custom_rect=(244, 76, 192, 74),
        ),
        BrickSpec("SH-L1", 0, 0, "shield", "SHIELD-L1 [250]", 250, hit_map.get("SH-L1"), "SH-L1" in destroyed_set),
        BrickSpec("SH-L2", 1, 0, "shield", "SHIELD-L2 [250]", 250, hit_map.get("SH-L2"), "SH-L2" in destroyed_set),
        BrickSpec("PYL-L", 2, 0, "pylon", "LASER-PYL-L [250]", 250, hit_map.get("PYL-L"), "PYL-L" in destroyed_set),
        BrickSpec("SH-R1", 0, 4, "shield", "SHIELD-R1 [250]", 250, hit_map.get("SH-R1"), "SH-R1" in destroyed_set),
        BrickSpec("SH-R2", 1, 4, "shield", "SHIELD-R2 [250]", 250, hit_map.get("SH-R2"), "SH-R2" in destroyed_set),
        BrickSpec("PYL-R", 2, 4, "pylon", "LASER-PYL-R [250]", 250, hit_map.get("PYL-R"), "PYL-R" in destroyed_set),
    ]
    return items


def build_all_rally_specs() -> list[RallySpec]:
    """Build the 21 deterministic rally specifications across Stages 1, 2, and 3."""
    specs: list[RallySpec] = []

    # ==================== STAGE 1: NEON WALL ====================
    specs.append(
        RallySpec(
            filename="s1_r1_hit.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.1 // OPTIMAL SLICE",
            status_badge="4x COMBO",
            score_start=0,
            score_end=320,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=2,
            next_target_sector=3,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M1": 24.0, "C1": 36.0, "C2": 52.0, "M2": 64.0},
                destroyed_set=set(),
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(300.0, 210.0),
                paddle_sector=2,
                ricochet_points=[(96.0, 124.0), (34.0, 102.0), (96.0, 90.0), (160.0, 62.0), (220.0, 90.0), (220.0, 124.0)],
                next_sector=3,
            ),
            banner_title="4x NEON COMBO (+320 PTS)",
            banner_subtitle="Left-wall slice cleared M1, C1, C2, M2 — Ball descending to SECTOR 3",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_r1_bank.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.1 // CENTER BANK",
            status_badge="2x BANK",
            score_start=0,
            score_end=160,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=2,
            next_target_sector=1,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M2": 32.0, "C2": 52.0},
                destroyed_set=set(),
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(300.0, 210.0),
                paddle_sector=2,
                ricochet_points=[(216.0, 124.0), (216.0, 90.0), (150.0, 64.0)],
                next_sector=1,
            ),
            banner_title="CENTER BANK (+160 PTS)",
            banner_subtitle="Cleared M2 & C2 — Execute Sector 1 Bank Recovery to sweep M1 & C1",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_r2_hit.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.2 // CEILING SWEEP",
            status_badge="ENLARGED VAUS",
            score_start=320,
            score_end=640,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=3,
            next_target_sector=4,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M3": 25.0, "C3": 38.0, "C4": 54.0, "M4": 66.0},
                destroyed_set={"M1", "C1", "C2", "M2"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(220.0, 160.0),
                paddle_sector=3,
                ricochet_points=[(340.0, 124.0), (340.0, 90.0), (402.0, 62.0), (464.0, 90.0), (464.0, 124.0)],
                next_sector=4,
            ),
            banner_title="TOP-WALL SWEEP (+320 PTS)",
            banner_subtitle="Enlarged Vaus shattered M3, C3, C4, M4 — Final corner snipe at SECTOR 4",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_r2_bank.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.2 // SHALLOW BANK",
            status_badge="2x DEFLECT",
            score_start=320,
            score_end=440,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=3,
            next_target_sector=3,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M3": 32.0, "M4": 55.0},
                destroyed_set={"M1", "C1", "C2", "M2"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(220.0, 160.0),
                paddle_sector=3,
                ricochet_points=[(340.0, 124.0), (464.0, 124.0)],
                next_sector=3,
            ),
            banner_title="SHALLOW BANK (+120 PTS)",
            banner_subtitle="Cleared M3 & M4 — Rebound at SECTOR 3 to finish upper C3 & C4",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_r3_hit.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.3 // CORNER SNIPE",
            status_badge="STAGE 01 CLEAR",
            score_start=640,
            score_end=800,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=4,
            next_target_sector=None,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M5": 32.0, "C5": 54.0},
                destroyed_set={"M1", "C1", "C2", "M2", "M3", "C3", "C4", "M4"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(464.0, 160.0),
                paddle_sector=4,
                ricochet_points=[(648.0, 180.0), (588.0, 124.0), (588.0, 90.0)],
                next_sector=None,
            ),
            banner_title="STAGE 01 CLEAR! (800 PTS)",
            banner_subtitle="All 10 Neon Bricks Destroyed — Expand STAGE 02: FORTRESS BUNKER Below",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_r3_bank.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="RALLY 1.3 // GRAZE BANK",
            status_badge="1 BRICK LEFT",
            score_start=640,
            score_end=700,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=4,
            next_target_sector=5,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={"M5": 38.0},
                destroyed_set={"M1", "C1", "C2", "M2", "M3", "C3", "C4", "M4"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(464.0, 160.0),
                paddle_sector=4,
                ricochet_points=[(588.0, 124.0)],
                next_sector=5,
            ),
            banner_title="CORNER GRAZE (+60 PTS)",
            banner_subtitle="M5 shattered, C5 remains — Tap the Sector 5 Recovery to clear Stage 1",
        )
    )

    specs.append(
        RallySpec(
            filename="s1_miss.svg",
            stage=1,
            stage_title="NEON WALL",
            rally_label="SHIELD BREACH // WHIFF",
            status_badge="-1 VAUS LIFE",
            score_start=320,
            score_end=320,
            lives=2,
            paddle_start_sector=2,
            paddle_hit_sector=5,
            next_target_sector=2,
            vaus_mode="BREACH",
            is_miss=True,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage1_bricks(
                hit_map={},
                destroyed_set={"M1", "C1", "C2", "M2"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(216.0, 160.0),
                paddle_sector=5,
                ricochet_points=[],
                next_sector=2,
                is_miss=True,
            ),
            banner_title="⚠️ SHIELD BREACH (-1 VAUS LIFE)",
            banner_subtitle="Paddle drifted to Sector 5 while ball crossed Sector 2 — Re-serve below",
        )
    )

    # ==================== STAGE 2: FORTRESS BUNKER ====================
    specs.append(
        RallySpec(
            filename="s2_r1_hit.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.1 // GAP THREAD",
            status_badge="BUMPER THREAD",
            score_start=800,
            score_end=1400,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=3,
            next_target_sector=2,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"S7": 24.0, "E1": 38.0, "E2": 52.0, "S3": 66.0},
                destroyed_set=set(),
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(340.0, 210.0),
                paddle_sector=3,
                ricochet_points=[(340.0, 124.0), (216.0, 124.0), (464.0, 124.0), (340.0, 90.0)],
                next_sector=2,
            ),
            banner_title="GAP THREADED (+600 PTS)",
            banner_subtitle="Bypassed Gold Bumpers & shattered S7, E1, E2, S3 — Aim at SECTOR 2",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_r1_bank.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.1 // BUMPER CLANG",
            status_badge="GOLD RICOCHET",
            score_start=800,
            score_end=1100,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=3,
            next_target_sector=3,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"G1": 24.0, "S6": 42.0, "E1": 58.0},
                destroyed_set=set(),
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(340.0, 210.0),
                paddle_sector=3,
                ricochet_points=[(216.0, 158.0), (96.0, 124.0), (216.0, 124.0)],
                next_sector=3,
            ),
            banner_title="GOLD BUMPER RICOCHET (+300 PTS)",
            banner_subtitle="Deflected off Gold Bumper G1 into S6 & E1 — Thread the center gap next",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_r2_hit.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.2 // PINBALL POCKET",
            status_badge="4x SILVER SHATTER",
            score_start=1400,
            score_end=2200,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=2,
            next_target_sector=5,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"S6": 24.0, "S1": 36.0, "S2": 50.0, "S4": 64.0},
                destroyed_set={"S7", "E1", "E2", "S3"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(280.0, 190.0),
                paddle_sector=2,
                ricochet_points=[(96.0, 124.0), (96.0, 90.0), (216.0, 60.0), (216.0, 90.0), (464.0, 90.0)],
                next_sector=5,
            ),
            banner_title="UPPER POCKET COMBO (+800 PTS)",
            banner_subtitle="Demolished Silver Armor S6, S1, S2, S4 — Final armor wing at SECTOR 5",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_r2_bank.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.2 // FLANK BANK",
            status_badge="2x SILVER",
            score_start=1400,
            score_end=1800,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=2,
            next_target_sector=2,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"S6": 28.0, "S1": 46.0, "G1": 62.0},
                destroyed_set={"S7", "E1", "E2", "S3"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(280.0, 190.0),
                paddle_sector=2,
                ricochet_points=[(96.0, 124.0), (96.0, 90.0), (216.0, 158.0)],
                next_sector=2,
            ),
            banner_title="LEFT FLANK BANK (+400 PTS)",
            banner_subtitle="Cleared S6 & S1 before clanging off G1 — Re-enter pocket from SECTOR 2",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_r3_hit.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.3 // ARMOR BREAKER",
            status_badge="STAGE 02 CLEAR",
            score_start=2200,
            score_end=2600,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=5,
            next_target_sector=None,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"S8": 28.0, "S5": 48.0, "G2": 64.0},
                destroyed_set={"S7", "E1", "E2", "S3", "S6", "S1", "S2", "S4"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(520.0, 180.0),
                paddle_sector=5,
                ricochet_points=[(588.0, 124.0), (588.0, 90.0), (464.0, 158.0)],
                next_sector=None,
            ),
            banner_title="STAGE 02 CLEAR! (2,600 PTS)",
            banner_subtitle="Fortress Bunker Cracked — Expand STAGE 03: DOH CORE (BOSS) Below",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_r3_bank.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="RALLY 2.3 // OUTER BANK",
            status_badge="1 ARMOR LEFT",
            score_start=2200,
            score_end=2400,
            lives=3,
            paddle_start_sector=2,
            paddle_hit_sector=5,
            next_target_sector=4,
            vaus_mode="ENLARGED",
            is_miss=False,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"S8": 34.0, "G2": 56.0},
                destroyed_set={"S7", "E1", "E2", "S3", "S6", "S1", "S2", "S4"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(520.0, 180.0),
                paddle_sector=5,
                ricochet_points=[(588.0, 124.0), (464.0, 158.0)],
                next_sector=4,
            ),
            banner_title="OUTER WALL BANK (+200 PTS)",
            banner_subtitle="S8 shattered, S5 remains — Finish the top-right corner from SECTOR 4",
        )
    )

    specs.append(
        RallySpec(
            filename="s2_miss.svg",
            stage=2,
            stage_title="FORTRESS BUNKER",
            rally_label="BUMPER TRAP // WHIFF",
            status_badge="-1 VAUS LIFE",
            score_start=1400,
            score_end=1400,
            lives=2,
            paddle_start_sector=3,
            paddle_hit_sector=1,
            next_target_sector=2,
            vaus_mode="BREACH",
            is_miss=True,
            boss_hp_start=None,
            boss_hp_end=None,
            bricks=stage2_bricks(
                hit_map={"G1": 18.0},
                destroyed_set={"S7", "E1", "E2", "S3"},
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(260.0, 175.0),
                paddle_sector=1,
                ricochet_points=[],
                next_sector=2,
                is_miss=True,
            ),
            banner_title="⚠️ BUMPER RICOCHET BREACH (-1 LIFE)",
            banner_subtitle="Gold Bumper deflected ball past Sector 1 — Re-align Vaus below",
        )
    )

    # ==================== STAGE 3: DOH CORE (BOSS) ====================
    specs.append(
        RallySpec(
            filename="s3_r1_hit.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.1 // LEFT ARRAY BREACH",
            status_badge="DOH HP: 2/3",
            score_start=2600,
            score_end=4100,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=1,
            next_target_sector=4,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=3,
            boss_hp_end=2,
            bricks=stage3_bricks(
                hit_map={"PYL-L": 22.0, "SH-L2": 34.0, "SH-L1": 48.0, "DOH": 64.0},
                destroyed_set=set(),
                boss_hp_end=2,
                boss_hit_pts=750,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(200.0, 210.0),
                paddle_sector=1,
                ricochet_points=[(96.0, 158.0), (96.0, 124.0), (96.0, 90.0), (260.0, 112.0)],
                next_sector=4,
            ),
            banner_title="LEFT SHIELD BREACHED (+1,500 PTS)",
            banner_subtitle="Destroyed PYL-L, SH-L1, SH-L2 & struck DOH Core (HP 2/3) — Aim at SECTOR 4",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_r1_bank.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.1 // SHIELD SKIM",
            status_badge="ARRAY CRACKED",
            score_start=2600,
            score_end=3100,
            lives=3,
            paddle_start_sector=3,
            paddle_hit_sector=1,
            next_target_sector=2,
            vaus_mode="STANDARD",
            is_miss=False,
            boss_hp_start=3,
            boss_hp_end=3,
            bricks=stage3_bricks(
                hit_map={"PYL-L": 28.0, "SH-L2": 52.0},
                destroyed_set=set(),
                boss_hp_end=3,
                boss_hit_pts=0,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(200.0, 210.0),
                paddle_sector=1,
                ricochet_points=[(96.0, 158.0), (96.0, 124.0)],
                next_sector=2,
            ),
            banner_title="OUTER SHIELD SKIM (+500 PTS)",
            banner_subtitle="Cleared PYL-L & SH-L2 — Follow up at SECTOR 2 to breach SH-L1 & strike DOH",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_r2_hit.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.2 // LASER VAUS ASSAULT",
            status_badge="DOH HP: 1/3 CRITICAL",
            score_start=4100,
            score_end=5600,
            lives=3,
            paddle_start_sector=1,
            paddle_hit_sector=4,
            next_target_sector=3,
            vaus_mode="LASER",
            is_miss=False,
            boss_hp_start=2,
            boss_hp_end=1,
            bricks=stage3_bricks(
                hit_map={"PYL-R": 22.0, "SH-R2": 34.0, "SH-R1": 48.0, "DOH": 64.0},
                destroyed_set={"PYL-L", "SH-L1", "SH-L2"},
                boss_hp_end=1,
                boss_hit_pts=750,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(420.0, 195.0),
                paddle_sector=4,
                ricochet_points=[(588.0, 158.0), (588.0, 124.0), (588.0, 90.0), (410.0, 112.0)],
                next_sector=3,
            ),
            banner_title="LASER VAUS STRIKE (+1,500 PTS)",
            banner_subtitle="Right Shield Array Vaporized & DOH Core Critical (HP 1/3) — Final Shot at SECTOR 3",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_r2_bank.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.2 // BARRIER DEFLECT",
            status_badge="RIGHT ARRAY HIT",
            score_start=4100,
            score_end=4600,
            lives=3,
            paddle_start_sector=1,
            paddle_hit_sector=4,
            next_target_sector=4,
            vaus_mode="LASER",
            is_miss=False,
            boss_hp_start=2,
            boss_hp_end=2,
            bricks=stage3_bricks(
                hit_map={"PYL-R": 28.0, "SH-R2": 52.0},
                destroyed_set={"PYL-L", "SH-L1", "SH-L2"},
                boss_hp_end=2,
                boss_hit_pts=0,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(420.0, 195.0),
                paddle_sector=4,
                ricochet_points=[(588.0, 158.0), (588.0, 124.0)],
                next_sector=4,
            ),
            banner_title="RIGHT BARRIER DEFLECT (+500 PTS)",
            banner_subtitle="Cleared PYL-R & SH-R2 — Fire Laser Salvo from SECTOR 4 to crack SH-R1 & DOH",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_r3_hit.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.3 // CORE OVERLOAD",
            status_badge="BOSS DESTROYED",
            score_start=5600,
            score_end=7600,
            lives=3,
            paddle_start_sector=4,
            paddle_hit_sector=3,
            next_target_sector=None,
            vaus_mode="LASER",
            is_miss=False,
            boss_hp_start=1,
            boss_hp_end=0,
            bricks=stage3_bricks(
                hit_map={"DOH": 42.0},
                destroyed_set={"PYL-L", "SH-L1", "SH-L2", "PYL-R", "SH-R1", "SH-R2"},
                boss_hp_end=0,
                boss_hit_pts=2000,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(340.0, 190.0),
                paddle_sector=3,
                ricochet_points=[(340.0, 114.0), (340.0, 64.0), (340.0, 114.0)],
                next_sector=None,
            ),
            banner_title="💥 DOH CORE OVERLOADED! (+2,000 PTS)",
            banner_subtitle="Campaign Complete (7,600 PTS) — Open the 3D Victory Vault Below!",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_r3_bank.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="RALLY 3.3 // CONTAINMENT GRAZE",
            status_badge="CORE EXPOSED",
            score_start=5600,
            score_end=6100,
            lives=3,
            paddle_start_sector=4,
            paddle_hit_sector=3,
            next_target_sector=3,
            vaus_mode="LASER",
            is_miss=False,
            boss_hp_start=1,
            boss_hp_end=1,
            bricks=stage3_bricks(
                hit_map={"DOH": 38.0},
                destroyed_set={"PYL-L", "SH-L1", "SH-L2", "PYL-R", "SH-R1", "SH-R2"},
                boss_hp_end=1,
                boss_hit_pts=500,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(340.0, 190.0),
                paddle_sector=3,
                ricochet_points=[(270.0, 140.0), (410.0, 140.0)],
                next_sector=3,
            ),
            banner_title="CONTAINMENT GRAZE (+500 PTS)",
            banner_subtitle="DOH Core armor stripped — Fire the Point-Blank Finisher in SECTOR 3",
        )
    )

    specs.append(
        RallySpec(
            filename="s3_miss.svg",
            stage=3,
            stage_title="DOH CORE",
            rally_label="COUNTER-LASER // WHIFF",
            status_badge="-1 VAUS LIFE",
            score_start=4100,
            score_end=4100,
            lives=2,
            paddle_start_sector=1,
            paddle_hit_sector=2,
            next_target_sector=4,
            vaus_mode="BREACH",
            is_miss=True,
            boss_hp_start=2,
            boss_hp_end=2,
            bricks=stage3_bricks(
                hit_map={},
                destroyed_set={"PYL-L", "SH-L1", "SH-L2"},
                boss_hp_end=2,
                boss_hit_pts=0,
            ),
            waypoints=build_rally_waypoints(
                serve_xy=(420.0, 195.0),
                paddle_sector=2,
                ricochet_points=[],
                next_sector=4,
                is_miss=True,
            ),
            banner_title="⚠️ DOH COUNTER-LASER BREACH (-1 LIFE)",
            banner_subtitle="Vaus caught out of position in Sector 2 — Re-engage Thrusters Below",
        )
    )

    return specs


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Dual-theme Marquee headers
    (ASSETS_DIR / "marquee-dark.svg").write_text(render_marquee_svg("dark"), encoding="utf-8")
    (ASSETS_DIR / "marquee-light.svg").write_text(render_marquee_svg("light"), encoding="utf-8")

    # 2. All 21 Rally SVGs across Stages 1..3
    specs = build_all_rally_specs()
    for spec in specs:
        out_path = ASSETS_DIR / spec.filename
        out_path.write_text(render_rally_svg(spec), encoding="utf-8")

    # 3. Victory screen SVG
    (ASSETS_DIR / "victory.svg").write_text(render_victory_svg(), encoding="utf-8")

    total_files = 2 + len(specs) + 1
    print(f"Generated {total_files} SVG arcade assets in {ASSETS_DIR}")


if __name__ == "__main__":
    main()
