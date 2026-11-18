"""기기 B: 4.26인치 터치 영어 공부, AI 대화 기기 (쐐기형 책상 케이스).

설계 좌표: 앞에서 봤을 때 X 오른쪽, Y 위, Z 뒤쪽. 바닥이 Y=0, 앞면 아래 모서리가 Z=0.
앞면은 위로 갈수록 뒤로 ALPHA도 기운다. 이 좌표는 실제 공간의 거울상이라 STL로 저장할 때
X를 뒤집는다 (그래야 USB-C가 앞에서 볼 때 오른쪽 옆면으로 나온다).

앞판 쪽 부품은 (x, v, w) 좌표로 그린다. v는 앞면을 따라 아래 끝에서 위로, w는 앞면에 수직으로
안쪽으로 잰 거리 (w=0이 앞면 바깥). to_dev()가 기기 좌표로 옮긴다.

실행: python device_b.py  →  stl/device-b/*.stl
"""
import math
from pathlib import Path

from manifold3d import Manifold

from cadlib import (EPS, along_x, box, check, cyl_z, extrude, overlap_volume, poly, rect,
                    roofed_rect, rounded_slab, rrect, save_stl, to_bed, union)

OUT = Path(__file__).parent / "stl" / "device-b"

# ───────────── 바깥 크기 ─────────────
ALPHA = 15.0                     # 앞면이 뒤로 기운 각도
FRONT_W, FRONT_L = 125.0, 107.0  # 앞면 가로, 앞면 경사 길이
DEPTH = 50.0                     # 바닥 깊이 (앞 아래 모서리 → 뒷면)
CA, SA = math.cos(math.radians(ALPHA)), math.sin(math.radians(ALPHA))
H_V = FRONT_L * CA               # 높이 103.4
CORNER_R = 5.0
PLATE_T = 2.0                    # 앞판 두께
WALL = 2.2                       # 몸통 벽 두께
BACK_T = 2.0                     # 뒷덮개 두께
FRONT_CHAMFER = 0.8
IN_X = FRONT_W / 2 - WALL        # 옆벽 안쪽 60.3
ROOF_Y = H_V - WALL              # 지붕 안쪽 101.15
BACK_Z = DEPTH - BACK_T          # 몸통 뒤 끝 48

# ───────────── 화면: GDEQ0426T82-T01C (터치 포함, 가로로 놓고 FPC는 왼쪽) ─────────────
PANEL_W, PANEL_H, PANEL_T = 105.33, 62.37, 1.41
PANEL_CLR = 0.3
AA_W, AA_H = 92.8, 55.68
AA_FPC_SIDE, AA_FAR_SIDE = 9.79, 2.74   # 표시 영역 여백: FPC 쪽(왼쪽), 반대쪽. 위아래는 3.35
PANEL_CX = -(AA_FPC_SIDE - AA_FAR_SIDE) / 2   # 표시 영역이 앞면 가운데에 오도록 패널을 왼쪽으로
PANEL_V0 = 36.4                  # 패널 아래 끝 v
WIN_MARGIN, WIN_CHAMFER = 0.6, 0.8
RIM_T, RIM_H = 1.2, PANEL_T + 0.4

# ───────────── 스피커: Adafruit 3351 ─────────────
SPK_L, SPK_H, SPK_D = 70.11, 30.72, 16.54  # 앞 플랜지 가로, 높이(v), 전체 깊이
SPK_CV = 24.0                              # 스피커 중심 v (뒤 아래 모서리가 바닥 벽에 안 닿는 최저 위치)
SPK_HOLE_DX, SPK_HOLE_DV = 63.79 / 2, 24.11 / 2
SPK_GAP = 2.5                              # 앞판 뒷면 ↔ 스피커 앞면 (스펀지 테이프)
GRILL_W, GRILL_H = 50.0, 18.0
GRILL_HOLE_D, GRILL_PITCH = 2.3, 3.0

MIC_D, MIC_V = 1.8, 102.0

