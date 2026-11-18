"""stl/ 아래 STL마다 미리보기 그림을 만들어 사이트 계획 페이지 이미지 폴더에 저장합니다.

왼쪽은 베드에 놓인 그대로 위에서 본 모습(베드 격자 10mm), 오른쪽은 아래에서 본 모습입니다.
결과: public/projects/eink-display/img/stl-<이름>.webp (1600×1000)와 stl-<이름>-800.webp
"""
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "public" / "projects" / "eink-display" / "img"
W, H = 1600, 1000
SS = 2                  # 2배로 그린 뒤 줄여서 가장자리를 부드럽게
GRID = 10.0             # 베드 격자 간격 (mm)
VIEWS = ((-60, 35, "출력 방향 그대로 (위에서)"), (-60, -35, "아래에서 본 모습"))
PART = np.array([0.97, 0.97, 0.96])
EDGE = np.array([0.36, 0.39, 0.43])
BG_TOP, BG_BOTTOM = np.array([0.93, 0.925, 0.91]), np.array([0.85, 0.84, 0.825])
BED, BED_LINE = np.array([0.80, 0.795, 0.785]), np.array([0.72, 0.715, 0.705])
LIGHTS = ((np.array([-0.45, 0.6, 0.65]), 0.42), (np.array([0.6, -0.2, 0.5]), 0.15))  # 화면 기준 방향, 세기
FONT = Path("C:/Windows/Fonts/malgun.ttf")


def load_stl(path):
    data = path.read_bytes()
    n = struct.unpack_from("<I", data, 80)[0]
    rec = np.frombuffer(data, dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n, offset=84)
    return rec["v"].astype(np.float64)


def camera(az, el):
    a, e = np.radians(az), np.radians(el)
    c = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])  # 물체에서 카메라 쪽
    x = np.cross([0.0, 0.0, 1.0], c)
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(c, x), c])  # 행: 화면 오른쪽, 화면 위, 카메라 쪽(깊이)


def rasterize(scr, w, h):
    """scr: (N,3,3) 삼각형 꼭짓점의 (px, py, 깊이). 가까운 면의 깊이와 삼각형 번호를 돌려줍니다."""
    depth = np.full((h, w), -np.inf)
    tid = np.full((h, w), -1, np.int64)
    for i, ((x0, y0, d0), (x1, y1, d1), (x2, y2, d2)) in enumerate(scr):
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        xa, xb = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, w - 1)
        ya, yb = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, h - 1)
        if xa > xb or ya > yb:
            continue
        xs = np.arange(xa, xb + 1) + 0.5
        ys = np.arange(ya, yb + 1)[:, None] + 0.5
        w0 = ((x1 - xs) * (y2 - ys) - (x2 - xs) * (y1 - ys)) / area
        w1 = ((x2 - xs) * (y0 - ys) - (x0 - xs) * (y2 - ys)) / area
        w2 = 1.0 - w0 - w1
        z = w0 * d0 + w1 * d1 + w2 * d2
        dsub, tsub = depth[ya:yb + 1, xa:xb + 1], tid[ya:yb + 1, xa:xb + 1]
        upd = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (z > dsub)
        dsub[upd] = z[upd]
        tsub[upd] = i
    return depth, tid


def edges(nrm, depth, valid, mm_per_px):
    """면이 꺾이는 곳, 앞뒤로 겹치는 곳, 외곽선을 찾습니다."""
    out = np.zeros(valid.shape, bool)
    depth = np.where(valid, depth, 0.0)
    for axis in (0, 1):
        sl_a = (slice(None, -1), slice(None)) if axis == 0 else (slice(None), slice(None, -1))
        sl_b = (slice(1, None), slice(None)) if axis == 0 else (slice(None), slice(1, None))
        both = valid[sl_a] & valid[sl_b]
        crease = (nrm[sl_a] * nrm[sl_b]).sum(-1) < np.cos(np.radians(30))
        jump = np.abs(depth[sl_a] - depth[sl_b]) > max(1.5, 8 * mm_per_px)
        e = (valid[sl_a] != valid[sl_b]) | (both & (crease | jump))
        out[sl_a] |= e
        out[sl_b] |= e
    return out


def bed_layer(rows, cx, cy, scale, w, h, lo, hi):
    """화면 픽셀마다 시선이 z=0 평면과 만나는 점을 구해 베드와 격자를 칠합니다."""
    xs = (np.arange(w) + 0.5 - cx) / scale
    ys = (cy - (np.arange(h) + 0.5))[:, None] / scale
    t = -ys * rows[1, 2] / rows[2, 2]
    px = xs * rows[0, 0] + ys * rows[1, 0] + t * rows[2, 0]
    py = xs * rows[0, 1] + ys * rows[1, 1] + t * rows[2, 1]
    on_bed = (px >= lo[0]) & (px <= hi[0]) & (py >= lo[1]) & (py <= hi[1])
    half = 0.9 / scale * 1.6
    gx = np.abs((px - lo[0] + GRID / 2) % GRID - GRID / 2) < half
    gy = np.abs((py - lo[1] + GRID / 2) % GRID - GRID / 2) < half
    return on_bed, on_bed & (gx | gy)


