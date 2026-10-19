"""Auditable scenario takeoff: module counts exact, panel budgets approximate."""
import math
from collections import Counter,defaultdict
from functools import lru_cache
import numpy as np
from .core import ROOT,read_json

CATEGORY={'floor':'樓板','corner':'角柱','wall':'牆','door':'門洞','window':'窗洞','closure':'山牆封板','roof':'屋頂',
          'stair':'樓梯踏步','trimmer':'洞口補強梁','guard':'臨時護欄','partition':'非承重隔間面板'}
DEFAULT_RATES={'sheet_price':1800.,'cnc_hour':800.,'cnc_minutes_sheet':22.5,'crew_hour':1200.,
               'equipment_hour':600.,'hardware_allowance':12000.,'transport_allowance':10000.,
               'contingency_percent':10.,'utilization':.8,'waste_percent':5.,'extra_materials':0.}

RATE_LABELS={'sheet_price':('18 mm 板材','TWD／張'),'cnc_hour':('CNC 加工','TWD／小時'),
    'crew_hour':('現場整組班組','TWD／小時'),'equipment_hour':('現場設備','TWD／小時'),
    'hardware_allowance':('接頭／緊固件暫列金','TWD／批'),'transport_allowance':('運輸暫列金','TWD／批'),
    'extra_materials':('其他材料／外購件','TWD／批'),'cnc_minutes_sheet':('CNC 加工時間','分鐘／張'),
    'contingency_percent':('預備金','%'),'utilization':('排版利用率','比例'),'waste_percent':('另加損耗','%')}

def rate_provenance(rates):
    rows=[]
    for key,(label,unit) in RATE_LABELS.items():
        changed=rates[key]!=DEFAULT_RATES[key]
        source='使用者設定；未附報價或實測憑證' if changed else '程式示範假設；無供應商或市場價格依據'
        if not changed and key=='cnc_minutes_sheet':source='MFG p.9 歷史例 15–30 分鐘／張；22.5 為示範中點，未校準'
        elif not changed and key in ['contingency_percent','utilization','waste_percent']:source='程式示範計算假設；未經實測校準'
        rows.append({'項目':label,'目前值':rates[key],'單位':unit,'來源／狀態':source})
    return rows

@lru_cache(maxsize=4)
def source_measures(revision=0):
    blocks={}
    for name in ['geometry','demo_geometry','gable_geometry']:
        blocks.update(read_json(ROOT/f'robotics/assets/{name}.json')['blocks'])
    out={}
    for key,b in blocks.items():
        area=0.;oversize=0;nonplanar=0
        for p in b['parts']:
            v=np.array(p['vertices_mm']);_,axes=np.linalg.eigh(np.cov((v-v.mean(0)).T))
            ext=np.sort(np.ptp((v-v.mean(0))@axes,axis=0))
            area+=ext[1]*ext[2]/1e6
            oversize+=int(ext[2]>2440+2 or ext[1]>1220+2)
            nonplanar+=int(ext[0]>40)
        out[key]={'area':area,'parts':len(b['parts']),'oversize':oversize,'nonplanar':nonplanar}
    return out

