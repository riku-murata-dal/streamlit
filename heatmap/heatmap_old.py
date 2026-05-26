import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# 曜日の表示順
DAY_ORDER = ["月", "火", "水", "木", "金", "土", "日"]


# =========================================================
# 放送局別フィルタの共有用同期関数
# - 画面上の widget key と、実際に共有したい state key は分ける
# - 視聴率タブ / INDEXタブ で widget key は別にしつつ
#   値だけ共通 state に保存して連動させる
# =========================================================
def sync_shared_station_filter(widget_key, shared_key):
    st.session_state[shared_key] = st.session_state[widget_key]

# =========================================================
# 放送局別フィルタ
# - 各放送局ごとに TOP / WORST 件数を入力する
# - rating / index で別 widget を使うが、実際の値は shared state で連動させる
# =========================================================
def build_station_filters(prefix="rating"):
    st.markdown("#### 放送局別フィルタ")

    # 局ごとの入力欄を横並びで表示
    cols = st.columns(5, gap="large")
    station_filters = {}

    for col, station in zip(cols, STATION_ORDER):
        with col:
            # 局名見出し
            st.markdown(f"**{station}**")

            # 画面上の widget key はタブごとに分ける
            top_widget_key = f"{prefix}_top_{station}"
            worst_widget_key = f"{prefix}_worst_{station}"

            # 実際に共有したい値は共通 key に保存
            top_shared_key = f"shared_top_{station}"
            worst_shared_key = f"shared_worst_{station}"

            # shared state が未作成なら初期値 0 を入れる
            if top_shared_key not in st.session_state:
                st.session_state[top_shared_key] = 0
            if worst_shared_key not in st.session_state:
                st.session_state[worst_shared_key] = 0

            # widget 側に shared state の値を流し込む
            # これにより rating / index 間で同じ値を表示できる
            if st.session_state.get(top_widget_key) != st.session_state[top_shared_key]:
                st.session_state[top_widget_key] = st.session_state[top_shared_key]

            if st.session_state.get(worst_widget_key) != st.session_state[worst_shared_key]:
                st.session_state[worst_widget_key] = st.session_state[worst_shared_key]

            # 現在値をラベルにも表示
            current_top = st.session_state[top_widget_key]
            current_worst = st.session_state[worst_widget_key]

            # TOP件数入力
            top_n = st.number_input(
                f"TOP 指定{current_top}位",
                min_value=0,
                max_value=50,
                step=1,
                key=top_widget_key,
                on_change=sync_shared_station_filter,
                args=(top_widget_key, top_shared_key),
            )

            # WORST件数入力
            worst_n = st.number_input(
                f"WORST 指定{current_worst}位",
                min_value=0,
                max_value=50,
                step=1,
                key=worst_widget_key,
                on_change=sync_shared_station_filter,
                args=(worst_widget_key, worst_shared_key),
            )

            # 各局の設定値を保持
            station_filters[station] = {
                "top": int(top_n),
                "worst": int(worst_n),
            }

    st.caption("赤枠: TOP指定件数（同値含む） / 青枠: WORST指定件数（同値含む）")

    return station_filters

# =========================================================
# 共通: 1局分の pivot 作成
# - 指定したグループ列 / グループ値 / 局 でデータを抽出
# - 時間帯 × 曜日のヒートマップ用 pivot を作る
# =========================================================
def make_station_pivot(df, group_col, group_value, station):
    sub = df[
        (df[group_col] == group_value) &
        (df["局"] == station)
    ].copy()

    # データがなければ None を返す
    if sub.empty:
        return None

    # 時間帯順に並べて pivot 形式にする
    sub = sub.sort_values("時間帯")
    pivot_df = sub[["時間帯"] + DAY_ORDER].set_index("時間帯")

    return pivot_df


# =========================================================
# TOP / WORST の座標取得
# - ヒートマップ上で赤枠 / 青枠を付けるセル位置を求める
# - 同値はすべて含める
# =========================================================
def get_highlight_positions(pivot_df, top_n=0, worst_n=0):
    if pivot_df is None or pivot_df.empty:
        return set(), set()

    # 縦持ちに変換
    stacked = pivot_df.stack(dropna=True).reset_index()
    stacked.columns = ["時間帯", "曜日", "値"]

    if stacked.empty:
        return set(), set()

    # ヒートマップ上の row / col 座標に変換するための対応表
    row_map = {idx: i for i, idx in enumerate(pivot_df.index)}
    col_map = {col: i for i, col in enumerate(pivot_df.columns)}

    stacked["row_idx"] = stacked["時間帯"].map(row_map)
    stacked["col_idx"] = stacked["曜日"].map(col_map)

    top_pos = set()
    worst_pos = set()

    # TOP件数の座標取得
    if top_n > 0 and top_n <= len(stacked):
        top_threshold = stacked["値"].nlargest(top_n).min()
        top_df = stacked[stacked["値"] >= top_threshold]
        top_pos = set(zip(top_df["row_idx"], top_df["col_idx"]))
    elif top_n > 0:
        top_pos = set(zip(stacked["row_idx"], stacked["col_idx"]))

    # WORST件数の座標取得
    if worst_n > 0 and worst_n <= len(stacked):
        worst_threshold = stacked["値"].nsmallest(worst_n).max()
        worst_df = stacked[stacked["値"] <= worst_threshold]
        worst_pos = set(zip(worst_df["row_idx"], worst_df["col_idx"]))
    elif worst_n > 0:
        worst_pos = set(zip(stacked["row_idx"], stacked["col_idx"]))

    return top_pos, worst_pos


