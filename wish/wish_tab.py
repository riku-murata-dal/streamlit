import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ゾーンタブ側で定義しているsession_state初期化関数を読み込む
from zone.zone_tab import init_zone_state


# =========================================================
# 定数
# =========================================================

# 曜日順
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# ゾーン名一覧
ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]


# =========================================================
# 希望枠タブで使用するゾーン設定を取得
# - zone_tab側で保持している正式なゾーン設定を取得する
# =========================================================
def get_wish_zone_df(selected_zone_name):
    return st.session_state["zone_filters"][selected_zone_name]


# =========================================================
# 共有ゾーン選択の同期
# - ラジオボタンで選択したゾーンを共有stateに保存する
# - 希望枠タブ / INDEXタブ / MIXタブで同じゾーン選択を使うため
# =========================================================
def sync_shared_wish_zone(widget_key):
    st.session_state["shared_wish_zone"] = st.session_state[widget_key]


# =========================================================
# 共有TOP割合の同期
# - TOP割合の入力値を共有stateに保存する
# =========================================================
def sync_shared_wish_top_rate(widget_key):
    st.session_state["shared_wish_top_rate"] = st.session_state[widget_key]


# =========================================================
# 共有WORST割合の同期
# - WORST割合の入力値を共有stateに保存する
# =========================================================
def sync_shared_wish_worst_rate(widget_key):
    st.session_state["shared_wish_worst_rate"] = st.session_state[widget_key]
    
    
# =========================================================
# セグメント絞り込みフィルター
# - 表示対象のセクション / 指標 / 組み合わせを絞り込む
# - 視聴率 / INDEX / MIX で prefix を分けて使う
# =========================================================
def build_segment_filter(section_order, prefix="wish"):

    # 表示候補がない場合
    if not section_order:
        return []

    selected_sections = st.multiselect(
        "絞り込み",
        options=section_order,
        # default=section_order,
        default=[],   # 初期未選択
        key=f"{prefix}_segment_filter",
    )

    # 何も選択されていない場合
    if not selected_sections:
        st.warning("表示するセクションを1つ以上選択してください。")

    return selected_sections


# =========================================================
# 希望枠共通コントロール
# - 対象ゾーンを選択する
# - TOP割合を指定する
# - WORST割合を指定する
#
# 変更点
# - TOP / WORST の入力欄を左端に寄せる
# - 右側に余白カラムを置く
# =========================================================
def render_shared_wish_controls(prefix):

    # 共有stateの初期化
    st.session_state.setdefault("shared_wish_zone", ZONE_NAMES[0])
    st.session_state.setdefault("shared_wish_top_rate", 30)
    st.session_state.setdefault("shared_wish_worst_rate", 30)

    # widget key
    zone_key = f"{prefix}_wish_zone"
    top_key = f"{prefix}_wish_top_rate"
    worst_key = f"{prefix}_wish_worst_rate"

    # shared state → widget state へ反映
    if st.session_state.get(zone_key) != st.session_state["shared_wish_zone"]:
        st.session_state[zone_key] = st.session_state["shared_wish_zone"]

    if st.session_state.get(top_key) != st.session_state["shared_wish_top_rate"]:
        st.session_state[top_key] = st.session_state["shared_wish_top_rate"]

    if st.session_state.get(worst_key) != st.session_state["shared_wish_worst_rate"]:
        st.session_state[worst_key] = st.session_state["shared_wish_worst_rate"]

    # 対象ゾーン選択
    selected_zone = st.radio(
        "対象ゾーン",
        ZONE_NAMES,
        horizontal=True,
        key=zone_key,
        on_change=sync_shared_wish_zone,
        args=(zone_key,),
    )

    # TOP / WORST を左端に寄せる
    col1, col2, _ = st.columns([1, 1, 4])

    with col1:
        top_rate = st.number_input(
            "TOP割合（%）",
            min_value=0,
            max_value=100,
            # value=st.session_state["shared_wish_top_rate"],
            step=5,
            key=top_key,
            on_change=sync_shared_wish_top_rate,
            args=(top_key,),
        )

    with col2:
        worst_rate = st.number_input(
            "WORST割合（%）",
            min_value=0,
            max_value=100,
            # value=st.session_state["shared_wish_worst_rate"],
            step=5,
            key=worst_key,
            on_change=sync_shared_wish_worst_rate,
            args=(worst_key,),
        )

    return selected_zone, int(top_rate), int(worst_rate)


