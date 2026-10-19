"""Versioned, page-addressed evidence from the three user-provided guides."""
SOURCES=[
 {'id':'MFG','title':'Wikihouse Manufacturing Guide','version':'1.0 / 2019','file':'Wikihouse Manufacturing Guide.pdf','pages':11},
 {'id':'USE','title':'Using WikiHouse','version':'2018 / WHouse_Guide_1.1','file':'WHouse_Guide_1.1.pdf','pages':20},
 {'id':'DFMA','title':'The DfMA Housing Manual','version':'1.1 / May 2019','file':'The DfMA Housing Manual.pdf','pages':50}]
RULES=[
 {'id':'M01','source':'MFG pp.2–4','topic':'板材與製造','evidence':'可加工 2440 × 1220 mm 板材的 CNC；常見 18 mm 結構用合板或 OSB。','application':'材料試算採 2440 × 1220 × 18 mm；材種與供應商仍需指定。'},
 {'id':'M02','source':'MFG pp.5–6','topic':'生產資訊','evidence':'分層 2D CAD、零件清單、CAM 轉換及首件試組裝。','application':'構件與材料清單附編號；研究圖說與可執行 CAM 分開標示。'},
 {'id':'M03','source':'MFG pp.7–8','topic':'公差','evidence':'0.25 mm offset、18 ± 0.5 mm 都是手冊例子；實際以各檔公差與試組結果為準。','application':'提示應記錄量測厚度與試組狀態；不將示例公差自動套入所有 Skylark 接頭。'},
 {'id':'M04','source':'MFG p.9','topic':'刀具／製造時間','evidence':'該版 dogbone 通常容許不大於 10 mm 刀具；歷史製造例約 15–30 分鐘／張。','application':'成本中 CNC 分鐘可改；不輸出主軸轉速、進給或直接可用刀路。'},
 {'id':'U01','source':'USE p.6','topic':'技術版本','evidence':'2018 表列 Wren 2 層／3.6 m、Blackbird 3 層／4.5 m，分屬不同系統。','application':'二層選項是目前 Skylark 模型的幾何研究，不能以此表證明 5.436 m 跨距的承載能力。'},
 {'id':'U02','source':'USE pp.8–10','topic':'材料與交付','evidence':'結構板材、螺絲固定；交付包含詳模、材料清單、加工檔及組裝手冊。','application':'統一方案編號，讓模型、圖說、清單與成本保持一致。'},
 {'id':'D01','source':'DFMA pp.18–21','topic':'裝配原則','evidence':'減少材料／零件種類、乾式接合、編碼、防錯、設計公差及降低高處作業風險。','application':'依樓層編排裝配，二樓洞口與護欄列出；工具／接合依工序整理。'},
 {'id':'D02','source':'DFMA pp.26–28,42,46,48','topic':'成本回饋','evidence':'配置時同步計算成本／材料／任務；以透明單價與試點實測持續修正。','application':'TWD 可編輯單價、明示數量依據、排除項與未報價項。'}]
TOOLS=[
 {'stage':'板材進場／試組','tools':'游標卡尺、捲尺、直角尺、標籤／記號筆','connection':'量測厚度、對位與零件編碼','joint':'槽寬／板厚試配','source':'MFG pp.6–8；DFMA p.20','status':'量測工具為執行該檢查的配置建議'},
 {'stage':'CNC 製造','tools':'CNC router、真空床、壓縮銑刀、集塵系統','connection':'數位輪廓切削','joint':'內角 dogbone 刀具避空','source':'MFG pp.2,9','status':'刀具直徑、進給與道次需依設備試切'},
 {'stage':'板件預組','tools':'木槌／橡膠槌、平整工作台、定位夾具','connection':'乾式插接／敲合','joint':'板槽嵌合；crush joint 壓配接頭','source':'MFG pp.3,7–8','status':'壓配屬該版原則，需逐一確認目前構件接頭'},
 {'stage':'構件固定','tools':'電動起子、適用批頭；扳手（若工程設計採螺栓）','connection':'可拆螺絲／螺栓固定','joint':'板材螺絲連接／工程指定金屬連接件','source':'USE p.8；DFMA p.19','status':'螺絲數量、直徑、長度與邊距未由手冊確定'},
 {'stage':'木銷／小零件整理','tools':'分裝盒、標籤、木槌','connection':'銷件定位','joint':'peg 木銷（是否適用需對照構件）','source':'MFG p.4','status':'手冊提及 pegs 包裝，未提供此模型用量'},
 {'stage':'現場定位／二樓','tools':'水平儀、定位治具、臨時支撐、作業平台與洞口護欄','connection':'構件對位、逐層穩定與臨時固定','joint':'牆—樓板／牆—屋頂／洞口補強接點','source':'DFMA pp.19–21；使用者二樓示意圖','status':'工作平台配置建議；臨時支撐及承載待規劃'},
 {'stage':'機器人搬運','tools':'六軸工業機械手臂、四吸盤末端夾具、真空監測／治具','connection':'取板、轉向、定位及退離','joint':'夾持面與插接面分開','source':'本研究機械手臂模型與模擬假設','status':'吸盤配置與承載未驗證，非手冊指定設備'},
 {'stage':'製造作業防護','tools':'護目鏡、耳部防護、粉塵防護及依工序選擇的防護用品','connection':'製造與搬運防護','joint':'不適用','source':'MFG p.3','status':'實際使用依設備與工序管理'}]
JOINTS=[
 {'id':'J01','name':'板—板槽口插接','method':'乾式嵌合','geometry':'來源網格可見槽口／凸榫；尚未自動識別每一接頭','source':'MFG pp.7–8 + 模型觀察','tools':'木槌、定位夾具','verification':'插入方向、公差、接觸與鎖固待試組'},
 {'id':'J02','name':'壓配 crush joint','method':'一次性敲合','geometry':'手冊描述；未認定所有 Skylark 槽口皆屬壓配','source':'MFG p.7','tools':'木槌、首件試配樣片','verification':'干涉量與可拆性待確認'},
 {'id':'J03','name':'螺絲／工程指定螺栓','method':'機械式固定','geometry':'目前未建模緊固件','source':'USE p.8；DFMA p.19','tools':'起子／適用扳手','verification':'規格、數量、孔位、扭矩待工程設計'},
 {'id':'J04','name':'dogbone 內角避空','method':'加工幾何','geometry':'圓刀內角退刀空間，不是獨立結構接頭','source':'MFG p.9','tools':'CNC 銑刀、量測工具','verification':'刀徑與加工檔內角對照'},
 {'id':'J05','name':'二樓／樓梯洞口連接','method':'承托、補強與固定（概念）','geometry':'非標準樓板、洞口補強梁與護欄為示意','source':'本研究設計假設；DFMA p.21','tools':'支撐治具、工作平台、定位工具','verification':'承載、受力路徑、樓梯與防墜細部待設計'}]
