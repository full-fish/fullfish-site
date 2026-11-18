"""기기 A: 7.3인치 컬러 e-ink, 케이스 디자인 ② (현관문 자석형 + 접이식 다리).

설계 좌표: 앞에서 봤을 때 X 오른쪽, Y 위, Z 뒤쪽. 앞면이 Z=0, 뒷면(문에 닿는 면)이 Z=18,
원점은 앞면 가운데. 이 좌표는 실제 공간의 거울상이라 STL로 저장할 때 X를 뒤집는다
(그래야 보드가 앞에서 볼 때 왼쪽 아래에 오고 ◀ ↻ ▶ 표시가 바로 보인다).

실행: python device_a.py  →  stl/device-a/*.stl
"""
import math
from pathlib import Path

from manifold3d import Manifold

from cadlib import (EPS, along_x, along_y, box, check, circle, cyl_z, extrude,
                    overlap_volume, poly, rect, roofed_rect, rounded_slab, rrect,
                    save_stl, teardrop_cs, to_bed, union)

OUT = Path(__file__).parent / "stl" / "device-a"

# ───────────── 바깥 크기 ─────────────
W, H = 186.0, 128.0          # 앞에서 본 가로, 세로
CORNER_R = 6.0
FRAME_D = 14.5               # 앞틀 깊이
BACK_T = 3.5                 # 뒷판 두께
DEPTH = FRAME_D + BACK_T     # 전체 두께 18
WALL = 2.2                   # 옆벽 두께
FRONT_T = 1.6                # 앞면(창 테두리) 두께
EDGE_CHAMFER = 1.0           # 베드에 닿는 바깥 모서리 45도 모따기
IN_X, IN_Y = W / 2 - WALL, H / 2 - WALL   # 안쪽 벽면 위치 90.8, 61.8

# ───────────── 패널: GDEP073E01 (Seeed 7.3인치 Spectra 6) ─────────────
PANEL_W, PANEL_H, PANEL_T = 170.2, 111.2, 0.91
PANEL_CLR = 0.4              # 패널 자리 여유 (한쪽) → 171.0 × 112.0
AA_W, AA_H = 160.0, 96.0     # 표시 영역
AA_LEFT, AA_TOP = 5.1, 4.7   # 패널 끝 → 표시 영역 (아래쪽 FPC 테두리는 10.5)
WIN_MARGIN = 1.0             # 창을 표시 영역보다 한쪽 1mm 크게 → 162 × 98
WIN_CHAMFER = 1.0            # 창 가장자리 앞쪽 모따기
FPC_X, FPC_W = 0.5, 26.5     # 패널 FPC 꼬리 중심, 폭 (아래쪽 긴 변)
FPC_NOTCH_W = 34.0           # 도면 좌우 해석 차이(약 1mm)까지 덮도록 넉넉히
RIM_TOP = FRONT_T + PANEL_T + 0.5   # 패널 옆을 잡는 턱 높이 (Z) 3.01

# ───────────── EN04 보드 (Seeed KiCad V1.2 기준) ─────────────
# 보드 좌표 (bx, by): 부품면을 보고 버튼 변을 위로 둔 KiCad 원점(왼쪽 위) 기준.
# 케이스 안에서는 부품면이 뒷판 쪽, 버튼 변이 아래 벽 쪽이고 (X, Y) = (BX0 + bx, BY0 + by).
BOARD_W, BOARD_H, BOARD_T = 80.0, 41.23, 1.6
BOARD_GAP = 3.0                         # 버튼 변 ↔ 아래 벽 안쪽 (버튼 캡 턱이 들어감)
BX0 = -IN_X + 0.3                       # 보드 왼쪽 끝 X
BY0 = -IN_Y + BOARD_GAP                 # 보드 버튼 변 Y
BOARD_Z = FRONT_T + PANEL_T + 3.0       # PCB 앞면 Z (패널 뒤 3mm 폼테이프)
BOARD_HOLES_LEFT = [(2.54, 2.47), (2.54, 38.68)]   # 앞틀 기둥에 나사로 고정
# 아래 벽 구멍: (이름, bx 중심, 폭, 높이, PCB 윗면에서 중심까지 Z)
EDGE_PARTS = [
    ("switch", 10.34, 9.5, 4.0, 1.75),    # 슬라이드 스위치 (손잡이 1.8 돌출, 이쑤시개로 밂)
    ("reset", 20.41, 2.0, 2.0, 1.75),     # 클립으로 누르는 구멍
    ("key3", 29.74, 5.0, 5.0, 1.75),      # ◀
    ("key2", 39.07, 5.0, 5.0, 1.75),      # ↻
    ("key1", 48.41, 5.0, 5.0, 1.75),      # ▶
]
BUTTON_TIP = 1.45                       # 버튼 액추에이터가 변 밖으로 나온 길이
USB_BX, USB_W, USB_H, USB_DZ = 65.62, 12.4, 7.4, 3.2   # 플러그 몸통 12×7 + 여유

