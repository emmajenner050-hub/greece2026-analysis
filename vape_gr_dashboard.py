import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="希腊电子烟油市场分析看板",
    page_icon="🇬🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 全局样式 ====================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102,126,234,0.3);
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; line-height: 1; }
    .metric-card .label { font-size: 0.85rem; opacity: 0.9; margin-top: 4px; }
    .section-title {
        font-size: 1.1rem; font-weight: 600;
        color: #374151; margin: 16px 0 8px 0;
        padding-left: 10px;
        border-left: 4px solid #667eea;
    }
    .insight-box {
        background: #f0f4ff; border-left: 4px solid #667eea;
        padding: 12px 16px; border-radius: 0 8px 8px 0;
        margin: 8px 0; font-size: 0.92rem;
    }
    .tag-chip {
        display: inline-block;
        background: #e0e7ff; color: #3730a3;
        padding: 2px 10px; border-radius: 999px;
        font-size: 0.8rem; margin: 2px;
    }
    .flavor-tag-row {
        margin: 4px 0 10px 0;
        padding: 6px 10px;
        background: #f8fafc;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #374151;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 颜色主题 ====================
COLORS = {
    "primary":  "#667eea",
    "secondary":"#764ba2",
    "local":    "#10b981",
    "foreign":  "#94a3b8",
    "ice":      "#38bdf8",
    "tobacco":  "#d97706",
    "fruit":    "#f59e0b",
    "sweet":    "#ec4899",
    "drink":    "#06b6d4",
    "candy":    "#8b5cf6",
    "menthol":  "#34d399",
}
CAT_COLOR_MAP = {
    "水果": COLORS["fruit"],
    "烟草": COLORS["tobacco"],
    "甜点": COLORS["sweet"],
    "饮料": COLORS["drink"],
    "糖果": COLORS["candy"],
    "薄荷": COLORS["menthol"],
}
PLOTLY_TEMPLATE = "plotly_white"

# ==================== 数据加载与预处理 ====================
@st.cache_data
def load_data():
    df = pd.read_excel("vape_gr_data-Erin-20260525.xlsx")
    df.columns = df.columns.str.strip()

    # 含冰/薄荷：'/' 视为不确定
    df["含冰/薄荷"] = df["含冰/薄荷"].replace("/", "不确定").fillna("不确定")
    df.loc[~df["含冰/薄荷"].isin(["是", "否", "不确定"]), "含冰/薄荷"] = "不确定"

    # 含烟草
    df["含烟草"] = df["含烟草"].replace("/", "不确定").fillna("不确定")
    df.loc[~df["含烟草"].isin(["是", "否", "不确定"]), "含烟草"] = "不确定"

    # 口味标签列表化（小写去重保序用）
    df["口味标签列表"] = df["口味标签"].apply(
        lambda x: [t.strip().lower() for t in str(x).split(",") if t.strip()]
        if pd.notna(x) else []
    )

    # 品牌标准化
    brand_map = {
        "ivg": "IVG", "alter ego": "Alter Ego", "alterego": "Alter Ego",
        "eliquid france": "ELiquid France", "eliquid france ": "ELiquid France",
        "halo": "Halo", "tnt vape": "TNT Vape", "tntvape": "TNT Vape",
        "hexocell": "HEXOcell", "liqua": "Liqua",
        "american stars": "American Stars",
        "nixx": "Nixx", "pod salt": "Pod Salt", "elux": "Elux",
        "dinner lady": "Dinner Lady", "steam train": "Steam Train",
        "vnv": "VnV", "vnv liquids": "VnV", "domino": "Domino",
        "atmos lab": "Atmos Lab", "nobacco": "NOBACCO", "bombo": "Bombo",
        "tasty clouds": "Tasty Clouds", "god's liquids": "God's Liquids",
        "gods liquids": "God's Liquids", "f*ck tpd": "F*ck TPD",
        "fuck tpd": "F*ck TPD", "remix juice": "Remix Juice",
        "fruit invasion": "Fruit Invasion", "mon dessert": "Mon Dessert",
        "myvapery": "MyVapery", "five pawns": "Five Pawns",
        "flavour sluts": "Flavour Sluts", "disco biscuits": "Disco Biscuits",
        "echoes": "Echoes", "black": "Black", "tasaki": "Tasaki",
        "aramax": "Aramax", "innovation": "Innovation",
    }
    def normalize_brand(b):
        if pd.isna(b):
            return "未知品牌"
        return brand_map.get(str(b).strip().lower(), str(b).strip().title())

    df["品牌_标准化"] = df["品牌"].apply(normalize_brand)
    df = df[df["品牌_标准化"] != "未知品牌"].copy()

    # 本土属性（每个标准化品牌取首条记录的属性，未知归为否）
    brand_origin = df.groupby("品牌_标准化")["是否希腊本土品牌"].first()
    df["本土属性"] = df["品牌_标准化"].map(brand_origin).fillna("否")
    df["本土属性"] = df["本土属性"].replace("未知", "否")

    # 口味名称标准化（保留原始大小写用于展示，小写仅用于聚合）
    def norm_flavor(name):
        if pd.isna(name):
            return None
        n = str(name).strip()
        n_low = n.lower()
        if "blue razz" in n_low or "blue raz" in n_low:
            return "Blue Razz Berry"
        if "strawberry raspberry cherry ice" in n_low:
            return "Strawberry Raspberry Cherry Ice"
        return n
    df["口味名称_标准化"] = df["口味名称"].apply(norm_flavor)

    return df


df = load_data()
brand_origin_dict = (
    df[["品牌_标准化", "本土属性"]].drop_duplicates()
    .set_index("品牌_标准化")["本土属性"].to_dict()
)

# ==================== 侧边栏筛选 ====================
with st.sidebar:
    st.markdown("## 🔍 数据筛选")
    st.markdown("---")
    sel_websites = st.multiselect("🌐 网站", df["网站名称"].unique(),
                                  default=df["网站名称"].unique())
    sel_types    = st.multiselect("📦 产品类型", df["产品类型"].unique(),
                                  default=df["产品类型"].unique())
    sel_brands   = st.multiselect("🏷️ 品牌", sorted(df["品牌_标准化"].unique()),
                                  default=sorted(df["品牌_标准化"].unique()))
    sel_origin   = st.multiselect("🏠 品牌归属", ["是", "否"], default=["是", "否"],
                                  help="是=希腊本土品牌，否=进口品牌")
    sel_cats     = st.multiselect("🍓 口味分类", df["分类"].unique(),
                                  default=df["分类"].unique())
    st.markdown("---")
    st.caption("数据采集日期：2026-05")
    st.caption(f"覆盖网站：{df['网站名称'].nunique()} 个")

fdf = df[
    df["网站名称"].isin(sel_websites) &
    df["产品类型"].isin(sel_types) &
    df["品牌_标准化"].isin(sel_brands) &
    df["本土属性"].isin(sel_origin) &
    df["分类"].isin(sel_cats)
].copy()

if fdf.empty:
    st.error("⚠️ 当前筛选条件下无数据，请放宽筛选范围。")
    st.stop()

# ==================== 标题 ====================
st.markdown("# 🇬🇷 希腊电子烟油市场热销榜单分析看板")
st.markdown(
    f"**当前筛选数据：{len(fdf)} 条记录** | "
    f"品牌 {fdf['品牌_标准化'].nunique()} 个 | "
    f"网站 {fdf['网站名称'].nunique()} 个"
)
st.markdown("---")

# ==================== 标签页 ====================
tabs = st.tabs([
    "📊 总览", "🏆 品牌分析", "🍭 口味分析",
    "🔖 口味元素", "🧩 分类洞察", "🌡️ 口感属性",
    "🌐 网站对比", "💡 总结建议"
])

# ─────────────────────────────────────────────
# TAB 1  总览
# ─────────────────────────────────────────────
with tabs[0]:
    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        ("📋 总记录数",   len(fdf)),
        ("🏷️ 品牌数",    fdf["品牌_标准化"].nunique()),
        ("🌐 网站数",     fdf["网站名称"].nunique()),
        ("🍭 独立口味数", fdf["口味名称_标准化"].nunique()),
        ("🏠 本土品牌占比", f"{(fdf['本土属性']=='是').sum()/len(fdf):.0%}"),
    ]
    for col, (label, val) in zip([c1, c2, c3, c4, c5], kpis):
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="value">{val}</div>'
            f'<div class="label">{label}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<p class="section-title">产品类型分布</p>', unsafe_allow_html=True)
        tc = fdf["产品类型"].value_counts().reset_index()
        tc.columns = ["产品类型", "数量"]
        fig = px.pie(tc, values="数量", names="产品类型",
                     color_discrete_sequence=[COLORS["primary"], COLORS["secondary"]],
                     hole=0.45, template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<p class="section-title">口味分类分布</p>', unsafe_allow_html=True)
        cc = fdf["分类"].value_counts().reset_index()
        cc.columns = ["分类", "数量"]
        fig = px.bar(cc, x="分类", y="数量",
                     color="分类", color_discrete_map=CAT_COLOR_MAP,
                     text="数量", template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20),
                          xaxis_title="", yaxis_title="产品数量")
        st.plotly_chart(fig, use_container_width=True)

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown('<p class="section-title">本土 vs 进口品牌分布</p>', unsafe_allow_html=True)
        oc = fdf["本土属性"].value_counts().reset_index()
        oc.columns = ["品牌归属", "数量"]
        oc["品牌归属"] = oc["品牌归属"].map({"是": "🏠 希腊本土", "否": "✈️ 进口品牌"})
        fig = px.pie(oc, values="数量", names="品牌归属",
                     color_discrete_sequence=[COLORS["local"], COLORS["foreign"]],
                     hole=0.45, template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    with col_r2:
        st.markdown('<p class="section-title">各网站记录数量</p>', unsafe_allow_html=True)
        sc = fdf["网站名称"].value_counts().reset_index()
        sc.columns = ["网站", "数量"]
        fig = px.bar(sc, x="数量", y="网站", orientation="h",
                     text="数量",
                     color_discrete_sequence=[COLORS["primary"]],
                     template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20),
                          xaxis_title="记录数", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# TAB 2  品牌分析
# ─────────────────────────────────────────────
with tabs[1]:
    st.markdown('<p class="section-title">品牌热销榜 Top 10（按出现次数）</p>', unsafe_allow_html=True)
    sel_type_brand = st.radio("选择产品类型", ["全部"] + list(fdf["产品类型"].unique()), horizontal=True)
    tdf = fdf if sel_type_brand == "全部" else fdf[fdf["产品类型"] == sel_type_brand]

    top10 = tdf["品牌_标准化"].value_counts().head(10).reset_index()
    top10.columns = ["品牌", "出现次数"]
    top10["是否本土"] = top10["品牌"].map(brand_origin_dict).fillna("否")
    top10["颜色标签"] = top10["是否本土"].map({"是": "🏠 希腊本土", "否": "✈️ 进口品牌"})
    top10 = top10.sort_values("出现次数", ascending=True)

    fig = px.bar(top10, x="出现次数", y="品牌", orientation="h",
                 color="颜色标签",
                 color_discrete_map={"🏠 希腊本土": COLORS["local"], "✈️ 进口品牌": COLORS["foreign"]},
                 text="出现次数", template=PLOTLY_TEMPLATE)
    fig.update_traces(textposition="outside")
    fig.update_layout(height=380, legend_title_text="品牌归属",
                      margin=dict(t=10, b=10), xaxis_title="榜单出现次数", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">本土 vs 进口品牌 —— 各口味分类对比</p>', unsafe_allow_html=True)
    ct = pd.crosstab(fdf["本土属性"], fdf["分类"]).reset_index()
    ct_long = ct.melt(id_vars="本土属性", var_name="分类", value_name="数量")
    ct_long["品牌归属"] = ct_long["本土属性"].map({"是": "🏠 希腊本土", "否": "✈️ 进口品牌"})
    fig = px.bar(ct_long, x="分类", y="数量", color="品牌归属",
                 barmode="group",
                 color_discrete_map={"🏠 希腊本土": COLORS["local"], "✈️ 进口品牌": COLORS["foreign"]},
                 template=PLOTLY_TEMPLATE)
    fig.update_layout(xaxis_title="", yaxis_title="记录数",
                      legend_title_text="品牌归属", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">主要品牌在各产品类型的上榜次数</p>', unsafe_allow_html=True)
    top_brands_all = fdf["品牌_标准化"].value_counts().head(12).index.tolist()
    heat_data = fdf[fdf["品牌_标准化"].isin(top_brands_all)]
    pivot = pd.crosstab(heat_data["品牌_标准化"], heat_data["产品类型"])
    fig = px.imshow(pivot, text_auto=True, aspect="auto",
                    color_continuous_scale="Blues", template=PLOTLY_TEMPLATE)
    fig.update_layout(xaxis_title="产品类型", yaxis_title="品牌",
                      coloraxis_showscale=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# TAB 3  口味分析
# ─────────────────────────────────────────────
with tabs[2]:
    col_l, col_r = st.columns([1, 1])

    with col_l:
        st.markdown('<p class="section-title">全榜热门口味 Top 15</p>', unsafe_allow_html=True)
        fl = fdf["口味名称_标准化"].value_counts().head(15).reset_index()
        fl.columns = ["口味名称", "出现次数"]
        fl = fl.sort_values("出现次数", ascending=True)
        fig = px.bar(fl, x="出现次数", y="口味名称", orientation="h",
                     text="出现次数",
                     color_discrete_sequence=[COLORS["primary"]],
                     template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside")
        fig.update_layout(height=480, margin=dict(t=10, b=10),
                          xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        # 图表下方：对应口味标签（与图表顺序一致：从多到少，即 fl 降序）
        fl_desc = fl.sort_values("出现次数", ascending=False)
        for _, row in fl_desc.iterrows():
            fname = row["口味名称"]
            rows_with_flavor = fdf[fdf["口味名称_标准化"] == fname]["口味标签列表"]
            all_tags_for_flavor = []
            seen = set()
            for tag_list in rows_with_flavor:
                for t in tag_list:
                    if t not in seen:
                        seen.add(t)
                        all_tags_for_flavor.append(t)
            # 按出现频次排序后去重展示
            tag_freq = Counter(
                [t for tl in rows_with_flavor for t in tl]
            )
            sorted_tags = [t for t, _ in tag_freq.most_common()]
            tags_html = " ".join(
                [f'<span class="tag-chip">{t}</span>' for t in sorted_tags]
            ) if sorted_tags else '<span style="color:#9ca3af">无标签</span>'
            st.markdown(
                f'<div class="flavor-tag-row">'
                f'<b>{fname}</b>　{tags_html}'
                f'</div>',
                unsafe_allow_html=True
            )

    with col_r:
        st.markdown('<p class="section-title">按产品类型的热门口味</p>', unsafe_allow_html=True)
        ptype = st.selectbox("产品类型", fdf["产品类型"].unique(), key="flavor_type")
        tfl = fdf[fdf["产品类型"] == ptype]["口味名称_标准化"].value_counts().head(12).reset_index()
        tfl.columns = ["口味名称", "出现次数"]
        tfl = tfl.sort_values("出现次数", ascending=True)
        fig = px.bar(tfl, x="出现次数", y="口味名称", orientation="h",
                     text="出现次数",
                     color_discrete_sequence=[COLORS["secondary"]],
                     template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside")
        fig.update_layout(height=480, margin=dict(t=10, b=10),
                          xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        # 图表下方：对应口味标签
        tfl_desc = tfl.sort_values("出现次数", ascending=False)
        for _, row in tfl_desc.iterrows():
            fname = row["口味名称"]
            rows_with_flavor = fdf[
                (fdf["口味名称_标准化"] == fname) & (fdf["产品类型"] == ptype)
            ]["口味标签列表"]
            tag_freq = Counter([t for tl in rows_with_flavor for t in tl])
            sorted_tags = [t for t, _ in tag_freq.most_common()]
            tags_html = " ".join(
                [f'<span class="tag-chip">{t}</span>' for t in sorted_tags]
            ) if sorted_tags else '<span style="color:#9ca3af">无标签</span>'
            st.markdown(
                f'<div class="flavor-tag-row">'
                f'<b>{fname}</b>　{tags_html}'
                f'</div>',
                unsafe_allow_html=True
            )

    # 本土 vs 进口 口味对比
    st.markdown('<p class="section-title">本土品牌 vs 进口品牌 —— 热门口味对比</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    for col, origin, label, color in [
        (col_a, "是", "🏠 希腊本土品牌", COLORS["local"]),
        (col_b, "否", "✈️ 进口品牌",     COLORS["foreign"]),
    ]:
        odf_src = fdf[fdf["本土属性"] == origin]
        odf = odf_src["口味名称_标准化"].value_counts().head(10).reset_index()
        odf.columns = ["口味名称", "出现次数"]
        odf = odf.sort_values("出现次数", ascending=True)
        with col:
            st.markdown(f"**{label}**")
            fig = px.bar(odf, x="出现次数", y="口味名称", orientation="h",
                         text="出现次数",
                         color_discrete_sequence=[color],
                         template=PLOTLY_TEMPLATE)
            fig.update_traces(textposition="outside")
            fig.update_layout(height=360, margin=dict(t=10, b=10),
                              xaxis_title="", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

            # 对应口味标签
            odf_desc = odf.sort_values("出现次数", ascending=False)
            for _, row in odf_desc.iterrows():
                fname = row["口味名称"]
                rows_with_flavor = odf_src[
                    odf_src["口味名称_标准化"] == fname
                ]["口味标签列表"]
                tag_freq = Counter([t for tl in rows_with_flavor for t in tl])
                sorted_tags = [t for t, _ in tag_freq.most_common()]
                tags_html = " ".join(
                    [f'<span class="tag-chip">{t}</span>' for t in sorted_tags]
                ) if sorted_tags else '<span style="color:#9ca3af">无标签</span>'
                st.markdown(
                    f'<div class="flavor-tag-row">'
                    f'<b>{fname}</b>　{tags_html}'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ─────────────────────────────────────────────
# TAB 4  口味元素
# ─────────────────────────────────────────────
with tabs[3]:
    all_tags = []
    for tags in fdf["口味标签列表"]:
        all_tags.extend(tags)
    tag_counts = Counter(all_tags)

    st.markdown('<p class="section-title">热门口味元素 Top 20（全量）</p>', unsafe_allow_html=True)
    top_tags = pd.DataFrame(tag_counts.most_common(20), columns=["口味元素", "出现次数"])
    top_tags = top_tags.sort_values("出现次数", ascending=True)
    fig = px.bar(top_tags, x="出现次数", y="口味元素", orientation="h",
                 text="出现次数",
                 color="出现次数",
                 color_continuous_scale="Blues",
                 template=PLOTLY_TEMPLATE)
    fig.update_traces(textposition="outside")
    fig.update_layout(coloraxis_showscale=False, height=520,
                      margin=dict(t=10, b=10), xaxis_title="", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">各口味分类的高频元素</p>', unsafe_allow_html=True)
    cats = fdf["分类"].unique().tolist()
    n_col = min(3, len(cats))
    cat_cols = st.columns(n_col)
    for i, cat in enumerate(cats):
        cdf = fdf[fdf["分类"] == cat]
        cat_tags = []
        for tags in cdf["口味标签列表"]:
            cat_tags.extend(tags)
        top5 = Counter(cat_tags).most_common(5)
        with cat_cols[i % n_col]:
            st.markdown(
                f"<b>{cat}</b><br>" +
                " ".join([f'<span class="tag-chip">{t} ({c})</span>' for t, c in top5]),
                unsafe_allow_html=True
            )

    st.markdown('<p class="section-title">高频口味元素 —— 按品牌归属对比</p>', unsafe_allow_html=True)
    tag_compare = []
    for origin in ["是", "否"]:
        odf = fdf[fdf["本土属性"] == origin]
        otags = []
        for tags in odf["口味标签列表"]:
            otags.extend(tags)
        for t, c in Counter(otags).most_common(10):
            tag_compare.append({
                "口味元素": t, "出现次数": c,
                "归属": "🏠 本土" if origin == "是" else "✈️ 进口"
            })
    tc_df = pd.DataFrame(tag_compare)
    if not tc_df.empty:
        fig = px.bar(tc_df, x="口味元素", y="出现次数", color="归属",
                     barmode="group",
                     color_discrete_map={"🏠 本土": COLORS["local"], "✈️ 进口": COLORS["foreign"]},
                     template=PLOTLY_TEMPLATE)
        fig.update_layout(xaxis_title="", yaxis_title="出现次数",
                          legend_title_text="品牌归属", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# TAB 5  分类洞察
# ─────────────────────────────────────────────
with tabs[4]:
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<p class="section-title">整体分类占比</p>', unsafe_allow_html=True)
        cc = fdf["分类"].value_counts().reset_index()
        cc.columns = ["分类", "数量"]
        fig = px.pie(cc, values="数量", names="分类",
                     color="分类", color_discrete_map=CAT_COLOR_MAP,
                     hole=0.4, template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<p class="section-title">产品类型 × 口味分类 交叉分布</p>', unsafe_allow_html=True)
        if fdf["产品类型"].nunique() >= 2:
            cross = pd.crosstab(fdf["产品类型"], fdf["分类"]).reset_index().melt(
                id_vars="产品类型", var_name="分类", value_name="数量"
            )
            fig = px.bar(cross, x="产品类型", y="数量", color="分类",
                         barmode="group", color_discrete_map=CAT_COLOR_MAP,
                         template=PLOTLY_TEMPLATE)
            fig.update_layout(xaxis_title="", yaxis_title="记录数",
                              legend_title_text="分类", margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("产品类型不足两种，无法对比。")

    st.markdown('<p class="section-title">各分类 Top 3 品牌</p>', unsafe_allow_html=True)
    cats_list = fdf["分类"].value_counts().index.tolist()
    n = min(3, len(cats_list))
    cat_brand_cols = st.columns(n)
    for i, cat in enumerate(cats_list):
        cdf = fdf[fdf["分类"] == cat]
        top3 = cdf["品牌_标准化"].value_counts().head(3)
        with cat_brand_cols[i % n]:
            st.markdown(
                f'<div class="insight-box"><b>{cat}</b><br>' +
                "<br>".join([
                    f"{'🥇🥈🥉'[j]} {b} ({c}次)"
                    for j, (b, c) in enumerate(top3.items())
                ]) +
                "</div>",
                unsafe_allow_html=True
            )

# ─────────────────────────────────────────────
# TAB 6  口感属性
# ─────────────────────────────────────────────
with tabs[5]:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">含冰/薄荷比例</p>', unsafe_allow_html=True)
        ic = fdf["含冰/薄荷"].value_counts().reset_index()
        ic.columns = ["含冰/薄荷", "数量"]
        fig = px.pie(ic, values="数量", names="含冰/薄荷",
                     color="含冰/薄荷",
                     color_discrete_map={"是": COLORS["ice"], "否": "#e2e8f0", "不确定": "#cbd5e1"},
                     hole=0.45, template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<p class="section-title">含烟草比例</p>', unsafe_allow_html=True)
        tc2 = fdf["含烟草"].value_counts().reset_index()
        tc2.columns = ["含烟草", "数量"]
        fig = px.pie(tc2, values="数量", names="含烟草",
                     color="含烟草",
                     color_discrete_map={"是": COLORS["tobacco"], "否": "#e2e8f0", "不确定": "#cbd5e1"},
                     hole=0.45, template=PLOTLY_TEMPLATE)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(margin=dict(t=20, b=20), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">本土 vs 进口品牌的口感偏好对比</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        bi = pd.crosstab(fdf["本土属性"], fdf["含冰/薄荷"]).reset_index().melt(
            id_vars="本土属性", var_name="含冰/薄荷", value_name="数量"
        )
        bi["品牌归属"] = bi["本土属性"].map({"是": "🏠 本土", "否": "✈️ 进口"})
        fig = px.bar(bi, x="品牌归属", y="数量", color="含冰/薄荷",
                     barmode="group",
                     color_discrete_map={"是": COLORS["ice"], "否": "#94a3b8", "不确定": "#e2e8f0"},
                     title="含冰/薄荷偏好", template=PLOTLY_TEMPLATE)
        fig.update_layout(xaxis_title="", margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        bt = pd.crosstab(fdf["本土属性"], fdf["含烟草"]).reset_index().melt(
            id_vars="本土属性", var_name="含烟草", value_name="数量"
        )
        bt["品牌归属"] = bt["本土属性"].map({"是": "🏠 本土", "否": "✈️ 进口"})
        fig = px.bar(bt, x="品牌归属", y="数量", color="含烟草",
                     barmode="group",
                     color_discrete_map={"是": COLORS["tobacco"], "否": "#94a3b8", "不确定": "#e2e8f0"},
                     title="含烟草偏好", template=PLOTLY_TEMPLATE)
        fig.update_layout(xaxis_title="", margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">各口味分类中"含冰/薄荷"分布</p>', unsafe_allow_html=True)
    ci = pd.crosstab(fdf["分类"], fdf["含冰/薄荷"]).reset_index().melt(
        id_vars="分类", var_name="含冰/薄荷", value_name="数量"
    )
    fig = px.bar(ci, x="分类", y="数量", color="含冰/薄荷",
                 barmode="stack",
                 color_discrete_map={"是": COLORS["ice"], "否": "#94a3b8", "不确定": "#e2e8f0"},
                 template=PLOTLY_TEMPLATE)
    fig.update_layout(xaxis_title="", yaxis_title="记录数",
                      legend_title_text="含冰/薄荷", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# TAB 7  网站对比
# ─────────────────────────────────────────────
with tabs[6]:
    st.markdown('<p class="section-title">各网站产品类型榜单数量</p>', unsafe_allow_html=True)
    st_type = fdf.groupby(["网站名称", "产品类型"]).size().reset_index(name="数量")
    fig = px.bar(st_type, x="网站名称", y="数量", color="产品类型",
                 barmode="group",
                 color_discrete_sequence=[COLORS["primary"], COLORS["secondary"]],
                 text="数量", template=PLOTLY_TEMPLATE)
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="", yaxis_title="记录数", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">各网站口味分类结构</p>', unsafe_allow_html=True)
    st_cat = fdf.groupby(["网站名称", "分类"]).size().reset_index(name="数量")
    fig = px.bar(st_cat, x="网站名称", y="数量", color="分类",
                 barmode="stack", color_discrete_map=CAT_COLOR_MAP,
                 template=PLOTLY_TEMPLATE)
    fig.update_layout(xaxis_title="", yaxis_title="记录数",
                      legend_title_text="分类", margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">各网站本土品牌记录占比</p>', unsafe_allow_html=True)
    sl = fdf.groupby("网站名称").apply(
        lambda x: round((x["本土属性"] == "是").sum() / len(x) * 100, 1)
    ).reset_index(name="本土占比%")
    sl = sl.sort_values("本土占比%", ascending=True)
    fig = px.bar(sl, x="本土占比%", y="网站名称", orientation="h",
                 text="本土占比%",
                 color_discrete_sequence=[COLORS["local"]],
                 template=PLOTLY_TEMPLATE)
    fig.update_traces(textposition="outside", texttemplate="%{text}%")
    fig.update_layout(margin=dict(t=10, b=10), xaxis_title="本土占比 (%)", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="section-title">各网站 Top 3 上榜品牌</p>', unsafe_allow_html=True)
    sites = fdf["网站名称"].unique()
    site_cols = st.columns(len(sites))
    for i, site in enumerate(sites):
        sdf = fdf[fdf["网站名称"] == site]
        top3 = sdf["品牌_标准化"].value_counts().head(3)
        with site_cols[i]:
            st.markdown(
                f'<div class="insight-box"><b>{site}</b><br>' +
                "<br>".join([
                    f"{'🥇🥈🥉'[j]} {b} ({c})"
                    for j, (b, c) in enumerate(top3.items())
                ]) +
                "</div>",
                unsafe_allow_html=True
            )

# ─────────────────────────────────────────────
# TAB 8  总结建议
# ─────────────────────────────────────────────
with tabs[7]:
    total   = len(fdf)
    local_n = (fdf["本土属性"] == "是").sum()
    foreign_n = (fdf["本土属性"] == "否").sum()
    local_r   = local_n / total
    foreign_r = foreign_n / total

    ice_r   = (fdf["含冰/薄荷"] == "是").sum() / total
    ice_unk = (fdf["含冰/薄荷"] == "不确定").sum() / total
    tob_r   = (fdf["含烟草"] == "是").sum() / total

    top_cat   = fdf["分类"].value_counts().idxmax()
    top_cat_r = fdf["分类"].value_counts().max() / total
    top_cat_n = fdf["分类"].value_counts().max()

    local_brands   = fdf[fdf["本土属性"] == "是"]["品牌_标准化"].value_counts()
    foreign_brands = fdf[fdf["本土属性"] == "否"]["品牌_标准化"].value_counts()
    top_local   = local_brands.index[0]   if len(local_brands)   > 0 else "无"
    top_local_n = local_brands.iloc[0]    if len(local_brands)   > 0 else 0
    top_foreign = foreign_brands.index[0] if len(foreign_brands) > 0 else "无"
    top_foreign_n = foreign_brands.iloc[0] if len(foreign_brands) > 0 else 0

    top3_flavors = fdf["口味名称_标准化"].value_counts().head(3).index.tolist()
    top3_str = "、".join(top3_flavors) if top3_flavors else "无"

    all_tags_sum = [t for tl in fdf["口味标签列表"] for t in tl]
    top5_tags = [t for t, _ in Counter(all_tags_sum).most_common(5)]

    local_brands_cnt  = fdf[fdf["本土属性"] == "是"]["品牌_标准化"].nunique()
    foreign_brands_cnt = fdf[fdf["本土属性"] == "否"]["品牌_标准化"].nunique()

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("### 📌 核心调研发现")
        findings = [
            ("调研规模",
             f"共 {total} 条记录，覆盖 {fdf['网站名称'].nunique()} 个希腊零售电商网站、"
             f"{fdf['品牌_标准化'].nunique()} 个品牌"),
            ("市场格局",
             f"希腊本土品牌占 **{local_r:.1%}**（{local_n} 条），进口品牌占 **{foreign_r:.1%}**（{foreign_n} 条）。"
             f"本土品牌在榜单数量上具有明显优势，但进口品牌以 {foreign_brands_cnt} 个品牌贡献了 {foreign_r:.0%} 的记录，品牌多样性同样很高"),
            ("主导分类",
             f"**{top_cat}** 为最大品类，共 {top_cat_n} 条，占比 **{top_cat_r:.1%}**，"
             f"在所有网站中均有稳定表现"),
            ("冰感偏好",
             f"明确含冰/薄荷产品占 **{ice_r:.1%}**，另有 {ice_unk:.1%} 未明确标注。"
             f"冰感+水果的复合口味是进口品牌的重要增长驱动"),
            ("烟草需求",
             f"含烟草产品占 **{tob_r:.1%}**，是希腊市场中体量最大的稳定需求，"
             f"本土品牌在此品类中优势突出"),
            ("热门口味",
             f"Top 3 口味：{top3_str}"),
            ("高频元素",
             "  ".join([f"`{t}`" for t in top5_tags])),
        ]
        for title, content in findings:
            st.markdown(
                f'<div class="insight-box"><b>🔹 {title}</b>：{content}</div>',
                unsafe_allow_html=True
            )

    with col_r:
        st.markdown("### 🎯 品牌对比快览")
        st.markdown(
            f'<div class="insight-box">'
            f'<b>🏠 本土品牌代表</b>：{top_local}（上榜 {top_local_n} 次）<br>'
            f'共 {local_brands_cnt} 个本土品牌，强项为烟草、甜点，深耕希腊本地口味偏好<br><br>'
            f'<b>✈️ 进口品牌代表</b>：{top_foreign}（上榜 {top_foreign_n} 次）<br>'
            f'共 {foreign_brands_cnt} 个进口品牌，品牌数量更多，强项为水果冰感与创新口味组合'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown("### 📊 数据快速指标")
        metrics = {
            "总记录数":      total,
            "本土品牌数":    local_brands_cnt,
            "进口品牌数":    foreign_brands_cnt,
            "含冰/薄荷产品": f"{ice_r:.0%}",
            "含烟草产品":    f"{tob_r:.0%}",
        }
        for k, v in metrics.items():
            st.metric(k, v)

    st.markdown("---")
    st.markdown("### 💼 业务建议")
    suggestions = [
        ("强化冰感+水果复合产品线",
         f"含冰产品占明确标注中的较高比例，水果冰感是进口品牌发力的核心方向。"
         f"建议推出 Mango Ice、Tropical Ice 等冰感复合系列，扩大在年轻用户群中的渗透率。"),
        ("深耕希腊本土特色烟草口味",
         f"本土品牌（如 {top_local}）在传统烟草领域根基深厚，占 {top_cat_r:.0%} 的烟草类记录。"
         f"建议参考经典系列（Virginia、Hellas Blend），同时融入本地特色元素（蜂蜜、咖啡）进行差异化。"),
        ("布局烟草+甜香融合口味",
         "Tobacco+Vanilla+Caramel 三元组合（如 Tribeca、Master）在多网站榜单稳定出现，"
         "是成熟消费者日常首选，建议扩充此类口味数量。"),
        ("提升 Flavor Shots 品类渗透",
         "Flavor Shots 在多个网站独立成榜。"
         "建议在核心口味基础上推出浓缩版本，抢占 DIY 调液市场份额。"),
    ]
    cols_s = st.columns(2)
    for i, (title, content) in enumerate(suggestions):
        with cols_s[i % 2]:
            st.markdown(
                f'<div class="insight-box" style="margin-bottom:10px;">'
                f'<b>✅ {title}</b><br>'
                f'<span style="color:#4b5563">{content}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