# =========================================================
# ヒートマップ図作成
# - 1局分の pivot を Plotly のヒートマップに変換
# - TOP / WORST のセルには枠線を付与
# =========================================================
def build_heatmap_figure(pivot_df, title, top_n=0, worst_n=0):
    # セルを少し広く見せるため、縦横サイズを大きめに設定
    chart_height = 440
    chart_width = 400

    # 文字サイズ
    title_font_size = 18
    axis_font_size = 13
    cell_font_size = 11
    annotation_font_size = 16

    # データがない場合は空の図を返す
    if pivot_df is None or pivot_df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                y=0.98,
                xanchor="center",
                yanchor="top",
                font=dict(size=title_font_size),
            ),
            width=chart_width,
            height=chart_height,
            margin=dict(l=10, r=10, t=70, b=10),
        )
        fig.add_annotation(
            text="データなし",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=annotation_font_size),
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    # ヒートマップ表示用の値・軸・表示文字列を作成
    z = pivot_df.values
    x = list(pivot_df.columns)
    y = list(pivot_df.index)
    text = [[f"{v:.2f}" if pd.notna(v) else "" for v in row] for row in z]

    # ヒートマップ本体
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale="Blues",
            text=text,
            texttemplate="%{text}",
            textfont={"size": cell_font_size},
            hovertemplate="時間帯: %{y}<br>曜日: %{x}<br>値: %{z:.2f}<extra></extra>",
            showscale=False,
        )
    )

    # TOP / WORST の枠線位置を取得
    top_positions, worst_positions = get_highlight_positions(
        pivot_df,
        top_n=top_n,
        worst_n=worst_n,
    )

    shapes = []

    # TOPセルに赤枠を付与
    for row_idx, col_idx in top_positions:
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=col_idx - 0.5,
                x1=col_idx + 0.5,
                y0=row_idx - 0.5,
                y1=row_idx + 0.5,
                line=dict(color="red", width=2),
                fillcolor="rgba(0,0,0,0)",
            )
        )

    # WORSTセルに青枠を付与
    for row_idx, col_idx in worst_positions:
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=col_idx - 0.5,
                x1=col_idx + 0.5,
                y0=row_idx - 0.5,
                y1=row_idx + 0.5,
                line=dict(color="blue", width=2),
                fillcolor="rgba(0,0,0,0)",
            )
        )

    # レイアウト設定
    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            y=0.98,
            xanchor="center",
            yanchor="top",
            font=dict(size=title_font_size),
        ),
        width=chart_width,
        height=chart_height,
        margin=dict(l=0, r=0, t=60, b=0),
        shapes=shapes,
    )

    # 軸設定
    fig.update_xaxes(
        side="top",
        tickangle=0,
        tickfont=dict(size=axis_font_size),
        constrain="domain",
        ticks="",                
    )
    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(size=axis_font_size),
        constrain="domain",
        ticks=""
    )

    return fig


# =========================================================
# 共通: 1セクション描画
# - 1つのセクションについて 5局のヒートマップを横並びで描画
# =========================================================
def render_heatmap_section(df, section_title, group_col, station_filters, key_prefix):
    st.markdown(f"### {section_title}")

    # 各局のヒートマップ同士の間隔を広げる
    cols = st.columns(5, gap="large")

    for col, station in zip(cols, STATION_ORDER):
        with col:
            # 1局分の pivot を作成
            pivot_df = make_station_pivot(df, group_col, section_title, station)

            # ヒートマップ図を作成
            fig = build_heatmap_figure(
                pivot_df,
                station,
                top_n=station_filters[station]["top"],
                worst_n=station_filters[station]["worst"],
            )

            # 図側で width を指定しているので、container 幅に無理に合わせない
            st.plotly_chart(
                fig,
                use_container_width=False,
                config={"displaylogo": False},
                key=f"{key_prefix}_{section_title}_{station}",
            )