# =========================================================
# 凡例表示
# - 視聴率単体 / INDEX単体の希望枠タブで使用
# =========================================================
def render_simple_wish_legend(
    wish_text,
    normal_text,
    reject_text,
    wish_color="#ff8f86",
    normal_color="#FFFFFF",
    reject_color="#b5b5b8",
    normal_border=True,
):
    normal_border_css = ""

    if normal_border:
        normal_border_css = "border:1px solid #bdbdbd; box-sizing:border-box;"

    legend_html = f"""
    <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap; margin:8px 0 16px 0;">
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:{wish_color};"></div>
                <span>希望枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:{normal_color}; {normal_border_css}"></div>
                <span>普通枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:{reject_color};"></div>
                <span>拒否枠</span>
            </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div>{wish_text}</div>
            <div>{normal_text}</div>
            <div>{reject_text}</div>
        </div>
    </div>
    """

    st.markdown(legend_html, unsafe_allow_html=True)


# =========================================================
# 視聴率データにセクション列を追加
# - データ種別 × カテゴリーを画面表示用の名称に変換する
# =========================================================
def add_rating_section_col(df):

    work = df.copy()
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
# 1局分のpivot作成
# - 指定セクション × 指定局のデータを抽出する
# - 時間帯をindex、曜日をcolumnsにした表にする
# =========================================================
def make_station_pivot(df, section_title, station):

    sub = df[
        (df["セクション"] == section_title) &
        (df["局"] == station)
    ].copy()

    if sub.empty:
        return None

    sub = sub.sort_values("時間帯")

    return sub[["時間帯"] + WEEKDAYS].set_index("時間帯")


# =========================================================
# ゾーンマスク作成
# - zone_dfを対象DataFrameのindex / columnsに合わせる
# - ゾーン内 True / ゾーン外 False の表として返す
# =========================================================
def get_zone_mask_for_df(zone_df, df):

    return zone_df.reindex(
        index=df.index,
        columns=df.columns,
        fill_value=False,
    ).astype(bool)


# =========================================================
# ランキング対象の系列を作成
# - DataFrameを縦持ちにして1系列にする
# - 有限値のみランキング対象にする
# - inf / -inf はランキングから除外する
#
# 注意）
# 分母0などを -inf で持っている場合、
# ここではランキング対象から外れる
# =========================================================
def get_rank_series(df, decimals=2):

    values = df.stack(dropna=True)
    values = pd.to_numeric(values, errors="coerce")

    finite_values = values[np.isfinite(values)]

    return finite_values.round(decimals)


# =========================================================
# TOP / WORST割合から対象セルを取得
# - ゾーン内の値だけを対象にする
# - 値が大きい順に上位TOP割合を抽出する
# - 値が小さい順に下位WORST割合を抽出する
# - 境界値と同じ値はすべて対象に含める
#
# 例）
# 対象セルが100個、TOP割合が30%の場合
# → 上位30個を希望枠候補にする
#
# ただし、30位と同じ値が31位以降にもある場合
# → 同値も希望枠に含める
# =========================================================
def get_top_worst_positions_by_rate(
    rank_values,
    top_rate=30,
    worst_rate=30,
):

    top_positions = set()
    worst_positions = set()

    if rank_values.empty:
        return top_positions, worst_positions

    n = len(rank_values)

    # 割合から件数へ変換
    # - ceilで切り上げ
    # - 例: 7セル × 30% = 2.1 → 3セル
    top_count = int(np.ceil(n * top_rate / 100))
    worst_count = int(np.ceil(n * worst_rate / 100))

    # 件数を安全化
    # - 0未満にならない
    # - データ件数を超えない
    top_count = max(0, min(top_count, n))
    worst_count = max(0, min(worst_count, n))

    # TOP側の対象セルを取得
    if top_count > 0:
        sorted_desc = rank_values.sort_values(ascending=False)

        # TOP範囲の境界値
        top_threshold = sorted_desc.iloc[top_count - 1]

        # 境界値と同じ値も含めてTOP扱い
        top_positions = set(
            rank_values[rank_values >= top_threshold].index.tolist()
        )

    # WORST側の対象セルを取得
    if worst_count > 0:
        sorted_asc = rank_values.sort_values(ascending=True)

        # WORST範囲の境界値
        worst_threshold = sorted_asc.iloc[worst_count - 1]

        # 境界値と同じ値も含めてWORST扱い
        worst_positions = set(
            rank_values[rank_values <= worst_threshold].index.tolist()
        )

    return top_positions, worst_positions


