import math
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = BASE_DIR / "ml" / "forecast.csv"

FORECAST_WEEKS = pd.to_datetime(
    [
        "2026-09-28",
        "2026-10-05",
        "2026-10-12",
        "2026-10-19",
    ]
)


def load_data():
    sales = pd.read_csv(
        DATA_DIR / "sales_history.csv",
        parse_dates=["week_start"],
    )

    lead_times = pd.read_csv(DATA_DIR / "lead_times.csv")

    promo = pd.read_csv(
        DATA_DIR / "promo_calendar.csv",
        parse_dates=["week_start"],
    )

    festival = pd.read_csv(
        DATA_DIR / "festival_calendar.csv",
        parse_dates=["date"],
    )

    return sales, lead_times, promo, festival


def calculate_uplift(train):
    """
    Estimate promotion uplift using only data available
    before the forecast/validation point.
    """

    normal = train.loc[
        train["promo_flag"] == 0,
        "units_sold",
    ]

    promoted = train.loc[
        train["promo_flag"] == 1,
        "units_sold",
    ]

    if len(normal) == 0 or len(promoted) == 0:
        return 1.0

    normal_mean = normal.mean()
    promo_mean = promoted.mean()

    if normal_mean <= 0:
        return 1.0

    uplift = promo_mean / normal_mean

    # Prevent extreme multipliers from dominating the forecast.
    return float(np.clip(uplift, 1.0, 3.0))


def normalised_sales(train, uplift):
    """
    Convert promotional historical sales into estimated
    normal demand so promotions are not double-counted.
    """

    result = train["units_sold"].astype(float).copy()

    promo_mask = train["promo_flag"] == 1

    if uplift > 1:
        result.loc[promo_mask] = (
            result.loc[promo_mask] / uplift
        )

    return result


def predict_model(history, model):
    """
    Predict normal demand using only historical observations.
    """

    values = history.astype(float).to_numpy()

    if len(values) == 0:
        return 0.0

    if model == "naive":
        return float(values[-1])

    if model == "ma4":
        window = values[-4:]
        return float(window.mean())

    if model == "seasonal":
        if len(values) < 52:
            return float(values[-4:].mean())

        return float(values[-52])

    raise ValueError(f"Unknown model: {model}")


def backtest_models(group):
    """
    Compare simple forecasting baselines using only past data.

    Models:
    - naive
    - 4-week moving average
    - 52-week seasonal
    """

    group = group.sort_values("week_start").reset_index(drop=True)

    models = ["naive", "ma4", "seasonal"]
    errors = {model: [] for model in models}

    # Validate on the most recent 12 weeks.
    start_index = max(52, len(group) - 12)

    for i in range(start_index, len(group)):
        train = group.iloc[:i].copy()
        actual_row = group.iloc[i]

        uplift = calculate_uplift(train)

        normal_history = normalised_sales(
            train,
            uplift,
        )

        actual = float(actual_row["units_sold"])
        is_promo = int(actual_row["promo_flag"]) == 1

        for model in models:

            if model == "seasonal" and len(normal_history) < 52:
                continue

            prediction = predict_model(
                normal_history,
                model,
            )

            if is_promo:
                prediction *= uplift

            prediction = max(0.0, prediction)

            errors[model].append(
                abs(actual - prediction)
            )

    scores = {}

    for model in models:
        if errors[model]:
            scores[model] = float(
                np.mean(errors[model])
            )

    if not scores:
        return "ma4"

    return min(
        scores,
        key=scores.get,
    )


def forecast_sku(group, future_promo_flags):
    """
    Build four future forecasts for one SKU.
    """

    group = group.sort_values("week_start").reset_index(drop=True)

    # Mature SKUs get a validated model.
    if len(group) >= 52:
        selected_model = backtest_models(group)
    else:
        # New / rare SKUs: use recent normal demand.
        selected_model = "ma4"

    # Estimate promotion uplift from all historical data.
    # This is acceptable for the final forecast because all
    # historical data ends before the future forecast horizon.
    uplift = calculate_uplift(group)

    normal_history = normalised_sales(
        group,
        uplift,
    )

    forecasts = []

    # For multi-week forecasting, maintain the normal-demand
    # history so the moving average can evolve.
    history = list(normal_history.astype(float))

    for _, future_row in future_promo_flags.iterrows():

        is_promo = int(
            future_row["promo_flag"]
        ) == 1

        prediction = predict_model(
            pd.Series(history),
            selected_model,
        )

        if is_promo:
            prediction *= uplift

        prediction = max(
            0.0,
            float(prediction),
        )

        forecasts.append(prediction)

        # Add the normal-demand forecast to history.
        # This avoids treating a future promotional uplift
        # as normal demand in the next forecast week.
        normal_prediction = prediction

        if is_promo and uplift > 1:
            normal_prediction = prediction / uplift

        history.append(normal_prediction)

    return forecasts, selected_model, uplift


