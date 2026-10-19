"""
WikiHouse 設計可視化模組 v2
============================
根據 Grammar 驗證後的 Block 配置，
生成 2D 平面圖和等角組合示意圖。
支援不同跨距和屋頂形式的差異化顯示。
"""
 
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
 
# ── 顏色定義 ──
COLORS = {
    "floor":      "#D4C5A9",
    "wall":       "#6B8FA3",
    "corner":     "#4A6F82",
    "window":     "#A8D8EA",
    "door":       "#7EC8E3",
    "roof_flat":  "#8FA36B",
    "roof_slope": "#6B8A4A",
    "roof_gable": "#4A6B30",
    "background": "#1A1A2E",
    "grid":       "#2A2A4E",
    "text":       "#FFFFFF",
    "highlight":  "#FFD700",
    "dimension":  "#FFD700",
}
 
GRID = 0.6  # 600mm = 0.6m
 
SPAN_MAP = {
    "S":    3.6,
    "XS":   3.0,
    "XXXS": 2.4,
    "M":    4.8,
    "L":    5.4,
}
 
ROOF_LABELS = {
    "flat":         "平頂",
    "sloping_10deg": "斜頂 10°",
    "gable_42deg":  "山牆 42°",
}
 
 
def get_span_from_blocks(blocks: list, default_span: str = "M") -> float:
    """從 Block 清單判斷跨距"""
    for b in blocks:
        name = (b.get("name") or b.get("id", "")).upper()
        for key, val in SPAN_MAP.items():
            if f"FLOOR-{key}" in name or f"XFLOOR-{key}" in name:
                return val
    return SPAN_MAP.get(default_span, 4.8)
 
 
def get_length_from_blocks(blocks: list, span_m: float) -> float:
    """從 Floor Block 數量估算建築長度"""
    floor_count = len([b for b in blocks if b.get("category") in ["floor", "end"]])
    if floor_count == 0:
        return span_m * 1.5
    return max(floor_count * GRID, GRID * 4)
 
 
