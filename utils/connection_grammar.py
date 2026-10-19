"""
WikiHouse Skylark Fabrication-Aware Connection Grammar
======================================================
A formalised connection grammar for the WikiHouse Skylark open-source
modular building system, derived from the official Design Guide.

Positioning in the CoEvo framework:
    - Layer within CoEvo: knowledge substrate for the "Formalisation"
      operation of the CoEvo methodology.
    - Serves as the machine-readable manifestation of the WikiHouse
      fabrication constraints against which CoEvo agents validate designs.

Official document sources:
- WikiHouse Design Guide: https://www.wikihouse.cc/design/designing-for-wikihouse
- How the Structure Works: https://www.wikihouse.cc/design/how-the-structure-works
- WikiHouse Blocks: https://www.wikihouse.cc/design/wikihouse-blocks
- Engineering Guide: https://www.wikihouse.cc/engineering/what-is-skylark

Version: 2.0 (revised against official documents)
"""

# ══════════════════════════════════════════════
# Layer 1: Material & Fabrication Constraints
# ══════════════════════════════════════════════

FABRICATION_CONSTRAINTS = {
    # Sheet material specification (official: 18mm OSB3)
    "sheet": {
        "material": "OSB3",
        "thickness_mm": 18,
        "standard_size_mm": {"width": 1220, "height": 2440},
        "cnc_tolerance_mm": 0.1,
    },
    # Fixings
    "fixings": {
        "type": "Brad nails",
        "gauge": "15",
        "length_mm": 35,
    },
    # Assembly safety limits (max weight liftable by a single person)
    "assembly": {
        "max_single_person_weight_kg": 25,
        "connector_type": "Bowtie timber ties",
    },
    # SK250 series specification (official)
    "skylark250": {
        "wall_depth_mm": 318,
        "insulation_depth_mm": 250,
        "insulation_type": "Mineral wool",
        "service_zone_mm": 32,
        "max_span_mm": 5400,
        "max_stories": 3,
        "u_value_wm2k": 0.14,
        "grid_unit_mm": 600,
        "wall_heights_mm": {
            "S":  2100,
            "M":  2400,
            "L":  2700,
            "XL": 3000,
        },
        # Floor spans (official)
        "floor_spans_mm": {
            "S":    3600,
            "M":    4800,
            "L":    5400,
        },
        # Opening widths (official)
        "opening_widths_mm": {
            "XS": 600,
            "S":  1200,
            "M":  1800,
            "L":  2400,
        },
    },
    # SK200 series specification (official)
    "skylark200": {
        "wall_depth_mm": 268,
        "insulation_depth_mm": 200,
        "insulation_type": "Mineral wool",
        "service_zone_mm": 32,
        "max_span_mm": 4200,
        "max_stories": 1,
        "u_value_wm2k": 0.17,
        "grid_unit_mm": 600,
        "wall_heights_mm": {
            "S":  2100,
            "M":  2400,
            "L":  2700,
            "XL": 3000,
        },
        # Floor spans (official)
        "floor_spans_mm": {
            "XXXS": 2400,
            "XXS":  3000,
            "XS":   3600,
            "S":    4200,
        },
        "opening_widths_mm": {
            "XS": 600,
            "S":  1200,
            "M":  1800,
            "L":  2400,
        },
    },
}


# ══════════════════════════════════════════════
# Layer 2: Geometric Constraints
# ══════════════════════════════════════════════

GEOMETRIC_CONSTRAINTS = {
    # Plan form (official: orthogonal only)
    "plan_form": "orthogonal_only",
    "curved_forms": False,
    "angular_layouts": False,

    # Grid unit (official: 600 mm × 600 mm)
    "grid_mm": 600,

    # Vertical height increment (official: multiples of 300 mm)
    "height_increment_mm": 300,

    # Wall panel composition
    "wall_composition": {
        "skylark250": {
            "outer_skin_mm": 18,
            "insulation_mm": 250,
            "inner_skin_mm": 18,
            "service_zone_mm": 32,
            "total_mm": 318,
        },
        "skylark200": {
            "outer_skin_mm": 18,
            "insulation_mm": 200,
            "inner_skin_mm": 18,
            "service_zone_mm": 32,
            "total_mm": 268,
        },
    },
}


# ══════════════════════════════════════════════
# Layer 3: Structural Constraints
# Source: WikiHouse Design Guide — How the Structure Works
# ══════════════════════════════════════════════

