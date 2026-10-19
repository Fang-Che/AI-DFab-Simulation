"""
Design Validator v2.4 (CoEvo)
=============================
v2.4 change: auto-generate conceptual partitions from the scheme typology.
Each shape carries an implicit spatial organisation (rectangle = 2 bedrooms
+ living + service; L = main + extension; U = wings + courtyard-facing
public zone), which is formalised into partition rules and passed to the
discrete engine alongside the shape geometry.

This is the first concrete demonstration of CoEvo's Formalisation operation
extending from *envelope* to *interior spatial organisation* — the same
knowledge-formalisation approach applied to a different scale.
"""

import json
import re
from utils.connection_grammar import validate_configuration, format_validation_report
from utils.discrete_engine import (
    generate_from_requirements,
    PartitionConfig,
    OpeningSpec,
)


# ══════════════════════════════════════════════
# Scheme-to-typology mapping
# ══════════════════════════════════════════════

SCHEME_TYPOLOGY = {
    "scheme_a": {
        "shape":     "rectangle",
        "roof":      "flat",
        "span":      "M",
        "extra":     {},
    },
    "scheme_b": {
        "shape":     "L",
        "roof":      "flat",
        "span":      "M",
        "extra":     {"wing_grids_x": 4, "wing_grids_y": 6},
    },
    "scheme_c": {
        "shape":     "U",
        "roof":      "flat",
        "span":      "M",
        "extra":     {"total_grids_x": 12, "court_grids_x": 4, "court_grids_y": 6},
    },
}


# ══════════════════════════════════════════════
# Auto-partition rules per shape
# ══════════════════════════════════════════════