# =========================================================
# 希望枠判定表を作成
# - 視聴率単体 / INDEX単体で使用する
#
# 判定ルール
# 1. ゾーン外は判定対象外
# 2. 欠損値は判定対象外
# 3. TOP割合に入るセルは「〇」
# 4. WORST割合に入るセルは「×」
# 5. それ以外は普通枠として空文字
#
# 表示上は、
# 〇 → 希望枠色
# × → 拒否枠色
# 空文字 → 普通枠色
# =========================================================
def build_wish_frame(
    df,
    top_rate,
    worst_rate,
    zone_df,
):

    numeric_df = df.apply(pd.to_numeric, errors="coerce")

    # ゾーン内だけTrueのマスクを作成
    mask = get_zone_mask_for_df(zone_df, numeric_df)

    # ゾーン外をNaNにしてランキング対象から外す
    scoped_df = numeric_df.where(mask)

    # ランキング対象系列を作成
    rank_values = get_rank_series(scoped_df, decimals=2)

    # 出力用DataFrame
    result = pd.DataFrame(
        "",
        index=numeric_df.index,
        columns=numeric_df.columns,
    )

    # ランキング対象がない場合
    if rank_values.empty:
        return result

    # TOP / WORST対象セルを取得
    top_positions, worst_positions = get_top_worst_positions_by_rate(
        rank_values=rank_values,
        top_rate=top_rate,
        worst_rate=worst_rate,
    )

    # セルごとに判定
    for row_label in numeric_df.index:
        for col_label in numeric_df.columns:

            value = numeric_df.loc[row_label, col_label]

            # ゾーン外
            if not bool(mask.loc[row_label, col_label]):
                result.loc[row_label, col_label] = ""

            # 欠損
            elif pd.isna(value):
                result.loc[row_label, col_label] = ""

            # 無限大は表示上Infとして持つ
            elif np.isinf(value):
                result.loc[row_label, col_label] = "Inf"

            # TOP割合に入るセルは希望枠
            elif (row_label, col_label) in top_positions:
                result.loc[row_label, col_label] = "〇"

            # WORST割合に入るセルは拒否枠
            elif (row_label, col_label) in worst_positions:
                result.loc[row_label, col_label] = "×"

            # それ以外は普通枠
            else:
                result.loc[row_label, col_label] = ""

    return result


# =========================================================
# 希望枠テーブル図を作成
# - wish_dfの記号をもとに色を付ける
# - 表示文字は空欄にし、色だけ表示する
# =========================================================
def build_wish_table_figure(wish_df, title):

    fill_df, font_df = build_simple_wish_color_matrices(wish_df)

    display_df = build_blank_wish_display_df(wish_df)

    return build_colored_wish_table_figure(
        display_df,
        title,
        fill_df,
        font_df,
    )


# =========================================================
# 表示文字を空欄化
# - セル内に〇 / × を表示せず、背景色だけで見せるため
# =========================================================
def build_blank_wish_display_df(source_df):

    return pd.DataFrame(
        "",
        index=source_df.index,
        columns=source_df.columns,
    )


# =========================================================
# 希望枠 / 普通枠 / 拒否枠の色設定
# =========================================================
def build_simple_wish_color_matrices(wish_df):

    fill_df = pd.DataFrame(
        "#FFFFFF",
        index=wish_df.index,
        columns=wish_df.columns,
    )

    font_df = pd.DataFrame(
        "#000000",
        index=wish_df.index,
        columns=wish_df.columns,
    )

    for row_label in wish_df.index:
        for col_label in wish_df.columns:

            value = wish_df.loc[row_label, col_label]

            # 希望枠
            if value == "〇":
                fill_df.loc[row_label, col_label] = "#ff8f86"

            # 拒否枠
            elif value == "×":
                fill_df.loc[row_label, col_label] = "#e7e7ea"

            # 特殊値
            elif value == "Inf":
                fill_df.loc[row_label, col_label] = "#FFFFFF"

    return fill_df, font_df


# =========================================================
# Plotly Table作成
# =========================================================
def build_colored_wish_table_figure(wish_df, title, fill_df, font_df):

    header_values = [""] + list(wish_df.columns)

    cell_values = [list(wish_df.index)] + [
        wish_df[col].fillna("").tolist()
        for col in wish_df.columns
    ]

    fill_values = [["#FFFFFF"] * len(wish_df.index)] + [
        fill_df[col].tolist()
        for col in wish_df.columns
    ]

    font_values = [["#000000"] * len(wish_df.index)] + [
        font_df[col].tolist()
        for col in wish_df.columns
    ]

    n_rows = len(wish_df)

    table_height = max(680, 90 + n_rows * 27)

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[70] + [42] * len(wish_df.columns),
                header=dict(
                    values=header_values,
                    align="center",
                    height=30,
                ),
                cells=dict(
                    values=cell_values,
                    align="center",
                    height=27,
                    fill_color=fill_values,
                    font=dict(color=font_values),
                ),
            )
        ]
    )

    fig.update_layout(
        title=title,
        title_x=0.5,
        height=table_height,
        margin=dict(l=5, r=5, t=45, b=5),
        font=dict(size=11),
    )

    return fig