STRUCTURAL_CONSTRAINTS = {

    # Lateral bracing rules (explicitly defined in official documents)
    # Resistance against lateral bending under wind loading
    "lateral_bracing": {
        "single_storey": {
            "description": "Lateral bracing rules for single-storey buildings",
            "option_a": {
                "min_continuous_solid_wall_mm": 1800,
                "min_blocks": 3,
                "max_spacing_mm": 6000,
                "note": "At least one continuous 1.8 m (3 wall blocks) of solid wall per 6 m"
            },
            "option_b": {
                "min_solid_wall_mm": 1200,
                "min_blocks": 2,
                "segments_required": 2,
                "max_spacing_mm": 6000,
                "note": "At least two 1.2 m (2 wall blocks each) segments of solid wall per 6 m"
            },
        },
        "two_storey": {
            "description": "Lateral bracing rules for two-storey buildings (ground floor)",
            "option_a": {
                "min_continuous_solid_wall_mm": 3600,
                "min_blocks": 6,
                "max_spacing_mm": 6000,
                "note": "At least one continuous 3.6 m (6 wall blocks) of solid wall per 6 m"
            },
            "option_b": {
                "min_solid_wall_mm": 2400,
                "min_blocks": 4,
                "segments_required": 2,
                "max_spacing_mm": 6000,
                "note": "At least two 2.4 m (4 wall blocks each) segments of solid wall per 6 m"
            },
        },
        "three_storey": {
            "description": "Three-storey buildings require individual structural engineering review",
            "requires_engineer": True,
            "note": "Unless supported by adjoining terraced units, Skylark is not recommended for three-storey buildings"
        },
    },

    # Opening rules (official)
    "opening_rules": {
        "min_solid_between_openings": 1,
        "note": "Between any two windows or doors, at least one solid wall block is required",
        "source": "WikiHouse Design Guide — How the structure works",
        "lintel_required": True,
        "lintel_note": "All openings require a lintel above them; dimensions specified by a structural engineer",
    },

    # Span rules (official)
    "span_rules": {
        "note": "Span defines the full width of the building in one direction; the other direction may extend freely",
        "floor_must_rest_on_wall": True,
        "both_ends_required": True,
        "sk250_max_span_mm": 5400,
        "sk200_max_span_mm": 4200,
        "larger_span_note": "Spans exceeding standard limits require additional supports between blocks",
    },

    # Roof-to-wall connection rules (official)
    "roof_wall_connection": {
        "floors_and_roofs_provide_lateral_stability": True,
        "avoid_consecutive_rooflights": True,
        "note": "Floors and roofs provide overall lateral stability; avoid placing rooflights consecutively",
    },

    # Series rules (official)
    "series_rules": {
        "sk200_single_storey_only": True,
        "sk250_up_to_3_storey": True,
        "no_mixing_series": True,
        "note": "SK200 and SK250 must not be mixed within the same building",
    },
}


# ══════════════════════════════════════════════
# Layer 4: Roof Type Rules
# Source: WikiHouse Design Guide — Designing for WikiHouse
# ══════════════════════════════════════════════

ROOF_TYPES = {
    "flat": {
        "name": "Flat",
        "actual_pitch_degrees": 0.72,
        "pitch_ratio": "1:80",
        "drainage": "single_side",
        "description": "Flat roof (pre-engineered with 1:80 drainage fall)",
        "compatible_wall_heights": ["S", "M", "L", "XL"],
        "requires_ridge_beam": False,
        "assembly_note": "Flat roofs are easy to access during and after assembly for maintenance",
        "available_for": ["skylark250", "skylark200"],
    },
    "roof_terrace": {
        "name": "Accessible roof terrace",
        "actual_pitch_degrees": 0,
        "description": "Upper-floor beams reused as the roof deck, forming an accessible platform",
        "requires_waterproofing": True,
        "requires_drainage_detail": True,
        "requires_ridge_beam": False,
        "note": "Waterproofing and drainage detailing require careful design",
        "available_for": ["skylark250"],
    },
    "sloping_10deg": {
        "name": "Single-slope (10°)",
        "actual_pitch_degrees": 10,
        "description": "10° single-slope roof, suitable for traditional roofing materials",
        "wall_pairing": {
            "low_side_wall_height": "M",   # 2400mm
            "high_side_wall_height": "XL", # 3000mm
        },
        "requires_ridge_beam": False,
        "available_for": ["skylark250", "skylark200"],
    },
    "gable_42deg": {
        "name": "Gable roof (42°)",
        "actual_pitch_degrees": 42,
        "description": "Traditional gable roof at 42° pitch",
        "compatible_spans": ["M"],
        "compatible_span_mm": 4800,
        "requires_ridge_beam": True,
        "ridge_beam": {
            "width_mm": 90,
            "material": "glulam or LVL",
            "packer": "18mm OSB or plywood on each side",
            "depth_note": "Depth to be specified by a structural engineer based on span and roof loading",
        },
        "assembly_method": "Two half-panels are lifted from inside the building and temporarily fixed at the ridge",
        "alternative": "A steel tie rod may replace the ridge beam, though installation is more complex",
        "available_for": ["skylark250"],
    },
}