# ───────────── 배터리: Maxpower MP523450P (다리 칸 오른쪽에 가로로) ─────────────
BAT_L, BAT_WID, BAT_T = 50.0, 34.0, 5.2
BAT_CLR = 0.8
BAT_CX, BAT_CY = 59.5, -38.5
BAT_Z0 = RIM_TOP + 0.5                  # 패널 뒷면 + 양면테이프

# ───────────── 자석, 나사 ─────────────
MAG_D, MAG_T, MAG_CLR, MAG_SKIN = 10.0, 3.0, 0.2, 0.5
MAG_POS = [(sx * 78.0, y) for sx in (-1, 1) for y in (-49.0, 0.0, 49.0)]
# 아래쪽 두 나사는 보드, 배터리와 겹치지 않게 옆벽 중간으로 올린다
SCREW_POS = [(-88.6, 59.6), (88.6, 59.6), (-88.6, -8.0), (88.6, -8.0)]
POST_R = 2.8
INSERT_D, INSERT_DEPTH = 3.1, 5.0       # M2 열 인서트 (OD 3.2, L3)
SCREW_D, HEAD_D, HEAD_DEPTH = 2.4, 4.4, 1.8

# ───────────── 다리와 경첩 ─────────────
LEG_W = 59.0
Y_AX = -H / 2 + 94.0         # 경첩 축: 아래 끝에서 94mm
Z_AX = DEPTH - 2.5           # 축은 바깥면에서 2.5mm 안쪽 (다리 두께 -1.0 ~ +2.5)
LEG_LEN = 87.0               # 축에서 다리 끝까지
STOP_DEG = 30.0              # 다리가 멈추는 각도
BAY_TOP = 3.0                # 축에서 다리 칸 위쪽 벽까지
KNUCKLE_R = 2.5              # 뒷판 쪽 경첩 마디 반지름
BARREL_R = 2.6               # 다리 쪽 마디 반지름 (위쪽 벽과 0.4mm 틈)
LEG_CORE = 19.0              # 다리 가운데 마디 반폭
KNUCKLE_GAP = 0.4
BAY_HALF = LEG_W / 2 + 0.3
BAY_BOTTOM = -LEG_LEN - 0.4  # 축 기준
NOTCH_CLR = 2.9              # 바깥 구역 다리 끝을 축에서 깎는 반지름
PIN_D = 1.9                  # 1.75mm 필라멘트 핀 구멍
PIN_GROOVE = 22.0            # 뒷판 안쪽 핀 넣는 홈 길이 (양쪽)
FINGER_W, FINGER_D, FINGER_DEPTH = 16.0, 4.0, 2.0

COVER_T, COVER_MARGIN = 1.0, 2.0


