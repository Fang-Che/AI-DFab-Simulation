"""Vector research drawing sheets from the same house parameters as the viewer."""
import html,io,math,sys,os
from pathlib import Path
from .estimating import CATEGORY
from .knowledge import JOINTS,SOURCES

class Sheet:
    def __init__(self,code,title,house):
        self.code=code;self.title=title;self.ops=[]
        self.rect(24,24,1152,802,fill='white',stroke='#193747')
        self.text(50,62,code+'  '+title,23)
        self.text(50,89,f"AI-DFab | {house['layout_name']} / {house['levels']} 層 | 尺寸 mm | 施工協調圖 R11 | {house.get('design_id','')}",12,'#527180')
        self.line(50,105,1150,105,'#b8cbd2')
        self.line(50,773,1150,773,'#b8cbd2')
        self.text(50,796,'研究／協調用施工圖說草稿。非核准施工圖、非結構驗算、非 CNC 刀路。',12,'#a04a31')
        self.text(50,815,'以尺寸標註為準；縮放列印時參照比例尺。接頭、樓梯、洞口補強及防水細部待深化。',11,'#527180')
    def line(self,x1,y1,x2,y2,color='#193747',width=1,dash=False):self.ops.append(('line',[x1,y1,x2,y2,color,width,dash]))
    def rect(self,x,y,w,h,fill='none',stroke='#193747',width=1):self.ops.append(('rect',[x,y,w,h,fill,stroke,width]))
    def poly(self,points,fill='none',stroke='#193747',width=1):self.ops.append(('poly',[points,fill,stroke,width]))
    def text(self,x,y,text,size=13,color='#193747'):self.ops.append(('text',[x,y,str(text),size,color]))
    def dimension(self,x1,y1,x2,y2,label):
        self.line(x1,y1,x2,y2,'#527180')
        for x,y in [(x1,y1),(x2,y2)]:self.line(x-5,y-5,x+5,y+5,'#527180')
        self.text(x1-58 if x1==x2 else (x1+x2)/2+6,(y1+y2)/2-7,label,12,'#527180')
    def svg(self):
        out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 850" role="img" aria-label="'+html.escape(self.title)+'"><style>text{font-family:Microsoft JhengHei,Arial,sans-serif}</style>']
        for kind,a in self.ops:
            if kind=='line':
                x,y,xx,yy,c,w,d=a;out.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{c}" stroke-width="{w}"'+(' stroke-dasharray="6 5"' if d else '')+'/>')
            elif kind=='rect':
                x,y,w,h,f,c,sw=a;out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{f}" stroke="{c}" stroke-width="{sw}"/>')
            elif kind=='poly':
                points,f,c,sw=a;out.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{f}" stroke="{c}" stroke-width="{sw}"/>')
            else:
                x,y,t,size,c=a;out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}">{html.escape(t)}</text>')
        return ''.join(out)+'</svg>'

def plan(h,level):
    from .technical_drawings import architectural_plan
    return architectural_plan(h,level)