# =========================================================
# DataFrame → CSV bytes
# - download_buttonでそのまま使える形式にする
# =========================================================
def dataframe_to_csv_bytes(df):

    return df.to_csv(
        index=True,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")


# =========================================================
# ページ全体CSV用の縦持ちDataFrameを作成
# - 視聴率用
# =========================================================
def build_all_wish_frames_long(
    df,
    section_order,
    top_rate,
    worst_rate,
    zone_df,
):

    all_frames = []

    for section_title in section_order:
        for station in STATION_ORDER:

            pivot_df = make_station_pivot(
                df,
                section_title,
                station,
            )

            if pivot_df is None:
                continue

            wish_df = build_wish_frame(
                df=pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            ).reset_index()

            wish_df["セクション"] = section_title
            wish_df["局"] = station

            wish_df = wish_df[
                ["セクション", "局", "時間帯"] + WEEKDAYS
            ]

            all_frames.append(wish_df)

    if not all_frames:
        return pd.DataFrame(
            columns=["セクション", "局", "時間帯"] + WEEKDAYS
        )

    return pd.concat(all_frames, axis=0, ignore_index=True)


# =========================================================
# 1セクション分を描画
# - 視聴率用
# =========================================================
def render_wish_row(
    section_title,
    df,
    top_rate,
    worst_rate,
    zone_df,
    file_name_builder,
):

    st.markdown(f"### {section_title}")

    cols = st.columns(5)

    for idx, (col, station) in enumerate(zip(cols, STATION_ORDER)):

        with col:

            pivot_df = make_station_pivot(
                df,
                section_title,
                station,
            )

            if pivot_df is None:
                st.info(f"{station}\n\nデータなし")
                continue

            wish_df = build_wish_frame(
                df=pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            )

            wish_fig = build_wish_table_figure(
                wish_df,
                station,
            )

            st.plotly_chart(
                wish_fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "displaylogo": False,
                },
                key=f"wish_table_{section_title}_{station}_{idx}",
            )


# =========================================================
# INDEX用: ページ全体CSV用の縦持ちDataFrame
# =========================================================
def build_all_wish_frames_long_index(
    df,
    section_order,
    top_rate,
    worst_rate,
    zone_df,
):

    all_frames = []

    for section_title in section_order:
        for station in STATION_ORDER:

            sub = df[
                (df["指標"] == section_title) &
                (df["局"] == station)
            ].copy()

            if sub.empty:
                continue

            pivot_df = (
                sub
                .sort_values("時間帯")[["時間帯"] + WEEKDAYS]
                .set_index("時間帯")
            )

            wish_df = build_wish_frame(
                df=pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            ).reset_index()

            wish_df["指標"] = section_title
            wish_df["局"] = station

            wish_df = wish_df[
                ["指標", "局", "時間帯"] + WEEKDAYS
            ]

            all_frames.append(wish_df)

    if not all_frames:
        return pd.DataFrame(
            columns=["指標", "局", "時間帯"] + WEEKDAYS
        )

    return pd.concat(all_frames, axis=0, ignore_index=True)


# =========================================================
# INDEX用: 1セクション分を描画
# =========================================================
def render_wish_row_index(
    section_title,
    df,
    top_rate,
    worst_rate,
    zone_df,
    file_name_builder,
):

    st.markdown(f"### {section_title}")

    cols = st.columns(5)

    for idx, (col, station) in enumerate(zip(cols, STATION_ORDER)):

        with col:

            sub = df[
                (df["指標"] == section_title) &
                (df["局"] == station)
            ].copy()

            if sub.empty:
                st.info(f"{station}\n\nデータなし")
                continue

            pivot_df = (
                sub
                .sort_values("時間帯")[["時間帯"] + WEEKDAYS]
                .set_index("時間帯")
            )

            wish_df = build_wish_frame(
                df=pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            )

            wish_fig = build_wish_table_figure(
                wish_df,
                station,
            )

            st.plotly_chart(
                wish_fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "displaylogo": False,
                },
                key=f"wish_index_table_{section_title}_{station}_{idx}",
            )