# ══════════════════════════════════════════════
# Layer 5: Block Category Mapping
# ══════════════════════════════════════════════

# Infer category from block name
BLOCK_CATEGORY_RULES = {
    "wall":      ["WALL"],
    "corner":    ["CORNER"],
    "floor":     ["FLOOR"],
    "end":       ["END"],
    "roof":      ["ROOF"],
    "window":    ["DOOR", "WINDOW", "SKYLIGHT"],
    "stair":     ["STAIR"],
    "trim":      ["VERGE", "LINTEL"],
    "connector": ["TIES"],
}

def get_block_category(block_name: str) -> str:
    """Infer a block's category from its name."""
    name_upper = block_name.upper()
    for category, keywords in BLOCK_CATEGORY_RULES.items():
        if any(kw in name_upper for kw in keywords):
            return category
    return "other"


# ══════════════════════════════════════════════
# Layer 6: Connection Rules
# ══════════════════════════════════════════════

# Connectability on each of the six faces of each block category.
# None  = closed face (cannot connect)
# list  = list of block categories that may connect to this face

CONNECTION_RULES = {

    # Floor cassettes (FLOOR / END)
    # Placed horizontally along the span; both ends must rest on walls.
    "floor": {
        "top":    ["wall", "corner", "window"],  # Top face receives walls above
        "bottom": [None],                         # Bottom is the foundation; not connectable
        "left":   ["floor", "end"],              # Extends laterally to the next cassette
        "right":  ["floor", "end"],
        "front":  [None],                         # Span ends enclosed by walls
        "back":   [None],
    },

    # End boards (END): closing panels at the ends of a floor span
    "end": {
        "top":    ["wall", "corner", "window"],
        "bottom": [None],
        "left":   ["floor"],
        "right":  ["floor"],
        "front":  [None],
        "back":   [None],
    },

    # Standard wall panels (WALL)
    # External walls are load-bearing; all wall panels are CNC-cut structural elements.
    "wall": {
        "top":    ["roof", "floor"],             # Top face connects to roof or upper-floor cassette
        "bottom": ["floor", "end"],              # Bottom must rest on floor or end board
        "left":   ["wall", "corner", "window"],  # Side connects to adjacent wall, corner, or opening
        "right":  ["wall", "corner", "window"],
        "front":  [None],                         # Thickness faces closed
        "back":   [None],
    },

    # Corner columns (CORNER)
    # Placed at the four corners of the building; connects two directions of wall panels.
    "corner": {
        "top":    ["roof", "floor"],
        "bottom": ["floor", "end"],
        "left":   ["wall", "window"],            # Each side face connects to walls of one direction
        "right":  ["wall", "window"],
        "front":  [None],
        "back":   [None],
    },

    # Opening panels (DOOR / WINDOW / SKYLIGHT)
    # Official rule: at least one solid wall block must separate any two openings.
    "window": {
        "top":    ["roof", "floor"],
        "bottom": ["floor", "end"],
        "left":   ["wall", "corner"],            # Only solid walls or corners — not another opening
        "right":  ["wall", "corner"],
        "front":  [None],
        "back":   [None],
    },

    # Roof panels (ROOF)
    # Provide overall lateral stability; consecutive rooflights are not recommended.
    "roof": {
        "top":    [None],                         # Exposed face
        "bottom": ["wall", "corner"],            # Must land on wall or corner blocks
        "left":   ["roof", "trim"],              # Extends laterally to the next roof panel or verge
        "right":  ["roof", "trim"],
        "front":  [None],
        "back":   [None],
    },

    # Verge / trim boards
    "trim": {
        "top":    [None],
        "bottom": ["wall"],
        "left":   ["roof"],
        "right":  [None],
        "front":  [None],
        "back":   [None],
    },

    # Staircases (STAIR)
    "stair": {
        "top":    ["floor"],
        "bottom": ["floor"],
        "left":   ["wall"],
        "right":  ["wall"],
        "front":  [None],
        "back":   [None],
    },

    # Connectors (TIES / Bowtie)
    # Not part of the spatial assembly; counted separately during fabrication validation.
    "connector": {
        "top": [None], "bottom": [None],
        "left": [None], "right": [None],
        "front": [None], "back": [None],
    },
}


