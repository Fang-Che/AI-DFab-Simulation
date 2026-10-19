# AI-DFab Simulation and Construction Agent

AI-DFab 自動化模擬與建造代理。以 Streamlit 和 Three.js 呈現配置、製造與裝配的數位研究流程。

## 功能
- 矩形、L 型與 U 型，單層與二層全屋裝配播放。
- 室內配置、單元組裝、機械手臂與夾具軌跡、干涉預檢。
- 現場吊裝情境、單元板件放樣與接頭工法參考。
- 平面與研究圖說、BOM、TWD 成本情境、三流程比較及修改回饋。

## 安裝
使用 Python 3.12。Windows 依序執行 `setup.bat`、`start-simulator.bat`，開啟 http://127.0.0.1:8502 。

```sh
python -m venv .venv
# Activate the virtual environment, then:
python -m pip install -r requirements.txt
python -m streamlit run robotics_app.py --server.port 8502
```

核心模擬不需要 API 金鑰。程式會在 `robotics/runs/` 產生執行資料，這些檔案不納入版本庫。
PDF 中文字型預設使用 Windows 微軟正黑體；其他平台可透過 `WIKIHOUSE_PDF_FONT` 指定相容字型。
選用 Rhino、RoboDK 與原始模型匯入工具需另外安裝對應軟體，並將合法取得的來源檔放在 `local_assets/`。

## 驗證與界線
```sh
python -m unittest test_building test_design_study test_lifecycle test_residential_r11 -q
```
工時、成本、公差與危險暴露為可修改假設下的數位模型結果。幾何預檢不等同安全認證、完整逆運動學或全尺度實驗。研究圖說不能直接作為核定施工或 CNC 刀路。

## 來源
構件參考 WikiHouse Skylark，機械手臂幾何與參數參考 Manis。詳見 `robotics/assets/sources.json`、`assembly_sources.json` 和第三方程式授權。原始手冊與私人文件不隨庫發布。
本整理版不新增授權承諾。重新發布第三方模型前應核對其適用授權。

## GitHub 與部署
此版本準備上傳至 Fang-Che 的獨立 AI-DFab-Simulation 儲存庫。上傳原始碼與部署公開網站為不同步驟。