# ═════════════ 앞틀 ═════════════
def front_frame():
    shell = rounded_slab(W, H, CORNER_R, 0, FRAME_D, cham_bottom=EDGE_CHAMFER)
    cavity = extrude(rrect(2 * IN_X, 2 * IN_Y, CORNER_R - WALL), RIM_TOP, FRAME_D + EPS)
    pocket = extrude(rrect(PANEL_W + 2 * PANEL_CLR, PANEL_H + 2 * PANEL_CLR, 0.8),
                     FRONT_T, RIM_TOP + EPS)
    aa_cx = -PANEL_W / 2 + AA_LEFT + AA_W / 2
    aa_cy = PANEL_H / 2 - AA_TOP - AA_H / 2
    ww, wh = AA_W + 2 * WIN_MARGIN, AA_H + 2 * WIN_MARGIN
    window = Manifold.batch_hull([
        extrude(rrect(ww + 2 * WIN_CHAMFER, wh + 2 * WIN_CHAMFER, 1.0 + WIN_CHAMFER, aa_cx, aa_cy),
                -EPS, 0),
        extrude(rrect(ww, wh, 1.0, aa_cx, aa_cy), WIN_CHAMFER, FRONT_T + EPS),
    ])
    # FPC가 패널 아래 변을 돌아 뒤로 꺾여 나가는 홈
    py0 = -PANEL_H / 2 - PANEL_CLR
    fpc_notch = box(FPC_X - FPC_NOTCH_W / 2, py0 - 3.0, FRONT_T,
                    FPC_X + FPC_NOTCH_W / 2, py0 + EPS, RIM_TOP + EPS)
    body = shell - cavity - pocket - window - fpc_notch

    # 뒷판 나사 기둥 (열 인서트)
    inner = extrude(rrect(W - 0.4, H - 0.4, CORNER_R - 0.2), 0, FRAME_D)
    posts = union([cyl_z(x, y, RIM_TOP - EPS, FRAME_D, POST_R) for x, y in SCREW_POS])
    body = body + (posts ^ inner)
    cuts = [cyl_z(x, y, FRAME_D - INSERT_DEPTH, FRAME_D + EPS, INSERT_D / 2) for x, y in SCREW_POS]

    # EN04 왼쪽 두 구멍 받침 기둥 (M2 나사를 바로 박는 1.6mm 구멍)
    for bx, by in BOARD_HOLES_LEFT:
        x, y = BX0 + bx, BY0 + by
        body = body + cyl_z(x, y, RIM_TOP - EPS, BOARD_Z, 2.2)
        cuts.append(cyl_z(x, y, BOARD_Z - 4.5, BOARD_Z + EPS, 0.8))

    # 아래 벽 구멍. 앞틀을 엎어 뽑으면 옆으로 뚫리므로 윗변 양 끝을 45도로 깎는다
    top = BOARD_Z + BOARD_T
    for name, bx, w_, h_, dz in EDGE_PARTS:
        cs = roofed_rect(w_ + 0.4, h_ + 0.4, up=(0, 1), cx=BX0 + bx, cy=top + dz)
        cuts.append(along_y(cs, -H / 2 - 1, -IN_Y + 1))
    # USB-C: 플러그 몸통 윗단이 앞틀 끝에 가까워 뒷판 쪽으로 열린 홈으로 낸다 (뒷판이 윗변이 됨)
    zc = top + USB_DZ
    cuts.append(box(BX0 + USB_BX - USB_W / 2, -H / 2 - 1, zc - USB_H / 2,
                    BX0 + USB_BX + USB_W / 2, -IN_Y + 1, FRAME_D + EPS))

    return body - union(cuts) - labels()


def labels():
    """버튼 아래 앞 테두리에 ◀ ↻ ▶ 표시를 0.4mm 새긴다."""
    y = -H / 2 + 4.5
    marks = []
    for name, bx, *_ in EDGE_PARTS:
        x = BX0 + bx
        if name == "key3":
            cs = poly([(x + 1.6, y - 1.8), (x + 1.6, y + 1.8), (x - 1.6, y)])
        elif name == "key1":
            cs = poly([(x - 1.6, y - 1.8), (x + 1.6, y), (x - 1.6, y + 1.8)])
        elif name == "key2":
            ring = circle(1.9, x, y) - circle(1.2, x, y)
            gap = poly([(x, y), (x + 3, y + 3), (x + 3, y)])
            head = poly([(x + 0.9, y + 0.3), (x + 2.9, y + 0.3), (x + 1.9, y - 1.0)])
            cs = ring - gap + head
        else:
            continue
        marks.append(extrude(cs, -EPS, 0.4))
    return union(marks)


# ═════════════ 경첩 단면 (s = Y - Y_AX, b = Z - Z_AX) ═════════════
def leg_core_profile():
    """다리 가운데 마디: 몸통 + 둥근 끝 + 30도 멈춤면.

    다리를 펴면 바깥쪽 끝이 다리 칸 위쪽 벽(s = BAY_TOP)으로 다가간다. 30도 방향보다 바깥쪽
    부분을 s·cos30 + b·sin30 = BAY_TOP 평면까지 채워 두면, 30도에서 그 면이 벽에 평평하게 닿는다.
    """
    body = rect(-LEG_LEN, -1.0, 0.0, 2.5)
    c, s = math.cos(math.radians(STOP_DEG)), math.sin(math.radians(STOP_DEG))
    w2 = BAY_TOP
    stop = poly([(0, 0), (w2 * c, w2 * s), ((w2 - 2.5 * s) / c, 2.5), (0, 2.5)])
    prof = body + circle(BARREL_R) + stop
    return prof ^ rect(-LEG_LEN - 1, -BARREL_R, BAY_TOP, 2.5)


def leg_side_profile():
    """다리 바깥 구역: 뒷판 마디와 부딪히지 않게 축 둘레를 깎는다."""
    return rect(-LEG_LEN, -1.0, 0.0, 2.5) - circle(NOTCH_CLR)


