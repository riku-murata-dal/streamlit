import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 定数
# =========================================================

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# 曜日の表示順
DAY_ORDER = ["月", "火", "水", "木", "金", "土", "日"]


# =========================================================
# 共有フィルタ同期関数
# - widget の値を shared state に保存する
# - 視聴率タブ / INDEXタブで widget key は分けつつ、
#   値だけ共通化したい場合に使用する
# =========================================================
def sync_shared_filter(widget_key, shared_key):

    # widget側の値をshared stateへ保存
    st.session_state[shared_key] = st.session_state[widget_key]


# =========================================================
# TOP / WORST 共通指定
# - TOP / WORST の件数を全局共通で指定する
# - NTV / TBS / CX / EX / TX すべて同じ件数を使用する
# - 視聴率タブ / INDEXタブ間で値を共有する
# =========================================================
def build_common_top_worst_filter(prefix="rating"):

    # shared state key
    # - 視聴率 / INDEX 間で共有する値
    top_shared_key = "shared_common_top"
    worst_shared_key = "shared_common_worst"

    # widget key
    # - widget自体は視聴率 / INDEXで別管理する
    top_widget_key = f"{prefix}_common_top"
    worst_widget_key = f"{prefix}_common_worst"

    # shared state初期化
    st.session_state.setdefault(top_shared_key, 0)
    st.session_state.setdefault(worst_shared_key, 0)

    # shared state → widget 同期
    # - タブを切り替えても同じ値を表示する
    if st.session_state.get(top_widget_key) != st.session_state[top_shared_key]:
        st.session_state[top_widget_key] = st.session_state[top_shared_key]

    if st.session_state.get(worst_widget_key) != st.session_state[worst_shared_key]:
        st.session_state[worst_widget_key] = st.session_state[worst_shared_key]

    # 入力欄を横並び表示（コンパクト）
    col1, col2, _ = st.columns([1, 1, 4])

    # TOP件数入力
    with col1:
        top_n = st.number_input(
            "TOP●位を選択｜赤枠表示",
            min_value=0,
            max_value=50,
            step=1,
            key=top_widget_key,
            on_change=sync_shared_filter,
            args=(top_widget_key, top_shared_key),
        )

    # WORST件数入力
    with col2:
        worst_n = st.number_input(
            "WORST●位を選択｜青枠表示",
            min_value=0,
            max_value=50,
            step=1,
            key=worst_widget_key,
            on_change=sync_shared_filter,
            args=(worst_widget_key, worst_shared_key),
        )

    # 後続処理で使いやすいようにdictで返す
    return {
        "top": int(top_n),
        "worst": int(worst_n),
    }


# =========================================================
# 表示セクション選択フィルター
# - 表示したいヒートマップセクションを複数選択する
# - 視聴率タブ / INDEXタブで選択状態は別管理する
# =========================================================
def build_section_filter(section_order, prefix="rating"):

    # 複数選択フィルター
    selected_sections = st.multiselect(
        "絞り込み",
        options=section_order,
        # default=section_order,
        default=[],   # 初期未選択
        key=f"{prefix}_selected_sections",
    )

    # 何も選択されていない場合
    if not selected_sections:
        st.warning("表示するセクションを1つ以上選択してください。")

    return selected_sections


# =========================================================
# 1局分のpivot作成
# - 指定セクション × 指定局のデータを抽出する
# - Plotlyヒートマップ用に「時間帯 × 曜日」のpivot形式へ変換する
# =========================================================
def make_station_pivot(df, group_col, group_value, station):

    # 対象セクション・対象局のみ抽出
    sub = df[
        (df[group_col] == group_value) &
        (df["局"] == station)
    ].copy()

    # 対象データがない場合
    if sub.empty:
        return None

    # 時間帯順に並べて、時間帯をindexにする
    pivot_df = (
        sub
        .sort_values("時間帯")
        [["時間帯"] + DAY_ORDER]
        .set_index("時間帯")
    )

    return pivot_df


