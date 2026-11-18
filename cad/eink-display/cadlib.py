"""기기 A, B 케이스 생성에 함께 쓰는 형상 도구.

manifold3d(불리언 연산 라이브러리)로 형상을 만들고 바이너리 STL로 저장한다.
단위는 모두 mm.
"""
import math
import struct
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

EMPTY = Manifold()
EPS = 0.01


def _segs(r):
    """반지름에 맞춰 원의 분할 수를 정한다 (변 길이 약 0.4mm)."""
    return max(16, min(160, int(2 * math.pi * r / 0.4)))


def box(x0, y0, z0, x1, y1, z1):
    """두 꼭짓점으로 정한 직육면체."""
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_z(x, y, z0, z1, r, r_top=None):
    """Z축 방향 원기둥 (r_top을 주면 원뿔대)."""
    rt = r if r_top is None else r_top
    return Manifold.cylinder(z1 - z0, r, rt, _segs(max(r, rt))).translate((x, y, z0))


def circle(r, cx=0.0, cy=0.0):
    return CrossSection.circle(r, _segs(r)).translate((cx, cy))


def rect(x0, y0, x1, y1):
    return CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def rrect(w, h, r, cx=0.0, cy=0.0):
    """가운데 기준 둥근 모서리 사각형 단면."""
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    if r <= 0:
        return CrossSection.square((w, h), center=True).translate((cx, cy))
    base = CrossSection.square((w - 2 * r, h - 2 * r), center=True)
    return base.offset(r, JoinType.Round, 2.0, _segs(r)).translate((cx, cy))


def poly(points):
    return CrossSection([points])


def extrude(cs, z0, z1):
    return cs.extrude(z1 - z0).translate((0, 0, z0))


def along_x(cs, x0, x1):
    """단면 (u, v)를 (Y, Z)로 놓고 X 방향 x0~x1로 밀어낸다."""
    m = cs.extrude(x1 - x0)
    return m.transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


def along_y(cs, y0, y1):
    """단면 (u, v)를 (X, Z)로 놓고 Y 방향 y0~y1로 밀어낸다."""
    m = cs.extrude(y1 - y0)
    return m.transform(np.array([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]], dtype=float))


def rounded_slab(w, h, r, z0, z1, cham_bottom=0.0, cham_top=0.0, cx=0.0, cy=0.0):
    """둥근 사각 판. 아래/위 모서리에 45도 모따기를 줄 수 있다 (볼록이라 hull로 만든다)."""
    t = 0.01
    cb, ct = cham_bottom, cham_top
    parts = [
        extrude(rrect(w - 2 * cb, h - 2 * cb, r - cb, cx, cy), z0, z0 + t),
        extrude(rrect(w, h, r, cx, cy), z0 + cb, z1 - ct),
        extrude(rrect(w - 2 * ct, h - 2 * ct, r - ct, cx, cy), z1 - t, z1),
    ]
    return Manifold.batch_hull(parts)


def teardrop_cs(r, up=(0.0, 1.0), cx=0.0, cy=0.0):
    """원 + 위쪽 45도 뾰족 지붕 단면 (옆으로 뚫리는 구멍을 서포트 없이 뽑기 위함).

    up: 출력할 때 위쪽(+Z)이 될 방향을 단면 좌표로 준 것.
    """
    ux, uy = up
    s = r / math.sqrt(2)
    px, py = -uy, ux
    a = (ux * s + px * s, uy * s + py * s)
    b = (ux * s - px * s, uy * s - py * s)
    tip = (ux * r * math.sqrt(2), uy * r * math.sqrt(2))
    roof = CrossSection([[b, tip, a, (0.0, 0.0)]])
    if roof.area() < 0:
        roof = CrossSection([[a, tip, b, (0.0, 0.0)]])
    return (circle(r) + roof).translate((cx, cy))


def roofed_rect(w, h, up=(0.0, 1.0), cx=0.0, cy=0.0, roof_max=1.5):
    """가운데 기준 사각 구멍 단면. up 쪽 변의 양 끝을 45도로 깎아 다리(브리지) 길이를 줄인다.

    옆으로 뚫리는 구멍용. roof_max: 45도 지붕의 최대 높이 (남는 윗변은 짧은 브리지로 뽑힌다).
    """
    ux, uy = up
    base = CrossSection.square((w, h), center=True)
    if abs(uy) > 0.5:
        e, half = (h / 2) * uy, w / 2
        rh = min(half, roof_max)
        pts = [(-half, e), (half, e), (half - rh, e + uy * rh), (-half + rh, e + uy * rh)]
    else:
        e, half = (w / 2) * ux, h / 2
        rh = min(half, roof_max)
        pts = [(e, -half), (e, half), (e + ux * rh, half - rh), (e + ux * rh, -half + rh)]
    if rh >= half - 1e-6:   # 꼭짓점이 한 점으로 모이면 삼각형
        pts = pts[:3]
    roof = CrossSection([pts])
    if roof.area() <= 0:
        roof = CrossSection([pts[::-1]])
    return (base + roof).translate((cx, cy))


def union(items):
    items = [i for i in items if not i.is_empty()]
    if not items:
        return EMPTY
    return Manifold.batch_boolean(items, __import__("manifold3d").OpType.Add)


def check(m, name):
    """형상이 비어 있지 않은지 확인하고 요약을 돌려준다."""
    if m.is_empty():
        raise RuntimeError(f"{name}: 형상이 비어 있음 ({m.status()})")
    x0, y0, z0, x1, y1, z1 = m.bounding_box()
    return {
        "name": name,
        "size": (round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)),
        "volume_cm3": round(m.volume() / 1000, 1),
        "parts": len(m.decompose()),
        "tris": m.num_tri(),
    }


def to_bed(m):
    """바닥(최소 Z)을 0에, XY 중심을 원점에 맞춘다."""
    x0, y0, z0, x1, y1, z1 = m.bounding_box()
    return m.translate((-(x0 + x1) / 2, -(y0 + y1) / 2, -z0))


def save_stl(m, path):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    t = np.asarray(mesh.tri_verts, dtype=np.int64)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln == 0] = 1
    n = n / ln
    data = np.zeros(len(t), dtype=[("n", "<f4", 3), ("a", "<f4", 3), ("b", "<f4", 3),
                                    ("c", "<f4", 3), ("attr", "<u2")])
    data["n"], data["a"], data["b"], data["c"] = n, p0, p1, p2
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"fullfish eink-display case".ljust(80, b" "))
        f.write(struct.pack("<I", len(t)))
        f.write(data.tobytes())


def overlap_volume(a, b):
    """두 형상이 겹치는 부피 (간섭 검사용)."""
    return (a ^ b).volume()