def legacy_plan(h,level):
    s=Sheet(f'A10{level}',f'{level}F 平面配置／裝配定位',h)
    scale=min(490/h['length'],680/h['width']);ox=170;oy=170
    def p(x,y):return ox+x*scale,oy+y*scale
    cells={tuple(c) for c in h['footprint_cells']}
    for i,j in cells:
        x,y=p(i*604,j*600);s.rect(x,y,604*scale,600*scale,'#f4f9f8','#d6e3e6',.5)
    interior=h.get('interior',{})
    if interior.get('config',{}).get('floor')==level:
        for r in interior['rooms']:
            x,y,xx,yy=r['box'];s.rect(*p(x,y),(xx-x)*scale,(yy-y)*scale,'#e4eee9' if r['meets_area'] else '#f8dfd3','#cadbd6',.5)
            s.text(*p(x+70,(y+yy)/2),r['name'],10);s.text(*p(x+70,(y+yy)/2+340),f"{r['area_m2']:.1f} m²",10)
        for part in interior['parts']:
            if part['header']:continue
            lo,hi=part['lo'],part['hi'];s.rect(*p(lo[0],lo[1]),(hi[0]-lo[0])*scale,(hi[1]-lo[1])*scale,'#876a9f','#654c7b',.8)
        for door in interior['doors']:
            s.line(*p(*door['a']),*p(*door['b']),'#cf963e',2,True)
    # Openings are projected from the exact module meshes at the selected storey.
    for it in h['items']:
        if it['level']!=level or it['category'] not in ['wall','door','window','corner']:continue
        v=h['meshes'][it['key']]['v'];c=math.cos(math.radians(it['rotation']));sn=math.sin(math.radians(it['rotation']))
        xs=[c*q[0]-sn*q[1]+it['translation'][0] for q in v];ys=[sn*q[0]+c*q[1]+it['translation'][1] for q in v]
        lo,hi=min(xs),max(xs);bottom,top=min(ys),max(ys);x,y=p(lo,bottom)
        col={'wall':'#385c68','corner':'#d3a85d','door':'#f0c385','window':'#83c2d4'}[it['category']]
        s.rect(x,y,(hi-lo)*scale,(top-bottom)*scale,col,col,.5)
    for a,b,_ in h['boundary_edges']:s.line(*p(a[0]*604,a[1]*600),*p(b[0]*604,b[1]*600),'#193747',1.2)
    if h['stair_opening_mm']:
        x1,y1,x2,y2=h['stair_opening_mm'];x,y=p(x1,y1);s.rect(x,y,(x2-x1)*scale,(y2-y1)*scale,'white','#d27b36',1.4)
        for k in range(16):s.line(*p(x1,y1+k*280),*p(x2,y1+k*280),'#8b9ba2',.7)
        s.line(*p((x1+x2)/2,y1+300),*p((x1+x2)/2,y2-300),'#c07134',2)
        s.text(x+5,y+15,'UP' if level==1 else '洞口',10,'#b76b30')
        s.text(850,325,'樓梯洞口 1208 × 4200',13)
        s.text(850,346,'16 級高差／15 片踏步（示意）',12)
        s.text(850,367,'補強、支承、護欄與淨高待設計',12,'#a04a31')
    s.dimension(ox,oy-27,ox+h['width']*scale,oy-27,f"{h['width']:.0f}")
    s.dimension(ox-35,oy,ox-35,oy+h['length']*scale,f"{h['length']:.0f}")
    s.line(*p(-200,9000),*p(h['width']+200,9000),'#c07134',1,True)
    s.text(*p(-500,9000),'B',13,'#c07134');s.text(*p(h['width']+250,9000),'B',13,'#c07134')
    for j in range(0,23,2):
        x,y=p(h['width']+850,j*600);s.text(x,y+4,f'{j*600:.0f}',9,'#6e8995')
    s.text(850,165,'圖例／範圍',16)
    for k,(label,col) in enumerate([('來源牆模組','#385c68'),('窗洞（非窗成品）','#83c2d4'),('門洞','#f0c385'),('轉角核心（示意）','#d3a85d')]):
        s.rect(850,187+k*29,16,12,col,col);s.text(875,198+k*29,label,12)
    s.text(850,425,'B-B 主屋橫向示意見 A201。',12)
    s.text(850,446,'紫色：研究用非承重隔間。' if interior.get('parts') else '尚未配置室內隔間。',12)
    s.text(850,487,'未配置機電或衛浴設備。',12)
    s.text(850,467,'門窗定位依目前展示方案。',12)
    s.text(850,510,f"本層標高 +{(level-1)*h['storey_height_mm']:.0f}",14)
    s.text(850,534,f"全案樓板面積 {h['floor_area_m2']:.2f} m²",13)
    s.text(850,555,'（全案外框計，扣樓梯洞口）',11,'#527180')
    s.line(ox,720,ox+2000*scale,720,'#193747',3);s.text(ox,741,'0',11);s.text(ox+2000*scale-20,741,'2000 mm',11)
    return s