# =========================================================
# TOP / WORST の座標取得
# - ヒートマップ上で赤枠 / 青枠を付けるセル位置を取得する
# - 同値はすべて含める
# =========================================================
def get_highlight_positions(pivot_df, top_n=0, worst_n=0):

    # データがない場合
    if pivot_df is None or pivot_df.empty:
        return set(), set()

    # 縦持ちに変換
    # index: 時間帯
    # columns: 曜日
    # values: 値
    stacked = pivot_df.stack(dropna=True).reset_index()
    stacked.columns = ["時間帯", "曜日", "値"]

    # 有効な値がない場合
    if stacked.empty:
        return set(), set()

    # Plotlyのshapeで枠線を引くため、
    # 時間帯・曜日を行番号・列番号へ変換する
    row_map = {idx: i for i, idx in enumerate(pivot_df.index)}
    col_map = {col: i for i, col in enumerate(pivot_df.columns)}

    stacked["row_idx"] = stacked["時間帯"].map(row_map)
    stacked["col_idx"] = stacked["曜日"].map(col_map)

    top_pos = set()
    worst_pos = set()

    # TOPセル取得
    if top_n > 0 and top_n <= len(stacked):

        # TOP n件目の値を閾値にする
        top_threshold = stacked["値"].nlargest(top_n).min()

        # 同値を含めて抽出
        top_df = stacked[stacked["値"] >= top_threshold]

        top_pos = set(zip(top_df["row_idx"], top_df["col_idx"]))

    elif top_n > 0:

        # 指定件数がデータ数を超える場合は全セル対象
        top_pos = set(zip(stacked["row_idx"], stacked["col_idx"]))

    # WORSTセル取得
    if worst_n > 0 and worst_n <= len(stacked):

        # WORST n件目の値を閾値にする
        worst_threshold = stacked["値"].nsmallest(worst_n).max()

        # 同値を含めて抽出
        worst_df = stacked[stacked["値"] <= worst_threshold]

        worst_pos = set(zip(worst_df["row_idx"], worst_df["col_idx"]))

    elif worst_n > 0:

        # 指定件数がデータ数を超える場合は全セル対象
        worst_pos = set(zip(stacked["row_idx"], stacked["col_idx"]))

    return top_pos, worst_pos


# =========================================================
# ヒートマップ図作成
# - 1局分のpivotをPlotlyヒートマップに変換する
# - TOP / WORSTセルには赤枠 / 青枠を付与する
# - -inf / inf は表示上「-」にする
# =========================================================
def build_heatmap_figure(pivot_df, title, top_n=0, worst_n=0):

    # グラフサイズ
    chart_height = 440
    chart_width = 400

    # フォントサイズ
    title_font_size = 18
    axis_font_size = 13
    cell_font_size = 11
    annotation_font_size = 16

    # データなしの場合
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

    # 元データ
    z = pivot_df.values.astype(float)

    x = list(pivot_df.columns)
    y = list(pivot_df.index)

    # ヒートマップ色付け用
    # - inf / -inf は NaN 扱い
    z_for_heatmap = np.where(np.isinf(z), np.nan, z)

    # セル表示文字列
    # - inf / -inf は "-"
    text = []

    for row in z:
        text_row = []

        for v in row:

            # NaN
            if pd.isna(v):
                text_row.append("")

            # inf / -inf
            elif np.isinf(v):
                text_row.append("-")

            # 通常数値
            else:
                text_row.append(f"{v:.2f}")

        text.append(text_row)

    # ヒートマップ本体
    fig = go.Figure(
        data=go.Heatmap(
            z=z_for_heatmap,
            x=x,
            y=y,
            colorscale="Blues",
            text=text,
            texttemplate="%{text}",
            textfont={"size": cell_font_size},
            hovertemplate=(
                "時間帯: %{y}"
                "<br>曜日: %{x}"
                "<br>値: %{text}"
                "<extra></extra>"
            ),
            showscale=False,
        )
    )

    # TOP / WORST 座標取得
    # - 判定は元pivot_dfを使用
    # - -inf は WORST 扱い
    top_positions, worst_positions = get_highlight_positions(
        pivot_df,
        top_n=top_n,
        worst_n=worst_n,
    )

    shapes = []

    # TOPセルに赤枠
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

    # WORSTセルに青枠
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
        margin=dict(l=45, r=5, t=60, b=10),
        shapes=shapes,
    )

    # x軸設定
    fig.update_xaxes(
        side="top",
        tickangle=0,
        tickfont=dict(size=axis_font_size),
        constrain="domain",
        ticks="",
    )

    # y軸設定
    fig.update_yaxes(
        autorange="reversed",
        tickfont=dict(size=axis_font_size),
        constrain="domain",
        ticks="",
        automargin=True,
    )

    return fig


