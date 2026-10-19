"""Run inside Rhino 8 Python 3 ScriptEditor. Sources remain untouched.

Use the exported simulation.3dm for a static review or this player for animation.
Only this script's named layer is replaced. ESC stops playback.
"""
import json
import time
import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rd
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System.Drawing

def run():
    path=rs.OpenFileName('選取 AI-DFab 匯出的 scene.json','JSON Files (*.json)|*.json||')
    if not path:return
    with open(path,encoding='utf-8') as f:data=json.load(f)
    if data.get('units')!='mm':raise ValueError('Scene unit must be mm.')
    doc=Rhino.RhinoDoc.ActiveDoc
    scale=Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Millimeters,doc.ModelUnitSystem)
    layer_name='AI_DFab_Robotics_Preview'
    layer=doc.Layers.FindName(layer_name)
    if layer is None:
        layer=rd.Layer();layer.Name=layer_name
        li=doc.Layers.Add(layer)
    else:li=layer.Index
    for obj in list(doc.Objects.FindByLayer(layer_name) or []):
        if obj.Attributes.GetUserString('AI_DFab_preview')=='1':doc.Objects.Delete(obj,True)
    def attr(name,color):
        a=rd.ObjectAttributes();a.LayerIndex=li;a.Name=name
        a.SetUserString('AI_DFab_preview','1')
        a.ObjectColor=System.Drawing.Color.FromArgb(*color);a.ColorSource=rd.ObjectColorSource.ColorFromObject
        return a
    def pt(p):return rg.Point3d(*[v*scale for v in p])
    bad={c['obstacle_id'] for c in data['collisions']}
    for m in data['modules']:
        if m['category']=='roof':continue
        bb=rg.BoundingBox(pt(m['bbox_mm'][0]),pt(m['bbox_mm'][1]))
        doc.Objects.AddBrep(bb.ToBrep(),attr(m['instance_id'],(210,90,75) if m['instance_id'] in bad else (158,185,201)))
    mesh=rg.Mesh()
    for v in data['target_mesh']['vertices_mm']:mesh.Vertices.Add(pt(v))
    for f in data['target_mesh']['triangles']:mesh.Faces.AddFace(*f)
    mesh.Normals.ComputeNormals();mesh.Compact()
    oid=doc.Objects.AddMesh(mesh,attr(data['target_id'],(219,171,94)))
    route=[pt(p) for p in data['route_mm']]
    doc.Objects.AddPolyline(route,attr('Preinstallation approach · final insertion not checked',(29,134,128)))
    doc.Views.ActiveView.ActiveViewport.SetProjection(Rhino.Display.DefinedViewportProjection.Perspective,'Perspective',False)
    doc.Views.ActiveView.ActiveViewport.ZoomExtents();doc.Views.Redraw()
    if rs.GetString('播放吊裝路徑？','Yes',['Yes','No'])!='Yes':return
    start_center=pt(data['target_center_mm'])
    lengths=[route[i].DistanceTo(route[i+1]) for i in range(len(route)-1)]
    total=sum(lengths)
    for step in range(101):
        if sc.escape_test(False):break
        left=total*step/100
        point=route[-1]
        for i,length in enumerate(lengths):
            if left<=length and length>0:
                point=route[i]+(route[i+1]-route[i])*(left/length);break
            left-=length
        moved=mesh.DuplicateMesh();moved.Transform(rg.Transform.Translation(point-start_center))
        doc.Objects.Replace(oid,moved);doc.Views.Redraw();Rhino.RhinoApp.Wait();time.sleep(.04)
    print('播放完成。顯示為幾何預檢，終點為安裝前接近點。')

if __name__=='__main__':run()