# =========================================================
# 単一指標を記号化
# - 視聴率×INDEXの組み合わせ判定用
#
# ここでは直接色を付けず、
# まず各セルを以下の記号に変換する
#
# ○ : TOP割合に入る
# × : WORST割合に入る
# "" : それ以外
#
# この結果をあとで実数値側とINDEX側で組み合わせる
# =========================================================
def build_symbol_frame(
    df,
    top_rate,
    worst_rate,
    zone_df,
):

    numeric_df = df.apply(pd.to_numeric, errors="coerce")

    mask = get_zone_mask_for_df(zone_df, numeric_df)

    scoped_df = numeric_df.where(mask)

    rank_values = get_rank_series(scoped_df, decimals=2)

    result = pd.DataFrame(
        "",
        index=numeric_df.index,
        columns=numeric_df.columns,
    )

    if rank_values.empty:
        return result

    top_positions, worst_positions = get_top_worst_positions_by_rate(
        rank_values=rank_values,
        top_rate=top_rate,
        worst_rate=worst_rate,
    )

    for row_label in numeric_df.index:
        for col_label in numeric_df.columns:

            value = numeric_df.loc[row_label, col_label]

            if not bool(mask.loc[row_label, col_label]):
                result.loc[row_label, col_label] = ""

            elif pd.isna(value):
                result.loc[row_label, col_label] = ""

            elif np.isinf(value):
                result.loc[row_label, col_label] = "Inf"

            elif (row_label, col_label) in top_positions:
                result.loc[row_label, col_label] = "○"

            elif (row_label, col_label) in worst_positions:
                result.loc[row_label, col_label] = "×"

            else:
                result.loc[row_label, col_label] = ""

    return result


# =========================================================
# 実数値 × INDEX の組み合わせ記号化
#
# 実数値側とINDEX側の判定結果を組み合わせる
#
# 判定ルール
# ○○ : 実数値もINDEXもTOP範囲 → 超希望枠
# ○  : 実数値またはINDEXのどちらかがTOP範囲 → 希望枠
# ○× : 片方がTOP範囲、片方がWORST範囲 → 普通枠
# ×  : 実数値またはINDEXのどちらかがWORST範囲 → 拒否枠
# ×× : 実数値もINDEXもWORST範囲 → 超拒否枠
# "" : どちらもTOP/WORSTに該当しない → 普通枠
# =========================================================
def build_mix_symbol_frame(
    actual_df,
    index_df,
    top_rate,
    worst_rate,
    zone_df,
):

    actual_symbol_df = build_symbol_frame(
        df=actual_df,
        top_rate=top_rate,
        worst_rate=worst_rate,
        zone_df=zone_df,
    )

    index_symbol_df = build_symbol_frame(
        df=index_df,
        top_rate=top_rate,
        worst_rate=worst_rate,
        zone_df=zone_df,
    )

    index_symbol_df = index_symbol_df.reindex(
        index=actual_symbol_df.index,
        columns=actual_symbol_df.columns,
    )

    result = pd.DataFrame(
        "",
        index=actual_symbol_df.index,
        columns=actual_symbol_df.columns,
    )

    for row_label in result.index:
        for col_label in result.columns:

            a = actual_symbol_df.loc[row_label, col_label]
            i = index_symbol_df.loc[row_label, col_label]

            if a == "Inf" or i == "Inf":
                result.loc[row_label, col_label] = "Inf"

            elif a == "○" and i == "○":
                result.loc[row_label, col_label] = "○○"

            elif (a == "○" and i == "") or (a == "" and i == "○"):
                result.loc[row_label, col_label] = "○"

            elif (a == "○" and i == "×") or (a == "×" and i == "○"):
                result.loc[row_label, col_label] = "○×"

            elif (a == "×" and i == "") or (a == "" and i == "×"):
                result.loc[row_label, col_label] = "×"

            elif a == "×" and i == "×":
                result.loc[row_label, col_label] = "××"

            else:
                result.loc[row_label, col_label] = ""

    return result