# ───────────── 온습도 센서 칸 (왼쪽 아래, 앞판에 붙은 벽 두 개) ─────────────
SENS_W, SENS_D = 21.0, 14.0      # 칸 안쪽 가로, 깊이(w)
SENS_TOP = 33.4                  # 칸 천장 아래면 v (화면 테두리 아래)
SENS_WALL, SENS_BACK_T = 1.2, 1.0
SENS_BACK_CHAMFER = 3.0          # 뒷판 왼쪽 아래 모서리 (몸통 안쪽 구석 반지름 2.8)
SENS_MODULE = (18.0, 26.0, 5.0)  # SHT40 모듈 가로, 세로, 두께 (여유를 더한 값)
SENS_FOAM = 3.0                  # 모듈과 앞벽 사이 폼테이프
VENT_Y = [6.0, 10.0, 14.0, 18.0, 22.0, 26.0]   # 왼쪽 옆벽 통풍 슬롯 높이
VENT_W, VENT_L = 1.6, 10.0

# ───────────── USB-C (XIAO, 오른쪽 옆벽) ─────────────
USB_V, USB_W = 70.0, 20.0        # 구멍 중심 (v, w). XIAO 자리를 정한 뒤 고친다
USB_HOLE_A, USB_HOLE_B = 12.4, 7.4   # 플러그 몸통 12×7 + 여유 (a: v 방향, b: w 방향)
XIAO_L, XIAO_W = 21.14, 17.78
XIAO_PCB_W = USB_W - 1.6 - 1.6   # XIAO PCB 앞면 w (USB-C가 PCB 위 1.6에 중심)

# ───────────── 조립 나사 ─────────────
LIP_T, LIP_H, LIP_CLR = 1.2, 3.0, 0.25
INSERT_D, INSERT_DEPTH = 3.1, 4.5          # M2 열 인서트 OD3.2 L3
SCREW_D, HEAD_CLR_D = 2.4, 4.6
BOSS_R, BOSS_LEN = 2.8, 6.0
TAB_T = 3.0
FRONT_SCREWS = [(-40.0, 102.2, "roof"), (40.0, 102.2, "roof"), (52.0, 20.0, "right")]
BACK_POSTS = [(sx * 58.0, y) for sx in (-1, 1) for y in (4.5, H_V - 4.5)]   # 모서리 벽에 묻히게
BACK_POST_R, BACK_POST_LEN = 3.0, 8.0


def to_dev(m):
    """앞판 좌표 (x, v, w) → 기기 좌표."""
    return m.rotate((ALPHA, 0, 0))


def w_slab(w0, w1):
    return to_dev(box(-300, -300, w0, 300, 300, w1))


def prism(inset=0.0, z0=-80.0, z1=DEPTH + 1):
    """앞에서 본 바깥 윤곽(둥근 사각)을 Z로 민 기둥. inset만큼 안으로 줄인다."""
    cs = rrect(FRONT_W - 2 * inset, H_V - 2 * inset, max(0.5, CORNER_R - inset), 0, H_V / 2)
    return extrude(cs, z0, z1)


def body_solid():
    return prism() ^ w_slab(PLATE_T, 400) ^ box(-200, -200, -200, 200, 200, BACK_Z)


def dev_yz(v, w):
    return v * CA - w * SA, v * SA + w * CA