# =========================================================
# 通常ヒートマップ用: セクション列追加
# - 視聴率ヒートマップ用に、表示用のセクション名を付与する
# =========================================================
def add_rating_section_col(df):
    work = df.copy()
    work["セクション"] = None

    work.loc[
        (work["データ種別"] == "VR") & (work["カテゴリー"] == "個人全体"),
        "セクション"
    ] = "VR（個人全体/世帯）"

    work.loc[
        (work["データ種別"] == "VR") & (work["カテゴリー"] == "ターゲット"),
        "セクション"
    ] = "VR（ターゲット）"

    work.loc[
        (work["データ種別"] == "TVAL") & (work["カテゴリー"] == "個人全体"),
        "セクション"
    ] = "TVAL（個人全体/世帯）"

    work.loc[
        (work["データ種別"] == "TVAL") & (work["カテゴリー"] == "ターゲット"),
        "セクション"
    ] = "TVAL（ターゲット）"

    work.loc[
        (work["データ種別"] == "REVISIO") & (work["カテゴリー"] == "個人全体"),
        "セクション"
    ] = "REVISIO（個人全体/世帯）"

    return work


# =========================================================
# 通常ヒートマップ表示
# - df_heatmap_all をもとに視聴率ヒートマップを描画する
# - アップロード済みファイルに応じて表示セクションを切り替える
# =========================================================
def render_rating_heatmap_from_df(
    df,
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):

    # データがなければ終了
    if df is None or df.empty:
        st.info("ヒートマップ用データがありません。")
        return

    # セクション列を付与し、表示対象のみ抽出
    work = add_rating_section_col(df)
    work = work[work["セクション"].notna()].copy()

    # アップロードされているファイルに応じて表示順を決定
    section_order = []

    if vr_all_file is not None:
        section_order.append("VR（個人全体/世帯）")

    if vr_target_file is not None:
        section_order.append("VR（ターゲット）")

    if tval_all_file is not None:
        section_order.append("TVAL（個人全体/世帯）")

    if tval_target_file is not None:
        section_order.append("TVAL（ターゲット）")

    if revisio_file is not None:
        section_order.append("REVISIO（個人全体/世帯）")

    if not section_order:
        st.info("視聴率ヒートマップ表示に必要なファイルがアップロードされていません。")
        return

     # 放送局別フィルタを取得
    station_filters = build_station_filters("rating")

    # セクションごとに描画
    for i, section_title in enumerate(section_order):
        render_heatmap_section(
            df=work,
            section_title=section_title,
            group_col="セクション",
            station_filters=station_filters,
            key_prefix="rating",
        )

        if i < len(section_order) - 1:
            st.markdown("---")

# =========================================================
# INDEXヒートマップで表示可能なセクション一覧を取得
# - アップロード済みファイルの組み合わせに応じて
#   INDEXの表示対象を決める
# =========================================================
def get_available_index_sections(
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):
    sections = []

    if vr_all_file is not None and tval_target_file is not None:
        sections.append("TVAL（ターゲット）÷ VR（個人全体/世帯）")

    if vr_all_file is not None and revisio_file is not None:
        sections.append("REVISIO（個人全体）÷ VR（個人全体/世帯）")

    if vr_all_file is not None and tval_target_file is not None and revisio_file is not None:
        sections.append("［TVAL（ターゲット）× REVISIO（個人全体）］÷ VR（個人全体/世帯）")

    if vr_all_file is not None and vr_target_file is not None:
        sections.append("VR（ターゲット）÷ VR（個人全体/世帯）")

    if tval_all_file is not None and tval_target_file is not None:
        sections.append("TVAL（ターゲット）÷ TVAL（個人全体/世帯）")

    return sections


# =========================================================
# INDEXヒートマップ表示
# - make_df_heatmap_index で作成した df_heatmap_index を描画する
# =========================================================
def render_index_heatmap_from_df(
    df_index,
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):

    if df_index is None or df_index.empty:
        st.info("INDEX表示に必要な関連ファイルがアップロードされていません。")
        return

    station_filters = build_station_filters("index")

    section_order = get_available_index_sections(
        vr_all_file=vr_all_file,
        vr_target_file=vr_target_file,
        tval_all_file=tval_all_file,
        tval_target_file=tval_target_file,
        revisio_file=revisio_file,
    )

    if not section_order:
        st.info("INDEX表示に必要な関連ファイルがアップロードされていません。")
        return

    for i, section_title in enumerate(section_order):
        render_heatmap_section(
            df=df_index,
            section_title=section_title,
            group_col="指標",
            station_filters=station_filters,
            key_prefix="index",
        )

        if i < len(section_order) - 1:
            st.markdown("---")