"""Browser-local lifting playback; current contact is separate from route precheck."""
import json
from .core import ROOT,transform,center

def viewer_html(geometry,scenario,result,route):
    target=scenario['target'];vertices=[];faces=[]
    for part in geometry['blocks'][target['block_id']]['parts']:
        offset=len(vertices)
        vertices.extend([transform(v,target['rotation_deg'],target['translation_mm']) for v in part['vertices_mm']])
        faces.extend([[j+offset for j in f] for f in part['triangles']])
    center_mm=center(target['bbox_mm'])
    # translation_mm already includes the imported placement datum correction.
    data=dict(target=target,vertices=vertices,faces=faces,center=center_mm,obstacles=scenario['obstacles'],route=route,crane=result['crane_base_mm'])
    root=ROOT/'robotics';html=(root/'lift_viewer.html').read_text(encoding='utf8')
    return html.replace('__THREE__',(root/'assets/vendor/three.min.js').read_text(encoding='utf8')).replace('__ORBIT__',(root/'assets/vendor/OrbitControls.js').read_text(encoding='utf8')).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
