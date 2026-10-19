import json
from pathlib import Path
from datetime import datetime
from .core import ROOT,center,path_position,size,sweep_box
from .visuals import module_mesh

def scene_snapshot(scene,geometry,scenario,result,progress=.45):
    target=scenario['target'];pos=path_position(result['route_mm'],progress)
    v,f=module_mesh(target,geometry,pos)
    return {'schema_version':'1.0','units':'mm','evidence_level':'digital_geometric_prescreen',
            'modules':[{k:m[k] for k in ['instance_id','block_id','category','bbox_mm','geometry_status']} for m in scenario['obstacles']],
            'target_id':target['instance_id'],'target_center_mm':pos,'target_mesh':{'vertices_mm':v,'triangles':f},
            'route_mm':result['route_mm'],'collisions':result['collisions'],'endpoint':'preinstallation_pose',
            'datum_mode':scene['datum_mode']}

def rhino_file(snapshot,path):
    import rhino3dm as rh
    from .import_geometry import box_mesh
    doc=rh.File3dm();doc.Settings.ModelUnitSystem=rh.UnitSystem.Millimeters
    layers={}
    for name,color in [('Installed envelopes',(150,175,192,255)),('Collision envelopes',(213,83,75,255)),
                       ('Moving module',(218,169,96,255)),('Lift path',(30,141,133,255))]:
        layer=rh.Layer();layer.Name=name;layer.Color=color
        layers[name]=doc.Layers.Add(layer)
    def add_mesh(v,f,layer,uid,bid):
        mesh=rh.Mesh()
        for p in v:mesh.Vertices.Add(*p)
        for face in f:mesh.Faces.AddFace(*face)
        mesh.Normals.ComputeNormals();mesh.Compact()
        attr=rh.ObjectAttributes();attr.LayerIndex=layers[layer];attr.Name=uid
        attr.SetUserString('instance_id',uid);attr.SetUserString('block_id',bid)
        attr.SetUserString('evidence_level','display_mesh_only')
        doc.Objects.AddMesh(mesh,attr)
    vertices=snapshot['target_mesh']['vertices_mm']
    lo=[min(p[i] for p in vertices) for i in range(3)];hi=[max(p[i] for p in vertices) for i in range(3)]
    pos=center([lo,hi]);half=[v/2 for v in size([lo,hi])]
    bad={m['instance_id'] for m in snapshot['modules'] if sweep_box(pos,pos,half,m['bbox_mm']) is not None}
    for m in snapshot['modules']:
        v,f=box_mesh(m['bbox_mm'])
        add_mesh(v,f,'Collision envelopes' if m['instance_id'] in bad else 'Installed envelopes',m['instance_id'],m['block_id'])
    add_mesh(snapshot['target_mesh']['vertices_mm'],snapshot['target_mesh']['triangles'],'Moving module',snapshot['target_id'],'selected_roof')
    line=rh.PolylineCurve([rh.Point3d(*p) for p in snapshot['route_mm']])
    attr=rh.ObjectAttributes();attr.LayerIndex=layers['Lift path'];attr.Name='Preinstallation approach route'
    doc.Objects.AddCurve(line,attr)
    if not doc.Write(str(path),8):raise RuntimeError('Rhino 檔案輸出失敗。')

def export_run(scene,geometry,scenario,result,report,progress=.45):
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out=ROOT/'robotics/runs'/stamp
    out.mkdir(parents=True,exist_ok=False)
    snapshot=scene_snapshot(scene,geometry,scenario,result,progress)
    for name,data in [('report.json',report),('scene.json',snapshot),
                      ('design_feedback.json',{'source_hash':report['source_hash'],'recommendations':report['recommendations'],'approved_design_changes':[]})]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    rhino_file(snapshot,out/'simulation.3dm')
    # Shared display state only. It never overwrites the original placement JSON.
    live=ROOT/'robotics/rhino_state.json'
    temp=live.with_suffix('.tmp')
    temp.write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
    temp.replace(live)
    return out
