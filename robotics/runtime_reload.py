"""Refresh locally edited feature modules on rerun when the watcher is disabled."""
import importlib
import sys
from pathlib import Path

_signature=None

def refresh():
    global _signature
    root=Path(__file__).parent
    signature=tuple((p.name,p.stat().st_mtime_ns) for p in sorted(root.glob('*.py')))
    if signature==_signature:return
    # Dependency order matters: consumers hold function references from imports.
    names=['core','knowledge','construction','house','housing_plan','interior','visuals','assembly',
           'export','drawings','technical_drawings','panel_layout','method_drawings','lift_viewer','design_ui','ui_next','ui']
    for name in names:
        module=sys.modules.get('robotics.'+name)
        if module is not None:importlib.reload(module)
    _signature=signature
