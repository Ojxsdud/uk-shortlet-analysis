import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import pydeck as pdk
import joblib

# ─────────────────────────────────────────────────────────────── page + theme
st.set_page_config(page_title="UK Short-Let Market", page_icon="▲",
                   layout="wide", initial_sidebar_state="expanded")

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = "19 June – 2 July 2026"

# Palette validated with the dataviz colour checks against surface #14151a:
# lightness band, chroma floor, all-pairs CVD separation, normal-vision floor
# and 3:1 contrast all pass in dark mode.
SURFACE   = "#14151a"
PLANE     = "#0d0d10"
INK       = "#eceae5"
INK_2     = "#9b9a95"
MUTED     = "#6e6d68"
GRID      = "#212229"
HAIRLINE  = "rgba(236,234,229,0.08)"

# Validated against surface #14151a with the dataviz colour checks.
# Only ONE city is ever accented: the rest go neutral grey. Three muted hues
# could not clear the normal-vision separation floor - less chroma means less
# distance between hues - so emphasis replaces a three-colour scheme.
# One hue per section, the way iOS gives each app its own accent. Each chart
# stays single-hue, so nothing inside a chart has to be told apart by colour;
# the variety lives BETWEEN sections. The five accents are deliberately never
# used as one categorical set - checked individually they clear the lightness
# band, the chroma floor and 3:1 contrast on this surface; as a set they would
# not clear the separation floors, which is why no chart ever mixes them.
ACCENTS = {
    "market":  "#4a93d1",   # sky
    "geo":     "#33a396",   # teal
    "conc":    "#7a74c9",   # lavender
    "book":    "#cf7157",   # coral
    "price":   "#4fa87b",   # green
}
RAMPS = {
    "market": ["#2b5d8a", "#3d80b5", "#5aa9e6", "#98cbef"],
    "geo":    ["#2f6b6f", "#41908f", "#5fb3ad", "#92d3c8"],
    "conc":   ["#4a4685", "#635ea8", "#8481c9", "#b0ade2"],
    "book":   ["#7a4433", "#a35f44", "#c8805f", "#e5ab92"],
}
ACCENT   = ACCENTS["market"]
ORDINAL  = RAMPS["conc"]
# A deliberate grey for "the remainder" - context, not a series. It carries no
# identity of its own, so the chroma floor does not apply; its meaning comes
# from the legend label beside it.
NEUTRAL  = "#5c6370"
def hue_for(c, sel, a=None): return (a or ACCENT) if c == sel else NEUTRAL

LABEL = {"london": "London", "edinburgh": "Edinburgh", "manchester": "Greater Manchester"}
CENTRE = {"london": (51.5074, -0.1278), "edinburgh": (55.9533, -3.1883),
          "manchester": (53.4794, -2.2453)}
BAND_ORDER = ["1 listing", "2-4", "5-20", "21+"]

st.markdown(f"""
<style>
  .stApp {{ background: {PLANE}; }}
  section[data-testid="stSidebar"] {{ background: {SURFACE};
        border-right: 1px solid {HAIRLINE}; }}
  .block-container {{ padding-top: 2.4rem; max-width: 1380px; }}
  h1, h2, h3, h4 {{ color: {INK}; letter-spacing: -0.018em; font-weight: 600; }}
  h1 {{ font-size: 2.05rem; margin-bottom: .15rem; }}
  p, span, label, li {{ color: {INK_2}; }}

  .eyebrow {{ color: {INK_2}; font-size: .70rem; letter-spacing: .15em;
        text-transform: uppercase; margin-bottom: .55rem; opacity: .72; }}

  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(168px,1fr));
        gap: 1px; background: {HAIRLINE}; border: 1px solid {HAIRLINE};
        border-radius: 10px; overflow: hidden; margin: .4rem 0 1.9rem; }}
  .tile {{ background: {SURFACE}; padding: 1.15rem 1.25rem 1.2rem; }}
  .tile .k {{ color: {INK_2}; font-size: .70rem; letter-spacing: .10em;
        text-transform: uppercase; opacity: .75; }}
  .tile .v {{ color: {INK}; font-size: 2.05rem; line-height: 1.12;
        margin-top: .38rem; font-weight: 600; }}
  .tile .s {{ color: {INK_2}; font-size: .78rem; margin-top: .22rem; opacity: .8; }}

  .lede {{ color: {INK}; font-size: 1.02rem; line-height: 1.62;
        border-left: 2px solid #4fa87b; padding: .1rem 0 .1rem 1.05rem;
        margin: .2rem 0 1.5rem; max-width: 62ch; }}
  .note {{ color: {INK_2}; font-size: .82rem; line-height: 1.6;
        margin-top: .7rem; max-width: 78ch; opacity: .88; }}
  .caveat {{ background: rgba(207,113,87,.07); border: 1px solid rgba(207,113,87,.24);
        border-radius: 8px; padding: .85rem 1.05rem; color: {INK_2};
        font-size: .82rem; line-height: 1.6; margin: 1.1rem 0; }}

  .stTabs [data-baseweb="tab-list"] {{ gap: 2rem; border-bottom: 1px solid {HAIRLINE}; }}
  .stTabs [data-baseweb="tab"] {{ background: transparent; padding: .55rem 0;
        color: {INK_2}; font-size: .93rem; }}
  .stTabs [aria-selected="true"] {{ color: {INK} !important; }}
  footer, #MainMenu {{ visibility: hidden; }}
</style>""", unsafe_allow_html=True)


