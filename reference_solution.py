"""Reference solution (INTERVIEWER ONLY). Shows the naive result and the cleaned result."""
import pandas as _p; _p.set_option("display.width",200); _p.set_option("display.max_columns",10)
import pandas as pd, numpy as np, matplotlib.pyplot as plt
BASE = "data/"   # in Colab: "https://raw.githubusercontent.com/<org>/<repo>/main/data/"
sales = pd.read_csv(BASE+"fact_sales.csv"); stock = pd.read_csv(BASE+"fact_stock.csv")
store = pd.read_csv(BASE+"dim_store.csv");  prod  = pd.read_csv(BASE+"dim_product.csv")
dates = pd.read_csv(BASE+"dim_date.csv", parse_dates=["date","week_start_date"])

def build(sales, stock, store, prod):
    wk = dates[["date_key","year_week"]]
    s = sales.merge(wk, on="date_key")
    ws = s.groupby(["store_id","product_id","year_week"], as_index=False).qty_sold.sum()
    n_weeks = dates.year_week.nunique()
    rate = (ws.groupby(["store_id","product_id"]).qty_sold.sum() / n_weeks).rename("avg_weekly_qty")
    latest = stock[stock.snapshot_date_key == stock.snapshot_date_key.max()]
    soh = latest.set_index(["store_id","product_id"]).stock_on_hand_qty.clip(lower=0)
    m = pd.concat([rate, soh], axis=1).reset_index()
    m["weeks_cover"] = m.stock_on_hand_qty / m.avg_weekly_qty.replace(0, np.nan)
    m = m.merge(store, on="store_id", how="left").merge(prod, on="product_id", how="left")
    return m

def plot(m, title, fname, hue="warehouse_code"):
    fig, ax = plt.subplots(figsize=(9,6))
    for k,g in m.groupby(hue):
        ax.scatter(g.weeks_cover, g.avg_weekly_qty, s=12, alpha=.6, label=k)
    ax.axvline(m.weeks_cover.median(), ls="--", c="grey"); ax.axhline(m.avg_weekly_qty.median(), ls="--", c="grey")
    ax.set_xlabel("Weeks cover (latest SOH / avg weekly qty)"); ax.set_ylabel("Avg weekly qty sold")
    ax.set_xlim(0, 25); ax.set_title(title); ax.legend(); fig.tight_layout(); fig.savefig(fname, dpi=110)

# ---- Naive (what an un-inspected AI answer tends to produce)
naive = build(sales, stock, store, prod)
plot(naive, "Naive: store x product, coloured by warehouse", "private/naive_plot.png")

# ---- Cleaned
sales_c = sales.drop_duplicates()                                  # German upstream duplicates
sales_c = sales_c[sales_c.product_id.isin(prod.product_id)]        # orphan key P1099
store_c = store.assign(country=store.country.replace({"Untied Kingdom":"United Kingdom"}),
                       warehouse_code=store.warehouse_code.replace({"WHO3":"WH03"}))
prod_c = prod.assign(category=prod.category.str.strip().str.title()).drop_duplicates("product_id", keep="first")
# S112 (Cork) missing final snapshot -> use each store's own latest snapshot
latest_per_store = stock.groupby("store_id").snapshot_date_key.transform("max")
stock_c = stock[stock.snapshot_date_key == latest_per_store].assign(snapshot_date_key=0)
clean = build(sales_c, stock_c, store_c, prod_c)
# New store S110 opened 30 Mar -> rate over trading weeks only
open_wks = dates[dates.date >= "2026-03-30"].year_week.nunique()
mask = clean.store_id=="S110"
clean.loc[mask,"avg_weekly_qty"] *= dates.year_week.nunique()/open_wks
clean.loc[mask,"weeks_cover"] = clean.loc[mask,"stock_on_hand_qty"]/clean.loc[mask,"avg_weekly_qty"]
plot(clean, "Cleaned: store x product, coloured by warehouse", "private/clean_plot.png")

for name, m in [("NAIVE", naive), ("CLEAN", clean)]:
    xm, ym = m.weeks_cover.median(), m.avg_weekly_qty.median()
    m["quadrant"] = np.select([(m.avg_weekly_qty>=ym)&(m.weeks_cover<xm),(m.avg_weekly_qty>=ym)&(m.weeks_cover>=xm),
                               (m.avg_weekly_qty<ym)&(m.weeks_cover<xm)],["HiSales-LoCover","HiSales-HiCover","LoSales-LoCover"],"LoSales-HiCover")
    print(f"\n{name}\n", pd.crosstab(m.warehouse_code, m.quadrant, normalize="index").round(2))
print("\nAvg weekly qty by country, naive:\n", naive.groupby("country").avg_weekly_qty.mean().round(2))