# ═════════════ 앞판 ═════════════
def front_plate():
    slab = rounded_slab(FRONT_W, FRONT_L + 6, CORNER_R, 0, PLATE_T, cham_bottom=FRONT_CHAMFER,
                        cy=FRONT_L / 2)
    plate = to_dev(slab) ^ prism()
    lip = (prism(WALL + LIP_CLR) - prism(WALL + LIP_CLR + LIP_T)) ^ w_slab(PLATE_T - EPS, PLATE_T + LIP_H)

    adds, cuts = [], []
    # 화면 자리 테두리. 왼쪽(FPC 쪽)은 FPC가 뒤로 꺾여 나가게 양 끝만 남긴다
    pw, ph = PANEL_W + 2 * PANEL_CLR, PANEL_H + 2 * PANEL_CLR
    pcv = PANEL_V0 + PANEL_H / 2
    rim = (extrude(rrect(pw + 2 * RIM_T, ph + 2 * RIM_T, 1.5, PANEL_CX, pcv), PLATE_T - EPS, PLATE_T + RIM_H)
           - extrude(rrect(pw, ph, 0.5, PANEL_CX, pcv), PLATE_T - 1, PLATE_T + RIM_H + 1)
           - box(PANEL_CX - pw / 2 - 3, PANEL_V0 + 5, PLATE_T - 1,
                 PANEL_CX - pw / 2 + 1, PANEL_V0 + PANEL_H - 5, PLATE_T + RIM_H + 1))
    adds.append(rim)

    # 창 (표시 영역 + 0.6, 앞쪽 모따기). 표시 영역이 앞면 가운데
    ww, wh = AA_W + 2 * WIN_MARGIN, AA_H + 2 * WIN_MARGIN
    cuts.append(Manifold.batch_hull([
        extrude(rrect(ww + 2 * WIN_CHAMFER, wh + 2 * WIN_CHAMFER, 1.0 + WIN_CHAMFER, 0, pcv), -EPS, 0),
        extrude(rrect(ww, wh, 1.0, 0, pcv), WIN_CHAMFER, PLATE_T + EPS),
    ]))

    # 스피커 그릴 (엇갈린 격자)
    holes = []
    r = 0
    while True:
        v = SPK_CV - GRILL_H / 2 + r * GRILL_PITCH * 0.866
        if v > SPK_CV + GRILL_H / 2 + 1e-6:
            break
        off = (r % 2) * GRILL_PITCH / 2
        x = -GRILL_W / 2 + off
        while x <= GRILL_W / 2 + 1e-6:
            holes.append(cyl_z(x, v, -EPS, PLATE_T + EPS, GRILL_HOLE_D / 2))
            x += GRILL_PITCH
        r += 1
    cuts.append(union(holes))

    # 스피커 아래 두 구멍 받침 기둥 (위 두 구멍은 화면 뒤라 나사 없이 스펀지 테이프로)
    for sx in (-1, 1):
        x, v = sx * SPK_HOLE_DX, SPK_CV - SPK_HOLE_DV
        adds.append(cyl_z(x, v, PLATE_T - EPS, PLATE_T + SPK_GAP, 2.6))
        cuts.append(cyl_z(x, v, 1.0, PLATE_T + SPK_GAP + EPS, 0.85))   # M2를 바로 박는 1.7mm 구멍

    cuts.append(cyl_z(0, MIC_V, -EPS, PLATE_T + EPS, MIC_D / 2))

    # 몸통과 잇는 나사 기둥 (열 인서트)
    for x, v, _ in FRONT_SCREWS:
        adds.append(cyl_z(x, v, PLATE_T - EPS, PLATE_T + BOSS_LEN, BOSS_R))
        cuts.append(cyl_z(x, v, PLATE_T + BOSS_LEN - INSERT_DEPTH, PLATE_T + BOSS_LEN + EPS, INSERT_D / 2))

    # 온습도 센서 칸 벽 두 개 (스피커 쪽 옆벽, 천장) + 천장의 전선 홈 2×4
    x0 = -IN_X + LIP_CLR + LIP_T
    adds.append(box(x0 + SENS_W, -5, PLATE_T - EPS, x0 + SENS_W + SENS_WALL, SENS_TOP + SENS_WALL,
                    PLATE_T + SENS_D))
    adds.append(box(x0 - 1, SENS_TOP, PLATE_T - EPS, x0 + SENS_W + SENS_WALL, SENS_TOP + SENS_WALL,
                    PLATE_T + SENS_D))
    cuts.append(box(x0 + SENS_W / 2 - 2, SENS_TOP - 1, PLATE_T + SENS_D - 2,
                    x0 + SENS_W / 2 + 2, SENS_TOP + SENS_WALL + 1, PLATE_T + SENS_D + 1))

    inside = to_dev(union(adds) - union(cuts)) ^ prism(WALL + LIP_CLR)
    return (plate - to_dev(union(cuts))) + inside + lip


def sensor_back():
    """센서 칸 뒤(w = 16)를 막는 1mm 판. 몸통 왼쪽 벽, 바닥 벽, 칸의 두 벽 끝에 글루로 붙인다.
    앞판 좌표 (x, v, w)로 돌려준다. 왼쪽 아래 모서리는 몸통 안쪽 둥근 구석에 걸리지 않게 잘라 낸다."""
    w = PLATE_T + SENS_D
    v_bottom = (WALL + w * SA) / CA        # 바닥 벽 안쪽 면이 w=16 평면과 만나는 v
    x0, x1 = -IN_X + 0.3, -IN_X + LIP_CLR + LIP_T + SENS_W + SENS_WALL
    v0, v1 = v_bottom + 0.3, SENS_TOP + SENS_WALL
    c = SENS_BACK_CHAMFER
    return extrude(poly([(x0 + c, v0), (x1, v0), (x1, v1), (x0, v1), (x0, v0 + c)]), w, w + SENS_BACK_T)