def elevations(h):
    from .technical_drawings import section_sheet
    return section_sheet(h)

def legacy_elevations(h):
    s=Sheet('A201','立面與橫向構架剖面示意',h);scale=.052;zmax=h['bounds_mm'][1][2];eave=2400+(h['levels']-1)*2780
    def p(x,z):return 130+x*scale,650-z*scale
    w=5436
    for level in range(h['levels']):
        z=level*2780;s.rect(*p(0,z+2400),w*scale,2400*scale,'#f3f8f7','#527180')
        s.rect(*p(0,z),w*scale,380*scale,'#d5e8e6','#527180')
        for x in range(0,5401,600):s.line(*p(x,z),*p(x,z+2400),'#9eb5bd',.6)
        s.text(*p(w+250,z),f'+{z:.0f}  {level+1}F',12)
    s.poly([p(0,eave),p(w/2,zmax-370),p(w,eave)],'#f3f8f7','#527180')
    s.poly([p(0,eave+370),p(w/2,zmax),p(w,eave+370),p(w,eave),p(w/2,zmax-370),p(0,eave)],'#dce5f5','#4569a6')
    s.dimension(*p(0,-800),*p(w,-800),'5436')
    s.dimension(*p(-550,-380),*p(-550,zmax),f'{zmax+380:.0f}')
    s.text(115,145,'主屋横向示意 B-B',16)
    s.text(660,145,'樓層／裝配對照',18)
    stages=['1F 樓板 → 室內隔間 → 外牆']
    if h['levels']==2:stages+=['2F 樓板與樓梯洞口補強','樓梯／防護 → 2F 室內 → 外牆']
    stages+=['山牆封板 → 雙坡屋頂']
    for k,t in enumerate(stages):
        s.rect(650,175+70*k,450,52,'#edf4f5','#d2e0e5');s.text(670,206+70*k,f'{k+1:02d}  {t}',15)
    y=210+70*len(stages)
    for t in ['樓層間距：2780 mm = 2400 牆高 + 380 樓板深度。','圖示為主屋横向，L／U 交叉屋頂不在此剖面完整呈現。',
              '樓梯洞口樓板使用示意分段，不能直接作為加工檔。','屋谷、柱腳、牆—樓板與牆—屋頂接頭待詳設。','二樓承載、側向穩定與樓梯規範尚未驗算。']:
        s.text(650,y,t,12);y+=27
    s.text(120,741,'屋面輪廓以來源最高點作定位參考；本頁不表達每一接頭或構件截面。',12,'#527180')
    return s

def connections(h):
    s=Sheet('A501','接合形式與工具／核對項目',h)
    for n,j in enumerate(JOINTS):
        y=155+n*111;s.rect(55,y-23,1090,101,'#f7fafb','#d4e2e6')
        s.text(72,y,j['id']+'  '+j['name'],16)
        s.text(72,y+25,j['method']+' | '+j['tools'],12)
        s.text(72,y+48,j['verification'],12,'#a04a31')
        s.text(670,y,j['source'],12,'#527180')
        # Symbolic joint diagrams; not dimensions or production geometry.
        if n==0:
            s.poly([(940,y+15),(985,y+15),(985,y+30),(1000,y+30),(1000,y+15),(1045,y+15),(1045,y+58),(940,y+58)],'#c5d8dc')
            s.rect(987,y-5,11,32,'#e3b967','#9c7233')
        elif n==3:
            s.rect(950,y+12,85,43,'#c5d8dc');s.rect(970,y+12,42,24,'white','#527180')
            for x in [970,1012]:s.rect(x-4,y+30,8,8,'white','#527180')
        else:s.line(950,y+37,1040,y+37,'#6d8c95',5);s.line(995,y+15,995,y+59,'#c38a40',6)
    s.text(65,743,'符號圖僅供辨識。來源 MFG＝製造指南；USE＝2018 使用指南；DFMA＝2019 DfMA 手冊。',12)
    return s