# ══════════════════════════════════════════════
# Layer 7: Height Compatibility Rules
# ══════════════════════════════════════════════

# All wall panels in the same row must share the same height (so the roof sits level).
HEIGHT_COMPATIBILITY_GROUPS = {
    "S":  {"height_mm": 2100, "compatible": ["WALL-S",  "CORNER-S"]},
    "M":  {"height_mm": 2400, "compatible": ["WALL-M",  "CORNER-M",
                                              "DOOR-M1", "DOOR-M2",
                                              "WINDOW-M1", "WINDOW-M2"]},
    "L":  {"height_mm": 2700, "compatible": ["WALL-L",  "CORNER-L",
                                              "DOOR-L1", "DOOR-L2",
                                              "WINDOW-L1"]},
    "XL": {"height_mm": 3000, "compatible": ["WALL-XL", "CORNER-XL",
                                              "DOOR-XL1"]},
}

# Sloping roof special pairing (official: low-side M wall + high-side XL wall)
SLOPING_ROOF_WALL_PAIRING = {
    "sloping_10deg": {
        "low_side_wall_height":  "M",   # 2400mm
        "high_side_wall_height": "XL",  # 3000mm
        "note": "Sloping roofs use M-height walls on the low side and XL-height walls on the high side",
    }
}


# ══════════════════════════════════════════════
# Layer 8: Span Compatibility Rules
# ══════════════════════════════════════════════

SPAN_COMPATIBILITY = {
    # SK250 span mapping
    "skylark250": {
        "FLOOR-S":  {"span_mm": 3600, "compatible_roof_prefix": "ROOF-S"},
        "FLOOR-M":  {"span_mm": 4800, "compatible_roof_prefix": "ROOF-M"},
        "FLOOR-L":  {"span_mm": 5400, "compatible_roof_prefix": "ROOF-L"},
        "END-S":    {"span_mm": 3600},
        "END-M":    {"span_mm": 4800},
        "END-L":    {"span_mm": 5400},
    },
    # SK200 span mapping
    "skylark200": {
        "FLOOR-XXXS": {"span_mm": 2400},
        "FLOOR-XXS":  {"span_mm": 3000},
        "FLOOR-XS":   {"span_mm": 3600},
        "FLOOR-S":    {"span_mm": 4200},
    },
}


# ══════════════════════════════════════════════
# Layer 9: Assembly Sequence Constraints
# Source: WikiHouse General Assembly Guide
# ══════════════════════════════════════════════

ASSEMBLY_ORDER = {
    # Step 1: With foundation ready, install floor cassettes
    "floor":     {"step": 1, "label": "Install floor cassettes"},
    "end":       {"step": 1, "label": "Install end blocks"},
    # Step 2: Erect surrounding walls (starting from the corners)
    "corner":    {"step": 2, "label": "Install corner columns"},
    "wall":      {"step": 2, "label": "Erect wall panels"},
    "window":    {"step": 2, "label": "Install door / window panels"},
    # Step 3: Install staircase (if any)
    "stair":     {"step": 3, "label": "Install stair blocks"},
    # Step 4: Install the roof
    "roof":      {"step": 4, "label": "Install roof panels"},
    # Step 5: Trim
    "trim":      {"step": 5, "label": "Install verge / trim boards"},
    # Step 6: Fix connectors
    "connector": {"step": 6, "label": "Fix Bowtie ties"},
}


# ══════════════════════════════════════════════
# Layer 10: Forbidden Combinations
# (Sourced from official documents; strict rules)
# ══════════════════════════════════════════════