# =========================================================
# 視聴率×INDEX の組み合わせ定義
# =========================================================
def get_mix_combination_definitions():

    return [
        # 【実数値】VR（個人全体/世帯）
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】VR（ターゲット）
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        
        
        # 【実数値】TVAL（個人全体/世帯）
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】TVAL（ターゲット）
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】REVISIO（世帯）
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（世帯）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（世帯）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】REVISIO（注視）
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（注視）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】REVISIO（滞在）
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（注視）",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（滞在）&【INDEX】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "REVISIO（滞在）",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】TVAL（ターゲット）×[REVISIO（各セル注視）÷REVISIO（局単位の注視全値の平均）]
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] &【INDEX】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
        },
        
        # 【実数値】【実数値】TVAL（ターゲット）×[REVISIO（各セル滞在）÷REVISIO（局単位の滞在全値の平均）]
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】TVAL（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】VR（ターゲット）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】REVISIO（注視）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "REVISIO（注視）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】REVISIO（滞在）÷ REVISIO（世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "REVISIO（滞在）÷ REVISIO（世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】REVISIO（注視）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "REVISIO（注視）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】REVISIO（滞在）÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "REVISIO（滞在）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] &【INDEX】TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
            "index_section": "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
        },
    ]


# =========================================================
# 指定セクション × 局 の実数値pivot取得
# =========================================================
def make_actual_station_pivot(
    df_actual,
    actual_section,
    station,
):

    sub = df_actual[
        (df_actual["セクション"] == actual_section) &
        (df_actual["局"] == station)
    ].copy()

    if sub.empty:
        return None

    sub = sub.sort_values("時間帯")

    return sub[["時間帯"] + WEEKDAYS].set_index("時間帯")


# =========================================================
# 指定指標 × 局 のINDEX pivot取得
# =========================================================
def make_index_station_pivot(
    df_index,
    index_section,
    station,
):

    sub = df_index[
        (df_index["指標"] == index_section) &
        (df_index["局"] == station)
    ].copy()

    if sub.empty:
        return None

    sub = sub.sort_values("時間帯")

    return sub[["時間帯"] + WEEKDAYS].set_index("時間帯")


# =========================================================
# 利用可能な組み合わせだけ返す
# - 実数値側セクションとINDEX側指標の両方が存在するものだけ対象
# =========================================================
def get_available_mix_combinations(
    df_actual,
    df_index,
    allowed_index_sections=None,
):

    available_actual_sections = set(
        df_actual["セクション"].dropna().unique().tolist()
    )

    available_index_sections = set(
        df_index["指標"].dropna().unique().tolist()
    )

    if allowed_index_sections is not None:
        available_index_sections &= set(allowed_index_sections)

    combinations = []

    for combo in get_mix_combination_definitions():

        if (
            combo["actual_section"] in available_actual_sections
            and combo["index_section"] in available_index_sections
        ):
            combinations.append(combo)

    return combinations


# =========================================================
# ページ全体CSV用の縦持ちDataFrame
# - 視聴率×INDEX用
# =========================================================
def build_all_wish_frames_long_mix(
    df_actual,
    df_index,
    combinations,
    top_rate,
    worst_rate,
    zone_df,
):

    all_frames = []

    for combo in combinations:
        for station in STATION_ORDER:

            actual_pivot_df = make_actual_station_pivot(
                df_actual=df_actual,
                actual_section=combo["actual_section"],
                station=station,
            )

            index_pivot_df = make_index_station_pivot(
                df_index=df_index,
                index_section=combo["index_section"],
                station=station,
            )

            if actual_pivot_df is None or index_pivot_df is None:
                continue

            mix_df = build_mix_symbol_frame(
                actual_df=actual_pivot_df,
                index_df=index_pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            ).reset_index()

            mix_df["組み合わせ"] = combo["label"]
            mix_df["局"] = station

            mix_df = mix_df[
                ["組み合わせ", "局", "時間帯"] + WEEKDAYS
            ]

            all_frames.append(mix_df)

    if not all_frames:
        return pd.DataFrame(
            columns=["組み合わせ", "局", "時間帯"] + WEEKDAYS
        )

    return pd.concat(all_frames, axis=0, ignore_index=True)

