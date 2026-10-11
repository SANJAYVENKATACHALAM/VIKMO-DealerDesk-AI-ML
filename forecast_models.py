import pandas as pd
import numpy as np

df = pd.read_csv(
    "data/sales_history.csv",
    parse_dates=["week_start"]
)

results = []

for sku, group in df.groupby("sku"):
    sales = (
        group
        .sort_values("week_start")["units_sold"]
        .to_numpy()
    )

    if len(sales) < 52:
        continue

    actual = sales[52:]

    naive_predictions = sales[51:-1]

    ma4_predictions = np.array([
        sales[i - 4:i].mean()
        for i in range(52, len(sales))
    ])

    seasonal_predictions = sales[:-52]

    results.append({
        "sku": sku,
        "naive": np.mean(
            np.abs(actual - naive_predictions)
        ),
        "ma4": np.mean(
            np.abs(actual - ma4_predictions)
        ),
        "seasonal": np.mean(
            np.abs(actual - seasonal_predictions)
        ),
    })

results_df = pd.DataFrame(results)

print("\nAverage MAE across mature SKUs:")
print(
    results_df[
        ["naive", "ma4", "seasonal"]
    ].mean().round(2)
)

print("\nBest model for each SKU:")
print(
    results_df[
        ["naive", "ma4", "seasonal"]
    ]
    .idxmin(axis=1)
    .value_counts()
)