def main():
    sales, lead_times, promo, festival = load_data()

    # Basic validation.
    required_sales_columns = {
        "sku",
        "week_start",
        "units_sold",
        "promo_flag",
    }

    missing = required_sales_columns - set(
        sales.columns
    )

    if missing:
        raise ValueError(
            f"sales_history.csv missing columns: {missing}"
        )

    required_lead_columns = {
        "sku",
        "lead_time_weeks",
    }

    missing = required_lead_columns - set(
        lead_times.columns
    )

    if missing:
        raise ValueError(
            f"lead_times.csv missing columns: {missing}"
        )

    required_promo_columns = {
        "sku",
        "week_start",
        "promo_flag",
    }

    missing = required_promo_columns - set(
        promo.columns
    )

    if missing:
        raise ValueError(
            f"promo_calendar.csv missing columns: {missing}"
        )

    forecast_skus = (
        lead_times["sku"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if len(forecast_skus) != 40:
        raise ValueError(
            f"Expected 40 forecast SKUs, found {len(forecast_skus)}"
        )

    rows = []
    model_summary = []

    for sku in forecast_skus:

        group = (
            sales[sales["sku"] == sku]
            .sort_values("week_start")
            .copy()
        )

        if group.empty:
            raise ValueError(
                f"No sales history found for {sku}"
            )

        future_promo = (
            promo[promo["sku"] == sku]
            .set_index("week_start")
            .reindex(FORECAST_WEEKS)
            .fillna({"promo_flag": 0})
            .reset_index()
        )

        future_promo["sku"] = sku

        forecasts, model, uplift = forecast_sku(
            group,
            future_promo,
        )

        model_summary.append(
            {
                "sku": sku,
                "history_weeks": len(group),
                "model": model,
                "promo_uplift": round(uplift, 3),
            }
        )

        for week, forecast_value in zip(
            FORECAST_WEEKS,
            forecasts,
        ):
            rows.append(
                {
                    "sku": sku,
                    "week_start": week.strftime(
                        "%Y-%m-%d"
                    ),
                    "forecast_units": round(
                        max(0.0, forecast_value),
                        2,
                    ),
                }
            )

    forecast_df = pd.DataFrame(rows)

    # Exact required column order.
    forecast_df = forecast_df[
        [
            "sku",
            "week_start",
            "forecast_units",
        ]
    ]

    # Exact 160-row requirement.
    if len(forecast_df) != 160:
        raise ValueError(
            f"Expected 160 rows, got {len(forecast_df)}"
        )

    # Every SKU must have exactly four weeks.
    counts = forecast_df.groupby("sku").size()

    if not (counts == 4).all():
        raise ValueError(
            "Every SKU must have exactly 4 forecast rows."
        )

    # Every required week must exist.
    actual_weeks = set(
        forecast_df["week_start"].unique()
    )

    required_weeks = {
        week.strftime("%Y-%m-%d")
        for week in FORECAST_WEEKS
    }

    if actual_weeks != required_weeks:
        raise ValueError(
            "Forecast weeks do not match the assignment."
        )

    # Forecasts cannot be negative.
    if (forecast_df["forecast_units"] < 0).any():
        raise ValueError(
            "Negative forecast detected."
        )

    # No duplicate SKU/week combinations.
    if forecast_df.duplicated(
        ["sku", "week_start"]
    ).any():
        raise ValueError(
            "Duplicate SKU/week forecast detected."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    forecast_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("Forecast generated successfully.")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Rows: {len(forecast_df)}")
    print(f"SKUs: {forecast_df['sku'].nunique()}")
    print(
        "Weeks:",
        ", ".join(
            forecast_df["week_start"].unique()
        ),
    )

    print()
    print("Model selection:")
    print(
        pd.DataFrame(model_summary)
        .sort_values("sku")
        .to_string(index=False)
    )

    print()
    print("First 10 forecast rows:")
    print(
        forecast_df.head(10).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()