def knuckle_profile():
    """뒷판 쪽 경첩 마디 (D자형, 다리 칸 위쪽 벽에 붙음)."""
    return circle(KNUCKLE_R) + rect(0, -KNUCKLE_R, BAY_TOP + 0.5, 2.5)


def pin_hole_profile():
    # 뒷판과 다리는 바깥면을 바닥에 두고 뽑으므로 출력할 때 위쪽 = -b
    return teardrop_cs(PIN_D / 2, up=(0, -1))


def at_hinge(m):
    return m.translate((0, Y_AX, Z_AX))


def leg():
    core = along_x(leg_core_profile(), -LEG_CORE, LEG_CORE)
    side = along_x(leg_side_profile(), LEG_CORE, LEG_W / 2)
    m = core + side + side.mirror((1, 0, 0))
    m = m - along_x(pin_hole_profile(), -LEG_CORE - 1, LEG_CORE + 1)
    return at_hinge(m)


def leg_at(angle_deg):
    """다리를 angle_deg 만큼 편 모습 (간섭 검사용)."""
    return at_hinge(leg().translate((0, -Y_AX, -Z_AX)).rotate((-angle_deg, 0, 0)))


# ═════════════ 뒷판 ═════════════
def back_plate():
    plate = rounded_slab(W, H, CORNER_R, FRAME_D, DEPTH, cham_top=EDGE_CHAMFER)
    plate = plate - box(-BAY_HALF, Y_AX + BAY_BOTTOM, FRAME_D - EPS, BAY_HALF, Y_AX + BAY_TOP, DEPTH + EPS)

    k0, k1 = LEG_CORE + KNUCKLE_GAP, BAY_HALF + 0.5
    kn = at_hinge(along_x(knuckle_profile(), k0, k1))
    plate = plate + kn + kn.mirror((1, 0, 0))

    # 위치 맞춤 턱 (앞틀 안쪽 벽에 닿음, 아래 변은 버튼과 USB 때문에 뺌)
    lip_h, lip_t, clr = 1.5, 1.2, 0.25
    xi, yi = IN_X - clr, IN_Y - clr
    lips = union([
        box(-60, yi - lip_t, FRAME_D - lip_h, 60, yi, FRAME_D + EPS),
        box(-xi, -40, FRAME_D - lip_h, -xi + lip_t, 45, FRAME_D + EPS),
        box(xi - lip_t, -40, FRAME_D - lip_h, xi, 45, FRAME_D + EPS),
    ]) - union([cyl_z(x, y, 0, 20, POST_R + 0.4) for x, y in SCREW_POS])
    plate = plate + lips

    # 배터리 칸 울타리 (뒷판 안쪽에서 배터리 옆면까지 내려옴, 왼쪽에 전선 틈)
    bw, bh = BAT_L + 2 * BAT_CLR, BAT_WID + 2 * BAT_CLR
    z_fence = BAT_Z0 + BAT_T - 2.0
    fence = (extrude(rrect(bw + 2.4, bh + 2.4, 1.5, BAT_CX, BAT_CY), z_fence, FRAME_D + EPS)
             - extrude(rrect(bw, bh, 0.5, BAT_CX, BAT_CY), z_fence - 1, FRAME_D + 1)
             - box(BAT_CX - bw / 2 - 3, BAT_CY - 6, z_fence - 1, BAT_CX - bw / 2 + 1, BAT_CY + 6, FRAME_D + 1))
    plate = plate + fence

    cuts = []
    # 핀 구멍 + 안쪽에서 핀을 밀어 넣는 홈
    pin = at_hinge(along_x(pin_hole_profile(), k0 - EPS, BAY_HALF + PIN_GROOVE))
    groove = at_hinge(along_x(rect(-PIN_D / 2, -3.0, PIN_D / 2, 0.0), BAY_HALF, BAY_HALF + PIN_GROOVE))
    cuts += [pin, pin.mirror((1, 0, 0)), groove, groove.mirror((1, 0, 0))]
    # 손톱 홈 (다리 끝을 들어 올리는 곳)
    yb = Y_AX + BAY_BOTTOM
    cuts.append(box(-FINGER_W / 2, yb - FINGER_D, DEPTH - FINGER_DEPTH, FINGER_W / 2, yb + EPS, DEPTH + EPS))
    # 자석 홈 (안쪽에서 3mm, 바깥에 0.5mm 막)
    for x, y in MAG_POS:
        cuts.append(cyl_z(x, y, FRAME_D - 1.6, DEPTH - MAG_SKIN, MAG_D / 2 + MAG_CLR))
    # 나사 구멍 + 머리 자리
    for x, y in SCREW_POS:
        cuts.append(cyl_z(x, y, FRAME_D - 2, DEPTH + EPS, SCREW_D / 2))
        cuts.append(cyl_z(x, y, DEPTH - HEAD_DEPTH, DEPTH + EPS, HEAD_D / 2))
    return plate - union(cuts)


