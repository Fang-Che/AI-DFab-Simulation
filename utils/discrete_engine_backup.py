"""
WikiHouse Fabrication-Aware Discrete Aggregation Engine
========================================================
Phase 1：Python 離散集合引擎
版本：v3.0（BoundingBox 實測修正插入點）

插入點規律（從 bbox_analysis.json 實測確認）：
  WALL-M   rot=0  : insert_x = bbox.min.x + 300  (幾何中心)
  WALL-M   rot=90 : insert_y = bbox.min.y + 300  (幾何中心)
  DOOR-M1  rot=0  : insert_x = bbox.max.x        (右邊緣), insert_y = 318
  WINDOW-M2 rot=90: insert_y = bbox.min.y + 600  (幾何中心)
  CORNER  → 移至 Grasshopper 端處理，Python 不輸出
  z 原點在頂部：所有 Block z=0，Grasshopper 端補 +wall_h
"""

import numpy as np
import json
from dataclasses import dataclass, field, asdict
from utils.connection_grammar import (
    ASSEMBLY_ORDER,
    validate_configuration,
)

# ══════════════════════════════════════════════
# 常數定義
# ══════════════════════════════════════════════

GRID = 0.6  # 600mm 網格單元

SPAN_GRIDS = {
    "S":    6,
    "M":    8,
    "L":    9,
    "XS":   5,
    "XXXS": 4,
}

WALL_HEIGHT_GRIDS = {
    "S":  3,
    "M":  4,
    "L":  5,
    "XL": 5,
}

WALL_HEIGHT_MM = {
    "S":  2100,
    "M":  2400,
    "L":  2700,
    "XL": 3000,
}

# ── Block 名稱對應表（對應 .3dm 圍塊定義名稱）──
BLOCK_3DM_NAME = {
    # Floor
    "FLOOR_XXXS": "SKYLARK250_XFLOOR-XXS-0",
    "FLOOR_XXS":  "SKYLARK250_XFLOOR-XXS-0",
    "FLOOR_XS":   "SKYLARK250_XFLOOR-XS-0",
    "FLOOR_S":    "SKYLARK250_XFLOOR-S-0",
    "FLOOR_M":    "SKYLARK250_XFLOOR-M-0",
    "FLOOR_L":    "SKYLARK250_XFLOOR-L-0",
    # End
    "END_S":      "SKYLARK250_END-S-0",
    "END_M":      "SKYLARK250_END-M-0",
    "END_L":      "SKYLARK250_END-L-0",
    "END_XS":     "SKYLARK250_END-XS-0",
    "END_XXS":    "SKYLARK250_END-XXS-0",
    # Wall
    "WALL_S":     "SKYLARK250_WALL-S",
    "WALL_M":     "SKYLARK250_WALL-M",
    "WALL_L":     "SKYLARK250_WALL-L",
    "WALL_XL":    "SKYLARK250_WALL-XL",
    # Corner
    "CORNER_S":   "SKYLARK200_CORNER-S",
    "CORNER_M":   "SKYLARK200_CORNER-M",
    "CORNER_L":   "SKYLARK200_CORNER-L",
    "CORNER_XL":  "SKYLARK200_CORNER-XL",
    # Door
    "DOOR_S1":    "SKYLARK250_DOOR-S1",
    "DOOR_M1":    "SKYLARK250_DOOR-M1",
    "DOOR_M2":    "SKYLARK250_DOOR-M2",
    "DOOR_L1":    "SKYLARK250_DOOR-L1",
    "DOOR_XL1":   "SKYLARK250_DOOR-XL1",
    # Window
    "WINDOW_S1":  "SKYLARK250_WINDOW-S1",
    "WINDOW_M1":  "SKYLARK250_WINDOW-M1",
    "WINDOW_M2":  "SKYLARK250_WINDOW-M2",
    "WINDOW_M3":  "SKYLARK250_WINDOW-M3",
    "WINDOW_M4":  "SKYLARK250_WINDOW-M4",
    "WINDOW_L1":  "SKYLARK250_WINDOW-L1",
    "WINDOW_XL1": "SKYLARK250_WINDOW-XL1",
    # Roof
    "ROOF_S10":   "SKYLARK250_ROOF-S10",
    "ROOF_M10":   "SKYLARK250_ROOF-M10",
    "ROOF_L10":   "SKYLARK250_ROOF-L10",
    "ROOF_XS10":  "SKYLARK250_ROOF-XS10",
    "ROOF_XXS10": "SKYLARK250_ROOF-XXS10",
    "ROOF_S42":   "SKYLARK250_ROOF-S42",
    "ROOF_M42":   "SKYLARK250_ROOF-M42",
    "ROOF_L42":   "SKYLARK250_ROOF-L42",
    # Wall 山牆/斜頂
    "WALL_G42_1": "SKYLARK250_WALL-G42-1",
    "WALL_G42_2": "SKYLARK250_WALL-G42-2",
    "WALL_G42_3": "SKYLARK250_WALL-G42-3",
    "WALL_G42_4": "SKYLARK250_WALL-G42-4",
    "WALL_G42_5": "SKYLARK250_WALL-G42-5R",
    "WALL_G42_6": "SKYLARK250_WALL-G42-6",
    "WALL_S10_1": "SKYLARK250_WALL-S10+1",
    "WALL_S10_2": "SKYLARK250_WALL-S10+2",
    "WALL_S10_3": "SKYLARK250_WALL-S10+3",
    "WALL_S10_4": "SKYLARK250_WALL-S10+4",
    "WALL_S10_5": "SKYLARK250_WALL-S10+5",
    # Bowtie
    "BOWTIE_1":   "SKYLARK250_BOWTIE-1",
    "BOWTIE_2":   "SKYLARK250_BOWTIE-2",
}

