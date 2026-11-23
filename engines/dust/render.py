"""Render a deterministic CAMS dust atlas animation from a small JSON snapshot."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "projects/001-saharan-dust/data/dust_snapshot.json"
BASEMAP = ROOT / "shared/ne_110m_land.geojson"
OUT = ROOT / "output/001-saharan-dust"
W, H = 1280, 720
MAP = (68, 185, 1212, 604)
BOUNDS = (-18, 17, 30, 45)


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def project(lon, lat):
    x0, y0, x1, y1 = MAP
    lo0, lo1, la0, la1 = BOUNDS
    return (x0 + (lon - lo0) / (lo1 - lo0) * (x1 - x0),
            y1 - (lat - la0) / (la1 - la0) * (y1 - y0))


def basemap():
    im = Image.new("RGB", (W, H), (8, 16, 30))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = MAP
    d.rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), 14,
                        fill=(12, 30, 48), outline=(51, 82, 99), width=2)
    for lon in range(-15, 20, 5):
        x, _ = project(lon, 32)
        d.line((x, y0, x, y1), fill=(28, 53, 70), width=1)
    for lat in range(30, 50, 5):
        _, y = project(-18, lat)
        d.line((x0, y, x1, y), fill=(28, 53, 70), width=1)
    geo = json.loads(BASEMAP.read_text(encoding="utf-8"))
    land = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(land)
    for feature in geo["features"]:
        geom = feature["geometry"]
        polygons = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for polygon in polygons:
            for ring in polygon:
                if len(ring) < 3:
                    continue
                # Clip via PIL's canvas; skip geometries outside the region.
                if not any(-25 <= p[0] <= 24 and 25 <= p[1] <= 54 for p in ring):
                    continue
                ld.polygon([project(p[0], p[1]) for p in ring], fill=(27, 42, 52, 255))
                ld.line([project(p[0], p[1]) for p in ring], fill=(80, 108, 109, 255), width=2, joint="curve")
    im.paste(land.crop(MAP), (x0, y0), land.crop(MAP))
    d.rectangle(MAP, outline=(63, 101, 116), width=2)
    d.text((69, 39), "SAHARAN DUST", font=font(51, True), fill=(242, 232, 203))
    d.text((70, 108), "Modeled near-surface dust over North Africa and the Mediterranean", font=font(23), fill=(165, 192, 198))
    d.text((70, 627), "CAMS EUROPE  /  NEAR-SURFACE DUST  /  μg/m³", font=font(18, True), fill=(174, 200, 203))
    d.text((70, 669), "Source: CAMS via Open-Meteo  •  Model forecast, not direct observation", font=font(16), fill=(130, 160, 167))
    for name, lon, lat in [("MOROCCO", -7.5, 33.3), ("SPAIN", -3.9, 40.5),
                           ("PORTUGAL", -9.2, 39.0), ("FRANCE", 2.2, 44.2),
                           ("ALGERIA", 4.0, 34.3), ("ITALY", 11.7, 42.3)]:
        x, y = project(lon, lat)
        d.text((x, y), name, font=font(13, True), anchor="mm", fill=(162, 177, 168), stroke_width=1, stroke_fill=(13, 25, 34))
    return im


def field(snapshot, hour_index):
    latitudes = sorted({p["lat"] for p in snapshot["points"]}, reverse=True)
    longitudes = sorted({p["lon"] for p in snapshot["points"]})
    values = {(p["lat"], p["lon"]): p["dust"][hour_index] for p in snapshot["points"]}
    grid = np.array([[values[(lat, lon)] if values[(lat, lon)] is not None else np.nan
                      for lon in longitudes] for lat in latitudes], dtype=np.float32)
    if np.isnan(grid).all():
        raise ValueError("All dust values are missing")
    grid = np.nan_to_num(grid, nan=0)
    x0, y0, x1, y1 = MAP
    # Linear interpolation is presentation only; it does not add model resolution.
    lat_px = np.linspace(BOUNDS[3], BOUNDS[2], y1-y0)
    lon_px = np.linspace(BOUNDS[0], BOUNDS[1], x1-x0)
    tmp = np.array([np.interp(lon_px, longitudes, row) for row in grid])
    smooth = np.array([np.interp(lat_px, latitudes[::-1], tmp[::-1, col])
                       for col in range(tmp.shape[1])]).T
    return smooth


def layer(values, scale):
    intensity = np.clip(values / scale, 0, 1) ** 0.65
    alpha = np.uint8(np.clip((intensity - 0.06) * 185, 0, 175))
    rgba = np.empty((*values.shape, 4), dtype=np.uint8)
    rgba[:, :, 0] = np.uint8(174 + 81 * intensity)
    rgba[:, :, 1] = np.uint8(146 - 36 * intensity)
    rgba[:, :, 2] = np.uint8(81 - 39 * intensity)
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba)


def render(snapshot_path=SNAPSHOT, out_dir=OUT, seconds=20, fps=20):
    snap = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    if snap["variable"] != "dust" or snap["domain"] != "cams_europe":
        raise ValueError("Unsupported scientific variable or domain")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_hours = len(snap["times_utc"])
    fields = [field(snap, h) for h in range(n_hours)]
    maximum = max(float(np.max(f)) for f in fields)
    if maximum <= 0:
        raise ValueError("Selected period has no positive dust concentrations")
    scale = max(25.0, float(np.percentile(np.stack(fields), 97)))
    overlays = [layer(f, scale) for f in fields]
    base = basemap().convert("RGBA")
    total = int(seconds * fps)
    x0, y0, x1, y1 = MAP
    output = out_dir / "saharan-dust.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for frame in range(total):
            phase = frame / max(1, total - 1) * (n_hours - 1)
            h0 = min(int(phase), n_hours - 2)
            blend = phase - h0
            dust = Image.blend(overlays[h0], overlays[h0 + 1], blend)
            canvas = base.copy()
            canvas.alpha_composite(dust, (x0, y0))
            draw = ImageDraw.Draw(canvas)
            stamp = dt.datetime.fromisoformat(snap["times_utc"][h0]) + dt.timedelta(hours=blend)
            draw.rounded_rectangle((914, 44, 1212, 134), 11, fill=(19, 38, 49, 240), outline=(81, 122, 126, 255), width=2)
            draw.text((938, 58), stamp.strftime("%d %b %Y"), font=font(22, True), fill=(242, 227, 196))
            draw.text((938, 95), stamp.strftime("%H:%M UTC"), font=font(19), fill=(176, 201, 199))
            draw.rounded_rectangle((1011, 626, 1212, 688), 8, fill=(18, 35, 45, 255), outline=(78, 113, 118, 255), width=1)
            draw.text((1030, 635), f"Peak {maximum:.0f} μg/m³", font=font(19, True), fill=(232, 192, 126))
            draw.text((1030, 660), "during this event", font=font(14), fill=(162, 190, 190))
            draw.text((723, 629), "DUST CONCENTRATION", font=font(13, True), fill=(171, 197, 195))
            for x in range(220):
                t = x / 219
                draw.rectangle((723 + x, 658, 723 + x, 668), fill=(int(174 + 81*t), int(146 - 36*t), int(81 - 39*t)))
            draw.text((723, 674), "0", font=font(12), fill=(159, 187, 188))
            draw.text((901, 674), f"{scale:.0f}+ μg/m³", font=font(12), fill=(159, 187, 188))
            draw.rectangle((70, 611, 1212, 615), fill=(38, 63, 75))
            draw.rectangle((70, 611, 70 + int((frame + 1) / total * 1142), 615), fill=(230, 177, 91))
            rgb = canvas.convert("RGB")
            if frame == round((int(np.argmax([f.max() for f in fields])) / (n_hours - 1)) * (total - 1)):
                rgb.save(out_dir / "thumbnail.png", optimize=True)
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(err[-2000:])
    except Exception:
        proc.kill()
        raise
    print(f"Rendered {output} ({seconds}s, {fps} fps); peak {maximum:.1f} μg/m³")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    render(out_dir=args.out, seconds=args.seconds, fps=args.fps)