CAP_W, CAP_M = 11, 11      # capsule thickness / round-cap size, in px
CAP_GAP = 2.4              # gap between stacked segments, in y-units

def capsule(fig, x, y0, y1, colour, name=None, show=False, hover=None,
            horizontal=False, w=None):
    """One rounded bar segment, drawn as a thick line with round caps.
    Plotly only rounds the outer ends of a stack, so stacked segments are
    drawn individually here to get a capsule per segment."""
    ww = w or CAP_W
    xs, ys = ([y0, y1], [x, x]) if horizontal else ([x, x], [y0, y1])
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=colour, width=ww),
        marker=dict(color=colour, size=ww, symbol="circle"),
        name=name or "", showlegend=show,
        hovertemplate=hover, hoverinfo="skip" if hover is None else None))


def layout(fig, h=400, xtitle="", ytitle="", legend=True):
    fig.update_layout(
        height=h, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif",
                  size=12, color=INK_2),
        margin=dict(t=18, b=48, l=64, r=26), hovermode="closest",
        showlegend=legend,
        legend=dict(orientation="h", y=1.10, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(color=INK_2, size=11)),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=HAIRLINE,
                        font=dict(color=INK, size=12)))
    axis = dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
                linecolor=GRID, linewidth=1, tickfont=dict(color=MUTED, size=11),
                title_font=dict(color=INK_2, size=11.5))
    fig.update_xaxes(**axis, title_text=xtitle)
    fig.update_yaxes(**axis, title_text=ytitle)
    return fig


def tiles(items, dots=None):
    out = []
    for i, (k, v, sub) in enumerate(items):
        c = (dots or [])[i] if dots and i < len(dots) else None
        dot = (f"<span style='display:inline-block;width:7px;height:7px;"
               f"border-radius:50%;background:{c};margin-right:.48rem;"
               f"vertical-align:middle'></span>") if c else ""
        out.append(f"<div class='tile'><div class='k'>{dot}{k}</div>"
                   f"<div class='v'>{v}</div><div class='s'>{sub}</div></div>")
    st.markdown("<div class='tiles'>" + "".join(out) + "</div>",
                unsafe_allow_html=True)