BLOCK_CATEGORY = {
    "FLOOR": "floor",
    "END":   "end",
    "WALL":  "wall",
    "CORNER":"corner",
    "DOOR":  "window",
    "WINDOW":"window",
    "ROOF":  "roof",
    "BOWTIE":"connector",
}

# ── Block 插入點偏移表（BoundingBox 實測）──────────
#
# 格點單位 = 600mm
# 每個 Block 的插入點相對於其 bbox.min 的偏移（mm）
#
# WALL-M：插入點在 X/Y 中心 → offset = +300mm = +0.5格
# DOOR-M1：插入點在 X 右邊緣 → offset = +1200mm = +2格（bbox 寬度）
#           y offset = +318mm（門框向內），z offset = -300mm（門檻）
# WINDOW-M2 rot=90：插入點在 Y 中心 → offset = +600mm = +1格
#
# 格式：block_key → (width_mm, insert_offset_mm)
# width_mm       = Block 在排列軸方向的實際寬度
# insert_offset_mm = 插入點 = bbox.min + offset
#
BLOCK_INSERT = {
    # WALL：寬 600mm，插入點在中心 (+300)
    "WALL_S":     {"w": 600,  "off": 300},
    "WALL_M":     {"w": 600,  "off": 300},
    "WALL_L":     {"w": 600,  "off": 300},
    "WALL_XL":    {"w": 600,  "off": 300},
    # DOOR：寬 1200mm，插入點在右邊緣 (+1200)，y=318, z=0
    "DOOR_S1":    {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_M1":    {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_M2":    {"w": 2400, "off": 2400, "y_off": 318, "z_off": -300},
    "DOOR_L1":    {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_XL1":   {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    # WINDOW：寬 1200mm，插入點在中心 (+600)
    "WINDOW_S1":  {"w": 600,  "off": 300, "z_off": -2400},
    "WINDOW_M1":  {"w": 600,  "off": 300, "z_off": -2400},
    "WINDOW_M2":  {"w": 1200, "off": 600, "z_off": -2400},
    "WINDOW_M3":  {"w": 600,  "off": 300, "z_off": -2400},
    "WINDOW_M4":  {"w": 1200, "off": 600, "z_off": -2400},
    "WINDOW_L1":  {"w": 600,  "off": 300, "z_off": -2400},
    "WINDOW_XL1": {"w": 1200, "off": 600, "z_off": -2400},
}

# CORNER 的插入點規律（供 Grasshopper 端參考，Python 不放置）
# CORNER-M：bbox 318×318，插入點在左邊緣+268（即右邊緣內縮50mm）
# y offset = +25mm（咬合槽口）
CORNER_INSERT = {
    "CORNER_S":  {"w": 318, "off": 268, "y_off": 25},
    "CORNER_M":  {"w": 318, "off": 268, "y_off": 25},
    "CORNER_L":  {"w": 318, "off": 268, "y_off": 25},
    "CORNER_XL": {"w": 318, "off": 268, "y_off": 25},
}


# ══════════════════════════════════════════════
# 資料結構
# ══════════════════════════════════════════════

@dataclass
class GridPosition:
    """座標單位為 mm（v3.0 起直接儲存 mm）"""
    x: int
    y: int
    z: int

    def to_mm(self):
        return {"x_mm": self.x, "y_mm": self.y, "z_mm": self.z}

    def to_m(self):
        return {
            "x_m": round(self.x / 1000, 3),
            "y_m": round(self.y / 1000, 3),
            "z_m": round(self.z / 1000, 3),
        }


@dataclass
class PlacedBlock:
    block_id:  str
    category:  str
    series:    str
    name:      str
    position:  GridPosition   # x, y, z 單位為 mm
    rotation:  int = 0
    face:      str = ""
    wall_height_mm: int = 2400

    def to_dict(self):
        return {
            "block_id":       self.block_id,
            "category":       self.category,
            "series":         self.series,
            "name":           self.name,
            "position_mm":    self.position.to_mm(),
            "position_m":     self.position.to_m(),
            "rotation":       self.rotation,
            "face":           self.face,
            "wall_height_mm": self.wall_height_mm,
        }


@dataclass
class TargetVolume:
    shape:    str
    grids_x:  int
    grids_y:  int
    grids_z:  int
    voxels:   set = field(default_factory=set)

    def contains(self, x, y, z) -> bool:
        return (x, y, z) in self.voxels


# ══════════════════════════════════════════════
# 形體生成器（不變）
# ══════════════════════════════════════════════

def make_rectangle(span_str, length_grids, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    gy = length_grids
    gz = height_grids
    voxels = {(x, y, z) for x in range(gx) for y in range(gy) for z in range(gz)}
    return TargetVolume(shape="rectangle", grids_x=gx, grids_y=gy, grids_z=gz, voxels=voxels)


def make_L_shape(span_str, length_grids, wing_grids_x, wing_grids_y, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    gy = length_grids
    gz = height_grids
    total_x = gx + wing_grids_x
    total_y = max(gy, wing_grids_y)
    voxels = set()
    for x in range(gx):
        for y in range(gy):
            for z in range(gz):
                voxels.add((x, y, z))
    for x in range(gx, total_x):
        for y in range(wing_grids_y):
            for z in range(gz):
                voxels.add((x, y, z))
    return TargetVolume(shape="L", grids_x=total_x, grids_y=total_y, grids_z=gz, voxels=voxels)


def make_U_shape(span_str, length_grids, court_grids_x, court_grids_y, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    gy = length_grids
    gz = height_grids
    voxels = set()
    cx0 = (gx - court_grids_x) // 2
    cx1 = cx0 + court_grids_x
    cy0 = gy - court_grids_y
    for x in range(gx):
        for y in range(gy):
            for z in range(gz):
                if not (cx0 <= x < cx1 and y >= cy0):
                    voxels.add((x, y, z))
    return TargetVolume(shape="U", grids_x=gx, grids_y=gy, grids_z=gz, voxels=voxels)


def make_arch(span_grids, length_grids, arch_height_grids):
    gx = span_grids
    gy = length_grids
    gz = arch_height_grids
    cx = gx / 2
    r  = gx / 2
    voxels = set()
    for x in range(gx):
        for y in range(gy):
            for z in range(gz):
                dist = ((x + 0.5 - cx) ** 2 + (z + 0.5) ** 2) ** 0.5
                if dist <= r:
                    inner_r = r - 2
                    inner_dist = ((x + 0.5 - cx) ** 2 + (z + 0.5) ** 2) ** 0.5
                    if inner_dist >= inner_r or z == 0:
                        voxels.add((x, y, z))
    return TargetVolume(shape="arch", grids_x=gx, grids_y=gy, grids_z=gz, voxels=voxels)


def make_cross(span_str, arm_length, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    gy = gx
    gz = height_grids
    total_x = gx + arm_length * 2
    total_y = gy + arm_length * 2
    cx0, cx1 = arm_length, arm_length + gx
    cy0, cy1 = arm_length, arm_length + gy
    voxels = set()
    for x in range(total_x):
        for y in range(total_y):
            for z in range(gz):
                if (cx0 <= x < cx1) or (cy0 <= y < cy1):
                    voxels.add((x, y, z))
    return TargetVolume(shape="cross", grids_x=total_x, grids_y=total_y, grids_z=gz, voxels=voxels)


# ══════════════════════════════════════════════
# 離散集合引擎核心
# ══════════════════════════════════════════════

class DiscreteAggregationEngine:

    def __init__(self, series="skylark250", span_str="M",
                 wall_height_str="M", roof_type="flat"):
        self.series          = series
        self.span_str        = span_str
        self.wall_height_str = wall_height_str
        self.roof_type       = roof_type
        self.span_grids      = SPAN_GRIDS.get(span_str, 8)
        self.wall_h_grids    = WALL_HEIGHT_GRIDS.get(wall_height_str, 4)
        self.wall_h_mm       = WALL_HEIGHT_MM.get(wall_height_str, 2400)
        self.placed_blocks:  list = []

    def _get_3dm_name(self, key):
        return BLOCK_3DM_NAME.get(key, key)

    def _get_category(self, key):
        prefix = key.split("_")[0]
        return BLOCK_CATEGORY.get(prefix, "other")

    def _add_block_mm(self, key, x_mm, y_mm, z_mm=0, rotation=0, face=""):
        """直接用 mm 座標放置 Block"""
        block_id = self._get_3dm_name(key)
        category = self._get_category(key)
        name     = block_id.replace("SKYLARK250_", "").replace("SKYLARK200_", "")
        self.placed_blocks.append(PlacedBlock(
            block_id=block_id,
            category=category,
            series=self.series,
            name=name,
            position=GridPosition(int(x_mm), int(y_mm), int(z_mm)),
            rotation=rotation,
            face=face,
            wall_height_mm=self.wall_h_mm,
        ))

    def generate(self, target):
        self.placed_blocks = []
        self._place_floor(target)
        self._place_walls(target)
        self._place_roof(target)

        bom = self._generate_bom()
        validation_input = [
            {"id": b.block_id, "name": b.name,
             "category": b.category, "series": b.series}
            for b in self.placed_blocks
        ]
        validation = validate_configuration(validation_input, stories=1)

        return {
            "placed_blocks": [b.to_dict() for b in self.placed_blocks],
            "bom":           bom,
            "validation":    validation,
            "target_shape":  target.shape,
            "dimensions": {
                "grids_x":  target.grids_x,
                "grids_y":  target.grids_y,
                "grids_z":  target.grids_z,
                "width_m":  round(target.grids_x * GRID, 2),
                "length_m": round(target.grids_y * GRID, 2),
                "height_m": round(target.grids_z * GRID, 2),
            },
            "config": {
                "series":      self.series,
                "span":        self.span_str,
                "wall_height": self.wall_height_str,
                "roof_type":   self.roof_type,
            }
        }

    def _place_floor(self, target):
        """Step 1：樓板底盤（XFLOOR + END）"""
        gx = target.grids_x
        gy = target.grids_y
        s  = self.span_str
        floor_key = f"FLOOR_{s}"
        end_key   = f"END_{s}"
        for y in range(gy):
            if any(target.contains(x, y, 0) for x in range(gx)):
                y_mm = y * 600
                if y == 0 or y == gy - 1:
                    self._add_block_mm(end_key, 0, y_mm, 0, face="floor")
                else:
                    self._add_block_mm(floor_key, 0, y_mm, 0, face="floor")

    def _place_walls(self, target):
        """
        Step 2：外牆（v3.0）
        ─────────────────────────────────────────────────
        插入點規律（BoundingBox 實測確認）：
          WALL rot=0  : insert_x = bbox.min.x + 300（幾何中心）
          WALL rot=90 : insert_y = bbox.min.y + 300（幾何中心）
          DOOR rot=0  : insert_x = bbox.max.x（右邊緣）, y=+318, z=-300
          WINDOW rot=90: insert_y = bbox.min.y + 600（中心）
          CORNER      → 不輸出，由 Grasshopper 端處理
        ─────────────────────────────────────────────────
        牆面起始 x=318（CORNER 寬度），結束 x=gx*600-318
        """
        gx = target.grids_x
        gy = target.grids_y
        wh = self.wall_height_str

        wall_key = f"WALL_{wh}"
        door_key = f"DOOR_{wh}1"
        win_key  = f"WINDOW_{wh}2"

        CORNER_W = 318   # CORNER 佔用寬度 mm
        WALL_W   = 600
        DOOR_W   = BLOCK_INSERT.get(door_key, {}).get("w", 1200)
        WIN_W    = BLOCK_INSERT.get(win_key,  {}).get("w", 1200)

        # ── 沿 X 軸排列（南/北面）────────────────────
        def place_x(y_mm, rotation, face, opening_key=None, opening_w=0):
            total_x = gx * 600
            x = CORNER_W
            end_x = total_x - CORNER_W
            inner_w = end_x - x

            # 開口置中位置（對齊 600mm）
            if opening_key and opening_w:
                o_left = x + ((inner_w - opening_w) // 2 // 600) * 600
            else:
                o_left = -1

            op_placed = False
            while x < end_x:
                rem = end_x - x
                # 嘗試放開口
                if opening_key and not op_placed and x >= o_left and rem >= opening_w:
                    info = BLOCK_INSERT.get(opening_key, {})
                    ix = x + info.get("off", opening_w)
                    iy = y_mm + info.get("y_off", 0)
                    iz = info.get("z_off", 0)
                    self._add_block_mm(opening_key, ix, iy, iz,
                                       rotation=rotation, face=face)
                    x += opening_w
                    op_placed = True
                elif rem >= WALL_W:
                    self._add_block_mm(wall_key, x + 300, y_mm, -self.wall_h_mm,
                                       rotation=rotation, face=face)
                    x += WALL_W
                else:
                    break

        # ── 沿 Y 軸排列（東/西面）────────────────────
        def place_y(x_mm, rotation, face, opening_key=None, opening_w=0, n_openings=1):
            total_y = gy * 600
            y = CORNER_W
            end_y = total_y - CORNER_W
            inner_h = end_y - y

            # 開口位置列表
            op_starts = []
            if opening_key and opening_w:
                if n_openings == 1:
                    op_starts = [y + ((inner_h - opening_w) // 2 // 600) * 600]
                elif n_openings == 2:
                    seg = inner_h // 3
                    op_starts = [
                        y + ((seg - opening_w // 2) // 600) * 600,
                        y + ((seg * 2 - opening_w // 2) // 600) * 600,
                    ]

            placed = set()
            while y < end_y:
                rem = end_y - y
                did_op = False
                for os in op_starts:
                    if os not in placed and y >= os and rem >= opening_w:
                        info = BLOCK_INSERT.get(opening_key, {})
                        iy = y + info.get("off", opening_w // 2)
                        info = BLOCK_INSERT.get(opening_key, {})
                        iz = info.get("z_off", -self.wall_h_mm)
                        self._add_block_mm(opening_key, x_mm, iy, iz,
                                           rotation=rotation, face=face)
                        y += opening_w
                        placed.add(os)
                        did_op = True
                        break
                if not did_op:
                    if rem >= WALL_W:
                        self._add_block_mm(wall_key, x_mm, y + 300, -self.wall_h_mm,
                                           rotation=rotation, face=face)
                        y += WALL_W
                    else:
                        break

        total_x_mm = gx * 600
        total_y_mm = gy * 600

        # 南面（y=0，有 DOOR）
        place_x(0, rotation=0, face="south",
                opening_key=door_key, opening_w=DOOR_W)

        # 北面（y=total_y，有 WINDOW）
        place_x(total_y_mm, rotation=180, face="north",
                opening_key=win_key, opening_w=WIN_W)

        # 西面（x=0）
        place_y(0, rotation=270, face="west")

        # 東面（x=total_x，有 WINDOW×2）
        place_y(total_x_mm, rotation=90, face="east",
                opening_key=win_key, opening_w=WIN_W, n_openings=2)

        # ── 四個角落 CORNER ──
        corner_key = f"CORNER_{wh}"
        corner_z   = -self.wall_h_mm
        OFF = 25
        CW  = 318

        OFF_A = 268
        OFF_B = 25
        OFF_C = 586
        OFF_D = 832

        self._add_block_mm(corner_key, OFF_A,                OFF_B,                corner_z, rotation=0,   face="corner")  # 左下
        self._add_block_mm(corner_key, total_x_mm - OFF_C,   OFF_A,                corner_z, rotation=90,  face="corner")  # 右下
        self._add_block_mm(corner_key, total_x_mm - OFF_D,   total_y_mm - OFF_C,   corner_z, rotation=180, face="corner")  # 右上
        self._add_block_mm(corner_key, OFF_B,                total_y_mm - OFF_D,   corner_z, rotation=270, face="corner")  # 左上

        # ── L/U/Cross 內部邊界 ──
        if target.shape in ["L", "U", "cross"]:
            for gxi in range(target.grids_x):
                for gyi in range(target.grids_y):
                    if not target.contains(gxi, gyi, 0):
                        continue
                    x_mm = gxi * 600
                    y_mm = gyi * 600
                    if not target.contains(gxi + 1, gyi, 0):
                        self._add_block_mm(wall_key, x_mm + 600, y_mm + 300, 0,
                                           rotation=90, face="east_inner")
                    if not target.contains(gxi, gyi + 1, 0):
                        self._add_block_mm(wall_key, x_mm + 300, y_mm + 600, 0,
                                           rotation=180, face="north_inner")

    def _place_roof(self, target):
        """Step 3：屋頂"""
        gx = target.grids_x
        gy = target.grids_y
        s  = self.span_str
        roof_key = f"ROOF_{s}42" if self.roof_type == "gable_42deg" else f"ROOF_{s}10"
        for y in range(gy):
            if any(target.contains(x, y, 0) for x in range(gx)):
                self._add_block_mm(roof_key, 0, y * 600, 0, face="top")

    def _generate_bom(self):
        count_map = {}
        for b in self.placed_blocks:
            key = (b.block_id, b.category, b.series, b.name)
            count_map[key] = count_map.get(key, 0) + 1
        bom = []
        for (block_id, category, series, name), qty in sorted(count_map.items()):
            bom.append({
                "block_id": block_id,
                "category": category,
                "series":   series,
                "name":     name,
                "quantity": qty,
                "assembly_step": ASSEMBLY_ORDER.get(category, {}).get("step", 99),
            })
        bom.sort(key=lambda x: x["assembly_step"])
        return bom


# ══════════════════════════════════════════════
# 便利介面函數
# ══════════════════════════════════════════════

def generate_from_requirements(
    shape="rectangle", area_sqm=50.0, series="skylark250",
    span_str="M", wall_height_str="M", roof_type="flat",
    stories=1, **kwargs
):
    engine = DiscreteAggregationEngine(
        series=series, span_str=span_str,
        wall_height_str=wall_height_str, roof_type=roof_type,
    )
    span_m = {"S": 3.6, "XS": 3.0, "XXXS": 2.4, "M": 4.8, "L": 5.4}.get(span_str, 4.8)
    length_grids = max(4, round((area_sqm / span_m) / 0.6))
    height_grids = {"S": 3, "M": 4, "L": 5, "XL": 5}.get(wall_height_str, 4)

    if shape == "rectangle":
        target = make_rectangle(span_str, length_grids, height_grids)
    elif shape == "L":
        target = make_L_shape(span_str, length_grids,
                               kwargs.get("wing_grids_x", SPAN_GRIDS.get(span_str, 8) // 2),
                               kwargs.get("wing_grids_y", length_grids // 2),
                               height_grids)
    elif shape == "U":
        target = make_U_shape(span_str, length_grids,
                               kwargs.get("court_grids_x", SPAN_GRIDS.get(span_str, 8) // 2),
                               kwargs.get("court_grids_y", length_grids // 3),
                               height_grids)
    elif shape == "arch":
        target = make_arch(SPAN_GRIDS.get(span_str, 8), length_grids,
                           kwargs.get("arch_height_grids", SPAN_GRIDS.get(span_str, 8) // 2))
    elif shape == "cross":
        target = make_cross(span_str, kwargs.get("arm_length", 4), height_grids)
    else:
        target = make_rectangle(span_str, length_grids, height_grids)

    return engine.generate(target)


def generate_three_schemes(area_sqm=50.0, series="skylark250"):
    schemes = {}
    configs = [
        ("scheme_a", "S",  "M", "flat",         "方案 A｜保守型", "窄長形、平頂、跨距 3.6m"),
        ("scheme_b", "M",  "M", "sloping_10deg", "方案 B｜標準型", "正方形、斜頂 10°、跨距 4.8m"),
        ("scheme_c", "M",  "M", "gable_42deg",   "方案 C｜進階型", "寬短形、山牆 42°、跨距 4.8m"),
    ]
    for key, span, wh, roof, label, desc in configs:
        result = generate_from_requirements(
            shape="rectangle", area_sqm=area_sqm,
            series=series, span_str=span,
            wall_height_str=wh, roof_type=roof,
        )
        result["label"]       = label
        result["description"] = desc
        result["span"]        = span
        result["roof"]        = roof
        schemes[key] = result
    return schemes


# ══════════════════════════════════════════════
# 測試
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=== 測試一：矩形 50m²（SK250 M 跨距 平頂）===")
    result = generate_from_requirements(
        shape="rectangle", area_sqm=50,
        series="skylark250", span_str="M",
        wall_height_str="M", roof_type="flat",
    )
    print(f"尺寸：{result['dimensions']['width_m']}m × {result['dimensions']['length_m']}m")
    print(f"總 Block 數：{len(result['placed_blocks'])}")
    print(f"Grammar 驗證：{'✅' if result['validation']['is_valid'] else '❌'}")

    # 驗證 DOOR/WINDOW 沒有和 WALL 重疊
    print("\n=== DOOR/WINDOW 位置驗證 ===")
    wall_positions = set()
    for b in result["placed_blocks"]:
        if b["category"] == "wall" and b["face"] == "south":
            wall_positions.add(b["position_mm"]["x_mm"])

    for b in result["placed_blocks"]:
        if b["name"].startswith("DOOR") or b["name"].startswith("WINDOW"):
            print(f"  {b['block_id']} @ x={b['position_mm']['x_mm']}mm "
                  f"face={b['face']} rotation={b['rotation']}")

    print(f"\n南面 WALL x 位置：{sorted(wall_positions)}")

    print("\n=== 測試四：三方案生成 ===")
    three = generate_three_schemes(area_sqm=50, series="skylark250")
    for key, scheme in three.items():
        valid     = scheme['validation']['is_valid']
        bom_count = sum(b['quantity'] for b in scheme['bom'])
        print(f"  {scheme['label']}：{bom_count} 個 Block，{'✅' if valid else '❌'}")