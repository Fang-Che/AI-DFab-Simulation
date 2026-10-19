"""
WikiHouse Fabrication-Aware Discrete Aggregation Engine
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional
from utils.connection_grammar import ASSEMBLY_ORDER, validate_configuration

GRID = 0.6
SPAN_GRIDS        = {"S": 6, "M": 8, "L": 9, "XS": 5, "XXXS": 4}
WALL_HEIGHT_MM    = {"S": 2100, "M": 2400, "L": 2700, "XL": 3000}
WALL_HEIGHT_GRIDS = {"S": 3, "M": 4, "L": 5, "XL": 5}

CATEGORY_COLOR = {
    "wall": "#2255CC", "window": "#22AA77", "door": "#DDAA22",
    "corner": "#CC2222", "floor": "#888888", "end": "#888888",
    "roof": "#AAAAAA", "connector": "#FFFFFF",
    "filler": "#FF66AA", "partition": "#FF8C42",
}

BLOCK_3DM_NAME = {
    "FLOOR_XXXS": "SKYLARK250_XFLOOR-XXS-0", "FLOOR_XXS": "SKYLARK250_XFLOOR-XXS-0",
    "FLOOR_XS": "SKYLARK250_XFLOOR-XS-0", "FLOOR_S": "SKYLARK250_XFLOOR-S-0",
    "FLOOR_M": "SKYLARK250_XFLOOR-M-0", "FLOOR_L": "SKYLARK250_XFLOOR-L-0",
    "END_S": "SKYLARK250_END-S-0", "END_M": "SKYLARK250_END-M-0",
    "END_L": "SKYLARK250_END-L-0", "END_XS": "SKYLARK250_END-XS-0",
    "END_XXS": "SKYLARK250_END-XXS-0",
    "WALL_S": "SKYLARK250_WALL-S", "WALL_M": "SKYLARK250_WALL-M",
    "WALL_L": "SKYLARK250_WALL-L", "WALL_XL": "SKYLARK250_WALL-XL",
    "CORNER_S": "SKYLARK200_CORNER-S", "CORNER_M": "SKYLARK200_CORNER-M",
    "CORNER_L": "SKYLARK200_CORNER-L", "CORNER_XL": "SKYLARK200_CORNER-XL",
    "DOOR_S1": "SKYLARK250_DOOR-S1", "DOOR_M1": "SKYLARK250_DOOR-M1",
    "DOOR_M2": "SKYLARK250_DOOR-M2", "DOOR_L1": "SKYLARK250_DOOR-L1",
    "DOOR_XL1": "SKYLARK250_DOOR-XL1",
    "WINDOW_S1": "SKYLARK250_WINDOW-S1", "WINDOW_M1": "SKYLARK250_WINDOW-M1",
    "WINDOW_M2": "SKYLARK250_WINDOW-M2", "WINDOW_M3": "SKYLARK250_WINDOW-M3",
    "WINDOW_M4": "SKYLARK250_WINDOW-M4", "WINDOW_L1": "SKYLARK250_WINDOW-L1",
    "WINDOW_XL1": "SKYLARK250_WINDOW-XL1",
    "ROOF_S10": "SKYLARK250_ROOF-S10", "ROOF_M10": "SKYLARK250_ROOF-M10",
    "ROOF_L10": "SKYLARK250_ROOF-L10", "ROOF_XS10": "SKYLARK250_ROOF-XS10",
    "ROOF_XXS10": "SKYLARK250_ROOF-XXS10", "ROOF_S42": "SKYLARK250_ROOF-S42",
    "ROOF_M42": "SKYLARK250_ROOF-M42", "ROOF_L42": "SKYLARK250_ROOF-L42",
    "WALL_G42_1": "SKYLARK250_WALL-G42-1", "WALL_G42_5": "SKYLARK250_WALL-G42-5R",
    "BOWTIE_1": "SKYLARK250_BOWTIE-1", "BOWTIE_2": "SKYLARK250_BOWTIE-2",
    "FILLER_EW": "WIKIHOUSE_FILLER-EW",
    "FILLER_NS": "WIKIHOUSE_FILLER-NS",
}

BLOCK_CATEGORY = {
    "FLOOR": "floor", "END": "end", "WALL": "wall", "CORNER": "corner",
    "DOOR": "door", "WINDOW": "window", "ROOF": "roof", "BOWTIE": "connector",
    "PARTITION": "partition", "FILLER": "filler",
}

BLOCK_INSERT = {
    "WALL_S":  {"w": 600,  "off": 300},
    "WALL_M":  {"w": 600,  "off": 300},
    "WALL_L":  {"w": 600,  "off": 300},
    "WALL_XL": {"w": 600,  "off": 300},
    "DOOR_S1":  {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_M1":  {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_M2":  {"w": 2400, "off": 2400, "y_off": 318, "z_off": -300},
    "DOOR_L1":  {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "DOOR_XL1": {"w": 1200, "off": 1200, "y_off": 318, "z_off": -300},
    "WINDOW_S1":  {"w": 600,  "off": 300,  "z_off": -2400},
    "WINDOW_M1":  {"w": 600,  "off": 300,  "z_off": -2400},
    "WINDOW_M2":  {"w": 1200, "off": 600,  "z_off": -2400},
    "WINDOW_M3":  {"w": 600,  "off": 300,  "z_off": -2400},
    "WINDOW_M4":  {"w": 1200, "off": 600,  "z_off": -2400},
    "WINDOW_L1":  {"w": 600,  "off": 300,  "z_off": -2400},
    "WINDOW_XL1": {"w": 1200, "off": 600,  "z_off": -2400},
}

CORNER_OFFSET = {
    0:   (+268, +25),
    90:  (-25,  +268),
    180: (-268, -25),
    270: (+25,  -268),
}


@dataclass
class OpeningSpec:
    type:     str
    position: str

@dataclass
class FaceConfig:
    openings: List[OpeningSpec] = field(default_factory=list)
    @classmethod
    def default_south(cls): return cls(openings=[OpeningSpec("door", "center")])
    @classmethod
    def default_north(cls): return cls(openings=[OpeningSpec("window", "center")])
    @classmethod
    def default_east(cls): return cls(openings=[OpeningSpec("window","left"),OpeningSpec("window","right")])
    @classmethod
    def default_west(cls): return cls(openings=[])
    @classmethod
    def empty(cls): return cls(openings=[])

@dataclass
class WallOpeningConfig:
    south: FaceConfig = field(default_factory=FaceConfig.default_south)
    north: FaceConfig = field(default_factory=FaceConfig.default_north)
    east:  FaceConfig = field(default_factory=FaceConfig.default_east)
    west:  FaceConfig = field(default_factory=FaceConfig.default_west)
    @classmethod
    def default(cls):
        return cls(south=FaceConfig.default_south(), north=FaceConfig.default_north(),
                   east=FaceConfig.default_east(),  west=FaceConfig.default_west())
    def get(self, face: str) -> FaceConfig:
        return getattr(self, face, FaceConfig.empty())

@dataclass
class PartitionConfig:
    direction:      str
    position_grids: int
    label:          str = ""
    openings:       List[OpeningSpec] = field(default_factory=list)

@dataclass
class GridPosition:
    x: int; y: int; z: int
    def to_mm(self): return {"x_mm": self.x, "y_mm": self.y, "z_mm": self.z}
    def to_m(self): return {"x_m": round(self.x/1000,3), "y_m": round(self.y/1000,3), "z_m": round(self.z/1000,3)}

@dataclass
class PlacedBlock:
    block_id: str; category: str; series: str; name: str
    position: GridPosition; rotation: int = 0; face: str = ""
    wall_height_mm: int = 2400; color: str = ""
    def to_dict(self):
        return {"block_id": self.block_id, "category": self.category, "series": self.series,
                "name": self.name, "position_mm": self.position.to_mm(),
                "position_m": self.position.to_m(), "rotation": self.rotation,
                "face": self.face, "wall_height_mm": self.wall_height_mm, "color": self.color}

@dataclass
class TargetVolume:
    shape: str; grids_x: int; grids_y: int; grids_z: int
    voxels: set = field(default_factory=set)
    def contains(self, x, y, z) -> bool: return (x, y, z) in self.voxels

def make_rectangle(span_str, length_grids, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    voxels = {(x,y,z) for x in range(gx) for y in range(length_grids) for z in range(height_grids)}
    return TargetVolume("rectangle", gx, length_grids, height_grids, voxels)

def make_L_shape(span_str, length_grids, wing_grids_x, wing_grids_y, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8)
    total_x = gx + wing_grids_x
    total_y = max(length_grids, wing_grids_y)
    voxels = set()
    for x in range(gx):
        for y in range(length_grids):
            for z in range(height_grids): voxels.add((x,y,z))
    for x in range(gx, total_x):
        for y in range(wing_grids_y):
            for z in range(height_grids): voxels.add((x,y,z))
    return TargetVolume("L", total_x, total_y, height_grids, voxels)

def make_U_shape(span_str, length_grids, court_grids_x, court_grids_y, height_grids,
                 total_grids_x=None):
    """
    total_grids_x: 整體東西向格數，預設等於 SPAN_GRIDS[span_str]
                   設定大於 span_grids 可做出寬扁 U 型
    院落置中，挖掉上方（北端）court_grids_y 格深、court_grids_x 格寬
    """
    gx = total_grids_x if total_grids_x else SPAN_GRIDS.get(span_str, 8)
    cx0 = (gx - court_grids_x) // 2; cx1 = cx0 + court_grids_x
    cy0 = length_grids - court_grids_y
    voxels = set()
    for x in range(gx):
        for y in range(length_grids):
            for z in range(height_grids):
                if not (cx0 <= x < cx1 and y >= cy0): voxels.add((x,y,z))
    return TargetVolume("U", gx, length_grids, height_grids, voxels)

def make_cross(span_str, arm_length, height_grids):
    gx = SPAN_GRIDS.get(span_str, 8); total = gx + arm_length * 2
    cx0, cx1 = arm_length, arm_length + gx
    voxels = {(x,y,z) for x in range(total) for y in range(total) for z in range(height_grids)
              if (cx0 <= x < cx1) or (cx0 <= y < cx1)}
    return TargetVolume("cross", total, total, height_grids, voxels)


class DiscreteAggregationEngine:
    def __init__(self, series="skylark250", span_str="M", wall_height_str="M", roof_type="flat"):
        self.series = series; self.span_str = span_str
        self.wall_height_str = wall_height_str; self.roof_type = roof_type
        self.span_grids = SPAN_GRIDS.get(span_str, 8)
        self.wall_h_grids = WALL_HEIGHT_GRIDS.get(wall_height_str, 4)
        self.wall_h_mm = WALL_HEIGHT_MM.get(wall_height_str, 2400)
        self.placed_blocks = []; self.warnings = []

    def _get_3dm_name(self, key): return BLOCK_3DM_NAME.get(key, key)
    def _get_category(self, key): return BLOCK_CATEGORY.get(key.split("_")[0], "other")
    def _get_color(self, key, category):
        if "DOOR" in key: return CATEGORY_COLOR["door"]
        return CATEGORY_COLOR.get(category, "#FFFFFF")

    def _add(self, key, x, y, z=0, rotation=0, face=""):
        block_id = self._get_3dm_name(key)
        category = self._get_category(key)
        name = block_id.replace("SKYLARK250_","").replace("SKYLARK200_","")
        color = self._get_color(key, category)
        self.placed_blocks.append(PlacedBlock(
            block_id=block_id, category=category, series=self.series, name=name,
            position=GridPosition(int(x),int(y),int(z)), rotation=rotation,
            face=face, wall_height_mm=self.wall_h_mm, color=color))

    def _add_filler(self, key, x, y, z=0, face="filler"):
        block_id = self._get_3dm_name(key)
        name = block_id.replace("WIKIHOUSE_","")
        self.placed_blocks.append(PlacedBlock(
            block_id=block_id, category="filler", series=self.series, name=name,
            position=GridPosition(int(x),int(y),int(z)), rotation=0,
            face=face, wall_height_mm=self.wall_h_mm, color=CATEGORY_COLOR["filler"]))

    def generate(self, target, opening_config=None, partitions=None):
        self.placed_blocks = []; self.warnings = []
        if opening_config is None: opening_config = WallOpeningConfig.default()
        if partitions is None: partitions = []
        self._place_floor(target)
        self._place_corners(target)           # Step 1：放所有 CORNER + FILLER
        self._place_walls(target, opening_config)  # Step 2：填 WALL/DOOR/WINDOW
        self._place_partitions(target, partitions)
        self._place_roof(target)
        bom = self._generate_bom()
        vi = [{"id":b.block_id,"name":b.name,"category":b.category,"series":b.series}
              for b in self.placed_blocks if b.category != "partition"]
        validation = validate_configuration(vi, stories=1)
        return {
            "placed_blocks": [b.to_dict() for b in self.placed_blocks],
            "bom": bom, "validation": validation, "warnings": self.warnings,
            "target_shape": target.shape,
            "dimensions": {"grids_x":target.grids_x,"grids_y":target.grids_y,
                           "grids_z":target.grids_z,
                           "width_m":round(target.grids_x*GRID,2),
                           "length_m":round(target.grids_y*GRID,2),
                           "height_m":round(target.grids_z*GRID,2)},
            "config": {"series":self.series,"span":self.span_str,
                       "wall_height":self.wall_height_str,"roof_type":self.roof_type}}

    def _place_floor(self, target):
        gx, gy = target.grids_x, target.grids_y; s = self.span_str
        for y in range(gy):
            if any(target.contains(x,y,0) for x in range(gx)):
                key = f"END_{s}" if (y==0 or y==gy-1) else f"FLOOR_{s}"
                self._add(key, 0, y*600, 0, face="floor")

    def _place_corners(self, target):
        G=600; CW=318; FW=282; wz=-self.wall_h_mm
        wh=self.wall_height_str; corn_key=f"CORNER_{wh}"
        for gx in range(target.grids_x+1):
            for gy in range(target.grids_y+1):
                sw=target.contains(gx-1,gy-1,0); se=target.contains(gx,gy-1,0)
                nw=target.contains(gx-1,gy,0);   ne=target.contains(gx,gy,0)
                total=sw+se+nw+ne
                if total==0 or total==4 or total==2: continue
                x=gx*G; y=gy*G
                # corner_once 參數規律：
                # rot=0,270（左端）: xm=gx*G        rot=90,180（右端）: xm=gx*G-2*FW
                # rot=0,90（下端）:  ym=gy*G         rot=270,180（上端）: ym=gy*G-2*FW
                TW = 2 * FW   # 564
                if total==1:
                    if   ne: xm,ym,rot = x,    y,    0
                    elif nw: xm,ym,rot = x-TW, y,    90
                    elif se: xm,ym,rot = x,    y-TW, 270
                    else:    xm,ym,rot = x-TW, y-TW, 180  # sw
                    dx,dy = CORNER_OFFSET[rot]
                    self._add(corn_key, xm+dx, ym+dy, wz, rotation=rot, face="corner")

                elif total==3:
                    # 凹角插入點：從實測偏移量反推
                    # ne=F(右上空格): C6 xm=x-TW, ym=y-CW-TW
                    #                FN (x-CW-TW, y-TW)
                    #                FE (x-TW-FW, y-CW-TW)
                    if not ne:   # 右上空格
                        xm,ym,rot = x-TW,    y-CW-TW, 90
                        self._add_filler("FILLER_NS", x-CW-TW, y-TW,    wz, face="filler_NS")
                        self._add_filler("FILLER_EW", x-TW,    y-CW-TW, wz, face="filler_EW")
                    elif not nw: # 左上空格（nw=F）
                        # C6: xm=x+CW, ym=y-TW → insert=(x+CW-268, y-TW-25)
                        xm,ym,rot = x+CW, y-TW, 180
                        self._add_filler("FILLER_NS", x,    y-TW,    wz, face="filler_NS")
                        self._add_filler("FILLER_EW", x-FW, y-CW-TW, wz, face="filler_EW")
                    elif not se: # 右下空格（對稱）
                        xm,ym,rot = x-TW,    y+CW,    0
                        self._add_filler("FILLER_NS", x-CW-TW, y+TW,    wz, face="filler_NS")
                        self._add_filler("FILLER_EW", x-TW-FW, y+CW,    wz, face="filler_EW")
                    else:        # 左下空格（對稱）
                        xm,ym,rot = x,       y+CW,    270
                        self._add_filler("FILLER_NS", x+CW,    y+TW,    wz, face="filler_NS")
                        self._add_filler("FILLER_EW", x+FW,    y+CW,    wz, face="filler_EW")
                    dx,dy = CORNER_OFFSET[rot]
                    self._add(corn_key, xm+dx, ym+dy, wz, rotation=rot, face="corner")

    def _place_walls(self, target, opening_config: WallOpeningConfig):
        wh=self.wall_height_str; wall_key=f"WALL_{wh}"
        door_key=f"DOOR_{wh}1"; win_key=f"WINDOW_{wh}2"
        G=600; CW=318; FW=G-CW; TW=2*FW; wz=-self.wall_h_mm
        DW=BLOCK_INSERT.get(door_key,{}).get("w",1200)
        WW=BLOCK_INSERT.get(win_key, {}).get("w",1200)

        x_segs,y_segs=[],[]
        for gy_i in range(target.grids_y):
            seg=None
            for gx_i in range(target.grids_x):
                if target.contains(gx_i,gy_i,0) and not target.contains(gx_i,gy_i-1,0):
                    if seg is None: seg=gx_i
                    end=gx_i+1
                else:
                    if seg is not None: x_segs.append((gy_i,seg,end,'south')); seg=None
            if seg is not None: x_segs.append((gy_i,seg,end,'south'))
            seg=None
            for gx_i in range(target.grids_x):
                if target.contains(gx_i,gy_i,0) and not target.contains(gx_i,gy_i+1,0):
                    if seg is None: seg=gx_i
                    end=gx_i+1
                else:
                    if seg is not None: x_segs.append((gy_i+1,seg,end,'north')); seg=None
            if seg is not None: x_segs.append((gy_i+1,seg,end,'north'))
        for gx_i in range(target.grids_x):
            seg=None
            for gy_i in range(target.grids_y):
                if target.contains(gx_i,gy_i,0) and not target.contains(gx_i-1,gy_i,0):
                    if seg is None: seg=gy_i
                    end=gy_i+1
                else:
                    if seg is not None: y_segs.append((gx_i,seg,end,'west')); seg=None
            if seg is not None: y_segs.append((gx_i,seg,end,'west'))
            seg=None
            for gy_i in range(target.grids_y):
                if target.contains(gx_i,gy_i,0) and not target.contains(gx_i+1,gy_i,0):
                    if seg is None: seg=gy_i
                    end=gy_i+1
                else:
                    if seg is not None: y_segs.append((gx_i+1,seg,end,'east')); seg=None
            if seg is not None: y_segs.append((gx_i+1,seg,end,'east'))

        s0=[(gy_i,s,e,d) for gy_i,s,e,d in x_segs if d=='south' and gy_i==0]
        main_south=max(s0,key=lambda t:t[2]-t[1]) if s0 else None

        def place_openings(specs,seg_start,seg_len,direction):
            all_specs=list(specs)
            total_w=sum(DW if o.type=="door" else WW for o in all_specs)
            if total_w>seg_len:
                self.warnings.append(f"{direction}面開口總寬{total_w}mm超出{seg_len}mm，已縮減")
                while all_specs and sum(DW if o.type=="door" else WW for o in all_specs)>seg_len:
                    all_specs.pop()
            plan=[]; n=len(all_specs)
            if n==0: return plan
            if n==1:
                spec=all_specs[0]; ow=DW if spec.type=="door" else WW
                ok=door_key if spec.type=="door" else win_key
                if spec.position=="left": p=seg_start
                elif spec.position=="right": p=((seg_start+seg_len-ow)//G)*G
                else: p=seg_start+((seg_len-ow)//2//G)*G
                plan.append((p,ow,ok))
            elif n==2:
                ow0=DW if all_specs[0].type=="door" else WW; ow1=DW if all_specs[1].type=="door" else WW
                ok0=door_key if all_specs[0].type=="door" else win_key
                ok1=door_key if all_specs[1].type=="door" else win_key
                seg=seg_len//3
                p0=seg_start+((max(0,seg//2-ow0//2))//G)*G
                p1=seg_start+seg+((max(0,seg//2-ow1//2))//G)*G
                if all_specs[0].position=="left": p0=seg_start
                elif all_specs[0].position=="right": p0=max(seg_start,((seg_start+seg-ow0)//G)*G)
                if all_specs[1].position=="left": p1=seg_start+seg
                elif all_specs[1].position=="right": p1=((seg_start+seg_len-ow1)//G)*G
                if p1<p0+ow0: p1=((p0+ow0)//G)*G
                plan=[(p0,ow0,ok0),(p1,ow1,ok1)]
            else:
                total_ow=sum(DW if o.type=="door" else WW for o in all_specs)
                spacing=max(G,(seg_len-total_ow)//(n+1)); cur=seg_start+spacing
                for spec in all_specs:
                    ow=DW if spec.type=="door" else WW; ok=door_key if spec.type=="door" else win_key
                    plan.append(((cur//G)*G,ow,ok)); cur+=ow+spacing
            plan.sort(key=lambda t:t[0]); return plan

        def fill_seg(start_mm,end_mm,openings_plan,direction,rot,fixed,is_x):
            pos=start_mm; op_placed=set()
            while pos<end_mm:
                rem=end_mm-pos; placed=False
                for i,(op_start,op_w,op_key) in enumerate(openings_plan):
                    if i not in op_placed and pos>=op_start and rem>=op_w:
                        info=BLOCK_INSERT.get(op_key,{})
                        y_off=info.get("y_off",0)
                        if direction=='north' and "DOOR" in op_key:
                            x_off=0; y_off=-318
                        else:
                            x_off=info.get("off",op_w)
                        z_off=info.get("z_off",wz)
                        if is_x: self._add(op_key,pos+x_off,fixed+y_off,z_off,rotation=rot,face=direction)
                        else:    self._add(op_key,fixed,pos+info.get("off",op_w//2),z_off,rotation=rot,face=direction)
                        pos+=op_w; op_placed.add(i); placed=True; break
                if not placed:
                    if rem>=G:
                        if is_x: self._add(wall_key,pos+300,fixed,wz,rotation=rot,face=direction)
                        else:    self._add(wall_key,fixed,pos+300,wz,rotation=rot,face=direction)
                        pos+=G
                    else: break

        # 預先計算凹角格點集合
        concave_pts = set()
        for cgx in range(target.grids_x+1):
            for cgy in range(target.grids_y+1):
                sw=target.contains(cgx-1,cgy-1,0); se=target.contains(cgx,cgy-1,0)
                nw=target.contains(cgx-1,cgy,0);   ne=target.contains(cgx,cgy,0)
                if sw+se+nw+ne==3:
                    concave_pts.add((cgx,cgy))

        for gy_i,gx_s,gx_e,d in x_segs:
            y_mm=gy_i*G-2*(G-CW) if d=='north' else gy_i*G
            rot=0 if d=='south' else 180
            # 凹角在西端（gx_s）時往西延伸一格，凹角在東端（gx_e）時往東延伸一格
            xs_adj = -FW if any((gx_s,gy_i)==p for p in concave_pts) else CW
            xe_adj = -FW if any((gx_e,gy_i)==p for p in concave_pts) else -CW
            xs=gx_s*G+xs_adj; xe=gx_e*G+xe_adj
            is_main=(main_south is not None and gy_i==main_south[0] and gx_s==main_south[1] and gx_e==main_south[2])
            face_cfg=opening_config.get(d) if (is_main or d=='north') else FaceConfig.empty()
            if not is_main and d=='south': face_cfg=FaceConfig.empty()
            openings=place_openings(face_cfg.openings,xs,xe-xs,d)
            fill_seg(xs,xe,openings,d,rot,y_mm,True)

        for gx_i,gy_s,gy_e,d in y_segs:
            # east面：x_mm = gx_i*G - TW
            # west面：gx_i=0是外牆x=0
            #         gx_i>0且格點在凹角集合(nw=F類型)：x_mm = gx_i*G
            #         gx_i>0其他內牆：x_mm = gx_i*G - TW
            if d == 'east':
                x_mm = gx_i*G - TW
            elif gx_i == 0:
                x_mm = 0
            elif any((gx_i,cgy) in concave_pts for cgy in range(target.grids_y+1)):
                x_mm = gx_i*G   # nw=F凹角右側牆
            else:
                x_mm = gx_i*G - TW
            rot=90 if d=='east' else 270
            # 凹角在南端（gy_s）時往南延伸一格，凹角在北端（gy_e）時往北延伸一格
            ys_adj = -FW if any((gx_i,gy_s)==p for p in concave_pts) else CW
            ye_adj = -TW if any((gx_i,gy_e)==p for p in concave_pts) else -CW
            ys=gy_s*G+ys_adj; ye=gy_e*G+ye_adj
            face_cfg=opening_config.get(d)
            openings=place_openings(face_cfg.openings,ys,ye-ys,d)
            fill_seg(ys,ye,openings,d,rot,x_mm,False)


    def _calc_partition_openings(self, openings, seg_start, seg_len, door_key, win_key, DW, WW, G):
        all_specs = list(openings)
        total_w = sum(DW if o.type=="door" else WW for o in all_specs)
        if total_w > seg_len:
            while all_specs and sum(DW if o.type=="door" else WW for o in all_specs) > seg_len:
                all_specs.pop()
        plan = []; n = len(all_specs)
        if n == 0: return plan
        elif n == 1:
            spec = all_specs[0]; ow = DW if spec.type=="door" else WW
            ok = door_key if spec.type=="door" else win_key
            if spec.position=="left": p = seg_start
            elif spec.position=="right": p = ((seg_start+seg_len-ow)//G)*G
            else: p = seg_start + ((seg_len-ow)//2//G)*G
            plan.append((p,ow,ok))
        elif n == 2:
            ow0=DW if all_specs[0].type=="door" else WW; ow1=DW if all_specs[1].type=="door" else WW
            ok0=door_key if all_specs[0].type=="door" else win_key
            ok1=door_key if all_specs[1].type=="door" else win_key
            seg=seg_len//3
            p0=seg_start+((max(0,seg//2-ow0//2))//G)*G
            p1=seg_start+seg+((max(0,seg//2-ow1//2))//G)*G
            if all_specs[0].position=="left": p0=seg_start
            elif all_specs[0].position=="right": p0=max(seg_start,((seg_start+seg-ow0)//G)*G)
            if all_specs[1].position=="left": p1=seg_start+seg
            elif all_specs[1].position=="right": p1=((seg_start+seg_len-ow1)//G)*G
            if p1<p0+ow0: p1=((p0+ow0)//G)*G
            plan=[(p0,ow0,ok0),(p1,ow1,ok1)]
        else:
            total_ow=sum(DW if o.type=="door" else WW for o in all_specs)
            spacing=max(G,(seg_len-total_ow)//(n+1)); cur=seg_start+spacing
            for spec in all_specs:
                ow=DW if spec.type=="door" else WW; ok=door_key if spec.type=="door" else win_key
                plan.append(((cur//G)*G,ow,ok)); cur+=ow+spacing
        plan.sort(key=lambda t: t[0]); return plan

    def _place_partitions(self, target, partitions):
        wh=self.wall_height_str; wall_key=f"WALL_{wh}"; door_key=f"DOOR_{wh}1"; win_key=f"WINDOW_{wh}2"
        G=600; CW=318; FW=G-CW; TW=2*FW; wz=-self.wall_h_mm
        DW=BLOCK_INSERT.get(door_key,{}).get("w",1200); WW=BLOCK_INSERT.get(win_key,{}).get("w",1200)
        for p in partitions:
            if p.direction=="EW":
                y_pos=p.position_grids*G
                if y_pos<=0 or y_pos>=target.grids_y*G:
                    self.warnings.append(f"隔間位置 {p.position_grids} 格超出範圍，已略過"); continue
                valid_gx=[gx_i for gx_i in range(target.grids_x)
                          if target.contains(gx_i,p.position_grids,0) and target.contains(gx_i,p.position_grids-1,0)]
                if not valid_gx: continue
                x_start=valid_gx[0]*G+CW; x_end=(valid_gx[-1]+1)*G-CW; iw=x_end-x_start
                openings_plan=self._calc_partition_openings(p.openings,x_start,iw,door_key,win_key,DW,WW,G)
                x=x_start; op_placed=set()
                while x<x_end:
                    rem=x_end-x; placed_op=False
                    for i,(op_start,op_w,op_key_p) in enumerate(openings_plan):
                        if i not in op_placed and x>=op_start and rem>=op_w:
                            info=BLOCK_INSERT.get(op_key_p,{}); block_id=self._get_3dm_name(op_key_p)
                            cat="door" if "DOOR" in op_key_p else "window"
                            name=block_id.replace("SKYLARK250_","").replace("SKYLARK200_","")
                            x_off=info.get("off",op_w) if "DOOR" in op_key_p else info.get("off",op_w//2)
                            rot_val=0 if "DOOR" in op_key_p else 180
                            self.placed_blocks.append(PlacedBlock(block_id=block_id,category=cat,series=self.series,name=name,
                                position=GridPosition(int(x+x_off),int(y_pos),int(info.get("z_off",wz))),
                                rotation=rot_val,face=f"partition_EW_{p.position_grids}",wall_height_mm=self.wall_h_mm,color=CATEGORY_COLOR[cat]))
                            x+=op_w; op_placed.add(i); placed_op=True; break
                    if not placed_op:
                        if rem>=G:
                            block_id=self._get_3dm_name(wall_key); name=block_id.replace("SKYLARK250_","").replace("SKYLARK200_","")
                            self.placed_blocks.append(PlacedBlock(block_id=block_id,category="partition",series=self.series,name=name,
                                position=GridPosition(int(x+300),int(y_pos),int(wz)),rotation=180,
                                face=f"partition_EW_{p.position_grids}",wall_height_mm=self.wall_h_mm,color=CATEGORY_COLOR["partition"]))
                            x+=G
                        else: break
            elif p.direction=="NS":
                x_pos=p.position_grids*G
                if x_pos<=0 or x_pos>=target.grids_x*G:
                    self.warnings.append(f"隔間位置 {p.position_grids} 格超出範圍，已略過"); continue
                valid_gy=[gy_i for gy_i in range(target.grids_y)
                          if target.contains(p.position_grids,gy_i,0) and target.contains(p.position_grids-1,gy_i,0)]
                if not valid_gy: continue
                y_start=valid_gy[0]*G+CW; y_end=(valid_gy[-1]+1)*G-CW; ih=y_end-y_start
                openings_plan=self._calc_partition_openings(p.openings,y_start,ih,door_key,win_key,DW,WW,G)
                y=y_start; op_placed=set()
                while y<y_end:
                    rem=y_end-y; placed_op=False
                    for i,(op_start,op_w,op_key_p) in enumerate(openings_plan):
                        if i not in op_placed and y>=op_start and rem>=op_w:
                            info=BLOCK_INSERT.get(op_key_p,{}); block_id=self._get_3dm_name(op_key_p)
                            cat="door" if "DOOR" in op_key_p else "window"
                            name=block_id.replace("SKYLARK250_","").replace("SKYLARK200_","")
                            x_adj=-318 if "DOOR" in op_key_p else 0
                            y_off=info.get("off",op_w) if "DOOR" in op_key_p else info.get("off",op_w//2)
                            self.placed_blocks.append(PlacedBlock(block_id=block_id,category=cat,series=self.series,name=name,
                                position=GridPosition(int(x_pos+x_adj),int(y+y_off),int(info.get("z_off",wz))),
                                rotation=90,face=f"partition_NS_{p.position_grids}",wall_height_mm=self.wall_h_mm,color=CATEGORY_COLOR[cat]))
                            y+=op_w; op_placed.add(i); placed_op=True; break
                    if not placed_op:
                        if rem>=G:
                            block_id=self._get_3dm_name(wall_key); name=block_id.replace("SKYLARK250_","").replace("SKYLARK200_","")
                            self.placed_blocks.append(PlacedBlock(block_id=block_id,category="partition",series=self.series,name=name,
                                position=GridPosition(int(x_pos),int(y+300),int(wz)),rotation=90,
                                face=f"partition_NS_{p.position_grids}",wall_height_mm=self.wall_h_mm,color=CATEGORY_COLOR["partition"]))
                            y+=G
                        else: break

    def _place_roof(self, target):
        gx, gy = target.grids_x, target.grids_y; s = self.span_str
        key = f"ROOF_{s}42" if self.roof_type=="gable_42deg" else f"ROOF_{s}10"
        for y in range(gy):
            if any(target.contains(x,y,0) for x in range(gx)):
                self._add(key, 0, y*600, 0, face="top")

    def _generate_bom(self):
        count_map = {}
        for b in self.placed_blocks:
            k = (b.block_id, b.category, b.series, b.name)
            count_map[k] = count_map.get(k, 0) + 1
        bom = []
        for (block_id, category, series, name), qty in sorted(count_map.items()):
            bom.append({"block_id":block_id,"category":category,"series":series,
                        "name":name,"quantity":qty,
                        "assembly_step":ASSEMBLY_ORDER.get(category,{}).get("step",99)})
        bom.sort(key=lambda x: x["assembly_step"]); return bom


def generate_from_requirements(shape="rectangle", area_sqm=50.0, series="skylark250",
    span_str="M", wall_height_str="M", roof_type="flat",
    opening_config=None, partitions=None, stories=1, **kwargs):
    engine = DiscreteAggregationEngine(series=series, span_str=span_str,
                                       wall_height_str=wall_height_str, roof_type=roof_type)
    span_m = {"S":3.6,"XS":3.0,"XXXS":2.4,"M":4.8,"L":5.4}.get(span_str, 4.8)
    lg = max(4, round(((area_sqm/span_m)-0.636)/0.6))
    hg = {"S":3,"M":4,"L":5,"XL":5}.get(wall_height_str, 4)
    if shape=="rectangle":   target = make_rectangle(span_str, lg, hg)
    elif shape=="L":         target = make_L_shape(span_str, lg, kwargs.get("wing_grids_x", SPAN_GRIDS.get(span_str,8)//2), kwargs.get("wing_grids_y", lg//2), hg)
    elif shape=="U":
        total_x = kwargs.get("total_grids_x", None)
        target = make_U_shape(span_str, lg,
                              kwargs.get("court_grids_x", SPAN_GRIDS.get(span_str,8)//2),
                              kwargs.get("court_grids_y", lg//3),
                              hg,
                              total_grids_x=total_x)
    elif shape=="cross":     target = make_cross(span_str, kwargs.get("arm_length",4), hg)
    else:                    target = make_rectangle(span_str, lg, hg)
    return engine.generate(target, opening_config=opening_config, partitions=partitions)


def generate_three_schemes(area_sqm=50.0, series="skylark250"):
    schemes = {}
    configs = [("scheme_a","S","M","flat","方案 A｜保守型","窄長形、平頂"),
               ("scheme_b","M","M","flat","方案 B｜標準型","正方形、平頂"),
               ("scheme_c","M","L","gable_42deg","方案 C｜進階型","山牆 42°")]
    for key, span, wh, roof, label, desc in configs:
        r = generate_from_requirements(shape="rectangle", area_sqm=area_sqm,
                                       series=series, span_str=span, wall_height_str=wh, roof_type=roof)
        r["label"]=label; r["description"]=desc; r["span"]=span; r["roof"]=roof
        schemes[key] = r
    return schemes