# ═════════════ 몸통 ═════════════
def front_tab(x_c, v_c, attach):
    """앞판 나사 기둥 뒤에 오는 귀. 몸통을 뒷면이 바닥에 오게 뽑으므로 아랫면(뒤쪽)을 45도로 받친다."""
    w0 = PLATE_T + BOSS_LEN + 0.2
    w1 = w0 + TAB_T
    if attach == "roof":
        blk = to_dev(box(x_c - 4, v_c - 4, w0, x_c + 4, v_c + 10, w1))
        y_low, z_lb = dev_yz(v_c - 4, w1)
        drop = ROOF_Y - y_low
        sliver = box(x_c - 4, ROOF_Y - EPS, z_lb, x_c + 4, ROOF_Y + 3, z_lb + drop)
    else:  # 오른쪽 옆벽
        x_in = x_c - BOSS_R - 0.5
        blk = to_dev(box(x_in, v_c - 4, w0, IN_X + 1, v_c + 4, w1))
        y_lo, _ = dev_yz(v_c - 4, w1)
        y_hi, z_bm = dev_yz(v_c + 4, w1)
        span = IN_X - x_in
        sliver = box(IN_X - EPS, y_lo, z_bm, IN_X + 1, y_hi + 2, z_bm + span)
    tab = Manifold.batch_hull([blk, sliver]) ^ body_solid()
    hole = to_dev(cyl_z(x_c, v_c, w0 - 1, w1 + EPS, SCREW_D / 2) + cyl_z(x_c, v_c, w1, 120, HEAD_CLR_D / 2))
    return tab, hole


def body():
    shell = body_solid() - prism(WALL)
    adds, cuts = [], []
    for x, v, attach in FRONT_SCREWS:
        tab, hole = front_tab(x, v, attach)
        adds.append(tab)
        cuts.append(hole)
    # 뒷덮개 나사 기둥 (뒤 끝에서 열 인서트)
    for x, y in BACK_POSTS:
        adds.append(cyl_z(x, y, BACK_Z - BACK_POST_LEN, BACK_Z, BACK_POST_R))
        cuts.append(cyl_z(x, y, BACK_Z - INSERT_DEPTH, BACK_Z + EPS, INSERT_D / 2))
    m = (shell + (union(adds) ^ body_solid())) - union(cuts)

    # USB-C 구멍 (오른쪽 옆벽). 출력할 때 위쪽은 앞쪽(-w)이라 그쪽 변 양 끝을 45도로
    cs = roofed_rect(USB_HOLE_A, USB_HOLE_B, up=(0, -1), cx=USB_V, cy=USB_W)
    usb = to_dev(along_x(cs, IN_X - 1, FRONT_W / 2 + 1))
    # 온습도 센서 칸 통풍 슬롯 (왼쪽 옆벽, 길이 방향이 앞뒤라 출력할 때 세로로 섬)
    vents = []
    for y in VENT_Y:
        zc = (PLATE_T + SENS_D / 2 + y * SA) / CA
        vents.append(box(-FRONT_W / 2 - 1, y - VENT_W / 2, zc - VENT_L / 2,
                         -IN_X + 1, y + VENT_W / 2, zc + VENT_L / 2))
    return m - usb - union(vents)


# ═════════════ 뒷덮개 ═════════════
def back_cover():
    plate = prism() ^ box(-200, -200, BACK_Z, 200, 200, DEPTH)
    lip = ((prism(WALL + LIP_CLR) - prism(WALL + LIP_CLR + LIP_T))
           ^ box(-200, -200, BACK_Z - 1.5, 200, 200, BACK_Z + EPS))
    lip = lip - union([cyl_z(x, y, 0, DEPTH + 1, BACK_POST_R + 0.6) for x, y in BACK_POSTS])
    # XIAO 받침벽: USB-C를 꽂는 힘을 XIAO 납땜이 아니라 케이스가 받게, XIAO 왼쪽 끝 바로 옆에 세운다
    fin_x1 = IN_X - 0.5 - XIAO_L - 0.3
    fin = to_dev(box(fin_x1 - 1.4, USB_V - XIAO_W / 2, XIAO_PCB_W - 0.5, fin_x1, USB_V + XIAO_W / 2, 120))
    fin = fin ^ box(-200, -200, -200, 200, 200, BACK_Z + EPS) ^ prism(WALL + 0.5)
    holes = union([cyl_z(x, y, BACK_Z - 2, DEPTH + 1, SCREW_D / 2) for x, y in BACK_POSTS])
    return plate + lip + fin - holes