FORBIDDEN_RULES = [
    {
        "rule_id": "F01",
        "name": "opening_adjacent_to_opening",
        "source": "WikiHouse Design Guide — How the structure works",
        "description": "At least one solid wall block must separate two openings",
        "severity": "error",
        "check": lambda a, b: (
            a.get("category") == "window" and
            b.get("category") == "window"
        ),
    },
    {
        "rule_id": "F02",
        "name": "floor_direct_to_roof",
        "source": "WikiHouse structural logic",
        "description": "A roof cannot sit directly on a floor cassette; walls must intervene",
        "severity": "error",
        "check": lambda a, b: (
            a.get("category") == "floor" and
            b.get("category") == "roof"
        ),
    },
    {
        "rule_id": "F03",
        "name": "corner_adjacent_to_corner",
        "source": "WikiHouse structural logic",
        "description": "Two corner columns cannot be adjacent (structurally redundant and cannot connect walls)",
        "severity": "error",
        "check": lambda a, b: (
            a.get("category") == "corner" and
            b.get("category") == "corner"
        ),
    },
    {
        "rule_id": "F04",
        "name": "mixed_series",
        "source": "WikiHouse Design Guide — 200 and 250 series",
        "description": "SK200 and SK250 cannot be mixed within the same building",
        "severity": "error",
        "check": lambda a, b: (
            a.get("series", "") != b.get("series", "") and
            a.get("series", "") != "" and
            b.get("series", "") != ""
        ),
    },
    {
        "rule_id": "F05",
        "name": "sk200_multi_storey",
        "source": "WikiHouse Design Guide — 200 and 250 series",
        "description": "The SK200 series is only suitable for single-storey buildings",
        "severity": "error",
        "check": None,  # Handled at the validator level
    },
    {
        "rule_id": "F06",
        "name": "gable_roof_wrong_span",
        "source": "WikiHouse Design Guide — Roof shape",
        "description": "The gable roof (42°) currently supports only M-span (4.8 m)",
        "severity": "error",
        "check": None,  # Handled at the validator level
    },
    {
        "rule_id": "F07",
        "name": "three_storey_without_engineer",
        "source": "WikiHouse Design Guide — Form and height",
        "description": "Three-storey buildings require structural engineering review unless supported by adjoining terraced units",
        "severity": "warning",
        "check": None,
    },
]


# ══════════════════════════════════════════════
# Core Functions
# ══════════════════════════════════════════════

def get_connectable_categories(block_category: str, face: str) -> list:
    """
    Return the categories of blocks that may connect to `block_category`
    on the given `face`.

    Parameters:
        block_category: category of the block
        face: face direction (top/bottom/left/right/front/back)
    Returns:
        list of connectable block categories, or [None] for a closed face
    """
    rules = CONNECTION_RULES.get(block_category, {})
    return rules.get(face, [None])


def is_connection_valid(block_a: dict, face_a: str, block_b: dict) -> tuple:
    """
    Check whether the connection between two blocks is valid.

    Returns: (is_valid: bool, rule_id: str, reason: str)
    """
    cat_a = block_a.get("category", "")
    cat_b = block_b.get("category", "")

    # Check connection rules
    connectable = get_connectable_categories(cat_a, face_a)
    if None in connectable:
        return False, "C01", f"The {face_a} face of a {cat_a} block is closed; no connection is allowed"
    if cat_b not in connectable:
        return False, "C02", f"The {face_a} face of a {cat_a} block cannot connect to a {cat_b} block"

    # Check forbidden rules
    for rule in FORBIDDEN_RULES:
        if rule["check"] and rule["check"](block_a, block_b):
            return False, rule["rule_id"], rule["description"]

    return True, None, "Connection is valid"


def calculate_ties(blocks_list: list) -> dict:
    """
    Estimate the number of Bowtie ties required for the configuration.

    Based on official assembly-guide rules:
    - Floor-Floor joint: 1 standard Bowtie per joint
    - Floor end at Wall: 3 outer + 3 inner = 6 per end; 12 per floor (both ends)
    - Wall-Wall joint: 1 outer + 1 inner = 2 per joint
    - Wall-Roof joint: 2 per joint

    Source: WikiHouse General Assembly Guide
    """
    floor_blocks = [b for b in blocks_list
                    if b.get("category") in ["floor", "end"]]
    wall_blocks  = [b for b in blocks_list
                    if b.get("category") in ["wall", "corner", "window"]]
    roof_blocks  = [b for b in blocks_list
                    if b.get("category") == "roof"]

    # Floor-to-floor joints (N floors → N-1 joints)
    floor_to_floor = max(0, len(floor_blocks) - 1)

    # Floor end connections to walls (each floor: 2 ends × 6 ties = 12)
    floor_to_wall = len(floor_blocks) * 2 * 6

    # Wall-to-wall joints (2 ties each, inner + outer)
    wall_to_wall = max(0, len(wall_blocks) - 1) * 2

    # Wall-top to roof connections (2 per joint)
    wall_to_roof = len(roof_blocks) * 2

    total = floor_to_floor + floor_to_wall + wall_to_wall + wall_to_roof

    return {
        "floor_to_floor": floor_to_floor,
        "floor_to_wall":  floor_to_wall,
        "wall_to_wall":   wall_to_wall,
        "wall_to_roof":   wall_to_roof,
        "total":          total,
        "note": "Estimated value; actual quantity determined by hole positions in the official CNC files"
    }


