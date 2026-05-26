import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ゾーンタブ側で定義しているゾーン名一覧と、
# 反映済みゾーン設定を取得する関数、
# session_state 初期化関数を読み込む
from zone.zone_tab import init_zone_state

# 曜日順
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# ゾーン名一覧（UIのフィルターやラジオボタンで使用）
ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]

def get_wish_zone_df(selected_zone_name):
    """希望枠タブで使用する正式ゾーンを返す"""
    return st.session_state["zone_filters"][selected_zone_name]


# =========================================================
# 共有ゾーン選択の同期
# - ラジオボタンで選ばれたゾーンを shared_wish_zone に保存
# - 他タブや再描画後も同じ選択を保持するために使う
# =========================================================
def sync_shared_wish_zone(widget_key):
    st.session_state["shared_wish_zone"] = st.session_state[widget_key]


# =========================================================
# 共有ワースト件数の同期
# - number_input で入力された件数を shared_wish_worst_n に保存
# - 他タブや再描画後も同じ値を保持するために使う
# =========================================================
def sync_shared_wish_worst(widget_key):
    st.session_state["shared_wish_worst_n"] = st.session_state[widget_key]


# =========================================================
# 希望枠共通コントロール
# - 対象ゾーン選択
# - ワースト下位件数入力
# - zone_tab と同じ session_state を使って値を共有する
# =========================================================
def render_shared_wish_controls(prefix):
    # widget 用 key
    zone_key = f"{prefix}_wish_zone"
    worst_key = f"{prefix}_wish_worst"

    # 現在の共有ゾーン
    current_shared_zone = st.session_state["shared_wish_zone"]

    # widget 側に shared state の値を流し込む
    if st.session_state.get(zone_key) != current_shared_zone:
        st.session_state[zone_key] = current_shared_zone

    if st.session_state.get(worst_key) != st.session_state["shared_wish_worst_n"]:
        st.session_state[worst_key] = st.session_state["shared_wish_worst_n"]

    # 対象ゾーンをラジオボタンで選択
    selected_zone = st.radio(
        "対象ゾーン",
        ZONE_NAMES,
        horizontal=True,
        key=zone_key,
        on_change=sync_shared_wish_zone,
        args=(zone_key,),
    )

    # ワースト下位件数を入力
    worst_n = st.number_input(
        "ワースト下位の件数",
        min_value=0,
        max_value=50,
        value=st.session_state["shared_wish_worst_n"],
        step=1,
        key=worst_key,
        on_change=sync_shared_wish_worst,
        args=(worst_key,),
    )

    return selected_zone, worst_n


# =========================================================
# 視聴率データにセクション列を追加
# - データ種別 × カテゴリー の組み合わせを
#   画面表示用のセクション名に変換する
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
# 1局分の pivot 作成
# - 指定セクション × 指定局 のデータを抽出
# - 時間帯を index、曜日を列にした表に変換する
# =========================================================
def make_station_pivot(df, section_title, station):
    sub = df[
        (df["セクション"] == section_title) &
        (df["局"] == station)
    ].copy()

    # 該当データがなければ None
    if sub.empty:
        return None

    # 時間帯順に並べて pivot 形式にする
    sub = sub.sort_values("時間帯")
    return sub[["時間帯"] + WEEKDAYS].set_index("時間帯")


# =========================================================
# ゾーンマスク作成
# - zone_df を、対象 DataFrame の index / columns に合わせる
# - True / False のマスク表として返す
# =========================================================
def get_zone_mask_for_df(zone_df, df):
    return zone_df.reindex(index=df.index, columns=df.columns, fill_value=False).astype(bool)


# =========================================================
# ランキング対象の系列を作成
# - DataFrame を縦持ちにして 1系列にする
# - 有限値だけを抽出して、小数桁を丸める
# =========================================================
def get_rank_series(df, decimals=2):
    values = df.stack(dropna=True)
    finite_values = values[np.isfinite(values)]
    return finite_values.round(decimals)


