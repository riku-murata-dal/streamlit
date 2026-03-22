#!/usr/bin/env -S python -m streamlit run

import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt
import japanize_matplotlib
from population_adk import load_population, load_prefectures, add_prefectures

# -----------------------------
# 共有state初期化
# -----------------------------
if "shared_prefs" not in st.session_state:
    st.session_state.shared_prefs = []

if "shared_transpose" not in st.session_state:
    st.session_state.shared_transpose = True

if "shared_graph_type" not in st.session_state:
    st.session_state.shared_graph_type = "折れ線グラフ"


# -----------------------------
# 同期用関数
# -----------------------------
def sync_from_tab1():
    st.session_state.shared_prefs = st.session_state.graph1_prefs
    st.session_state.shared_transpose = st.session_state.graph1_transpose
    st.session_state.shared_graph_type = st.session_state.graph1_graph_type

    st.session_state.graph2_prefs = st.session_state.shared_prefs
    st.session_state.graph2_transpose = st.session_state.shared_transpose
    st.session_state.graph2_graph_type = st.session_state.shared_graph_type


def sync_from_tab2():
    st.session_state.shared_prefs = st.session_state.graph2_prefs
    st.session_state.shared_transpose = st.session_state.graph2_transpose
    st.session_state.shared_graph_type = st.session_state.graph2_graph_type

    st.session_state.graph1_prefs = st.session_state.shared_prefs
    st.session_state.graph1_transpose = st.session_state.shared_transpose
    st.session_state.graph1_graph_type = st.session_state.shared_graph_type

st.set_page_config(layout='wide')
st.title('都道府県別人口データ表示アプリ')


@st.cache_data
def get_population_table(population_file):
    return load_population(population_file)

@st.cache_data
def get_map_table(population_file, prefectures_file):
    pop = load_population(population_file)
    prefs = load_prefectures(prefectures_file)
    pop_prefs = add_prefectures(pop, prefs)
    return pop_prefs


upload_tab, table_tab, graph_tab, graph_tab2, geolocation_tab, scatter_tab, scatter_tab2 = st.tabs(
    ['ファイルアップロード', '表', 'グラフ', 'グラフ2', '地図', '散布図', '散布図2']
)

with upload_tab:
    st.markdown('### ファイルアップロード')
    col1, col2, col3 = st.columns(3)

    with col1:
        population_file = st.file_uploader(
            '人口データ（Excel）をアップロードしてください',
            type=['xlsx', 'xls']
        )

    with col2:
        prefectures_file = st.file_uploader(
            '都道府県位置データ（CSV）をアップロードしてください',
            type=['csv'],
            help='列名は「都道府県名」「緯度」「経度」を含めてください'
        )

    with col3:
        population2_file = st.file_uploader(
            '   散布図用データ（CSV）をアップロードしてください',
            type=['xlsx', 'xls'],
        )


# with table_tab:
#     if population_file is not None:
#         pop = get_population_table(population_file)
#         st.dataframe(pop, use_container_width=True)
#     else:
#         st.info('人口データ（Excel）をアップロードすると表を表示できます。')

with table_tab:
    if population_file is not None:
        pop = get_population_table(population_file)

        st.markdown("### 表")
        st.dataframe(pop, use_container_width=True)

        st.markdown("### ヒートマップ")
        st.dataframe(
            pop.style.background_gradient(cmap="Blues"),
            use_container_width=True
        )

        # -----------------------------
        # 判定テーブル
        # -----------------------------
        st.markdown("### 判定テーブル（1000以上：〇）")

        threshold = 1000

        judge_table = pop.applymap(lambda x: "〇" if x >= threshold else "×")

        # 色付け関数
        def color_judge(val):
            if val == "〇":
                return "background-color: #ffcccc; color: black;"  # 薄い赤
            else:
                return "background-color: #eeeeee; color: black;"  # グレー

        st.dataframe(
            judge_table.style.applymap(color_judge),
            use_container_width=True
        )

    else:
        st.info('人口データ（Excel）をアップロードすると表を表示できます。')