def validate_configuration(blocks_list: list, stories: int = 1) -> dict:
    """
    Validate the legality of a block configuration.

    Parameters:
        blocks_list: list of block dictionaries
        stories: number of storeys (affects lateral-bracing rules)

    Returns:
        {
            "is_valid": bool,
            "errors": [...],
            "warnings": [...],
            "assembly_order": [...],
            "summary": {...},
            "fabrication_notes": [...],
        }
    """
    errors = []
    warnings = []
    fabrication_notes = []

    # Classify blocks
    floor_blocks   = [b for b in blocks_list if b.get("category") in ["floor", "end"]]
    wall_blocks    = [b for b in blocks_list if b.get("category") == "wall"]
    corner_blocks  = [b for b in blocks_list if b.get("category") == "corner"]
    roof_blocks    = [b for b in blocks_list if b.get("category") == "roof"]
    opening_blocks = [b for b in blocks_list if b.get("category") == "window"]
    all_wall_type  = wall_blocks + corner_blocks + opening_blocks

    # ── Hard errors ──

    # E01: floor is required
    if not floor_blocks:
        errors.append({
            "rule_id": "E01",
            "message": "The configuration contains no floor blocks; a valid structure cannot be formed"
        })

    # E02: at least one wall required
    if not all_wall_type:
        errors.append({
            "rule_id": "E02",
            "message": "The configuration contains no wall blocks; the space cannot be enclosed"
        })

    # E03: series consistency (SK200 and SK250 cannot be mixed)
    series_set = set(
        b.get("series", "") for b in blocks_list if b.get("series")
    )
    if len(series_set) > 1:
        errors.append({
            "rule_id": "E03",
            "message": f"The configuration mixes multiple series {series_set}; SK200 and SK250 cannot be combined"
        })

    # E04: SK200 cannot be used for multi-storey buildings
    if "skylark200" in series_set and stories > 1:
        errors.append({
            "rule_id": "E04",
            "message": "The SK200 series is only suitable for single-storey buildings; use SK250 for multi-storey designs"
        })

    # E05: consecutive-openings check (each pair of openings must be separated by a solid wall)
    # Simplified check: opening ratio must not exceed 50%
    if all_wall_type:
        opening_ratio = len(opening_blocks) / len(all_wall_type)
        if opening_ratio > 0.5:
            errors.append({
                "rule_id": "E05",
                "message": (
                    f"Opening ratio is too high ({opening_ratio:.0%}). "
                    f"Exceeding 50% of the wall face will inevitably place two openings adjacent to each other, "
                    f"violating the official rule that at least one solid wall block must separate any two openings."
                )
            })

    # ── Soft warnings ──

    # W01: no roof
    if not roof_blocks:
        warnings.append({
            "rule_id": "W01",
            "message": "The configuration contains no roof blocks; a roof scheme needs to be designed separately"
        })

    # W02: lateral bracing (approximate check based on official rules)
    solid_wall_count = len(wall_blocks)
    bracing = STRUCTURAL_CONSTRAINTS["lateral_bracing"]

    if stories == 1:
        min_solid = bracing["single_storey"]["option_a"]["min_blocks"]
        if solid_wall_count < min_solid:
            warnings.append({
                "rule_id": "W02",
                "message": (
                    f"The number of solid wall blocks is low ({solid_wall_count}). "
                    f"A single-storey building requires at least 3 continuous solid wall blocks (1.8 m) per 6 m for lateral bracing. "
                    f"Structural engineering confirmation is recommended."
                )
            })
    elif stories == 2:
        min_solid = bracing["two_storey"]["option_a"]["min_blocks"]
        if solid_wall_count < min_solid:
            warnings.append({
                "rule_id": "W02",
                "message": (
                    f"The number of solid wall blocks is low ({solid_wall_count}). "
                    f"A two-storey building requires at least 6 continuous solid wall blocks (3.6 m) per 6 m for lateral bracing. "
                    f"Structural engineering confirmation is recommended."
                )
            })
    elif stories >= 3:
        warnings.append({
            "rule_id": "W03",
            "message": (
                "Three-storey buildings require an individual structural engineering review. "
                "Unless supported by adjoining terraced units, Skylark is officially not recommended for three-storey buildings."
            )
        })

    # W04: three-storey warning
    if stories >= 3:
        warnings.append({
            "rule_id": "W04",
            "message": "All configurations must be reviewed by a structural engineer; three-storey designs especially require professional confirmation"
        })

    # ── Fabrication notes ──
    fabrication_notes.append("All blocks are made from 18 mm OSB3 panels; CNC cutting tolerance ±0.1 mm")
    fabrication_notes.append("Blocks are joined using Bowtie timber ties")
    fabrication_notes.append("Insulation: mineral wool, installed within the internal cavities of each block")
    if any("DOOR" in b.get("name", "").upper() or
           "WINDOW" in b.get("name", "").upper()
           for b in blocks_list):
        fabrication_notes.append("A lintel is required above each opening; dimensions to be specified by a structural engineer")
    if roof_blocks and any("G42" in b.get("name", "").upper() for b in roof_blocks):
        fabrication_notes.append(
            "The gable roof requires a 90 mm-wide glulam or LVL ridge beam; depth to be specified by a structural engineer"
        )

    # ── Assembly sequence ──
    def get_step(block):
        cat = block.get("category", "other")
        return ASSEMBLY_ORDER.get(cat, {"step": 99})["step"]

    sorted_blocks = sorted(blocks_list, key=get_step)
    assembly_sequence = []
    seen_steps = {}
    for block in sorted_blocks:
        cat = block.get("category", "other")
        step_info = ASSEMBLY_ORDER.get(cat, {"step": 99, "label": "Other"})
        step = step_info["step"]
        if step not in seen_steps:
            seen_steps[step] = len(assembly_sequence)
            assembly_sequence.append({
                "step": step,
                "label": step_info["label"],
                "blocks": [],
            })
        idx = seen_steps[step]
        assembly_sequence[idx]["blocks"].append(block.get("id", block.get("name", "")))

    # ── Summary ──
    summary = {
        "total_blocks":   len(blocks_list),
        "floor_count":    len(floor_blocks),
        "wall_count":     len(wall_blocks),
        "corner_count":   len(corner_blocks),
        "roof_count":     len(roof_blocks),
        "opening_count":  len(opening_blocks),
        "stories":        stories,
        "series":         list(series_set),
    }

    # ── Ties estimate ──
    ties = calculate_ties(blocks_list)

    return {
        "is_valid":          len(errors) == 0,
        "errors":            errors,
        "warnings":          warnings,
        "assembly_order":    assembly_sequence,
        "summary":           summary,
        "fabrication_notes": fabrication_notes,
        "ties":              ties,
    }


