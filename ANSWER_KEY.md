# Interviewer answer key – Sales vs Stock exercise
Keep this folder (answer key, generator, reference solution, plots) OUT of the public repo.
Candidates who can see `generate_data.py` can read every planted issue.

## Expected model
Star schema, two facts at different grains sharing conformed dimensions.
- `fact_sales`: store × product × day, sparse (a row only exists when something sold). Fully additive.
- `fact_stock`: store × product × snapshot, **dense** (a row for every store/product whether or not it sold). **Semi-additive**: sums across store/product, but NOT across time — use last snapshot (or average) in the period.
- Dims: `dim_date` (to both facts; stock joins on `snapshot_date_key`), `dim_store`, `dim_product`.
- Weekly analysis means both facts need a common week grain (`year_week`) before comparing.

## Q2 – why the model gets big
Strong answers hit most of these:
- Stock is a periodic snapshot: rows = stores × SKUs × snapshots regardless of activity. 400 × 25,000 × 365 ≈ **3.65bn rows/year**, versus sales which only grows with actual transactions.
- Semi-additivity means you can't simply pre-sum stock over time; naive aggregation is wrong, so people keep full detail "just in case".
- History accumulates; both facts grow forever unless retention is set.
- Wide fact tables with text keys (e.g. "S101", "P1003"), unused columns, high-cardinality fields (line IDs, timestamps) hurt columnar compression.
- Many-to-many / bi-directional workarounds when facts are joined directly instead of via shared dims.

## Q3 – ways to reduce size (tool-agnostic where possible)
- Choose the right grain: weekly (period-end) stock rather than daily; aggregate sales to store × product × week.
- Only store stock where SOH ≠ 0, or store stock as change events / validity ranges instead of daily copies.
- Tiered retention: daily for the last N weeks, weekly or monthly beyond that.
- Integer surrogate keys, drop unused columns (sales line ID once de-duplicated), avoid high-cardinality columns.
- Measures, not calculated columns; define metrics once in a semantic/metrics layer (dbt metrics, Databricks metric views, PBI measures) so the logic is portable.
- Aggregation tables / dual grain (summary for dashboards, detail on demand via DirectQuery/composite).
- Incremental refresh and partitioning by date.
- Push heavy lifting upstream (lakehouse/warehouse views) so the BI layer stays thin.
Bonus: recognising that a well-defined star schema is also easier for AI tools to query correctly.

## Q4 – reference measures
- Avg Weekly Qty Sold = total qty in period ÷ **number of weeks in period** (13), not the mean of weekly rows — `groupby(week).mean()` skips zero weeks and inflates slow sellers.
- Weeks Cover = latest SOH ÷ Avg Weekly Qty Sold. Handle zero sales (divide-by-zero → NaN/∞).
- Scatter: x = weeks cover, y = avg weekly qty, point = store × product (or store × category), colour = warehouse/country, median lines → four quadrants.

## Expected quadrant story (clean data)
| Warehouse | Region | Pattern | Share in main quadrant |
|---|---|---|---|
| WH01 | UK North | High sales, low cover → stock-out risk | ~82% |
| WH02 | UK South | High sales, healthy cover | ~54% |
| WH03 | Ireland | Low sales, high cover → overstock | ~88% |
| WH04 | Germany | Low sales, low cover (lean, slow) | ~43% |

With the duplicates left in, **Germany looks like WH01** (fast seller, stock-out risk) — the
business recommendation flips from "range review / it's a slow region" to "send more stock". That
is the headline test: does the candidate notice?

## Planted issues (roughly easiest → hardest to spot)
| # | Where | Issue | How to spot | Fix |
|---|---|---|---|---|
| 1 | `fact_sales` | Every German sales line duplicated (identical rows, same `sales_line_id`) → German qty ~2× | `sales_line_id` not unique; `df.duplicated().sum()`; Germany qty/store similar to UK despite being set up as slow | `drop_duplicates()` |
| 2 | `dim_store` | York country = "Untied Kingdom" | Group by country → extra category | Map to "United Kingdom" |
| 3 | `dim_store` | Galway `warehouse_code` = "WHO3" (letter O) | Colour by warehouse → five warehouses, "WHO3" looks identical to WH03 | Map to "WH03" |
| 4 | `dim_product` | P1003 appears twice (campaign changed to Clearance, no SCD flag) → join fans out, doubles P1003 sales | `product_id` not unique; row count changes after merge | Dedupe / take current version; discuss SCD2 |
| 5 | `dim_product` | Category "footwear" (×2) and "Accessories " (trailing space) | Group by category → 7 categories instead of 5 | `.str.strip().str.title()` |
| 6 | `fact_sales` | 25 lines with `product_id` P1099, not in product dim | Anti-join / left-join nulls; inner join silently drops them | Report as orphan; exclude or add "Unknown" member |
| 7 | `fact_stock` | 18 negative SOH values | `describe()` / min < 0 | Clip to 0 or flag as book-stock error |
| 8 | `fact_stock` | Cork (S112) missing final week snapshot | Filtering to last snapshot date → Cork's products disappear or cover = NaN | Use each store's own latest snapshot; flag the gap |
| 9 | `dim_store` / facts | Southampton (S110) opened 30 Mar → no sales/stock for first 4 weeks | `open_date`; weekly sales starting late | Divide by trading weeks (9) not 13 |
| – | model | Stock summed across weeks (semi-additive trap) | Weeks cover values ~13× too high | Last snapshot or average SOH |
| – | data | ~1.5% of sales lines are returns (negative qty) | Legit — good candidates note and decide whether to net off | Discussion point |

Suggested scoring: #1 is the must-find; #2–#5 show attention to detail; #6–#9 and the
semi-additive point separate strong candidates. Credit candidates who *prompt the AI* to run
data-quality checks (key uniqueness, referential integrity, value distributions) rather than
spotting everything by eye.

## Other ideas you could add
- Mixed date formats or a `date_key` stored as text in one extract.
- A store that changes warehouse mid-period (SCD2 on the store dim).
- Stock snapshot taken Saturday for one country, Sunday for others (misaligned week-end).
- Currency: German `net_sales_value` in EUR, UK in GBP, with no currency column.
- A price outlier (unit price £9,999) that distorts value-based measures.