def auto_partitions_for_shape(
    shape: str,
    grids_x: int,
    grids_y: int,
    extra: dict | None = None,
) -> list:
    """
    Return a list of PartitionConfig objects representing the conceptual
    partitions implied by the shape's room programme.

    - Rectangle: split north bedrooms from south public zone, and split
      the two bedrooms with a NS partition on the north half.
    - L-shape:   separate the main wing (public) from the extension wing
      (bedrooms) with a NS partition at the wing boundary.
    - U-shape:   separate the two north wings (bedrooms + courtyard) from
      the south public zone with an EW partition.

    grids_x / grids_y are the target building's grid counts.
    extra carries shape-specific parameters (e.g. wing widths).
    """
    extra = extra or {}
    partitions: list = []

    if shape == "rectangle":
        # EW partition splitting north bedrooms from south public zone
        y_split = max(2, int(round(grids_y * 0.55)))
        partitions.append(PartitionConfig(
            direction      = "EW",
            position_grids = y_split,
            label          = "Bed / Public zone divider",
            openings       = [OpeningSpec("door", "center")],
        ))
        # NS partition splitting the two bedrooms (only above y_split)
        x_split = max(2, grids_x // 2)
        partitions.append(PartitionConfig(
            direction      = "NS",
            position_grids = x_split,
            label          = "Bedroom divider",
            openings       = [],
        ))
        return partitions

    if shape == "L":
        # NS partition at the junction between main wing and extension wing.
        # In make_L_shape(), main body is x=[0, gx), extension is x=[gx, total_x).
        # So the boundary is at x = gx (which equals the span grid count).
        # We approximate: it's at "main wing width" which is grids_x - wing_grids_x.
        wing_grids_x = extra.get("wing_grids_x", 4)
        x_boundary = max(2, grids_x - wing_grids_x)
        partitions.append(PartitionConfig(
            direction      = "NS",
            position_grids = x_boundary,
            label          = "Main / Extension divider",
            openings       = [OpeningSpec("door", "center")],
        ))
        return partitions

    if shape == "U":
        # EW partition dividing the south public zone from the north
        # (wings + courtyard) region.
        # In make_U_shape(), courtyard depth = court_grids_y at the north end.
        # The wings extend from y=0 upward; the public zone sits at the south.
        # Public zone height ≈ grids_y - court_grids_y.
        court_grids_y = extra.get("court_grids_y", 6)
        y_boundary = max(2, grids_y - court_grids_y)
        partitions.append(PartitionConfig(
            direction      = "EW",
            position_grids = y_boundary,
            label          = "Public / Wing divider",
            openings       = [OpeningSpec("door", "center")],
        ))
        return partitions

    return []


# ══════════════════════════════════════════════
# JSON extraction & block expansion
# ══════════════════════════════════════════════

def extract_design_json(reply: str) -> dict | None:
    match = re.search(r"<DESIGN_JSON>([\s\S]*?)</DESIGN_JSON>", reply)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def expand_blocks(scheme: dict) -> list:
    expanded = []
    for block in scheme.get("blocks", []):
        qty = block.get("quantity", 1)
        for _ in range(qty):
            expanded.append({
                "id":       block.get("id", ""),
                "name":     block.get("name", block.get("id", "").split("_")[-1]),
                "category": block.get("category", ""),
                "series":   block.get("series", ""),
            })
    return expanded


# ══════════════════════════════════════════════
# Area fallback
# ══════════════════════════════════════════════

def _estimate_area_from_blocks(scheme: dict) -> float:
    span_area = {
        "XXXS": 1.44, "XXS": 1.80, "XS": 2.16,
        "S": 2.16, "M": 2.88, "L": 3.24,
    }
    span = scheme.get("span", "M")
    floor_qty = sum(
        b.get("quantity", 0) for b in scheme.get("blocks", [])
        if b.get("category") in ("floor", "end")
    )
    return max(20.0, floor_qty * span_area.get(span, 2.88))


# ══════════════════════════════════════════════
# Geometry generation with auto-partitions
# ══════════════════════════════════════════════

def generate_geometry_for_scheme(scheme_key: str, scheme: dict) -> dict:
    """
    Invoke the discrete aggregation engine with:
    - shape/roof/span/extras forced from SCHEME_TYPOLOGY
    - partitions auto-generated from the shape's room programme
    """
    try:
        typology = SCHEME_TYPOLOGY.get(scheme_key, SCHEME_TYPOLOGY["scheme_a"])

        series      = scheme.get("series", "skylark250")
        area_sqm    = scheme.get("area_sqm") or _estimate_area_from_blocks(scheme)

        span_str = typology["span"]
        if series == "skylark200" and span_str in ("M", "L"):
            span_str = "S"

        wall_h = "M"

        # First pass: generate without partitions, just to learn actual grids_x/y
        # (make_L_shape / make_U_shape derive grids from area_sqm)
        preview = generate_from_requirements(
            shape           = typology["shape"],
            area_sqm        = float(area_sqm),
            series          = series,
            span_str        = span_str,
            wall_height_str = wall_h,
            roof_type       = typology["roof"],
            **typology["extra"],
        )
        preview_dims = preview.get("dimensions", {})
        grids_x = preview_dims.get("grids_x", 0)
        grids_y = preview_dims.get("grids_y", 0)

        # Now derive partitions using the actual grid dimensions
        partitions = auto_partitions_for_shape(
            typology["shape"],
            grids_x,
            grids_y,
            extra=typology["extra"],
        )

        # Regenerate with partitions
        result = generate_from_requirements(
            shape           = typology["shape"],
            area_sqm        = float(area_sqm),
            series          = series,
            span_str        = span_str,
            wall_height_str = wall_h,
            roof_type       = typology["roof"],
            partitions      = partitions,
            **typology["extra"],
        )
        return {
            "placed_blocks":   result.get("placed_blocks", []),
            "dimensions":      result.get("dimensions", {}),
            "engine_warnings": result.get("warnings", []),
        }
    except Exception as e:
        return {
            "placed_blocks":   [],
            "dimensions":      {},
            "engine_warnings": [f"Geometry generation failed: {e}"],
        }


# ══════════════════════════════════════════════
# Scheme validation
# ══════════════════════════════════════════════

def validate_all_schemes(design_json: dict) -> dict:
    results = {}
    all_valid = True
    invalid_schemes = []

    for scheme_key in ["scheme_a", "scheme_b", "scheme_c"]:
        scheme = design_json.get(scheme_key, {})
        if not scheme:
            results[scheme_key] = {
                "is_valid": False,
                "validation": {
                    "errors": [{"rule_id": "E00", "message": f"{scheme_key} scheme data is missing"}],
                    "warnings": [], "assembly_order": [],
                    "summary": {}, "fabrication_notes": [], "ties": {}
                },
                "blocks":        [],
                "placed_blocks": [],
                "dimensions":    {},
                "span":          SCHEME_TYPOLOGY[scheme_key]["span"],
                "roof":          SCHEME_TYPOLOGY[scheme_key]["roof"],
            }
            all_valid = False
            invalid_schemes.append(scheme_key)
            continue

        blocks  = expand_blocks(scheme)
        stories = scheme.get("stories", 1)
        validation = validate_configuration(blocks, stories=stories)

        geometry = generate_geometry_for_scheme(scheme_key, scheme)

        results[scheme_key] = {
            "is_valid":        validation["is_valid"],
            "validation":      validation,
            "blocks":          blocks,
            "placed_blocks":   geometry["placed_blocks"],
            "dimensions":      geometry["dimensions"],
            "engine_warnings": geometry["engine_warnings"],
            "span":            SCHEME_TYPOLOGY[scheme_key]["span"],
            "roof":            SCHEME_TYPOLOGY[scheme_key]["roof"],
            "shape":           SCHEME_TYPOLOGY[scheme_key]["shape"],
            "series":          scheme.get("series", "skylark250"),
        }

        if not validation["is_valid"]:
            all_valid = False
            invalid_schemes.append(scheme_key)

    results["all_valid"]       = all_valid
    results["invalid_schemes"] = invalid_schemes
    return results


# ══════════════════════════════════════════════
# Correction prompt
# ══════════════════════════════════════════════

def build_correction_prompt(original_request, design_json, validation_results):
    corrections = []
    scheme_names = {
        "scheme_a": "Scheme A | Compact (rectangle)",
        "scheme_b": "Scheme B | Balanced (L-shape)",
        "scheme_c": "Scheme C | Expansive (U-shape courtyard)",
    }
    for scheme_key in validation_results.get("invalid_schemes", []):
        result = validation_results[scheme_key]
        errors = result["validation"].get("errors", [])
        error_text = "\n".join(f"  - [{e['rule_id']}] {e['message']}" for e in errors)
        corrections.append(f"**{scheme_names.get(scheme_key)}** errors:\n{error_text}")

    return f"""Some of the schemes you generated do not comply with the WikiHouse Skylark fabrication rules. Please correct them and regenerate the output.

Original request: {original_request}

Schemes requiring correction:
{chr(10).join(corrections)}

Correction rules:
- The number of opening blocks (doors + windows) must not exceed 40% of the total wall panel count.
- Every scheme must include at least one Floor block.
- Every scheme must include at least one Wall block.
- SK200 and SK250 series must not be mixed within the same scheme.
- All three schemes should target similar orders of magnitude in floor area (small / medium / large), regardless of shape.

Please correct the flawed schemes inside `<DESIGN_JSON>` and keep the `series`, `stories`, and `area_sqm` fields reasonable.
"""


# ══════════════════════════════════════════════
# Top-level pipeline
# ══════════════════════════════════════════════

def validate_and_format_result(reply: str, all_blocks: list, original_request: str = "") -> dict:
    design_json = extract_design_json(reply)

    if not design_json:
        block_map = {b["id"]: b for b in all_blocks}
        found = [b for bid, b in block_map.items() if bid in reply]
        multi_storey_hints = ["two-storey", "two storey", "2-storey", "2 storey",
                              "two-story", "two story", "2-story", "2 story",
                              "兩層", "二層", "2層"]
        stories = 2 if any(w in reply.lower() for w in [h.lower() for h in multi_storey_hints]) else 1
        validation = validate_configuration(found, stories=stories) if found else {
            "is_valid": False, "errors": [], "warnings": [],
            "assembly_order": [], "summary": {}, "fabrication_notes": [], "ties": {}
        }
        return {
            "has_json":           False,
            "all_valid":          validation["is_valid"],
            "scheme_results":     {},
            "needs_correction":   False,
            "correction_prompt":  None,
            "recommended_blocks": found,
            "validation":         validation,
            "is_valid":           validation["is_valid"],
            "ties":               validation.get("ties", {}),
            "report":             format_validation_report(validation),
        }

    scheme_results = validate_all_schemes(design_json)
    all_valid = scheme_results["all_valid"]

    correction_prompt = None
    if not all_valid:
        correction_prompt = build_correction_prompt(original_request, design_json, scheme_results)

    best       = scheme_results.get("scheme_b", {})
    rep_blocks = best.get("blocks", [])
    rep_valid  = best.get("validation", {})

    return {
        "has_json":           True,
        "all_valid":          all_valid,
        "scheme_results":     scheme_results,
        "needs_correction":   not all_valid,
        "correction_prompt":  correction_prompt,
        "recommended_blocks": rep_blocks,
        "validation":         rep_valid,
        "is_valid":           all_valid,
        "ties":               rep_valid.get("ties", {}),
        "report":             format_validation_report(rep_valid) if rep_valid else "",
    }