# =========================================================
# 希望枠判定表を作成
# - ゾーン内の値だけを対象にランキング判定
# - 平均以上は 〇
# - WORST 指定件数は ×
# - inf は "Inf"
# - ゾーン外は空文字
# =========================================================
def build_wish_frame(df, worst_n, zone_df):
    # 念のため数値化
    numeric_df = df.apply(pd.to_numeric, errors="coerce")

    # ゾーン内だけ True のマスクを作成
    mask = get_zone_mask_for_df(zone_df, numeric_df)

    # ゾーン外を NaN にした集計対象表
    scoped_df = numeric_df.where(mask)

    # ランキング用の値系列
    rank_values = get_rank_series(scoped_df, decimals=2)

    # 出力用 DataFrame
    result = pd.DataFrame("", index=numeric_df.index, columns=numeric_df.columns)

    # ランキング対象が空の場合
    if rank_values.empty:
        for row_label in numeric_df.index:
            for col_label in numeric_df.columns:
                value = numeric_df.loc[row_label, col_label]
                if bool(mask.loc[row_label, col_label]) and np.isinf(value):
                    result.loc[row_label, col_label] = "Inf"
        return result

    # ゾーン内の平均値
    mean_val = rank_values.mean()

    # worst_n は有効範囲に丸める
    worst_n = max(0, min(int(worst_n), len(rank_values)))

    # WORST 判定位置を取得
    worst_positions = set()
    if worst_n > 0:
        sorted_values = rank_values.sort_values(ascending=True)
        threshold = sorted_values.iloc[worst_n - 1]
        worst_positions = set(rank_values[rank_values <= threshold].index.tolist())

    # セルごとに記号を判定
    for row_label in numeric_df.index:
        for col_label in numeric_df.columns:
            value = numeric_df.loc[row_label, col_label]

            # ゾーン外は空文字
            if not bool(mask.loc[row_label, col_label]):
                result.loc[row_label, col_label] = ""

            # 欠損は空文字
            elif pd.isna(value):
                result.loc[row_label, col_label] = ""

            # inf は Inf 表記
            elif np.isinf(value):
                result.loc[row_label, col_label] = "Inf"

            # WORST 指定範囲は ×
            elif (row_label, col_label) in worst_positions:
                result.loc[row_label, col_label] = "×"

            # 平均以上は 〇
            elif round(value, 2) >= mean_val:
                result.loc[row_label, col_label] = "〇"

            # それ以外は空文字
            else:
                result.loc[row_label, col_label] = ""

    return result


# =========================================================
# 希望枠テーブル図を作成
# - wish_df を Plotly の Table で表示する
# =========================================================
def build_wish_table_figure(wish_df, title):
    header_values = [""] + list(wish_df.columns)
    cell_values = [list(wish_df.index)] + [wish_df[col].fillna("").tolist() for col in wish_df.columns]

    # 行数に応じて高さを調整
    n_rows = len(wish_df)
    table_height = max(680, 90 + n_rows * 27)

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[70] + [42] * len(wish_df.columns),
                header=dict(values=header_values, align="center", height=30),
                cells=dict(values=cell_values, align="center", height=27),
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
# - download_button でそのまま使えるように bytes 化する
# =========================================================
def dataframe_to_csv_bytes(df):
    return df.to_csv(index=True, encoding="utf-8-sig").encode("utf-8-sig")


# =========================================================
# ページ全体CSV用の縦持ち DataFrame を作成
# - セクション × 局 ごとに wish_df を作成
# - セクション名と局名を付けて縦に結合する
# =========================================================
def build_all_wish_frames_long(df, section_order, worst_n, zone_df):
    all_frames = []

    for section_title in section_order:
        for station in STATION_ORDER:
            pivot_df = make_station_pivot(df, section_title, station)

            if pivot_df is None:
                continue

            wish_df = build_wish_frame(pivot_df, worst_n, zone_df).reset_index()
            wish_df["セクション"] = section_title
            wish_df["局"] = station
            wish_df = wish_df[["セクション", "局", "時間帯"] + WEEKDAYS]
            all_frames.append(wish_df)

    if not all_frames:
        return pd.DataFrame(columns=["セクション", "局", "時間帯"] + WEEKDAYS)

    return pd.concat(all_frames, axis=0, ignore_index=True)