def format_validation_report(result: dict) -> str:
    """Format the validation result into a human-readable report."""
    lines = []
    lines.append("═" * 50)
    lines.append("CoEvo Configuration Validation Report")
    lines.append("═" * 50)

    status = "✅ Valid (fabricable)" if result.get("is_valid") else "❌ Invalid (requires correction)"
    lines.append(f"Status: {status}")
    lines.append("")

    if result.get("errors"):
        lines.append("[ Errors — must be corrected ]")
        for e in result["errors"]:
            lines.append(f"  [{e['rule_id']}] {e['message']}")
        lines.append("")

    if result.get("warnings"):
        lines.append("[ Warnings — please review ]")
        for w in result["warnings"]:
            lines.append(f"  [{w['rule_id']}] {w['message']}")
        lines.append("")

    s = result.get("summary", {})
    if s:
        lines.append("[ Summary ]")
        lines.append(f"  Total blocks: {s.get('total_blocks', 0)}")
        lines.append(f"  Floor: {s.get('floor_count', 0)} | Wall: {s.get('wall_count', 0)} | "
                     f"Corner: {s.get('corner_count', 0)} | Roof: {s.get('roof_count', 0)} | "
                     f"Opening: {s.get('opening_count', 0)}")
        lines.append(f"  Storeys: {s.get('stories', 1)} | Series: {s.get('series', [])}")
        lines.append("")

    if result.get("assembly_order"):
        lines.append("[ Assembly Sequence ]")
        for step in result["assembly_order"]:
            lines.append(f"  Step {step['step']}: {step['label']}")
            lines.append(f"    Blocks: {', '.join(step['blocks'][:5])}"
                         + ("..." if len(step["blocks"]) > 5 else ""))
        lines.append("")

    if result.get("fabrication_notes"):
        lines.append("[ Fabrication Notes ]")
        for note in result["fabrication_notes"]:
            lines.append(f"  • {note}")

    ties = result.get("ties", {})
    if ties:
        lines.append("")
        lines.append("[ Ties Estimate ]")
        lines.append(f"  Floor-Floor joints: {ties.get('floor_to_floor', 0)} units")
        lines.append(f"  Floor-Wall ends:    {ties.get('floor_to_wall', 0)} units")
        lines.append(f"  Wall-Wall joints:   {ties.get('wall_to_wall', 0)} units")
        lines.append(f"  Wall-Roof joints:   {ties.get('wall_to_roof', 0)} units")
        lines.append(f"  ─────────────────")
        lines.append(f"  Total:              {ties.get('total', 0)} units")
        lines.append(f"  ({ties.get('note', '')})")

    lines.append("═" * 50)
    lines.append("⚠️  Final design must be reviewed by a licensed structural engineer")
    lines.append("═" * 50)

    return "\n".join(lines)