def quantities(h,takeoff,cost):
    s=Sheet('A601','材料、成本與待確認清單',h)
    s.text(65,145,'構件統計（依目前方案）',18)
    y=180
    for r in takeoff['rows']:
        s.text(65,y,r['name'],14);s.text(220,y,f"{r['modules']} 件",14);s.text(330,y,f"預算面積 {r['area_m2']:.2f} m²",12);y+=27
    s.text(640,145,'TWD 情境試算（尚未詢價）',18)
    y=180
    for r in cost['lines']:
        s.text(640,y,r['項目'],12);s.text(1000,y,f"{r['小計 TWD']:,.0f}",13);y+=31
    s.text(640,y+12,f"預備金 {cost['contingency']:,.0f}  /  範圍小計 {cost['total']:,.0f}",16)
    s.text(65,520,f"18 mm 板材預算張數：{cost['sheets_budget']} 張；未經排版確認。",15)
    s.text(65,546,'來源板件按外框面積；隔間按雙面板面積；其餘示意構件按半表面積。骨架、接頭及特殊材料待核對。',12)
    s.text(65,572,'接頭與緊固件採暫列金：實際規格及數量未知。未包含完整建築各工種，不是總工程報價。',12,'#a04a31')
    s.text(65,604,'排除：'+ '、'.join(cost['exclusions']),11)
    s.text(65,647,'文件依據（使用者提供；歷史版本）',15)
    for i,source in enumerate(SOURCES):s.text(65,672+23*i,source['id']+' | '+source['title']+' | '+source['version'],12)
    return s

def drawing_sheets(h,takeoff,cost):
    from .technical_drawings import facade_sheet,detail_sheets
    return [plan(h,l) for l in range(1,h['levels']+1)]+[elevations(h),facade_sheet(h),connections(h)]+detail_sheets(h)+[quantities(h,takeoff,cost)]

def pdf_bytes(sheets):
    try:import reportlab
    except ImportError:
        bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'
        if bundled.exists():sys.path.append(str(bundled))
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import toColor as HexColor
    from reportlab.lib.pagesizes import A3,landscape
    font=Path(os.environ.get('WIKIHOUSE_PDF_FONT',r'C:\Windows\Fonts\msjh.ttc'))
    if not font.exists():raise FileNotFoundError('請以 WIKIHOUSE_PDF_FONT 指定支援繁體中文的 TrueType 字型。')
    if 'WikiHouseCJK' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('WikiHouseCJK',str(font),subfontIndex=0))
    output=io.BytesIO();pw,ph=landscape(A3);c=canvas.Canvas(output,pagesize=(pw,ph))
    c.setTitle('AI-DFab Research Drawing Set')
    for sheet in sheets:
        c.saveState();c.scale(pw/1200,ph/850)
        for kind,a in sheet.ops:
            if kind=='text':
                x,y,t,sz,col=a;c.setFillColor(HexColor(col));c.setFont('WikiHouseCJK',sz);c.drawString(x,850-y,t)
            elif kind=='line':
                x,y,xx,yy,col,w,d=a;c.setStrokeColor(HexColor(col));c.setLineWidth(w);c.setDash([6,5] if d else []);c.line(x,850-y,xx,850-yy);c.setDash([])
            elif kind=='rect':
                x,y,w,h,f,col,sw=a;c.setStrokeColor(HexColor(col));c.setLineWidth(sw)
                if f!='none':c.setFillColor(HexColor(f))
                c.rect(x,850-y-h,w,h,stroke=1,fill=int(f!='none'))
            else:
                pts,f,col,sw=a;c.setStrokeColor(HexColor(col));c.setLineWidth(sw)
                if f!='none':c.setFillColor(HexColor(f))
                p=c.beginPath();p.moveTo(pts[0][0],850-pts[0][1])
                for x,y in pts[1:]:p.lineTo(x,850-y)
                p.close();c.drawPath(p,stroke=1,fill=int(f!='none'))
        c.restoreState();c.showPage()
    c.save();return output.getvalue()