# =========================================================
# 視聴率×INDEX 組み合わせ可視化
# - セル内の文字は表示しない
# - 判定記号に応じて背景色だけを変える
#
# 色定義
# ○○ : 濃い赤     → 超希望枠
# ○  : 薄い赤     → 希望枠
# ○× : グレー     → 拒否枠 (変更済み)
# ×  : グレー     → 拒否枠
# ×× : 濃いグレー → 超拒否枠
# "" : 白         → 普通枠
# =========================================================
def build_mix_color_table_figure(
    mix_df,
    title,
):

    # =====================================================
    # 表示文字は空欄にする
    # - 色だけで状態を見せる
    # =====================================================
    display_df = mix_df.copy()

    for col in display_df.columns:
        display_df[col] = ""

    # =====================================================
    # ヘッダー
    # =====================================================
    header_values = [""] + list(display_df.columns)

    # =====================================================
    # セル値
    # =====================================================
    cell_values = [list(display_df.index)] + [
        display_df[col].tolist()
        for col in display_df.columns
    ]

    # =====================================================
    # 記号ごとの色定義
    # =====================================================
    color_map = {
        "○○": "#ff5050",   # 超希望枠
        "○":  "#ff8f86",   # 希望枠
        "○×": "#b5b5b8",   # 拒否枠 ※片方TOP・片方WORST
        # "○×": "#ffffff",   # 普通枠
        "×":  "#b5b5b8",   # 拒否枠
        "××": "#404040",   # 超拒否枠
        "Inf": "#ffffff",
        "":   "#ffffff",
    }

    # =====================================================
    # 背景色リスト作成
    # =====================================================
    fill_colors = []

    for col in mix_df.columns:

        fill_colors.append([
            color_map.get(v, "#ffffff")
            for v in mix_df[col].tolist()
        ])

    # =====================================================
    # テーブル高さ
    # =====================================================
    n_rows = len(mix_df)

    table_height = max(
        680,
        90 + n_rows * 27,
    )

    # =====================================================
    # Plotly Table
    # =====================================================
    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[70] + [42] * len(mix_df.columns),

                header=dict(
                    values=header_values,
                    align="center",
                    height=30,
                ),

                cells=dict(
                    values=cell_values,
                    align="center",
                    height=27,

                    fill_color=[
                        ["#ffffff"] * n_rows
                    ] + fill_colors,

                    font=dict(size=11),
                ),
            )
        ]
    )

    # =====================================================
    # レイアウト
    # =====================================================
    fig.update_layout(
        title=title,
        title_x=0.5,
        height=table_height,
        margin=dict(
            l=5,
            r=5,
            t=45,
            b=5,
        ),
    )

    return fig


# =========================================================
# 1組み合わせ分を描画
# - 視聴率×INDEX用
# =========================================================
def render_mix_wish_row(
    combo,
    df_actual,
    df_index,
    top_rate,
    worst_rate,
    zone_df,
    file_name_builder,
):

    st.markdown(f"### {combo['label']}")

    cols = st.columns(5)

    for idx, (col, station) in enumerate(zip(cols, STATION_ORDER)):

        with col:

            actual_pivot_df = make_actual_station_pivot(
                df_actual=df_actual,
                actual_section=combo["actual_section"],
                station=station,
            )

            index_pivot_df = make_index_station_pivot(
                df_index=df_index,
                index_section=combo["index_section"],
                station=station,
            )

            if actual_pivot_df is None or index_pivot_df is None:
                st.info(f"{station}\n\nデータなし")
                continue

            mix_df = build_mix_symbol_frame(
                actual_df=actual_pivot_df,
                index_df=index_pivot_df,
                top_rate=top_rate,
                worst_rate=worst_rate,
                zone_df=zone_df,
            )

            mix_fig = build_mix_color_table_figure(
                mix_df,
                station,
            )

            st.plotly_chart(
                mix_fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "displaylogo": False,
                },
                key=f"wish_mix_table_{combo['label']}_{station}_{idx}",
            )