def draw_2d_plan(scheme_blocks: list, scheme_label: str = "",
                 span_str: str = "M", roof_type: str = "flat",
                 ax=None) -> plt.Figure:
    """生成 2D 平面配置示意圖"""
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(6, 7))
    else:
        fig = ax.get_figure()
 
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["background"])
 
    span_m = SPAN_MAP.get(span_str, 4.8)
    length_m = get_length_from_blocks(scheme_blocks, span_m)
    W = span_m
    L = length_m
    wt = 0.318  # 牆板厚度
 
    # ── 網格 ──
    for x in np.arange(0, W + GRID, GRID):
        ax.axvline(x, color=COLORS["grid"], lw=0.3, alpha=0.4)
    for y in np.arange(0, L + GRID, GRID):
        ax.axhline(y, color=COLORS["grid"], lw=0.3, alpha=0.4)
 
    # ── 樓板底盤 ──
    ax.add_patch(patches.FancyBboxPatch(
        (0, 0), W, L,
        boxstyle="round,pad=0.02",
        linewidth=1.5, edgecolor=COLORS["roof_flat"],
        facecolor=COLORS["floor"], alpha=0.25
    ))
 
    # ── 四面外牆 ──
    wall_rects = [
        (0, 0, wt, L),
        (W - wt, 0, wt, L),
        (0, 0, W, wt),
        (0, L - wt, W, wt),
    ]
    for wx, wy, ww, wh in wall_rects:
        ax.add_patch(patches.Rectangle(
            (wx, wy), ww, wh,
            linewidth=0.8, edgecolor="#2C4A5A",
            facecolor=COLORS["wall"], alpha=0.9
        ))
 
    # ── 轉角標記 ──
    cs = 0.25
    for cx, cy in [(0,0),(W-cs,0),(0,L-cs),(W-cs,L-cs)]:
        ax.add_patch(patches.Rectangle(
            (cx, cy), cs, cs,
            linewidth=0.8, edgecolor="#1A3A4A",
            facecolor=COLORS["corner"], alpha=0.95
        ))
 
    # ── 開口（門窗）──
    opening_blocks = [b for b in scheme_blocks if b.get("category") == "window"]
    opening_count  = len(opening_blocks)
 
    # 門（南面中央）
    door_w = 1.2
    dx = (W - door_w) / 2
    ax.add_patch(patches.Rectangle(
        (dx, 0), door_w, wt,
        linewidth=1, edgecolor="#1A5276",
        facecolor=COLORS["door"], alpha=0.95
    ))
    ax.text(dx + door_w/2, wt/2, "門",
            ha="center", va="center", fontsize=5,
            color=COLORS["background"], fontweight="bold")
 
    # 其餘開口：東西牆
    remaining = max(0, opening_count - 1)
    if remaining > 0:
        win_h = 0.9
        step = L / (remaining + 1)
        for i in range(remaining):
            wy = (i + 1) * step
            wy = max(wt + 0.1, min(L - wt - win_h - 0.1, wy))
            ax.add_patch(patches.Rectangle(
                (0, wy), wt, win_h,
                linewidth=0.8, edgecolor="#1A5276",
                facecolor=COLORS["window"], alpha=0.9
            ))
 
    # ── 屋頂類型標注 ──
    roof_label = ROOF_LABELS.get(roof_type, roof_type)
    ax.text(W/2, L + 0.1, roof_label,
            ha="center", va="bottom", fontsize=7,
            color=COLORS["roof_flat"], style="italic")
 
    # ── 尺寸標注 ──
    ax.annotate("", xy=(W, -0.35), xytext=(0, -0.35),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dimension"], lw=1))
    ax.text(W/2, -0.5, f"{W:.1f}m",
            ha="center", va="center", fontsize=7, color=COLORS["dimension"])
 
    ax.annotate("", xy=(-0.35, L), xytext=(-0.35, 0),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dimension"], lw=1))
    ax.text(-0.55, L/2, f"{L:.1f}m",
            ha="center", va="center", fontsize=7,
            color=COLORS["dimension"], rotation=90)
 
    # ── 面積標注 ──
    area = round(W * L, 1)
    floor_n   = len([b for b in scheme_blocks if b.get("category") in ["floor","end"]])
    wall_n    = len([b for b in scheme_blocks if b.get("category") in ["wall","corner"]])
    opening_n = len([b for b in scheme_blocks if b.get("category") == "window"])
    info = f"{area} m²  |  樓板:{floor_n}  牆:{wall_n}  開口:{opening_n}"
    ax.text(W/2, L + 0.3, info,
            ha="center", va="bottom", fontsize=6, color="#AAAAAA")
 
    if scheme_label:
        ax.set_title(scheme_label, color=COLORS["text"],
                     fontsize=9, fontweight="bold", pad=6)
 
    ax.set_xlim(-0.8, W + 0.5)
    ax.set_ylim(-0.8, L + 0.6)
    ax.set_aspect("equal")
    ax.axis("off")
 
    if standalone:
        plt.tight_layout()
    return fig
 
 
def draw_isometric(scheme_blocks: list, scheme_label: str = "",
                   roof_type: str = "flat", span_str: str = "M",
                   ax=None) -> plt.Figure:
    """生成等角示意圖，根據屋頂類型顯示不同形態"""
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(6, 7))
    else:
        fig = ax.get_figure()
 
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["background"])
 
    span_m   = SPAN_MAP.get(span_str, 4.8)
    length_m = get_length_from_blocks(scheme_blocks, span_m)
    W = span_m
    L = length_m
 
    # 牆高依系列判斷
    wall_h = 2.4
    for b in scheme_blocks:
        name = (b.get("name") or "").upper()
        if "WALL-L" in name:  wall_h = 2.7; break
        if "WALL-XL" in name: wall_h = 3.0; break
 
    def iso(x, y, z):
        """3D → 等角 2D"""
        ix = (x - y) * np.cos(np.radians(30))
        iy = (x + y) * np.sin(np.radians(30)) + z
        return ix, iy
 
    # ── 地板面 ──
    fp = [iso(0,0,0), iso(W,0,0), iso(W,L,0), iso(0,L,0)]
    ax.add_patch(plt.Polygon(fp, closed=True,
                              facecolor=COLORS["floor"],
                              edgecolor="#8FA36B", alpha=0.4, lw=1))
 
    # ── 前牆（南面）──
    fw = [iso(0,0,0), iso(W,0,0), iso(W,0,wall_h), iso(0,0,wall_h)]
    ax.add_patch(plt.Polygon(fw, closed=True,
                              facecolor=COLORS["wall"],
                              edgecolor="#2C4A5A", alpha=0.9, lw=1))
 
    # ── 右牆（東面）──
    rw = [iso(W,0,0), iso(W,L,0), iso(W,L,wall_h), iso(W,0,wall_h)]
    ax.add_patch(plt.Polygon(rw, closed=True,
                              facecolor="#4A6F82",
                              edgecolor="#2C4A5A", alpha=0.85, lw=1))
 
    # ── 屋頂（依類型）──
    roof_color = COLORS.get(f"roof_{roof_type.split('_')[0]}", COLORS["roof_flat"])
 
    if roof_type == "gable_42deg":
        # 山牆屋頂：兩坡 + 山牆三角形
        ridge_extra = W / 2 * np.tan(np.radians(42))
        ridge_h = wall_h + ridge_extra
 
        # 前坡
        front_roof = [
            iso(0, 0, wall_h), iso(W, 0, wall_h),
            iso(W/2, 0, ridge_h)
        ]
        ax.add_patch(plt.Polygon(front_roof, closed=True,
                                  facecolor=COLORS["roof_gable"],
                                  edgecolor="#2C4A5A", alpha=0.9, lw=1))
 
        # 左坡面
        left_roof = [
            iso(0, 0, wall_h), iso(W/2, 0, ridge_h),
            iso(W/2, L, ridge_h), iso(0, L, wall_h)
        ]
        ax.add_patch(plt.Polygon(left_roof, closed=True,
                                  facecolor=COLORS["roof_gable"],
                                  edgecolor="#2C4A5A", alpha=0.85, lw=1.2))
 
        # 右坡面
        right_roof = [
            iso(W, 0, wall_h), iso(W/2, 0, ridge_h),
            iso(W/2, L, ridge_h), iso(W, L, wall_h)
        ]
        ax.add_patch(plt.Polygon(right_roof, closed=True,
                                  facecolor="#3A5B20",
                                  edgecolor="#2C4A5A", alpha=0.85, lw=1.2))
 
        # 脊樑線
        r1x, r1y = iso(W/2, 0, ridge_h)
        r2x, r2y = iso(W/2, L, ridge_h)
        ax.plot([r1x, r2x], [r1y, r2y],
                color="#FFD700", lw=1.5, alpha=0.8, linestyle="--")
 
    elif roof_type == "sloping_10deg":
        # 單坡斜頂：低側 M 高（2.4m）、高側 XL（3.0m）
        high_h = wall_h + W * np.tan(np.radians(10))
        slope_roof = [
            iso(0, 0, wall_h), iso(W, 0, high_h),
            iso(W, L, high_h), iso(0, L, wall_h)
        ]
        ax.add_patch(plt.Polygon(slope_roof, closed=True,
                                  facecolor=COLORS["roof_slope"],
                                  edgecolor="#2C4A5A", alpha=0.88, lw=1.2))
 
        # 高側牆三角形
        high_tri = [
            iso(W, 0, wall_h), iso(W, 0, high_h),
            iso(W, L, high_h), iso(W, L, wall_h)
        ]
        ax.add_patch(plt.Polygon(high_tri, closed=True,
                                  facecolor="#3A5B35",
                                  edgecolor="#2C4A5A", alpha=0.85, lw=1))
 
    else:
        # 平頂
        flat_roof = [
            iso(0, 0, wall_h), iso(W, 0, wall_h),
            iso(W, L, wall_h), iso(0, L, wall_h)
        ]
        ax.add_patch(plt.Polygon(flat_roof, closed=True,
                                  facecolor=COLORS["roof_flat"],
                                  edgecolor="#2C4A5A", alpha=0.85, lw=1.2))
 
    # ── 開口（門）在前牆 ──
    opening_blocks = [b for b in scheme_blocks if b.get("category") == "window"]
    if opening_blocks:
        dw = 1.2
        dh = 2.1
        dx = (W - dw) / 2
        door_pts = [
            iso(dx, 0, 0), iso(dx+dw, 0, 0),
            iso(dx+dw, 0, dh), iso(dx, 0, dh)
        ]
        ax.add_patch(plt.Polygon(door_pts, closed=True,
                                  facecolor=COLORS["door"],
                                  edgecolor="#1A5276", alpha=0.9, lw=1))
 
        # 窗戶（右牆）
        if len(opening_blocks) > 1:
            win_y = L * 0.4
            wpts = [
                iso(W, win_y, 0.9), iso(W, win_y+1.2, 0.9),
                iso(W, win_y+1.2, 1.8), iso(W, win_y, 1.8)
            ]
            ax.add_patch(plt.Polygon(wpts, closed=True,
                                      facecolor=COLORS["window"],
                                      edgecolor="#1A5276", alpha=0.85, lw=0.8))
 
    # ── 跨距標注 ──
    p1x, p1y = iso(0, 0, -0.3)
    p2x, p2y = iso(W, 0, -0.3)
    ax.annotate("", xy=(p2x, p2y), xytext=(p1x, p1y),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dimension"], lw=1))
    mx, my = iso(W/2, 0, -0.3)
    ax.text(mx, my - 0.15, f"跨距 {W:.1f}m",
            ha="center", va="top", fontsize=7, color=COLORS["dimension"])
 
    if scheme_label:
        ax.set_title(scheme_label, color=COLORS["text"],
                     fontsize=9, fontweight="bold", pad=6)
 
    ax.autoscale()
    ax.set_aspect("equal")
    ax.axis("off")
 
    if standalone:
        plt.tight_layout()
    return fig
 
 
def draw_three_schemes(scheme_results: dict) -> plt.Figure:
    """
    並排顯示三個方案的 2D 平面圖 + 等角圖
    2 行 × 3 欄
    """
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.patch.set_facecolor(COLORS["background"])
    fig.suptitle("WikiHouse 三方案配置視覺化",
                 color=COLORS["text"], fontsize=14, fontweight="bold", y=0.98)
 
    scheme_info = {
        "scheme_a": "方案 A｜保守型",
        "scheme_b": "方案 B｜標準型",
        "scheme_c": "方案 C｜進階型",
    }
 
    for col, (key, label) in enumerate(scheme_info.items()):
        sr = scheme_results.get(key, {})
        blks = sr.get("blocks", [])
        span_str  = sr.get("span",  "M")
        roof_type = sr.get("roof",  "flat")
 
        if not blks:
            for row in range(2):
                axes[row][col].set_facecolor(COLORS["background"])
                axes[row][col].text(0.5, 0.5, "無資料",
                                    ha="center", va="center",
                                    color="#666666", fontsize=12,
                                    transform=axes[row][col].transAxes)
                axes[row][col].axis("off")
            continue
 
        roof_label = ROOF_LABELS.get(roof_type, roof_type)
        span_m     = SPAN_MAP.get(span_str, 4.8)
 
        # 第一行：2D 平面圖
        draw_2d_plan(blks,
                     f"{label}\n2D 平面  跨距{span_m}m  {roof_label}",
                     span_str=span_str, roof_type=roof_type,
                     ax=axes[0][col])
 
        # 第二行：等角示意圖
        draw_isometric(blks,
                       f"{label}\n等角示意",
                       roof_type=roof_type, span_str=span_str,
                       ax=axes[1][col])
 
        # 驗證狀態標記
        is_valid = sr.get("is_valid", False)
        status   = "✅ 合法" if is_valid else "❌ 需修正"
        color    = "#4CAF50" if is_valid else "#F44336"
        axes[0][col].text(0.02, 0.98, status,
                          ha="left", va="top", fontsize=8,
                          color=color, fontweight="bold",
                          transform=axes[0][col].transAxes)
 
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig
 