# ══════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════

if __name__ == "__main__":

    print("\n=== Test 1: Valid single-storey two-bedroom configuration (SK250) ===")
    config_valid = [
        {"id": "SKYLARK250_FLOOR-M-0", "name": "FLOOR-M-0", "category": "floor",   "series": "skylark250"},
        {"id": "SKYLARK250_FLOOR-M-0", "name": "FLOOR-M-0", "category": "floor",   "series": "skylark250"},
        {"id": "SKYLARK250_END-M-0",   "name": "END-M-0",   "category": "end",     "series": "skylark250"},
        {"id": "SKYLARK250_END-M-0",   "name": "END-M-0",   "category": "end",     "series": "skylark250"},
        {"id": "SKYLARK250_CORNER-M",  "name": "CORNER-M",  "category": "corner",  "series": "skylark250"},
        {"id": "SKYLARK250_CORNER-M",  "name": "CORNER-M",  "category": "corner",  "series": "skylark250"},
        {"id": "SKYLARK250_CORNER-M",  "name": "CORNER-M",  "category": "corner",  "series": "skylark250"},
        {"id": "SKYLARK250_CORNER-M",  "name": "CORNER-M",  "category": "corner",  "series": "skylark250"},
        {"id": "SKYLARK250_WALL-M",    "name": "WALL-M",    "category": "wall",    "series": "skylark250"},
        {"id": "SKYLARK250_WALL-M",    "name": "WALL-M",    "category": "wall",    "series": "skylark250"},
        {"id": "SKYLARK250_WALL-M",    "name": "WALL-M",    "category": "wall",    "series": "skylark250"},
        {"id": "SKYLARK250_WALL-M",    "name": "WALL-M",    "category": "wall",    "series": "skylark250"},
        {"id": "SKYLARK250_DOOR-M1",   "name": "DOOR-M1",   "category": "window",  "series": "skylark250"},
        {"id": "SKYLARK250_WINDOW-M1", "name": "WINDOW-M1", "category": "window",  "series": "skylark250"},
        {"id": "SKYLARK250_ROOF-M10",  "name": "ROOF-M10",  "category": "roof",    "series": "skylark250"},
        {"id": "SKYLARK250_ROOF-M10",  "name": "ROOF-M10",  "category": "roof",    "series": "skylark250"},
    ]
    result1 = validate_configuration(config_valid, stories=1)
    print(format_validation_report(result1))

    print("\n=== Test 2: Invalid configuration (mixed series + excessive opening ratio) ===")
    config_invalid = [
        {"id": "SKYLARK250_FLOOR-M-0", "name": "FLOOR-M-0", "category": "floor",  "series": "skylark250"},
        {"id": "SKYLARK200_WALL-M",    "name": "WALL-M",    "category": "wall",   "series": "skylark200"},
        {"id": "SKYLARK250_DOOR-M1",   "name": "DOOR-M1",   "category": "window", "series": "skylark250"},
        {"id": "SKYLARK250_DOOR-M1",   "name": "DOOR-M1",   "category": "window", "series": "skylark250"},
        {"id": "SKYLARK250_DOOR-M1",   "name": "DOOR-M1",   "category": "window", "series": "skylark250"},
    ]
    result2 = validate_configuration(config_invalid, stories=1)
    print(format_validation_report(result2))

    print("\n=== Test 3: Connection validity checks ===")
    wall_block   = {"name": "WALL-M",   "category": "wall",   "series": "skylark250"}
    window_block = {"name": "DOOR-M1",  "category": "window", "series": "skylark250"}
    roof_block   = {"name": "ROOF-M10", "category": "roof",   "series": "skylark250"}
    floor_block  = {"name": "FLOOR-M",  "category": "floor",  "series": "skylark250"}

    tests = [
        (wall_block,   "top",    roof_block,   "wall top → roof"),
        (wall_block,   "left",   window_block, "wall side → opening"),
        (window_block, "left",   window_block, "opening side → opening (should fail)"),
        (floor_block,  "top",    roof_block,   "floor top → roof (should fail)"),
        (wall_block,   "front",  roof_block,   "wall front → roof (closed face, should fail)"),
    ]

    for a, face, b, desc in tests:
        valid, rule_id, reason = is_connection_valid(a, face, b)
        status = "✅" if valid else "❌"
        print(f"  {status} {desc}")
        if not valid:
            print(f"     → [{rule_id}] {reason}")