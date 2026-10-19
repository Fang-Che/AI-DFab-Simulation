import json
from pathlib import Path

def _load_json():
    path = Path(__file__).parent.parent / "data" / "blocks_full.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_blocks():
    return _load_json()["blocks"]

def load_system_rules():
    return {
        "grid_mm": 600,
        "max_stories": 3,
        "plan_form": "orthogonal_only",
        "sk200": {
            "wall_depth_mm": 268,
            "max_span_m": 4.5,
            "suitable_stories": [1],
            "u_value_wm2k": 0.17
        },
        "sk250": {
            "wall_depth_mm": 318,
            "max_span_m": 5.7,
            "suitable_stories": [1, 2, 3],
            "u_value_wm2k": 0.14
        },
        "opening_sizes_mm": [600, 1200, 1800, 2400],
        "wall_height_increments_mm": 300
    }

def load_design_guidance():
    return {
        "series_selection": {
            "sk200_suitable_when": [
                "單層建築",
                "較溫和氣候，隔熱需求較低",
                "跨距在 4.5m 以內",
                "預算優先（較輕 = 較少材料）"
            ],
            "sk250_suitable_when": [
                "兩層或三層建築",
                "需要高隔熱性能（U=0.14）",
                "跨距最大 5.7m",
                "一般住宅首選"
            ]
        },
        "span_to_floor_block": {
            "up_to_3600mm": "SKYLARK250_FLOOR-S",
            "up_to_4800mm": "SKYLARK250_FLOOR-M",
            "up_to_5400mm": "SKYLARK250_FLOOR-L"
        },
        "cost_estimate_per_sqm_gbp": "400-450"
    }