# =========================================================
# 視聴率×INDEX 希望枠タブ描画
# =========================================================
def render_wish_mix_tab(
    df_heatmap_all,
    df_heatmap_index,
    allowed_index_sections=None,
):

    init_zone_state()

    # =====================================================
    # データ存在チェック
    # =====================================================
    if df_heatmap_all is None or df_heatmap_all.empty:
        st.info("実数値データがありません。")
        return

    if df_heatmap_index is None or df_heatmap_index.empty:
        st.info("INDEXデータがありません。")
        return

    # =====================================================
    # 実数値側データにセクション列を追加
    # =====================================================
    df_actual = add_rating_section_col(df_heatmap_all)

    df_actual = df_actual[
        df_actual["セクション"].notna()
    ].copy()

    # =====================================================
    # 利用可能な組み合わせだけ抽出
    # =====================================================
    combinations = get_available_mix_combinations(
        df_actual=df_actual,
        df_index=df_heatmap_index,
        allowed_index_sections=allowed_index_sections,
    )

    if not combinations:
        st.info("表示可能な視聴率×INDEX組み合わせデータがありません。")
        return

    # =====================================================
    # 実数値 / INDEX を別々に絞り込み
    # =====================================================
    actual_section_master = [
        "VR（個人全体/世帯）",
        "VR（ターゲット）",
        "TVAL（個人全体/世帯）",
        "TVAL（ターゲット）",
        "REVISIO（個人全体/世帯）",
        "REVISIO（注視）",
        "REVISIO（滞在）",
        "REVISIO（世帯）",
        "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
        "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
    ]

    index_section_master = [
        "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        "VR（ターゲット）÷ VR（個人全体/世帯）",
        "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        "REVISIO（注視）÷ REVISIO（世帯）",
        "REVISIO（滞在）÷ REVISIO（世帯）",
        "REVISIO（注視）÷ VR（個人全体/世帯）",
        "REVISIO（滞在）÷ VR（個人全体/世帯）",
        "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
        "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
    ]

    available_actual_sections = {
        combo["actual_section"]
        for combo in combinations
    }

    available_index_sections = {
        combo["index_section"]
        for combo in combinations
    }

    actual_options = [
        s for s in actual_section_master
        if s in available_actual_sections
    ]

    index_options = [
        s for s in index_section_master
        if s in available_index_sections
    ]

    col_actual, col_index = st.columns(2)

    with col_actual:
        selected_actual_sections = st.multiselect(
            "【実数値】を絞り込み",
            options=actual_options,
            # default=actual_options,
            default=[],
            key="wish_mix_actual_filter",
        )

    with col_index:
        selected_index_sections = st.multiselect(
            "【INDEX】を絞り込み",
            options=index_options,
            # default=index_options,
            default=[],
            key="wish_mix_index_filter",
        )

    combinations = [
        combo for combo in combinations
        if combo["actual_section"] in selected_actual_sections
        and combo["index_section"] in selected_index_sections
    ]

    if not combinations:
        st.warning("表示する実数値・INDEXの組み合わせを選択してください。")
        return

    # =====================================================
    # 希望枠タブで選択された共有フィルター値を使用
    # - 視聴率 / INDEX と同期
    # - MIXタブ側ではUIは表示しない
    # =====================================================
    selected_zone = st.session_state.get(
        "shared_wish_zone",
        "全日",
    )

    top_rate = st.session_state.get(
        "shared_wish_top_rate",
        30,
    )

    worst_rate = st.session_state.get(
        "shared_wish_worst_rate",
        30,
    )

    # =====================================================
    # ゾーン設定取得
    # =====================================================
    zone_df = get_wish_zone_df(selected_zone)

    # =====================================================
    # 使用データ / CSV用データを作成
    # =====================================================
    all_mix_df = build_all_wish_frames_long_mix(
        df_actual=df_actual,
        df_index=df_heatmap_index,
        combinations=combinations,
        top_rate=top_rate,
        worst_rate=worst_rate,
        zone_df=zone_df,
    )

    # =====================================================
    # 使用データ表示
    # =====================================================
    with st.expander("使用データ", expanded=False):

        st.dataframe(
            all_mix_df,
            use_container_width=True,
        )

    # =====================================================
    # ページ全体CSVダウンロード
    # =====================================================
    st.download_button(
        label="ページ全体CSV",
        data=dataframe_to_csv_bytes(all_mix_df),
        file_name="wish_mix_all.csv",
        mime="text/csv",
        key="wish_mix_csv_all",
        use_container_width=False,
        on_click="ignore",
    )

    # =====================================================
    # 凡例（表の直前に表示）
    # =====================================================
    legend_html = """
    <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap; margin:8px 0 16px 0;">
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#ff5050;"></div>
                <span>超希望枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#ff8f86;"></div>
                <span>希望枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#FFFFFF; border:1px solid #bdbdbd; box-sizing:border-box;"></div>
                <span>普通枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#b5b5b8;"></div>
                <span>拒否枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#404040;"></div>
                <span>超拒否枠</span>
            </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div>どちらもTOP範囲</div>
            <div>いずれかがTOP範囲</div>
            <div>該当なし</div>
            <div>いずれかがWORST範囲</div>
            <div>どちらもWORST範囲</div>
        </div>
    </div>
    """

    st.markdown(
        legend_html,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # =====================================================
    # 組み合わせごとに描画
    # =====================================================
    for i, combo in enumerate(combinations):

        render_mix_wish_row(
            combo=combo,
            df_actual=df_actual,
            df_index=df_heatmap_index,
            top_rate=top_rate,
            worst_rate=worst_rate,
            zone_df=zone_df,
            file_name_builder=lambda label, station: f"{label}_{station}_wish_mix.csv",
        )

        if i < len(combinations) - 1:
            st.markdown("---")