# =========================================================
# 1セクション分を描画
# - セクションごとに 5局を横並び表示
# - 各局について CSV ダウンロードと Table 表示を行う
# =========================================================
def render_wish_row(section_title, df, worst_n, zone_df, file_name_builder):
    st.markdown(f"### {section_title}")
    cols = st.columns(5)

    for idx, (col, station) in enumerate(zip(cols, STATION_ORDER)):
        with col:
            # 1局分の pivot を作成
            pivot_df = make_station_pivot(df, section_title, station)

            # データがなければメッセージ表示
            if pivot_df is None:
                st.info(f"{station}\n\nデータなし")
                continue

            # 希望枠判定表を作成
            wish_df = build_wish_frame(pivot_df, worst_n, zone_df)

            # 表示用テーブル図を作成
            wish_fig = build_wish_table_figure(wish_df, station)

            # CSV ダウンロード用 bytes
            csv_bytes = dataframe_to_csv_bytes(wish_df)

            # 局別 CSV ダウンロードボタン
            st.download_button(
                label="CSV",
                data=csv_bytes,
                file_name=file_name_builder(section_title, station),
                mime="text/csv",
                key=f"wish_csv_{section_title}_{station}_{idx}",
                use_container_width=True,
                on_click="ignore",
            )

            # 局別希望枠テーブルを描画
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
# INDEX用: ページ全体CSV用の縦持ち DataFrame を作成
# - df_index の「指標」列をそのまま使う
# =========================================================
def build_all_wish_frames_long_index(df, section_order, worst_n, zone_df):
    all_frames = []

    for section_title in section_order:
        for station in STATION_ORDER:
            sub = df[
                (df["指標"] == section_title) &
                (df["局"] == station)
            ].copy()

            if sub.empty:
                continue

            pivot_df = sub.sort_values("時間帯")[["時間帯"] + WEEKDAYS].set_index("時間帯")
            wish_df = build_wish_frame(pivot_df, worst_n, zone_df).reset_index()
            wish_df["指標"] = section_title
            wish_df["局"] = station
            wish_df = wish_df[["指標", "局", "時間帯"] + WEEKDAYS]
            all_frames.append(wish_df)

    if not all_frames:
        return pd.DataFrame(columns=["指標", "局", "時間帯"] + WEEKDAYS)

    return pd.concat(all_frames, axis=0, ignore_index=True)


