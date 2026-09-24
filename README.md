# Store Performance – Sales vs Stock exercise

## Data

| File | Grain | Notes |
|---|---|---|
| `data/fact_sales.csv` | one row per sales line (store × product × day) | `qty_sold`, `net_sales_value` |
| `data/fact_stock.csv` | one row per store × product × weekly snapshot (Sunday close) | `stock_on_hand_qty`, `stock_on_order_qty` |
| `data/dim_product.csv` | one row per product | category, subcategory, campaign, price, cost |
| `data/dim_store.csv` | one row per store | store → region → country, serving warehouse |
| `data/dim_date.csv` | one row per day | ISO week, `year_week`, month, quarter |

Period: 2 March – 31 May 2026 (13 trading weeks). This is a sample: in production the business has
around 400 stores, 25,000 live SKUs and a stock snapshot taken **every day**.

## Loading in Colab

```python
import pandas as pd

BASE = "https://raw.githubusercontent.com/<org>/<repo>/main/data/"

fact_sales  = pd.read_csv(BASE + "fact_sales.csv")
fact_stock  = pd.read_csv(BASE + "fact_stock.csv")
dim_product = pd.read_csv(BASE + "dim_product.csv")
dim_store   = pd.read_csv(BASE + "dim_store.csv", parse_dates=["open_date"])
dim_date    = pd.read_csv(BASE + "dim_date.csv", parse_dates=["date", "week_start_date", "week_end_date"])
```

## The task

We want to build a store performance report using a **sales versus stock** model.

1. Sketch the semantic model for these tables: which are facts, which are dimensions, how they
   relate, and at what grain each fact sits.
2. Explain why a sales versus stock model can become difficult to manage as it grows. Using the
   production figures above, roughly how large would the stock table be after one year?
3. Suggest ways of reducing the size of the semantic layer. We use AI routinely and the BI
   landscape keeps shifting, so the semantic layer may end up in Power BI, Databricks or another
   tool — favour approaches that are not tied to one platform where you can.
4. Explore the data and produce a plot investigating store performance. We suggest measures such
   as **Weeks Cover** and **Average Weekly Qty Sold**, analysed by week, category and campaign,
   and a view that compares stores or warehouses. Try to apply some of the size-management
   methods from question 3 in how you shape the data.
5. Tell us what you found — including anything in the data you would question or correct before
   trusting the result.

You are welcome to use AI tools. We are interested in how you check and challenge the output.