# =========================================================
# 1セクション描画
# - 1つのセクションについて、5局のヒートマップを横並びで表示する
# =========================================================
def render_heatmap_section(df, section_title, group_col, filter_values, key_prefix):

    # セクション見出し
    st.markdown(f"### {section_title}")

    # 5局分のカラムを作成
    cols = st.columns(5, gap="large")

    # 局ごとにヒートマップを描画
    for col, station in zip(cols, STATION_ORDER):
        with col:

            # 1局分のpivot作成
            pivot_df = make_station_pivot(
                df=df,
                group_col=group_col,
                group_value=section_title,
                station=station,
            )

            # ヒートマップ作成
            fig = build_heatmap_figure(
                pivot_df,
                station,
                top_n=filter_values["top"],
                worst_n=filter_values["worst"],
            )

            # ヒートマップ表示
            st.plotly_chart(
                fig,
                use_container_width=False,
                config={"displaylogo": False},
                key=f"{key_prefix}_{section_title}_{station}",
            )


# =========================================================
# 視聴率ヒートマップ用: セクション列追加
# - データ種別 × カテゴリーから表示用セクション名を作成する
# =========================================================
def add_rating_section_col(df):

    work = df.copy()

    # 初期値
    work["セクション"] = None

    # VR 個人全体
    work.loc[
        (work["データ種別"] == "VR") &
        (work["カテゴリー"] == "個人全体"),
        "セクション"
    ] = "VR（個人全体/世帯）"

    # VR ターゲット
    work.loc[
        (work["データ種別"] == "VR") &
        (work["カテゴリー"] == "ターゲット"),
        "セクション"
    ] = "VR（ターゲット）"

    # TVAL 個人全体
    work.loc[
        (work["データ種別"] == "TVAL") &
        (work["カテゴリー"] == "個人全体"),
        "セクション"
    ] = "TVAL（個人全体/世帯）"

    # TVAL ターゲット
    work.loc[
        (work["データ種別"] == "TVAL") &
        (work["カテゴリー"] == "ターゲット"),
        "セクション"
    ] = "TVAL（ターゲット）"
    
    # REVISIO 注視TRP
    work.loc[
        (work["データ種別"] == "REVISIO") &
        (work["カテゴリー"] == "注視"),
        "セクション"
    ] = "REVISIO（注視）"
    
    # REVISIO 滞在TRP
    work.loc[
        (work["データ種別"] == "REVISIO") &
        (work["カテゴリー"] == "滞在"),
        "セクション"
    ] = "REVISIO（滞在）"
    
    # REVISIO 世帯
    work.loc[
        (work["データ種別"] == "REVISIO") &
        (work["カテゴリー"] == "世帯"),
        "セクション"
    ] = "REVISIO（世帯）"
    
    # TVAL×REVISIO補正（注視補正）
    work.loc[
        (work["データ種別"] == "TVAL×REVISIO補正") &
        (work["カテゴリー"] == "注視補正"),
        "セクション"
    ] = "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]"
    
    # TVAL×REVISIO補正（滞在補正）
    work.loc[
        (work["データ種別"] == "TVAL×REVISIO補正") &
        (work["カテゴリー"] == "滞在補正"),
        "セクション"
    ] = "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]"

    return work


# =========================================================
# 視聴率ヒートマップ表示
# - df_heatmap_all をもとに視聴率ヒートマップを描画する
# - アップロード済みファイルに応じて表示可能セクションを切り替える
# =========================================================
def render_rating_heatmap_from_df(
    df,
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):

    # データがない場合
    if df is None or df.empty:
        st.info("ヒートマップ用データがありません。")
        return

    # 表示用セクション列を追加
    work = add_rating_section_col(df)

    # セクションが付与された行のみ残す
    work = work[work["セクション"].notna()].copy()

    # アップロード済みファイルに応じて表示可能セクションを作成
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
        section_order.append("REVISIO（注視）")
        
    if revisio_file is not None:
        section_order.append("REVISIO（滞在）")
        
    if revisio_file is not None:
        section_order.append("REVISIO（世帯）")
        
    if revisio_file is not None:
        section_order.append("TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]")
    
    if revisio_file is not None:
        section_order.append("TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]")

    # 表示対象がない場合
    if not section_order:
        st.info("視聴率ヒートマップ表示に必要なファイルがアップロードされていません。")
        return

    # 表示セクションフィルター
    # - 表示するセクションを複数選択
    selected_sections = build_section_filter(
        section_order=section_order,
        prefix="rating",
    )

    # 未選択の場合は描画しない
    if not selected_sections:
        return

    # TOP / WORST 共通指定
    filter_values = build_common_top_worst_filter("rating")

    # セクションごとにヒートマップ描画
    for i, section_title in enumerate(selected_sections):

        render_heatmap_section(
            df=work,
            section_title=section_title,
            group_col="セクション",
            filter_values=filter_values,
            key_prefix="rating",
        )

        # セクション間の区切り線
        if i < len(selected_sections) - 1:
            st.markdown("---")