# =========================================================
# INDEX用: 1セクション分を描画
# - 指標ごとに5局を横並び表示
# =========================================================
def render_wish_row_index(section_title, df, worst_n, zone_df, file_name_builder):
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

            pivot_df = sub.sort_values("時間帯")[["時間帯"] + WEEKDAYS].set_index("時間帯")

            wish_df = build_wish_frame(pivot_df, worst_n, zone_df)
            wish_fig = build_wish_table_figure(wish_df, station)
            csv_bytes = dataframe_to_csv_bytes(wish_df)

            st.download_button(
                label="CSV",
                data=csv_bytes,
                file_name=file_name_builder(section_title, station),
                mime="text/csv",
                key=f"wish_index_csv_{section_title}_{station}_{idx}",
                use_container_width=True,
                on_click="ignore",
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

###########################################################################################################
# 視聴率×INDEX用

# =========================================================
# 単一指標を記号化
# - ○ : 平均以上
# - × : ワースト下位件数
# - "" : 通常 / ゾーン外 / 欠損
# - Inf : 無限大
# =========================================================
def build_symbol_frame(df, worst_n, zone_df):
    # 数値化
    numeric_df = df.apply(pd.to_numeric, errors="coerce")

    # ゾーンマスク
    mask = get_zone_mask_for_df(zone_df, numeric_df)

    # ゾーン内だけ評価対象
    scoped_df = numeric_df.where(mask)

    # ランキング対象系列
    rank_values = get_rank_series(scoped_df, decimals=2)

    # 出力用
    result = pd.DataFrame("", index=numeric_df.index, columns=numeric_df.columns)

    # 評価対象が空なら Inf だけ反映
    if rank_values.empty:
        for row_label in numeric_df.index:
            for col_label in numeric_df.columns:
                value = numeric_df.loc[row_label, col_label]
                if bool(mask.loc[row_label, col_label]) and np.isinf(value):
                    result.loc[row_label, col_label] = "Inf"
        return result

    # ゾーン内平均
    mean_val = rank_values.mean()

    # ワースト件数を有効範囲に丸める
    worst_n = max(0, min(int(worst_n), len(rank_values)))

    # ワースト対象セル
    worst_positions = set()
    if worst_n > 0:
        sorted_values = rank_values.sort_values(ascending=True)
        threshold = sorted_values.iloc[worst_n - 1]
        worst_positions = set(rank_values[rank_values <= threshold].index.tolist())

    # 各セル判定
    for row_label in numeric_df.index:
        for col_label in numeric_df.columns:
            value = numeric_df.loc[row_label, col_label]

            if not bool(mask.loc[row_label, col_label]):
                result.loc[row_label, col_label] = ""
            elif pd.isna(value):
                result.loc[row_label, col_label] = ""
            elif np.isinf(value):
                result.loc[row_label, col_label] = "Inf"
            elif (row_label, col_label) in worst_positions:
                result.loc[row_label, col_label] = "×"
            elif round(value, 2) >= mean_val:
                result.loc[row_label, col_label] = "○"
            else:
                result.loc[row_label, col_label] = ""

    return result


# =========================================================
# 実数値 × INDEX の組み合わせ記号化
# 凡例
# - ○○ : 超希望枠   （実数値・INDEXともに平均以上）
# - ○  : 希望枠     （実数値・INDEXいずれか平均以上）
# - ○× : 普通枠     （一方が平均以上、もう一方がワースト）
# - ×  : 拒否枠     （実数値・INDEXいずれかワースト）
# - ×× : 超拒否枠   （実数値・INDEXともにワースト）
# =========================================================
def build_mix_symbol_frame(actual_df, index_df, worst_n, zone_df):
    # 実数値側を ○ / × / 空欄 に変換
    actual_symbol_df = build_symbol_frame(
        df=actual_df,
        worst_n=worst_n,
        zone_df=zone_df,
    )

    # INDEX側を ○ / × / 空欄 に変換
    index_symbol_df = build_symbol_frame(
        df=index_df,
        worst_n=worst_n,
        zone_df=zone_df,
    )

    # shape をそろえる
    index_symbol_df = index_symbol_df.reindex(
        index=actual_symbol_df.index,
        columns=actual_symbol_df.columns,
    )

    # 出力用
    result = pd.DataFrame("", index=actual_symbol_df.index, columns=actual_symbol_df.columns)

    # セルごとに組み合わせ判定
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
# - 表示名
# - 実数値側セクション名
# - INDEX側指標名
# をまとめて管理
# =========================================================
def get_mix_combination_definitions():
    return [
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】REVISIO（個人全体/世帯）÷VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "REVISIO（個人全体）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】［TVAL（ターゲット）×REVISIO（個人全体/世帯）］÷VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "［TVAL（ターゲット）× REVISIO（個人全体）］÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（個人全体/世帯）&【INDEX】VR（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "VR（個人全体/世帯）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（個人全体/世帯）&【INDEX】TVAL（ターゲット）÷TVAL（個人全体/世帯）",
            "actual_section": "TVAL（個人全体/世帯）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（個人全体/世帯）&【INDEX】REVISIO（個人全体/世帯）÷VR（個人全体/世帯）",
            "actual_section": "REVISIO（個人全体/世帯）",
            "index_section": "REVISIO（個人全体）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】REVISIO（個人全体/世帯）&【INDEX】VR（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "REVISIO（個人全体/世帯）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】REVISIO（個人全体/世帯）÷VR（個人全体/世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "REVISIO（個人全体）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】VR（ターゲット）&【INDEX】VR（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "VR（ターゲット）",
            "index_section": "VR（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】TVAL（ターゲット）÷VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "TVAL（ターゲット）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】REVISIO（個人全体/世帯）÷VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "REVISIO（個人全体）÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】［TVAL（ターゲット）×REVISIO（個人全体/世帯）］÷VR（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "［TVAL（ターゲット）× REVISIO（個人全体）］÷ VR（個人全体/世帯）",
        },
        {
            "label": "【実数値】TVAL（ターゲット）&【INDEX】TVAL（ターゲット）÷TVAL（個人全体/世帯）",
            "actual_section": "TVAL（ターゲット）",
            "index_section": "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
        },
    ]