# -----------------------------
# グラフ
# -----------------------------
if population_file is not None:
    pop = get_population_table(population_file)
    pref_names = list(pop.index)

    # 初回だけ各タブ用widget値を共有値で初期化
    if "graph1_prefs" not in st.session_state:
        st.session_state.graph1_prefs = st.session_state.shared_prefs
    if "graph1_transpose" not in st.session_state:
        st.session_state.graph1_transpose = st.session_state.shared_transpose
    if "graph1_graph_type" not in st.session_state:
        st.session_state.graph1_graph_type = st.session_state.shared_graph_type

    if "graph2_prefs" not in st.session_state:
        st.session_state.graph2_prefs = st.session_state.shared_prefs
    if "graph2_transpose" not in st.session_state:
        st.session_state.graph2_transpose = st.session_state.shared_transpose
    if "graph2_graph_type" not in st.session_state:
        st.session_state.graph2_graph_type = st.session_state.shared_graph_type

    with graph_tab:
        st.subheader("グラフ（標準表示）")

        col1, col2 = st.columns(2)
        with col1:
            st.multiselect(
                "表示する都道府県を選択してください",
                options=pref_names,
                key="graph1_prefs",
                on_change=sync_from_tab1,
                help="未選択時はすべての都道府県が表示されます"
            )
        with col2:
            st.radio(
                "グラフタイプ",
                options=["折れ線グラフ", "棒グラフ"],
                horizontal=True,
                key="graph1_graph_type",
                on_change=sync_from_tab1
            )

        st.checkbox(
            "転置",
            value=st.session_state.shared_transpose,
            key="graph1_transpose",
            on_change=sync_from_tab1
        )

        graph_data_1 = pop.copy()
        if len(st.session_state.shared_prefs) > 0:
            graph_data_1 = graph_data_1.loc[st.session_state.shared_prefs]

        if st.session_state.shared_transpose:
            graph_data_1 = graph_data_1.transpose()

        graph_data_1.index = graph_data_1.index.astype(str)
        graph_data_1.columns = graph_data_1.columns.astype(str)

        if st.session_state.shared_graph_type == "折れ線グラフ":
            st.line_chart(
                data=graph_data_1,
                x_label="年" if st.session_state.shared_transpose else "都道府県",
                y_label="人口（単位千）"
            )
        else:
            st.bar_chart(
                data=graph_data_1,
                x_label="年" if st.session_state.shared_transpose else "都道府県",
                y_label="人口（単位千）",
                stack=False
            )

    with graph_tab2:
        st.subheader("グラフ（PNG保存対応）")

        col1, col2 = st.columns(2)
        with col1:
            st.multiselect(
                "表示する都道府県を選択してください",
                options=pref_names,
                key="graph2_prefs",
                on_change=sync_from_tab2,
                help="未選択時はすべての都道府県が表示されます"
            )
        with col2:
            st.radio(
                "グラフタイプ",
                options=["折れ線グラフ", "棒グラフ"],
                horizontal=True,
                key="graph2_graph_type",
                on_change=sync_from_tab2
            )

        st.checkbox(
            "転置",
            value=st.session_state.shared_transpose,
            key="graph2_transpose",
            on_change=sync_from_tab2
        )

        graph_data_2 = pop.copy()
        if len(st.session_state.shared_prefs) > 0:
            graph_data_2 = graph_data_2.loc[st.session_state.shared_prefs]

        if st.session_state.shared_transpose:
            graph_data_2 = graph_data_2.transpose()

        graph_data_2.index = graph_data_2.index.astype(str)
        graph_data_2.columns = graph_data_2.columns.astype(str)

        fig, ax = plt.subplots(figsize=(8, 5))

        if st.session_state.shared_graph_type == "折れ線グラフ":
            graph_data_2.plot(ax=ax)
        else:
            graph_data_2.plot(kind="bar", ax=ax)

        ax.set_xlabel("年" if st.session_state.shared_transpose else "都道府県")
        ax.set_ylabel("人口（単位千）")
        ax.set_title(st.session_state.shared_graph_type)
        ax.legend(
            title="都道府県" if st.session_state.shared_transpose else "年",
            bbox_to_anchor=(1.02, 1),
            loc="upper left"
        )
        plt.tight_layout()

        st.pyplot(fig)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)

        st.download_button(
            label="グラフをPNGでダウンロード",
            data=buf,
            file_name=f"population_graph_{st.session_state.shared_graph_type}.png",
            mime="image/png",
            key="download_graph_png"
        )

        plt.close(fig)

else:
    with graph_tab:
        st.subheader("グラフ")
        st.info("アップロードタブで人口データをアップロードしてください。")

    with graph_tab2:
        st.subheader("保存用グラフ")
        st.info("アップロードタブで人口データをアップロードしてください。")

with geolocation_tab:
    if population_file is not None and prefectures_file is not None:
        pop = get_population_table(population_file)
        pop_prefs = get_map_table(population_file, prefectures_file)

        years = list(pop.columns)
        year = st.select_slider('年', options=years, value=years[0])

        map_data = pop_prefs[['都道府県名', '緯度', '経度', year]].copy()
        map_data = map_data.rename(columns={year: '人口'})

        st.dataframe(map_data, use_container_width=True)

        st.map(
            data=map_data,
            latitude='緯度',
            longitude='経度',
            size='人口',
            color='#32CD3280'
        )

    elif population_file is not None and prefectures_file is None:
        st.info('地図表示には、都道府県位置データ（CSV）のアップロードも必要です。')

    elif population_file is None and prefectures_file is not None:
        st.info('地図表示には、人口データ（Excel）のアップロードも必要です。')

    else:
        st.info('地図表示には、人口データ（Excel）と都道府県位置データ（CSV）の両方が必要です。')

with scatter_tab:
    if population2_file is not None:
        df = pd.read_excel(population2_file)

        st.markdown("### 散布図（広告費 × 検索数）")

        # X軸選択（広告費）
        x_col = st.selectbox(
            "広告費を選択",
            options=["A広告費", "B広告費", "C広告費"],
            key="scatter_x"
        )

        # 散布図
        st.scatter_chart(
            df,
            x=x_col,
            y="検索数"
        )

        # データ確認（おすすめ）
        st.dataframe(df[[x_col, "検索数"]])

    else:
        st.info("ファイルをアップロードしてください")

import altair as alt

with scatter_tab2:
    if population2_file is not None:
        df = pd.read_excel(population2_file)

        x_col = st.selectbox(
            "広告費を選択",
            ["A広告費", "B広告費", "C広告費"]
        )

        # 相関係数
        corr = df[x_col].corr(df["検索数"])
        st.write(f"相関係数: {corr:.2f}")

        # 散布図＋回帰線
        base = alt.Chart(df).encode(
            x=x_col,
            y="検索数"
        )

        scatter = base.mark_circle(size=80)

        line = base.transform_regression(
            x_col, "検索数"
        ).mark_line(color="red")

        st.altair_chart(scatter + line, use_container_width=True)