def render(tris):
    tris = tris - (tris.reshape(-1, 3).min(0) + tris.reshape(-1, 3).max(0)) / 2 * np.array([1, 1, 0])
    vmin, vmax = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    lo = np.floor((vmin[:2] - GRID) / GRID) * GRID
    hi = np.ceil((vmax[:2] + GRID) / GRID) * GRID
    bed_corners = np.array([[lo[0], lo[1], 0], [hi[0], lo[1], 0], [lo[0], hi[1], 0], [hi[0], hi[1], 0]])
    top_pad, margin = 80 * SS, 36 * SS

    cams = [camera(az, el) for az, el, _ in VIEWS]
    spans = []
    for k, rows in enumerate(cams):
        pts = tris.reshape(-1, 3) if k else np.vstack([tris.reshape(-1, 3), bed_corners])
        p = pts @ rows[:2].T
        spans.append((p.min(0), p.max(0)))

    def fit(pw, ph):
        return min(min((pw - 2 * margin) / (b[0] - a[0]), (ph - top_pad - margin) / (b[1] - a[1])) for a, b in spans)

    # 두 모습을 좌우로 놓을지 위아래로 놓을지, 조각이 더 크게 보이는 쪽을 고릅니다.
    side = fit(W * SS // 2, H * SS) >= fit(W * SS, H * SS // 2)
    pw, ph = (W * SS // 2, H * SS) if side else (W * SS, H * SS // 2)
    scale = fit(pw, ph)
    origins = [(k * pw, 0) if side else (0, k * ph) for k in range(2)]

    gy = np.linspace(0, 1, H * SS)[:, None, None]
    canvas = np.empty((H * SS, W * SS, 3))
    canvas[:] = BG_TOP * (1 - gy) + BG_BOTTOM * gy
    tri_n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    tri_n /= np.linalg.norm(tri_n, axis=1, keepdims=True) + 1e-12
    for k, rows in enumerate(cams):
        (ax, ay), (bx, by) = spans[k]
        cx = pw / 2 - scale * (ax + bx) / 2
        cy = top_pad + (ph - top_pad - margin) / 2 + scale * (ay + by) / 2
        v = tris @ rows.T
        scr = np.stack([cx + scale * v[..., 0], cy - scale * v[..., 1], v[..., 2]], -1)
        nv = tri_n @ rows.T
        front = nv[:, 2] > 0
        depth, tid = rasterize(scr[front], pw, ph)
        nv = nv[front]
        valid = tid >= 0
        n = nv[np.clip(tid, 0, None)]
        lam = np.full(valid.shape, 0.6)
        flip = np.array([1.0, np.sign(VIEWS[k][1]), 1.0])  # 아래에서 볼 때는 조명도 아래에서
        for d, s in LIGHTS:
            lam += s * np.clip(n @ (d * flip / np.linalg.norm(d)), 0, None)
        ox, oy = origins[k]
        img = canvas[oy:oy + ph, ox:ox + pw]
        if k == 0:
            on_bed, line = bed_layer(rows, cx, cy, scale, pw, ph, lo, hi)
            img[on_bed & ~valid] = BED
            img[line & ~valid] = BED_LINE
        img[valid] = np.clip(PART * lam[valid][:, None], 0, 1)
        e = edges(n, depth, valid, 1 / scale)
        img[e] = img[e] * 0.35 + EDGE * 0.65

    im = Image.fromarray((canvas * 255).round().astype(np.uint8)).resize((W, H), Image.LANCZOS)
    draw = ImageDraw.Draw(im)
    divider = [(W // 2, 30), (W // 2, H - 30)] if side else [(30, H // 2), (W - 30, H // 2)]
    draw.line(divider, fill=(200, 197, 191), width=2)
    if FONT.exists():
        font = ImageFont.truetype(str(FONT), 28)
        for (ox, oy), (_, _, label) in zip(origins, VIEWS):
            draw.text((ox // SS + 36, oy // SS + 28), label, font=font, fill=(82, 96, 119))
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted((HERE / "stl").glob("device-*/*.stl")):
        name = "stl-" + path.stem.replace("_", "-")
        im = render(load_stl(path))
        im.save(OUT / f"{name}.webp", quality=88, method=6)
        im.resize((W // 2, H // 2), Image.LANCZOS).save(OUT / f"{name}-800.webp", quality=88, method=6)
        print(f"{path.relative_to(HERE)} -> {name}.webp")


if __name__ == "__main__":
    main()