@st.cache_data
def load(name):
    p = os.path.join(ROOT, "data", "dashboard", f"{name}.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_resource
def load_model():
    p = os.path.join(ROOT, "outputs", "price_model.joblib")
    return joblib.load(p) if os.path.exists(p) else None

@st.cache_data
def model_features():
    """Which columns the trained model actually uses. Written by model.py,
    which drops features the snapshot no longer publishes."""
    import json
    p = os.path.join(ROOT, "outputs", "model_features.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        d = json.load(f)
    return d["cat"] + d["num"] + d["bool"]


listings = load("listings")
cities   = [c for c in ["london", "edinburgh", "manchester"] if c in set(listings.city)]

# ───────────────────────────────────────────────────────────────── filter row
st.sidebar.markdown("<div class='eyebrow'>Filters</div>", unsafe_allow_html=True)
city = st.sidebar.selectbox("City", cities, format_func=lambda c: LABEL.get(c, c.title()))
all_rooms = sorted(listings.room_type.dropna().unique())
rooms = st.sidebar.multiselect("Room type", all_rooms, default=all_rooms)
lo, hi = int(listings.price_gbp.min()), int(listings.price_gbp.max())
prange = st.sidebar.slider("Nightly price (£)", lo, hi, (lo, hi))
st.sidebar.markdown(
    f"<div class='note'>Inside Airbnb, {SNAPSHOT}. Licensed CC BY 4.0.</div>",
    unsafe_allow_html=True)

d = listings[(listings.city == city) & (listings.room_type.isin(rooms))
             & listings.price_gbp.between(*prange)]
HUE = ACCENTS['market']

st.markdown("<div class='eyebrow'>Inside Airbnb · "
            f"{SNAPSHOT}</div>", unsafe_allow_html=True)
st.markdown("# Who actually owns the UK short-let market?")

t1, t2, t3, t4, t5 = st.tabs(
    ["Market", "Geography", "Concentration", "Listed vs bookable", "Price a listing"])

# ───────────────────────────────────────────────────────────────────── MARKET
with t1:
    if d.empty:
        st.warning("No listings match these filters.")
    else:
        ms = load("market_shape"); row = ms[ms.city == city]
        hosts = int(d.host_id.nunique())
        tiles([
            ("Live listings",  f"{len(d):,}",   "priced and bookable"),
            ("Hosts",          f"{hosts:,}",    f"{len(d)/max(hosts,1):.2f} listings each"),
            ("Median price",   f"£{d.price_gbp.median():,.0f}", "per night"),
            ("Entire homes",   f"{100*(d.room_type=='Entire home/apt').mean():.0f}%",
                               "of live supply"),
        ], dots=RAMPS["market"])

        st.markdown("#### What a night costs, city by city")
        ps = load("price_summary")
        ps["ord"] = ps.city.map({c: i for i, c in enumerate(cities)})
        ps = ps.sort_values("ord")
        fig = go.Figure()
        for _, r in ps.iterrows():
            c = hue_for(r.city, city, ACCENTS['market'])
            fig.add_trace(go.Scatter(
                x=[float(r.p25), float(r.p75)], y=[LABEL[r.city]]*2,
                mode="lines", line=dict(color=c, width=9), opacity=.34,
                showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=[float(r.p75), float(r.p90)], y=[LABEL[r.city]]*2,
                mode="lines", line=dict(color=c, width=2), opacity=.45,
                showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=[float(r["median"])], y=[LABEL[r.city]], mode="markers+text",
                marker=dict(color=c, size=15, line=dict(color=SURFACE, width=2)),
                text=[f"£{float(r['median']):,.0f}"], textposition="top center",
                textfont=dict(color=INK, size=13), showlegend=False,
                hovertemplate=(f"<b>{LABEL[r.city]}</b><br>median £%{{x:,.0f}}"
                               f"<br>middle half £{float(r.p25):,.0f}–£{float(r.p75):,.0f}"
                               f"<br>{int(r.n):,} listings<extra></extra>")))
        st.plotly_chart(layout(fig, 300, "Nightly price (£)", "", legend=False),
                        width="stretch")
        st.markdown(
            "<div class='note'>Dot is the median. The thick band is the middle half of "
            "listings; the thin line runs on to the 90th percentile. Edinburgh's typical "
            "night costs more than London's — its stock is smaller, more central and far "
            "more established.</div>", unsafe_allow_html=True)

        st.markdown("#### How price decays with distance from the centre")
        dp = load("distance_price")
        fig = go.Figure()
        for c in cities:
            sub = dp[dp.city == c].sort_values("bucket_km")
            if sub.empty: continue
            fig.add_trace(go.Scatter(
                x=sub.bucket_km, y=sub.median_price, name=LABEL[c],
                mode="lines", line=dict(color=hue_for(c, city, ACCENTS['market']),
                          width=2.2 if c == city else 1.6,
                          shape="spline"), opacity=1.0 if c == city else .55,
                hovertemplate=f"<b>{LABEL[c]}</b><br>%{{x}} km out"
                              "<br>median £%{y:,.0f}<extra></extra>"))
        st.plotly_chart(layout(fig, 360, "Kilometres from the city centre",
                               "Median nightly price (£)"), width="stretch")
        st.markdown(
            "<div class='note'>Each point is the median of listings in a 1 km ring. "
            "The steep fall in the first few kilometres is the centrality premium; "
            "where the curve flattens is where being further out stops costing "
            "the host anything.</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────── GEOGRAPHY
with t2:
    HUE = ACCENTS['geo']
    if d.empty:
        st.warning("No listings match these filters.")
    else:
        lat, lon = CENTRE.get(city, (51.5, -0.12))
        st.markdown("<div class='eyebrow'>Mean nightly price per 300 m cell"
                    "</div>", unsafe_allow_html=True)
        layer = pdk.Layer(
            "HexagonLayer", data=d[["longitude", "latitude", "price_gbp"]],
            get_position="[longitude, latitude]", radius=300,
            elevation_scale=26, elevation_range=[0, 2600], extruded=True,
            pickable=True, coverage=0.88,
            get_elevation_weight="price_gbp", elevation_aggregation="MEAN",
            get_color_weight="price_gbp", color_aggregation="MEAN",
            color_range=[[38,78,80],[47,107,111],[65,144,143],[95,179,173],
                         [131,201,192],[169,220,211]], opacity=0.82)
        st.pydeck_chart(pdk.Deck(
            layers=[layer], map_style="dark",
            initial_view_state=pdk.ViewState(latitude=lat, longitude=lon,
                                             zoom=10.4, pitch=52, bearing=14),
            tooltip={"html": "<b>£{elevationValue}</b> mean per night",
                     "style": {"backgroundColor": SURFACE, "color": INK,
                               "fontSize": "12px", "borderRadius": "6px"}}),
            height=560)
        st.markdown(
            "<div class='note'>Height and colour both carry mean nightly price. "
            "Drag to rotate, scroll to zoom. Cells with very few listings are "
            "noisy — read the shape of the surface, not any single spike.</div>",
            unsafe_allow_html=True)

        nb = load("neighbourhoods"); nb = nb[nb.city == city].head(10)
        if not nb.empty:
            st.markdown("#### The ten priciest neighbourhoods")
            nb = nb.sort_values("median_price")
            fig = go.Figure()
            for i, r in nb.reset_index(drop=True).iterrows():
                capsule(fig, r.neighbourhood, 0, float(r.median_price), ACCENTS['geo'],
                        horizontal=True, w=9,
                        hover=(f"<b>{r.neighbourhood}</b><br>median "
                               f"£{float(r.median_price):,.0f}<extra></extra>"))
                fig.add_annotation(y=r.neighbourhood, x=float(r.median_price),
                                   text=f"£{float(r.median_price):,.0f}",
                                   showarrow=False, xshift=40,
                                   font=dict(color=INK_2, size=11))
            fig.update_layout(showlegend=False)
            layout(fig, 38*len(nb)+120, "Median nightly price (£)", "", legend=False)
            fig.update_yaxes(type="category", showgrid=False,
                             tickfont=dict(color=INK, size=12))
            fig.update_xaxes(range=[0, float(nb.median_price.max())*1.22])
            st.plotly_chart(fig, width="stretch")
            st.markdown("<div class='note'>Neighbourhoods with fewer than 30 live "
                        "listings are excluded — with a handful of listings a single "
                        "mansion tops the table.</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────── CONCENTRATION
with t3:
    HUE = ACCENTS['conc']; ORDINAL = RAMPS['conc']
    hc = load("host_concentration"); hc = hc[hc.city == city].copy()
    if hc.empty:
        st.warning("No concentration data for this city.")
    else:
        hc["ord"] = hc.host_bucket.map({b: i for i, b in enumerate(BAND_ORDER)})
        hc = hc.sort_values("ord")
        multi = hc[hc.host_bucket != "1 listing"]
        big   = hc[hc.host_bucket.isin(["5-20", "21+"])]
        tiles([
            ("Hosts with 5+ listings", f"{big.pct_of_hosts.sum():.1f}%", "of all hosts"),
            ("…they hold",             f"{big.pct_of_supply.sum():.1f}%", "of live supply"),
            ("Single-listing hosts",   f"{hc[hc.host_bucket=='1 listing'].pct_of_hosts.sum():.1f}%",
                                       "of all hosts"),
            ("…they hold",             f"{hc[hc.host_bucket=='1 listing'].pct_of_supply.sum():.1f}%",
                                       "of live supply"),
        ], dots=[RAMPS["conc"][3], RAMPS["conc"][3], RAMPS["conc"][0], RAMPS["conc"][0]])

        st.markdown("#### A few hosts, a lot of the stock")
        fig = go.Figure()
        for col, field in [("All hosts", "pct_of_hosts"),
                           ("All listings", "pct_of_supply")]:
            base = 0.0
            for i, (_, r) in enumerate(hc.iterrows()):
                v = float(r[field])
                if v <= 0.05:
                    base += v; continue
                top = base + v - (CAP_GAP if i < len(hc) - 1 else 0)
                capsule(fig, col, base + .4, max(top, base + .6), ORDINAL[i],
                        name=(f"{r.host_bucket}" +
                              ("" if r.host_bucket == "1 listing" else " listings")),
                        show=(col == "All hosts"), w=26,
                        hover=(f"<b>{r.host_bucket} per host</b><br>{col}: "
                               f"{v:.1f}%<extra></extra>"))
                if v >= 6:
                    fig.add_annotation(x=col, y=base + v/2, text=f"{v:.1f}%",
                                       showarrow=False, xshift=34,
                                       font=dict(color=INK_2, size=11.5))
                base += v
        layout(fig, 470, "", "")
        fig.update_layout(legend=dict(traceorder="reversed"))
        fig.update_xaxes(type="category", showgrid=False, range=[-0.72, 1.72],
                         tickfont=dict(color=INK, size=13.5))
        fig.update_yaxes(range=[-2, 104], ticksuffix="%")
        st.plotly_chart(fig, width="stretch")
        st.markdown(
            f"<div class='note'>Both columns add to 100%. On the left, hosts are "
            f"sorted into bands by how many listings they hold; on the right, the "
            f"listings themselves. Hosts with 21 or more listings are "
            f"{hc[hc.host_bucket=='21+'].pct_of_hosts.sum():.1f}% of the left column "
            f"and {hc[hc.host_bucket=='21+'].pct_of_supply.sum():.1f}% of the right. "
            f"Across {LABEL[city]}, {big.pct_of_hosts.sum():.1f}% of hosts hold "
            f"{big.pct_of_supply.sum():.1f}% of live listings.</div>",
            unsafe_allow_html=True)

        st.markdown("#### How unequally revenue is spread")
        rc = load("revenue_curve"); rc = rc[rc.city == city].sort_values("pct_of_listings")
        if not rc.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[0, 100], y=[0, 100], mode="lines", name="Perfect equality",
                line=dict(color=GRID, width=1.5), hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=pd.concat([pd.Series([0]), rc.pct_of_listings]),
                y=pd.concat([pd.Series([0]), rc.pct_of_revenue]),
                mode="lines", name="Actual", line=dict(color=HUE, width=2),
                fill="tonexty", fillcolor="rgba(122,116,201,0.13)",
                hovertemplate="Top %{x:.0f}% of listings<br>"
                              "take %{y:.0f}% of estimated revenue<extra></extra>"))
            st.plotly_chart(layout(fig, 400, "Share of listings, highest-earning first (%)",
                                   "Share of estimated revenue (%)"), width="stretch")
            st.markdown(
                "<div class='caveat'><b>How revenue is estimated.</b> Inside Airbnb's "
                "calendar no longer publishes a rate for each night, so revenue here is "
                "booked nights × the listing's current advertised rate. That ignores "
                "seasonal and weekend pricing, so treat the shape of this curve as "
                "sound and the pound figures as indicative.</div>",
                unsafe_allow_html=True)

        top = load("listings")
        top = (top[top.city == city].groupby("host_id")
               .agg(listings=("listing_id", "count"),
                    median_price=("price_gbp", "median")).reset_index()
               .sort_values("listings", ascending=False).head(15))
        top.insert(0, "rank", range(1, len(top) + 1))
        top["host"] = "host " + top.host_id.astype(str).str[-5:]
        st.markdown("#### The fifteen largest hosts")
        st.dataframe(top[["rank", "host", "listings", "median_price"]]
                     .rename(columns={"listings": "live listings",
                                      "median_price": "median £/night"}),
                     hide_index=True, width="stretch")
        st.markdown("<div class='note'>Hosts are identified by a truncated id, not by "
                    "name. The names are in the public dataset; publishing them on a "
                    "dashboard serves no analytical purpose.</div>",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────── LISTED VS BOOKABLE
with t4:
    HUE = ACCENTS['book']
    lb = load("listed_vs_bookable")
    if lb.empty:
        st.info("Run sql/analysis/q11_listed_vs_bookable.sql and re-export.")
    else:
        r = lb[lb.city == city]
        if not r.empty:
            r = r.iloc[0]
            tiles([
                ("Listings advertised", f"{int(r.listed):,}", "in the snapshot"),
                ("Actually bookable",   f"{int(r.bookable):,}", "some availability"),
                ("Not bookable",        f"{int(r.not_bookable):,}",
                                        f"{float(r.pct_not_bookable):.1f}% of the total"),
                ("Reviews, not bookable", f"{float(r.avg_reviews_not):,.0f}",
                                        f"vs {float(r.avg_reviews_bookable):,.0f} bookable"),
            ], dots=RAMPS["book"])

        st.markdown("#### Advertised supply is not available supply")
        fig = go.Figure()
        for _, row in lb.iterrows():
            c = hue_for(row.city, city, ACCENTS['book'])
            fig.add_trace(go.Scatter(
                x=["Advertised", "Bookable"], y=[int(row.listed), int(row.bookable)],
                mode="lines+markers+text", name=LABEL.get(row.city, row.city),
                line=dict(color=c, width=2),
                marker=dict(color=c, size=11, line=dict(color=SURFACE, width=2)),
                text=[f"{int(row.listed):,}", f"{int(row.bookable):,}"],
                textposition=["middle left", "middle right"],
                textfont=dict(color=INK_2, size=11),
                hovertemplate=f"<b>{LABEL.get(row.city, row.city)}</b><br>"
                              "%{x}: %{y:,}<extra></extra>"))
        fig.update_yaxes(type="log")
        st.plotly_chart(layout(fig, 400, "", "Listings (log scale)"), width="stretch")
        st.markdown(
            "<div class='note'>A log scale, so three very differently-sized cities "
            "share one axis and the <i>slope</i> is comparable. The steeper the fall, "
            "the more of a city's advertised stock cannot actually be booked.</div>",
            unsafe_allow_html=True)
        st.markdown(
            "<div class='caveat'><b>Read this carefully.</b> A listing with no "
            "availability across the next 365 days may be fully booked or may be "
            "switched off by its host. Across a whole year the second is far more "
            "likely, but this is <i>not bookable</i>, not proof of a dormant listing. "
            "Headline counts of “Airbnbs in London” include every one of them.</div>",
            unsafe_allow_html=True)

    s_ = load("seasonality"); s_ = s_[s_.city == city]
    if not s_.empty:
        st.markdown("#### Occupancy through the year")
        fig = go.Figure()
        s2 = s_.copy()
        s2["lbl"] = pd.to_datetime(s2.month).dt.strftime("%b")
        for i, r in s2.reset_index(drop=True).iterrows():
            taken = float(r.occupancy_pct)
            capsule(fig, r.lbl, 0.8, max(taken, 1.2), ACCENTS['book'],
                    name="Nights taken", show=(i == 0),
                    hover=(f"<b>{r.lbl}</b><br>{taken:.1f}% of nights taken"
                           "<extra></extra>"))
            capsule(fig, r.lbl, taken + CAP_GAP, 99.2, NEUTRAL,
                    name="Nights free", show=(i == 0),
                    hover=(f"<b>{r.lbl}</b><br>{100-taken:.1f}% free<extra></extra>"))
        layout(fig, 380, "", "")
        fig.update_xaxes(type="category", showgrid=False, range=[-0.7, 11.7],
                         tickfont=dict(color=INK_2, size=12))
        fig.update_yaxes(range=[-2, 104], ticksuffix="%")
        st.plotly_chart(fig, width="stretch")
        w = load("weekend"); w = w[w.city == city]
        if not w.empty:
            w = w.iloc[0]
            tiles([("Weekend occupancy", f"{float(w.weekend_occupancy_pct):.1f}%", "Fri–Sat"),
                   ("Weekday occupancy", f"{float(w.weekday_occupancy_pct):.1f}%", "Sun–Thu"),
                   ("Weekend uplift", f"{float(w.weekend_uplift_pts):+.1f} pts", "difference")],
                  dots=[ACCENTS['book'], NEUTRAL, RAMPS['book'][2]])
        st.markdown(
            "<div class='note'>Occupancy, not price — the calendar no longer publishes "
            "nightly rates. A night counts as taken whether it was booked or blocked by "
            "the host, so this is an upper bound.</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────── PRICE A LISTING
with t5:
    HUE = ACCENTS['price']
    model = load_model()
    if model is None:
        st.info("No trained model found — run `python src/model.py` first.")
    else:
        st.markdown("<div class='lede'>What comparable listings charge — not what "
                    "yours is worth. The model learns the rates hosts currently "
                    "advertise, so it reproduces the market's judgement, including "
                    "its mistakes.</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        nb_opts = sorted(d.neighbourhood.dropna().unique()) if not d.empty else ["—"]
        nb   = c1.selectbox("Neighbourhood", nb_opts)
        rt   = c1.selectbox("Room type", all_rooms)
        guests = c2.slider("Guests", 1, 16, 2)
        beds   = c2.slider("Bedrooms", 0, 8, 1)
        baths  = c3.slider("Bathrooms", 1, 5, 1)
        superh = c3.checkbox("Superhost", value=False)

        if st.button("Estimate", type="primary"):
            lat, lon = CENTRE.get(city, (51.5, -0.12))
            sub = d[d.neighbourhood == nb]
            km = 3.0
            if not sub.empty:
                R = 6371.0
                p1, p2 = np.radians(sub.latitude.mean()), np.radians(lat)
                dp = np.radians(lat - sub.latitude.mean())
                dl = np.radians(lon - sub.longitude.mean())
                a = np.sin(dp/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
                km = float(2*R*np.arcsin(np.sqrt(a)))
            row = pd.DataFrame([{
                "city": city, "neighbourhood": nb, "room_type": rt,
                "property_type": listings.property_type.mode()[0],
                "accommodates": guests, "bedrooms": beds, "beds": max(beds, 1),
                "bathrooms": float(baths), "minimum_nights": 2,
                "number_of_reviews": 10, "rating": 4.7, "rating_cleanliness": 4.7,
                "rating_location": 4.7, "host_listings": 1, "host_years": 5.0,
                "amenity_count": 20, "centre_km": km,
                "instant_bookable": 0.0,
                "is_superhost": 1.0 if superh else 0.0,
                "has_wifi": 1.0, "has_aircon": 0.0, "has_free_parking": 0.0,
                "has_washer": 1.0, "has_dishwasher": 0.0, "has_hot_tub": 0.0,
                "has_self_checkin": 1.0, "has_workspace": 1.0,
                "pets_allowed": 0.0, "has_lift": 0.0}])
            feats = model_features()
            if feats:                      # keep only what the model was fit on
                for c in feats:
                    if c not in row.columns:
                        row[c] = np.nan
                row = row[feats]
            pred = float(np.exp(model.predict(row))[0])
            comps = d[(d.neighbourhood == nb) & (d.room_type == rt)
                      & d.accommodates.between(guests-1, guests+1)]
            tiles([
                ("Comparable rate", f"£{pred:,.0f}", "per night"),
                ("Similar listings", f"{len(comps):,}", f"in {nb}"),
                ("Their median",
                 f"£{comps.price_gbp.median():,.0f}" if len(comps) else "—",
                 "actual advertised" if len(comps) else "too few to compare"),
            ])
            if len(comps) < 10:
                st.markdown("<div class='caveat'>Fewer than ten comparable listings. "
                            "The estimate leans on the model's general pattern rather "
                            "than on this neighbourhood, so treat it loosely.</div>",
                            unsafe_allow_html=True)

st.markdown(f"<div class='note' style='margin-top:3rem;border-top:1px solid {HAIRLINE};"
            "padding-top:1.1rem'>Data: Inside Airbnb (insideairbnb.com), "
            f"{SNAPSHOT}, CC BY 4.0. Built with PostgreSQL, scikit-learn, XGBoost, "
            "SHAP, Plotly and Streamlit. Occupancy and revenue are estimates derived "
            "from advertised availability, not booking records.</div>",
            unsafe_allow_html=True)
