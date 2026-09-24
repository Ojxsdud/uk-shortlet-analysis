import os, numpy as np, pandas as pd, joblib
from sqlalchemy import text
from db import engine
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import xgboost as xgb

ENGINE = engine()

CENTRES = {"london":(51.5074,-0.1278), "edinburgh":(55.9533,-3.1883), "manchester":(53.4794,-2.2453)}

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2-lat1), np.radians(lon2-lon1)
    a = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
    return 2*R*np.arcsin(np.sqrt(a))

def load():
    q = """
    SELECT l.listing_id, l.city, l.neighbourhood, l.price_gbp, l.room_type, l.property_type,
           l.accommodates, COALESCE(l.bedrooms,1) AS bedrooms, COALESCE(l.beds,1) AS beds,
           COALESCE(l.bathrooms,1) AS bathrooms, l.minimum_nights, l.number_of_reviews,
           l.rating, l.rating_cleanliness, l.rating_location, l.instant_bookable,
           l.latitude, l.longitude, h.is_superhost, h.listings_count AS host_listings,
           EXTRACT(year FROM age(current_date, h.host_since)) AS host_years,
           f.has_wifi, f.has_aircon, f.has_free_parking, f.has_washer, f.has_dishwasher,
           f.has_hot_tub, f.has_self_checkin, f.has_workspace, f.pets_allowed,
           f.has_lift, f.amenity_count
    FROM core.listings_model l
    JOIN core.hosts h USING (host_id)
    LEFT JOIN core.listing_features f USING (listing_id)
    """
    df = pd.read_sql(text(q), ENGINE)
    # Postgres numeric(x,y) arrives as decimal.Decimal, which sklearn cannot use.
    # Coerce every non-categorical column to float explicitly.
    TEXT_COLS = {"city", "neighbourhood", "room_type", "property_type"}
    for c in df.columns:
        if c not in TEXT_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    df["centre_km"] = haversine_km(
        df.latitude.values, df.longitude.values,
        df.city.map(lambda c: CENTRES[c][0]).values,
        df.city.map(lambda c: CENTRES[c][1]).values)
    return df

CAT  = ["city","neighbourhood","room_type","property_type"]
NUM  = ["accommodates","bedrooms","beds","bathrooms","minimum_nights","number_of_reviews",
        "rating","rating_cleanliness","rating_location","host_listings","host_years",
        "amenity_count","centre_km"]
BOOL = ["instant_bookable","is_superhost","has_wifi","has_aircon","has_free_parking",
        "has_washer","has_dishwasher","has_hot_tub","has_self_checkin","has_workspace",
        "pets_allowed","has_lift"]

def build_pre(cat=None, num=None, bl=None):
    cat, num, bl = cat or CAT, num or NUM, bl or BOOL
    return ColumnTransformer([
        # sparse_output=False is REQUIRED: shap.TreeExplainer cannot take a sparse matrix
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=20,
                              sparse_output=False), cat),
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc",  StandardScaler())]), num),
        ("bool", SimpleImputer(strategy="most_frequent"), bl),
    ])

def usable(df, cols, min_frac=0.005):
    """Drop features that are entirely (or near-entirely) missing.
    Inside Airbnb has removed published fields between snapshots - host_since,
    instant_bookable and the calendar's nightly price have all gone at various
    points - so the feature list is derived from the data rather than assumed.
    A column imputed from nothing contributes no signal and makes sklearn warn."""
    keep, dropped = [], []
    for c in cols:
        frac = df[c].notna().mean()
        (keep if frac >= min_frac else dropped).append((c, frac))
    if dropped:
        print("  dropped (no usable values): "
              + ", ".join(f"{c} ({f:.1%} present)" for c, f in dropped))
    return [c for c, _ in keep]


def main():
    df = load()
    print(f"rows from DB: {len(df):,}")

    cat  = usable(df, CAT)
    num  = usable(df, NUM)
    bl   = usable(df, BOOL)
    print(f"  features used: {len(cat)} categorical, {len(num)} numeric, "
          f"{len(bl)} boolean")

    df["y"] = np.log(df["price_gbp"])
    X, y = df[cat+num+bl], df["y"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42,
                                          stratify=df["city"])

    # Baseline 0: neighbourhood median
    nb_med = df.loc[Xtr.index].groupby(["city","neighbourhood"])["price_gbp"].median()
    gm = df.loc[Xtr.index,"price_gbp"].median()
    base_pred = np.array([nb_med.get((r.city, r.neighbourhood), gm) for r in Xte.itertuples()])

    ridge = Pipeline([("pre", build_pre(cat,num,bl)), ("m", Ridge(alpha=1.0))]).fit(Xtr, ytr)
    model = Pipeline([("pre", build_pre(cat,num,bl)), ("m", xgb.XGBRegressor(
        n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8,
        colsample_bytree=0.8, random_state=42, n_jobs=4))]).fit(Xtr, ytr)

    actual = np.exp(yte)
    print(f"\n{'model':<26}{'MAE £':>9}{'MedAE £':>10}{'R2(log)':>10}")
    print(f"{'baseline: nbhd median':<26}{mean_absolute_error(actual, base_pred):>9.2f}"
          f"{np.median(np.abs(actual-base_pred)):>10.2f}{r2_score(yte, np.log(base_pred)):>10.3f}")
    for name, m in [("ridge", ridge), ("xgboost", model)]:
        pl = m.predict(Xte); p = np.exp(pl)
        print(f"{name:<26}{mean_absolute_error(actual,p):>9.2f}"
              f"{np.median(np.abs(actual-p)):>10.2f}{r2_score(yte,pl):>10.3f}")

    import json
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/model_features.json", "w") as f:
        json.dump({"cat": cat, "num": num, "bool": bl}, f, indent=2)
    joblib.dump(model, "outputs/price_model.joblib")
    sz = os.path.getsize("outputs/price_model.joblib")/1e6
    print(f"\nsaved price_model.joblib  {sz:.1f} MB")
    return model, Xte



# ---------------------------------------------------------------- SHAP
def explain(model, Xte, sample=800):
    import shap, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pre  = model.named_steps["pre"]
    Xenc = pre.transform(Xte.sample(min(sample, len(Xte)), random_state=0))
    names = pre.get_feature_names_out()
    print(f"encoded matrix: {type(Xenc).__name__} shape={Xenc.shape}")

    explainer = shap.TreeExplainer(model.named_steps["m"])
    sv = explainer.shap_values(Xenc)
    print(f"shap_values shape={sv.shape}")

    shap.summary_plot(sv, Xenc, feature_names=names, max_display=20, show=False)
    plt.tight_layout(); plt.savefig("outputs/shap_summary.png", dpi=110); plt.close()

    ci = list(names).index("num__centre_km")
    shap.dependence_plot(ci, sv, Xenc, feature_names=names, show=False)
    plt.tight_layout(); plt.savefig("outputs/shap_centre_km.png", dpi=110); plt.close()

    ex = shap.Explanation(values=sv[0], base_values=explainer.expected_value,
                          data=Xenc[0], feature_names=list(names))
    shap.plots.waterfall(ex, max_display=12, show=False)
    plt.tight_layout(); plt.savefig("outputs/shap_waterfall.png", dpi=110); plt.close()

    top = sorted(zip(names, np.abs(sv).mean(0)), key=lambda t: -t[1])[:15]
    print("\ntop 15 features by mean |SHAP|:")
    for n, v in top: print(f"  {n:<45}{v:.4f}")
    return explainer


if __name__ == "__main__":
    _model, _Xte = main()
    explain(_model, _Xte)