# =========================================================
# INDEXヒートマップで表示可能なセクション一覧を取得
# - アップロード済みファイルの組み合わせに応じて、
#   INDEXとして表示可能な指標を決める
# =========================================================
def get_available_index_sections(
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):

    sections = []

    # 1. TVAL（ターゲット）÷ VR（個人全体/世帯）
    if vr_all_file is not None and tval_target_file is not None:
        sections.append("TVAL（ターゲット）÷ VR（個人全体/世帯）")
        
    # 2. VR（ターゲット）÷ VR（個人全体/世帯）
    if vr_all_file is not None and vr_target_file is not None:
        sections.append("VR（ターゲット）÷ VR（個人全体/世帯）")
        
    # 3. TVAL（ターゲット）÷ TVAL（個人全体/世帯）
    if tval_all_file is not None and tval_target_file is not None:
        sections.append("TVAL（ターゲット）÷ TVAL（個人全体/世帯）")
        
    # 4. REVISIO（注視）÷ REVISIO（世帯）
    if revisio_file is not None:
        sections.append("REVISIO（注視）÷ REVISIO（世帯）")
        
    # 5. REVISIO（滞在）÷ REVISIO（世帯）
    if revisio_file is not None:
        sections.append("REVISIO（滞在）÷ REVISIO（世帯）")
        
    # 6. REVISIO（注視）÷ VR（個人全体/世帯）
    if revisio_file is not None and vr_all_file is not None:
        sections.append("REVISIO（注視）÷ VR（個人全体/世帯）")
        
    # 7. REVISIO（滞在）÷ VR（個人全体/世帯）
    if revisio_file is not None and vr_all_file is not None:
        sections.append("REVISIO（滞在）÷ VR（個人全体/世帯）")

    # 8. TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）
    if tval_target_file is not None and revisio_file is not None and vr_all_file is not None:
        sections.append("TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）")

    # 9. TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）
    if tval_target_file is not None and revisio_file is not None and vr_all_file is not None:
        sections.append("TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）")

    return sections


# =========================================================
# INDEXヒートマップ表示
# - make_df_heatmap_index で作成した df_heatmap_index を描画する
# - アップロード済みファイルの組み合わせに応じて表示セクションを切り替える
# =========================================================
def render_index_heatmap_from_df(
    df_index,
    vr_all_file,
    vr_target_file,
    tval_all_file,
    tval_target_file,
    revisio_file,
):

    # INDEXデータがない場合
    if df_index is None or df_index.empty:
        st.info("INDEX表示に必要な関連ファイルがアップロードされていません。")
        return

    # 表示可能なINDEXセクション一覧を取得
    section_order = get_available_index_sections(
        vr_all_file=vr_all_file,
        vr_target_file=vr_target_file,
        tval_all_file=tval_all_file,
        tval_target_file=tval_target_file,
        revisio_file=revisio_file,
    )

    # 表示対象がない場合
    if not section_order:
        st.info("INDEX表示に必要な関連ファイルがアップロードされていません。")
        return

    # 表示セクションフィルター
    # - 表示するINDEX指標を複数選択
    selected_sections = build_section_filter(
        section_order=section_order,
        prefix="index",
    )

    # 未選択の場合は描画しない
    if not selected_sections:
        return

    # TOP / WORST 共通指定
    filter_values = build_common_top_worst_filter("index")

    # セクションごとにヒートマップ描画
    for i, section_title in enumerate(selected_sections):

        render_heatmap_section(
            df=df_index,
            section_title=section_title,
            group_col="指標",
            filter_values=filter_values,
            key_prefix="index",
        )

        # セクション間の区切り線
        if i < len(selected_sections) - 1:
            st.markdown("---")