# =========================================================
# 指定セクション × 局 の実数値 pivot を取得
# =========================================================
def make_actual_station_pivot(df_actual, actual_section, station):
    sub = df_actual[
        (df_actual["セクション"] == actual_section) &
        (df_actual["局"] == station)
    ].copy()

    if sub.empty:
        return None

    sub = sub.sort_values("時間帯")
    return sub[["時間帯"] + WEEKDAYS].set_index("時間帯")


# =========================================================
# 指定指標 × 局 の INDEX pivot を取得
# =========================================================
def make_index_station_pivot(df_index, index_section, station):
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
# - 実数値側セクションと INDEX側指標の両方が存在するものだけ対象
# =========================================================
def get_available_mix_combinations(df_actual, df_index):
    available_actual_sections = set(df_actual["セクション"].dropna().unique().tolist())
    available_index_sections = set(df_index["指標"].dropna().unique().tolist())

    combinations = []
    for combo in get_mix_combination_definitions():
        if (
            combo["actual_section"] in available_actual_sections
            and combo["index_section"] in available_index_sections
        ):
            combinations.append(combo)

    return combinations


# =========================================================
# ページ全体CSV用の縦持ち DataFrame を作成
# =========================================================
def build_all_wish_frames_long_mix(df_actual, df_index, combinations, worst_n, zone_df):
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
                worst_n=worst_n,
                zone_df=zone_df,
            ).reset_index()

            mix_df["組み合わせ"] = combo["label"]
            mix_df["局"] = station
            mix_df = mix_df[["組み合わせ", "局", "時間帯"] + WEEKDAYS]
            all_frames.append(mix_df)

    if not all_frames:
        return pd.DataFrame(columns=["組み合わせ", "局", "時間帯"] + WEEKDAYS)

    return pd.concat(all_frames, axis=0, ignore_index=True)


