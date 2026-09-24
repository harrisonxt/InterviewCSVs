"""Synthetic Sales-vs-Stock dataset generator (INTERVIEWER ONLY - do not publish)."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
OUT = "data"

# ---------------- Date dimension: 13 weeks, Mon 2 Mar 2026 -> Sun 31 May 2026
dates = pd.date_range("2026-03-02", "2026-05-31", freq="D")
dim_date = pd.DataFrame({"date": dates})
dim_date["date_key"] = dim_date.date.dt.strftime("%Y%m%d").astype(int)
dim_date["day_name"] = dim_date.date.dt.day_name()
dim_date["week_start_date"] = dim_date.date - pd.to_timedelta(dim_date.date.dt.weekday, unit="D")
dim_date["week_end_date"] = dim_date.week_start_date + pd.Timedelta(days=6)
dim_date["iso_year"] = dim_date.date.dt.isocalendar().year.astype(int)
dim_date["iso_week"] = dim_date.date.dt.isocalendar().week.astype(int)
dim_date["year_week"] = dim_date.iso_year.astype(str) + "-W" + dim_date.iso_week.astype(str).str.zfill(2)
dim_date["month_name"] = dim_date.date.dt.month_name()
dim_date["month_num"] = dim_date.date.dt.month
dim_date["quarter"] = "Q" + dim_date.date.dt.quarter.astype(str)
dim_date["is_weekend"] = dim_date.date.dt.weekday >= 5
dim_date = dim_date[["date_key","date","day_name","week_start_date","week_end_date","iso_year",
                     "iso_week","year_week","month_num","month_name","quarter","is_weekend"]]

# ---------------- Geography / store dimension
# (warehouse, region, country, n_stores, weekly rate of sale per item, target weeks cover)
wh_profile = {
    "WH01": ("UK North", "United Kingdom", 5, 11.0, 1.4),   # fast sellers, lean stock  -> stock-out risk
    "WH02": ("UK South", "United Kingdom", 5,  9.0, 5.0),   # healthy, well stocked
    "WH03": ("Ireland",  "Ireland",        4,  3.0, 9.5),   # slow sellers, heavy stock -> overstock
    "WH04": ("Germany",  "Germany",        6,  4.8, 3.2),   # slow-ish, lean (looks FAST until dup removed)
}
towns = {
 "WH01": ["Leeds","Manchester","Newcastle","Sheffield","York"],
 "WH02": ["London Oxford St","Brighton","Bristol","Reading","Southampton"],
 "WH03": ["Dublin","Cork","Galway","Limerick"],
 "WH04": ["Berlin","Hamburg","Munich","Cologne","Frankfurt","Stuttgart"],
}
rows, sid = [], 101
for wh,(region,country,n,_,_) in wh_profile.items():
    for t in towns[wh]:
        rows.append({"store_id": f"S{sid}", "store_name": t, "store_format":
                     rng.choice(["High Street","Retail Park","Shopping Centre"]),
                     "region": region, "country": country, "warehouse_code": wh, "open_date": "2019-01-01"})
        sid += 1
dim_store = pd.DataFrame(rows)
dim_store["open_date"] = pd.to_datetime(dim_store.open_date)
dim_store.loc[dim_store.store_name=="Southampton","open_date"] = pd.Timestamp("2026-03-30")  # TRAP 9 new store
NEW_STORE = dim_store.loc[dim_store.store_name=="Southampton","store_id"].item()

# ---------------- Product dimension (with category + campaign)
cats = {
 "Tops":        (["T-Shirt","Shirt","Knit Jumper","Hoodie","Polo"], 18, 45),
 "Bottoms":     (["Jeans","Chinos","Shorts","Joggers"],             25, 60),
 "Outerwear":   (["Rain Jacket","Puffer","Gilet","Trench Coat"],    55, 140),
 "Footwear":    (["Trainer","Boot","Sandal","Loafer"],              40, 110),
 "Accessories": (["Cap","Scarf","Belt","Backpack","Socks 3pk"],       8, 35),
}
campaigns = ["Spring Launch","Summer Essentials","Core Range","Clearance"]
camp_mult = {"Spring Launch":1.3,"Summer Essentials":1.1,"Core Range":1.0,"Clearance":0.6}
colours = ["Black","Navy","Stone","Olive","White","Red"]
prows, pid = [], 1001
for cat,(subs,lo,hi) in cats.items():
    for i in range(8):
        sub = subs[i % len(subs)]
        col = colours[(i*3 + len(cat)) % len(colours)]
        price = round(rng.uniform(lo,hi)) - 0.01
        prows.append({"product_id": f"P{pid}", "product_name": f"{col} {sub}",
                      "category": cat, "subcategory": sub,
                      "campaign": campaigns[(pid + i) % 4],
                      "unit_price": price, "unit_cost": round(price*rng.uniform(0.35,0.55),2)})
        pid += 1
dim_product = pd.DataFrame(prows)

# ---------------- True store x product weekly rates and covers
sp = dim_store.merge(dim_product, how="cross")
prof = pd.DataFrame(wh_profile, index=["r","c","n","rate","cover"]).T
sp["rate"] = (sp.warehouse_code.map(prof.rate).astype(float)
              * sp.campaign.map(camp_mult)
              * rng.lognormal(0, 0.30, len(sp)))
sp["cover"] = sp.warehouse_code.map(prof.cover).astype(float) * rng.lognormal(0, 0.28, len(sp))
# a few stores that buck their warehouse trend, so it's "mainly" one quadrant, not all
mav = rng.random(len(sp)) < 0.08
sp.loc[mav,"cover"] = rng.uniform(1, 12, mav.sum())

# ---------------- Sales fact (daily, sparse: only store/product/days with a sale)
dow = np.array([0.8,0.8,0.9,1.0,1.2,1.6,1.3]); dow = dow/dow.mean()
recs = []
for d in dates:
    lam = sp.rate.values/7 * dow[d.weekday()] * (1 + 0.004*(d - dates[0]).days)  # mild spring uplift
    q = rng.poisson(lam)
    open_mask = (sp.open_date.values <= np.datetime64(d))
    keep = (q > 0) & open_mask
    s = sp.loc[keep, ["store_id","product_id","unit_price"]].copy()
    s["qty_sold"] = q[keep]; s["date_key"] = int(d.strftime("%Y%m%d"))
    recs.append(s)
fact_sales = pd.concat(recs, ignore_index=True)
# returns (legit negatives)
ret = fact_sales.sample(frac=0.015, random_state=1).copy()
ret["qty_sold"] = -rng.integers(1, 3, len(ret))
fact_sales = pd.concat([fact_sales, ret], ignore_index=True)
disc = rng.choice([1.0,1.0,1.0,0.9,0.8], len(fact_sales))
fact_sales["net_sales_value"] = (fact_sales.qty_sold*fact_sales.unit_price*disc).round(2)
# TRAP 6: orphan product key (not in product dim)
orph = fact_sales.sample(25, random_state=7).copy(); orph["product_id"] = "P1099"
fact_sales = pd.concat([fact_sales, orph], ignore_index=True)
fact_sales = fact_sales.sort_values(["date_key","store_id","product_id"]).reset_index(drop=True)
fact_sales.insert(0, "sales_line_id", np.arange(1, len(fact_sales)+1) + 5_000_000)
# TRAP 1: upstream duplication of every German sales line (identical rows incl. line id)
de_stores = dim_store.loc[dim_store.country=="Germany","store_id"]
dup = fact_sales[fact_sales.store_id.isin(de_stores)]
fact_sales = (pd.concat([fact_sales, dup]).sort_values(["date_key","store_id","product_id","sales_line_id"])
              .reset_index(drop=True))
fact_sales = fact_sales[["sales_line_id","date_key","store_id","product_id","qty_sold","net_sales_value"]]

# ---------------- Stock fact (weekly snapshot, Sunday close, dense)
week_ends = dim_date.loc[dim_date.day_name=="Sunday","date"]
srecs = []
for we in week_ends:
    s = sp[["store_id","product_id","rate","cover","open_date"]].copy()
    s = s[s.open_date <= we]
    soh = rng.poisson(np.maximum(s.rate*s.cover*rng.lognormal(0,0.25,len(s)), 0.2))
    srecs.append(pd.DataFrame({"snapshot_date_key": int(we.strftime("%Y%m%d")),
        "store_id": s.store_id.values, "product_id": s.product_id.values,
        "stock_on_hand_qty": soh,
        "stock_on_order_qty": (rng.random(len(s))<0.3)*rng.poisson(s.rate.values*2)}))
fact_stock = pd.concat(srecs, ignore_index=True)
# TRAP 7: a handful of negative SOH (book-stock errors)
neg = fact_stock.sample(18, random_state=3).index
fact_stock.loc[neg,"stock_on_hand_qty"] = -rng.integers(1, 6, len(neg))
# TRAP 8: one store missing its final weekly snapshot
last = fact_stock.snapshot_date_key.max()
fact_stock = fact_stock[~((fact_stock.store_id=="S112") & (fact_stock.snapshot_date_key==last))]

# ---------------- Dimension dirt (applied AFTER facts so the facts stay "true")
# TRAP 2: country typo on one UK store
dim_store.loc[dim_store.store_name=="York","country"] = "Untied Kingdom"
# TRAP 3: warehouse code with letter O instead of zero on one Irish store
dim_store.loc[dim_store.store_name=="Galway","warehouse_code"] = "WHO3"
# TRAP 5: inconsistent category casing / whitespace
dim_product.loc[dim_product.product_id.isin(["P1025","P1030"]),"category"] = "footwear"
dim_product.loc[dim_product.product_id=="P1037","category"] = "Accessories "
# TRAP 4: duplicate product key (re-classified campaign, no SCD flag) -> join fan-out
dupe_p = dim_product[dim_product.product_id=="P1003"].copy(); dupe_p["campaign"] = "Clearance"
dim_product = pd.concat([dim_product, dupe_p]).sort_values("product_id").reset_index(drop=True)

dim_date.to_csv(f"{OUT}/dim_date.csv", index=False, date_format="%Y-%m-%d")
dim_store.to_csv(f"{OUT}/dim_store.csv", index=False, date_format="%Y-%m-%d")
dim_product.to_csv(f"{OUT}/dim_product.csv", index=False)
fact_sales.to_csv(f"{OUT}/fact_sales.csv", index=False)
fact_stock.to_csv(f"{OUT}/fact_stock.csv", index=False)
print("new store:", NEW_STORE, "| S112 =", dim_store.loc[dim_store.store_id=="S112","store_name"].item())
for n,d in [("date",dim_date),("store",dim_store),("product",dim_product),("sales",fact_sales),("stock",fact_stock)]:
    print(n, d.shape)
