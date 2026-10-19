"""Read original Rhino definitions without editing source documents.

Nested transforms are applied before extracting cached render meshes. Bounding-box
fallbacks are explicitly labelled and are never described as exact solid checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import rhino3dm as rh

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIBRARY = ROOT / 'local_assets/design-kit.3dm'
DEFAULT_SUPPLEMENT = ROOT / 'local_assets/supplement.3dm'

def point(p):
    return [round(p.X, 4), round(p.Y, 4), round(p.Z, 4)]

def bounds_union(bounds):
    return [[min(b[0][i] for b in bounds) for i in range(3)],
            [max(b[1][i] for b in bounds) for i in range(3)]]

def box_mesh(bounds):
    lo, hi = bounds
    verts = [[x,y,z] for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
    faces = [[0,2,3],[0,3,1],[4,5,7],[4,7,6],[0,1,5],[0,5,4],
             [2,6,7],[2,7,3],[0,4,6],[0,6,2],[1,3,7],[1,7,5]]
    return verts, faces

def extract_library(path, wanted):
    model = rh.File3dm.Read(str(path))
    if model is None:
        raise ValueError(f'Cannot read Rhino model: {path}')
    if model.Settings.ModelUnitSystem != rh.UnitSystem.Millimeters:
        raise ValueError('Only explicitly millimetre-based source models are accepted.')
    objects = {str(o.Attributes.Id): o for o in model.Objects}
    defs = {str(d.Id): d for d in model.InstanceDefinitions}
    by_name = {d.Name: d for d in model.InstanceDefinitions}
    source = {'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'units':'mm', 'definition_count':len(defs)}

    def flatten(obj, transform, depth=0):
        if depth > 24:
            raise ValueError('Nested definition depth exceeds 24.')
        geom = obj.Geometry
        if isinstance(geom, rh.InstanceReference):
            definition = defs.get(str(geom.ParentIdefId))
            if definition:
                combined = rh.Transform.Multiply(transform, geom.Xform)
                for oid in definition.GetObjectIds():
                    if str(oid) in objects:
                        yield from flatten(objects[str(oid)], combined, depth+1)
        elif isinstance(geom, (rh.Brep, rh.Extrusion, rh.Mesh)):
            transformed = geom.Duplicate()
            transformed.Transform(transform)
            yield transformed

    found = {}
    for name in sorted(wanted & by_name.keys()):
        definition = by_name[name]
        parts = []
        for part_index, oid in enumerate(definition.GetObjectIds()):
            obj = objects.get(str(oid))
            if obj is None:
                continue
            geometries = list(flatten(obj, rh.Transform.Identity()))
            if not geometries:
                continue
            vertices, triangles, bounds = [], [], []
            fallback_count = 0
            for geom in geometries:
                bb = geom.GetBoundingBox()
                bounds.append([point(bb.Min),point(bb.Max)])
                meshes = []
                if isinstance(geom, rh.Mesh):
                    meshes = [geom]
                elif isinstance(geom, rh.Brep):
                    meshes = [face.GetMesh(rh.MeshType.Render) for face in geom.Faces]
                    meshes = [m for m in meshes if m is not None]
                elif isinstance(geom, rh.Extrusion):
                    m = geom.GetMesh(rh.MeshType.Render)
                    meshes = [m] if m else []
                if not meshes:
                    fallback_count += 1
                    v, f = box_mesh(bounds[-1])
                    offset = len(vertices)
                    vertices.extend(v)
                    triangles.extend([[offset+i for i in face] for face in f])
                for mesh in meshes:
                    offset = len(vertices)
                    vertices.extend(point(v) for v in mesh.Vertices)
                    for face in mesh.Faces:
                        a,b,c,d = face
                        triangles.append([offset+a,offset+b,offset+c])
                        if c != d:
                            triangles.append([offset+a,offset+c,offset+d])
            # Deduplicate render vertices without discarding triangles or geometry.
            index, compact, remap = {}, [], []
            for v in vertices:
                key=tuple(v)
                if key not in index:
                    index[key]=len(compact)
                    compact.append(v)
                remap.append(index[key])
            triangles=[[remap[i] for i in f] for f in triangles]
            label = obj.Attributes.Name or f'Part {part_index+1:02d}'
            if isinstance(obj.Geometry, rh.InstanceReference):
                nested = defs.get(str(obj.Geometry.ParentIdefId))
                if nested:
                    label=nested.Name
            parts.append({'part_id':f'{name}:P{part_index+1:02d}', 'label':label,
                          'source_object_id':str(oid),'bbox_mm':bounds_union(bounds),
                          'vertices_mm':compact,'triangles':triangles,
                          'bbox_fallback_solids':fallback_count})
        if parts:
            found[name]={'block_id':name,'bbox_mm':bounds_union([p['bbox_mm'] for p in parts]),
                         'parts':parts,'source':source,
                         'geometry_status':'cached_mesh' if not any(p['bbox_fallback_solids'] for p in parts) else 'mixed_mesh_and_bbox'}
    return found, source

def build_geometry(library=DEFAULT_LIBRARY, supplement=DEFAULT_SUPPLEMENT):
    placements=json.loads((ROOT/'output_placement.json').read_text(encoding='utf-8'))
    wanted={p['block_id'] for p in placements}
    geometry, primary=extract_library(library,wanted)
    sources=[primary]
    if supplement and supplement.exists():
        more, secondary=extract_library(supplement,wanted-geometry.keys())
        geometry.update(more)
        sources.append(secondary)
    destination=ROOT/'robotics/assets/geometry.json'
    destination.write_text(json.dumps({'schema_version':'1.0','units':'mm','sources':sources,
        'missing_block_ids':sorted(wanted-geometry.keys()),'blocks':geometry},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'output':str(destination),'matched':list(geometry),
        'missing':sorted(wanted-geometry.keys()),'parts':{k:len(v['parts']) for k,v in geometry.items()},
        'size_bytes':destination.stat().st_size},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--library',type=Path,default=DEFAULT_LIBRARY)
    parser.add_argument('--supplement',type=Path,default=DEFAULT_SUPPLEMENT)
    args=parser.parse_args()
    build_geometry(args.library,args.supplement)