def quantity_takeoff(house):
    source=source_measures();groups=defaultdict(lambda:{'modules':0,'source_parts':0,'source_area':0.,'provisional_area':0.,'oversize':0,'nonplanar':0})
    bom=Counter((i['level'],i['category'],i['key'],i['evidence']) for i in house['items'])
    for it in house['items']:
        r=groups[it['category']];r['modules']+=1
        if it['evidence']=='source_mesh' and it['key'] in source:
            s=source[it['key']];r['source_parts']+=s['parts'];r['source_area']+=s['area'];r['oversize']+=s['oversize'];r['nonplanar']+=s['nonplanar']
        elif it['evidence']=='interior_concept':
            r['provisional_area']+=it['panel_area_m2']
        else:
            # Half the surface area is a transparent skin-area proxy. It is not
            # a solid timber volume or a confirmed cutting-list conversion.
            mesh=house['meshes'][it['key']];v=np.array(mesh['v']);f=np.array(mesh['f'])
            tri=v[f];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()/4e6
            r['provisional_area']+=float(area)
    rows=[{'category':cat,'name':CATEGORY.get(cat,cat),**v,'area_m2':v['source_area']+v['provisional_area']} for cat,v in groups.items()]
    bill=[{'樓層':f'{level}F','類別':CATEGORY.get(cat,cat),'構件定義':key,'數量':n,'依據':evidence} for (level,cat,key,evidence),n in sorted(bom.items())]
    return {'rows':rows,'bom':bill,'modules':len(house['items']),'source_parts':sum(r['source_parts'] for r in rows),
            'source_area_m2':sum(r['source_area'] for r in rows),'provisional_area_m2':sum(r['provisional_area'] for r in rows),
            'area_m2':sum(r['area_m2'] for r in rows),'oversize':sum(r['oversize'] for r in rows),
            'nonplanar':sum(r['nonplanar'] for r in rows),'sheet_size_mm':[2440,1220,18],
            'basis':'來源子物件平面主軸外框面積 + 隔間雙面板面積 + 其餘示意構件半表面積；未排版，隔間骨架接頭待核對，非精確下單表'}

def cost_estimate(house,takeoff,rates=None,area_override=None):
    r={**DEFAULT_RATES,**(rates or {})}
    if any(not math.isfinite(float(v)) or float(v)<0 for v in r.values()):raise ValueError('Rates must be finite and nonnegative')
    if not 0<r['utilization']<=1:raise ValueError('Utilization must be in (0,1]')
    area=takeoff['area_m2'] if area_override is None else float(area_override)
    if not math.isfinite(area) or area<0:raise ValueError('Invalid material area')
    sheets=math.ceil(area/(2.440*1.220*r['utilization'])*(1+r['waste_percent']/100))
    cnc_hours=sheets*r['cnc_minutes_sheet']/60
    hours=house['time_estimate']['hours']
    rows=[['18 mm 板材（面積預算張數）',sheets,'張',r['sheet_price']],
          ['CNC 製造（情境工時）',cnc_hours,'小時',r['cnc_hour']],
          ['現場班組（整組費率）',hours,'小時',r['crew_hour']],
          ['現場設備（情境費率）',hours,'小時',r['equipment_hour']],
          ['接頭／緊固件暫列金',1,'批',r['hardware_allowance']],
          ['運輸暫列金',1,'批',r['transport_allowance']],
          ['其他材料／外購件暫列金',1,'批',r['extra_materials']]]
    money_keys=['sheet_price','cnc_hour','crew_hour','equipment_hour','hardware_allowance','transport_allowance','extra_materials']
    provenance={row['項目']:row for row in rate_provenance(r)}
    lines=[{'項目':name,'數量':qty,'單位':unit,'單價 TWD':price,'小計 TWD':qty*price,
            '單價依據':provenance[RATE_LABELS[key][0]]['來源／狀態']} for (name,qty,unit,price),key in zip(rows,money_keys)]
    subtotal=sum(x['小計 TWD'] for x in lines);contingency=subtotal*r['contingency_percent']/100
    return {'currency':'TWD','rates':r,'lines':lines,'sheets_budget':sheets,'panel_area_m2':area,'cnc_hours':cnc_hours,
            'subtotal':subtotal,'contingency':contingency,'total':subtotal+contingency,'quote_status':'示範預算／尚未詢價；非市場報價',
            'rate_provenance':rate_provenance(r),
            'exclusions':['基地與基礎','結構設計與審查','外牆／屋面完整防水與隔熱系統','門窗成品','機電與裝修','稅費'],
            'unknowns':['接頭／螺絲／銷件規格與實際數量','非標準構件實際分板及材料','排版後板材張數','板材等級與供應商報價']}