def bay_cover():
    """다리 칸 가림판: 뒷판 안쪽에 붙여 다리를 폈을 때 속이 안 보이게 한다."""
    y0 = Y_AX + BAY_BOTTOM - COVER_MARGIN
    y1 = Y_AX - NOTCH_CLR - 0.3
    x = BAY_HALF + COVER_MARGIN
    return box(-x, y0, FRAME_D - COVER_T, x, y1, FRAME_D)


def button_cap():
    """버튼 캡: 안쪽 턱(지름 7) + 벽을 지나 0.8mm 튀어나오는 기둥. 턱 쪽이 바닥.

    턱 두께는 아래 벽 안쪽 면에서 버튼 끝까지 거리 - 0.3mm 틈.
    """
    flange_t = BOARD_GAP - BUTTON_TIP - 0.3
    stem_len = WALL + 0.8
    return (cyl_z(0, 0, 0, flange_t, 3.5)
            + cyl_z(0, 0, flange_t - EPS, flange_t + stem_len, 2.5, 2.3))   # 구멍 5.4에 기둥 5.0


# ═════════════ 확인용 부품 모형 ═════════════
def dummies():
    panel = box(-PANEL_W / 2, -PANEL_H / 2, FRONT_T, PANEL_W / 2, PANEL_H / 2, FRONT_T + PANEL_T)
    board = box(BX0, BY0, BOARD_Z, BX0 + BOARD_W, BY0 + BOARD_H, BOARD_Z + BOARD_T)
    parts_top = box(BX0 + 5, BY0 + 0.5, BOARD_Z + BOARD_T, BX0 + BOARD_W - 5, BY0 + BOARD_H - 5,
                    BOARD_Z + BOARD_T + 5.5)   # 부품면 최고 높이 5.5
    battery = box(BAT_CX - BAT_L / 2, BAT_CY - BAT_WID / 2, BAT_Z0,
                  BAT_CX + BAT_L / 2, BAT_CY + BAT_WID / 2, BAT_Z0 + BAT_T)
    return {"패널": panel, "EN04": board + parts_top, "배터리": battery}


def main():
    frame, plate, lg, cover, cap = front_frame(), back_plate(), leg(), bay_cover(), button_cap()

    def phys(m):            # 설계 좌표(거울상) → 실제 공간
        return m.mirror((1, 0, 0))

    parts = {
        "a1_front_frame": phys(frame),                                 # 앞면이 바닥
        "a2_back_plate": phys(plate).rotate((0, 180, 0)),              # 바깥면이 바닥
        "a3_leg": phys(lg).rotate((0, 180, 0)),                        # 바깥면이 바닥
        "a4_button_cap_x3": union([cap.translate((i * 10.0, 0, 0)) for i in range(3)]),
        "a5_bay_cover": cover,
        # 맞춤 테스트: 앞틀 왼쪽 아래 (버튼, USB-C 구멍, 보드 기둥, 패널 모서리)만 얇게 먼저 뽑아 본다
        "a0_test_bottom_left": phys(frame ^ box(-W / 2 - 1, -H / 2 - 1, -1, -10, -H / 2 + 14, FRAME_D + 1)),
    }
    for name, m in parts.items():
        m = to_bed(m)
        print(check(m, name))
        save_stl(m, OUT / f"{name}.stl")

    print("\n[간섭 검사] 0이면 겹치지 않음 (mm³)")
    print("  앞틀 × 뒷판:", round(overlap_volume(frame, plate), 3))
    print("  뒷판 × 다리(접힘):", round(overlap_volume(plate, lg), 3))
    print("  가림판 × 뒷판:", round(overlap_volume(cover, plate), 3))
    print("  가림판 × 다리(접힘):", round(overlap_volume(cover, lg), 3))
    for name, d in dummies().items():
        print(f"  {name} × 앞틀: {round(overlap_volume(d, frame), 3)}, × 뒷판: {round(overlap_volume(d, plate), 3)}")
    rows = [(a, round(overlap_volume(leg_at(a), plate), 2)) for a in (0, 10, 20, 25, 29, 31, 33, 36)]
    print("  다리 각도별 뒷판과 겹침 (각도, mm³):", rows)


if __name__ == "__main__":
    main()
