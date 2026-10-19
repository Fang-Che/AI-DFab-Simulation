"""Frozen public-price references. Currency conversion is not a Taiwan quote."""
import math
FX = dict(gbp_twd=42.68, quote_time='2026-10-13 14:06 Asia/Taipei', kind='臺灣銀行英鎊即期賣出',
          url='https://rate.bot.com.tw/xrt?Lang=zh-TW',retrieved='2026-10-13')
REFERENCES = [
 dict(id='UK-CHASSIS',title='ReFrame Studio｜WikiHouse 保溫構架',gbp_low=400.,gbp_high=450.,unit='m² 室內樓地板面積',
      url='https://www.reframestudio.co.uk/wikihouse',date='網頁未列報價日期；2026-10-13 查閱',
      scope='建築師公布的英國保溫構架概算；非個案正式報價。VAT、運輸與現場組裝是否全含未明確列出，需詢價。'),
 dict(id='UK-DESIGN',title='WikiHouse 官方｜構架設計與檢查',gbp_low=1200.,gbp_high=5000.,unit='專案',
      url='https://www.wikihouse.cc/services',date='網頁未列報價日期；2026-10-13 查閱',scope='設計與預檢服務；另加 VAT，複雜／大型案可能更高。'),
 dict(id='UK-CUSTOM',title='WikiHouse 官方｜客製構件設計',gbp_low=100.,gbp_high=350.,unit='客製構件設計',
      url='https://www.wikihouse.cc/services',date='網頁未列報價日期；2026-10-13 查閱',scope='客製構件設計與檢查費；另加 VAT；不是構件製造單價。'),
 dict(id='UK-ADVICE',title='WikiHouse 官方｜生產採購指導',gbp_low=350.,gbp_high=450.,unit='日',
      url='https://www.wikihouse.cc/services',date='網頁未列報價日期；2026-10-13 查閱',scope='顧問指導；另加 VAT；不是現場班組施工費。'),
 dict(id='UK-CASE',title='Architecture Unknown｜Little Hulton Pavilion',gbp_low=52000.,gbp_high=52000.,unit='特定案例',
      url='https://www.linkedin.com/posts/architecture-unknown_wikihouse-what-will-activity-7291799632261570562-6QXx',
      date='案例貼文；2026-10-13 查閱',scope='事務所公布 WikiHouse 部分：材料加工運送、緊固件工具、臨時儲存遮蔽、施工與設計管理。整體工程預算超過 £950,000；不轉作本案單價。')]

def converted(fx=None):
    value=FX['gbp_twd'] if fx is None else float(fx)
    if not math.isfinite(value) or value<=0:raise ValueError('匯率必須大於零')
    return [{**r,'twd_low':round(r['gbp_low']*value,2),'twd_high':round(r['gbp_high']*value,2),'fx':value,
             'fx_status':'已查證牌告快照' if value==FX['gbp_twd'] else '使用者自訂匯率'} for r in REFERENCES]

def benchmark(house,fx=None,area=None):
    # Clearly labelled external-wall-inner-face area proxy; no claim of measured GIA.
    wings={'rectangle':0,'L':1,'U':2}[house['layout']]
    proxy=(4.8*12.564+wings*5.436*4.764)*house['levels']-(1.208*4.2 if house['levels']==2 else 0)
    area=round(proxy,3) if area is None else float(area)
    if not math.isfinite(area) or area<0:raise ValueError('參考面積須為有限非負數')
    ref=converted(fx)[0]
    return dict(area_m2=area,area_basis='外牆內緣概算、扣二樓梯洞；非實測 GIA，L/U 接角為矩形近似',
                gbp_low=area*ref['gbp_low'],gbp_high=area*ref['gbp_high'],
                twd_low=area*ref['twd_low'],twd_high=area*ref['twd_high'],reference=ref,
                status='英國構架價換匯情境；未作台灣在地化、通膨、稅費、跨國運輸調整；不與材料明細重複相加')