# =========================================================
# 1組み合わせ分を描画
# - 実数値側と INDEX側の組み合わせ記号表を5局横並びで表示
# =========================================================
# =========================================================
# 1組み合わせ分を描画
# - 実数値側と INDEX側の組み合わせを5局横並びで色だけ表示
# =========================================================
def render_mix_wish_row(combo, df_actual, df_index, worst_n, zone_df, file_name_builder):
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
                worst_n=worst_n,
                zone_df=zone_df,
            )

            # 色だけ表示する図を作成
            mix_fig = build_mix_color_table_figure(mix_df, station)
            csv_bytes = dataframe_to_csv_bytes(mix_df)

            st.download_button(
                label="CSV",
                data=csv_bytes,
                file_name=file_name_builder(combo["label"], station),
                mime="text/csv",
                key=f"wish_mix_csv_{combo['label']}_{station}_{idx}",
                use_container_width=True,
                on_click="ignore",
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
# - 可視化は色だけで表示
# =========================================================
def render_wish_mix_tab(df_heatmap_all, df_heatmap_index):
    init_zone_state()

    st.subheader("希望枠(視聴率×INDEX)")

    # 凡例
    legend_html = """
    <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap; margin:8px 0 16px 0;">
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#ff6b6b;"></div>
                <span>超希望枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#f4a261;"></div>
                <span>希望枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#d9d9d9;"></div>
                <span>普通枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#9e9e9e;"></div>
                <span>拒否枠</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <div style="width:70px; height:22px; background:#4f4f4f;"></div>
                <span>超拒否枠</span>
            </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:6px;">
            <div>超希望枠：視聴率・indexともに平均以上</div>
            <div>希望枠：視聴率・indexいずれか平均以上</div>
            <div>普通枠：一方が平均以上、もう一方がワースト</div>
            <div>拒否枠：視聴率・indexいずれかワースト</div>
            <div>超拒否枠：視聴率・indexともにワースト</div>
        </div>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)

    if df_heatmap_all is None or df_heatmap_all.empty:
        st.info("実数値データがありません。")
        return

    if df_heatmap_index is None or df_heatmap_index.empty:
        st.info("INDEXデータがありません。")
        return

    # 実数値側データにセクション列を追加
    df_actual = add_rating_section_col(df_heatmap_all)
    df_actual = df_actual[df_actual["セクション"].notna()].copy()

    # 利用可能な組み合わせだけ抽出
    combinations = get_available_mix_combinations(
        df_actual=df_actual,
        df_index=df_heatmap_index,
    )

    if not combinations:
        st.info("表示可能な視聴率×INDEX組み合わせデータがありません。")
        return

    # 共通コントロールからゾーンとワースト件数を取得
    selected_zone, worst_n = render_shared_wish_controls("wish_mix")

    # 反映済みゾーン設定を取得
    zone_df = get_wish_zone_df(selected_zone)

    # ページ全体CSV用データを作成
    all_mix_df = build_all_wish_frames_long_mix(
        df_actual=df_actual,
        df_index=df_heatmap_index,
        combinations=combinations,
        worst_n=worst_n,
        zone_df=zone_df,
    )
    all_mix_df["対象ゾーン"] = selected_zone
    all_mix_df["ワースト下位件数"] = worst_n

    # ページ全体CSVダウンロード
    st.download_button(
        label="ページ全体CSV",
        data=dataframe_to_csv_bytes(all_mix_df),
        file_name=f"wish_mix_all_{selected_zone}.csv",
        mime="text/csv",
        key="wish_mix_csv_all",
        use_container_width=False,
        on_click="ignore",
    )

    st.markdown("---")

    # 組み合わせごとに可視化
    for i, combo in enumerate(combinations):
        render_mix_wish_row(
            combo=combo,
            df_actual=df_actual,
            df_index=df_heatmap_index,
            worst_n=worst_n,
            zone_df=zone_df,
            file_name_builder=lambda label, station: f"{label}_{station}_wish_mix.csv",
        )

        if i < len(combinations) - 1:
            st.markdown("---")

# =========================================================
# 視聴率×INDEX 組み合わせ可視化（色だけ表示）
# - セル文字は表示せず、背景色だけで区分を表す
# =========================================================
def build_mix_color_table_figure(mix_df, title):
    # 表示文字は空欄にする
    display_df = mix_df.copy()
    for col in display_df.columns:
        display_df[col] = ""

    header_values = [""] + list(display_df.columns)
    cell_values = [list(display_df.index)] + [display_df[col].tolist() for col in display_df.columns]

    # 記号ごとの色定義
    color_map = {
        "○○": "#ff6b6b",   # 超希望枠
        "○":  "#f4a261",   # 希望枠
        "○×": "#d9d9d9",   # 普通枠
        "×":  "#9e9e9e",   # 拒否枠
        "××": "#4f4f4f",   # 超拒否枠
        "Inf": "#ffffff",  # 特殊値
        "":   "#ffffff",   # 何もなし
    }

    # 各列ごとの背景色
    fill_colors = []
    for col in mix_df.columns:
        fill_colors.append([color_map.get(v, "#ffffff") for v in mix_df[col].tolist()])

    n_rows = len(mix_df)
    table_height = max(680, 90 + n_rows * 27)

    fig = go.Figure(
        data=[
            go.Table(
                columnwidth=[70] + [42] * len(mix_df.columns),
                header=dict(
                    values=header_values,
                    align="center",
                    height=30,
                    fill_color="#8c8c8c",
                    font=dict(color="white", size=11),
                ),
                cells=dict(
                    values=cell_values,
                    align="center",
                    height=27,
                    fill_color=[["#8c8c8c"] * n_rows] + fill_colors,
                    font=dict(
                        color=[["white"] * n_rows] + [["rgba(0,0,0,0)"] * n_rows for _ in mix_df.columns],
                        size=11,
                    ),
                ),
            )
        ]
    )

    fig.update_layout(
        title=title,
        title_x=0.5,
        height=table_height,
        margin=dict(l=5, r=5, t=45, b=5),
    )

    return fig