# ═════════════ 확인용 부품 모형 ═════════════
def dummies():
    panel = to_dev(box(PANEL_CX - PANEL_W / 2, PANEL_V0, PLATE_T,
                       PANEL_CX + PANEL_W / 2, PANEL_V0 + PANEL_H, PLATE_T + PANEL_T))
    speaker = to_dev(box(-SPK_L / 2, SPK_CV - SPK_H / 2, PLATE_T + SPK_GAP,
                         SPK_L / 2, SPK_CV + SPK_H / 2, PLATE_T + SPK_GAP + SPK_D))
    xiao = to_dev(box(IN_X - 0.5 - XIAO_L, USB_V - XIAO_W / 2, XIAO_PCB_W,
                      IN_X - 0.5, USB_V + XIAO_W / 2, XIAO_PCB_W + 1.6 + 3.2))
    mw, ml, mt = SENS_MODULE
    cx = -IN_X + LIP_CLR + LIP_T + SENS_W / 2
    module = to_dev(box(cx - mw / 2, SENS_TOP - 0.5 - ml, PLATE_T + SENS_FOAM,
                        cx + mw / 2, SENS_TOP - 0.5, PLATE_T + SENS_FOAM + mt))
    return {"패널": panel, "스피커": speaker, "XIAO": xiao, "SHT40 모듈": module}


def main():
    fp, bd, bc = front_plate(), body(), back_cover()

    def phys(m):            # 설계 좌표(거울상) → 실제 공간
        return m.mirror((1, 0, 0))

    parts = {
        "b1_front_plate": phys(fp).rotate((-ALPHA, 0, 0)),     # 앞면이 바닥
        "b2_body": phys(bd).rotate((0, 180, 0)),               # 뒤 끝이 바닥
        "b3_back_cover": phys(bc).rotate((0, 180, 0)),         # 바깥면이 바닥
        "b4_sensor_back": sensor_back(),
        # 맞춤 테스트: 앞판 아래쪽 (그릴, 스피커 기둥, 센서 칸, 화면 테두리 아래 변) 두께 5mm까지만
        "b0_test_front_bottom": phys(to_dev(box(-70, -5, -1, 70, 45, 5)) ^ fp).rotate((-ALPHA, 0, 0)),
    }
    for name, m in parts.items():
        m = to_bed(m)
        print(check(m, name))
        save_stl(m, OUT / f"{name}.stl")

    print("\n[간섭 검사] 0이면 겹치지 않음 (mm³)")
    print("  앞판 × 몸통:", round(overlap_volume(fp, bd), 3))
    print("  뒷덮개 × 몸통:", round(overlap_volume(bc, bd), 3))
    print("  앞판 × 뒷덮개:", round(overlap_volume(fp, bc), 3))
    sb = to_dev(sensor_back())
    print(f"  센서 칸 뒷판 × 앞판: {round(overlap_volume(sb, fp), 3)}, × 몸통: {round(overlap_volume(sb, bd), 3)},"
          f" × 뒷덮개: {round(overlap_volume(sb, bc), 3)}")
    for name, d in dummies().items():
        print(f"  {name} × 앞판: {round(overlap_volume(d, fp), 3)}, × 몸통: {round(overlap_volume(d, bd), 3)},"
              f" × 뒷덮개: {round(overlap_volume(d, bc), 3)}, × 센서 칸 뒷판: {round(overlap_volume(d, sb), 3)}")
    x0, y0, z0, x1, y1, z1 = (fp + bd + bc).bounding_box()
    print(f"  조립 크기: 가로 {x1 - x0:.1f}, 높이 {y1 - y0:.1f}, 깊이 {z1 - z0:.1f}")


if __name__ == "__main__":
    main()
