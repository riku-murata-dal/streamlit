import pandas as pd
import streamlit as st

ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]


# =========================================================
# 共通処理
# =========================================================
def format_num(x):
    """数値表示用フォーマット"""
    if pd.isna(x):
        return "-"
    return f"{x:,.0f}"


def get_metric_columns(prefix: str):
    """
    指標ごとの列名を返す
    例:
        prefix='パーコスト'
        -> ['パーコスト_全日', 'パーコスト_ヨの字', ...]
    """
    return [f"{prefix}_{z}" for z in ZONE_NAMES]


def make_display_table(area_df: pd.DataFrame, prefix: str, formatter):
    """
    エリア別の表示用テーブルを作成する共通関数

    Parameters
    ----------
    area_df : pd.DataFrame
        エリアで絞り込んだデータ
    prefix : str
        'パーコスト' / 'ターゲットINDEX' / 'ターゲットコスト'
    formatter : function
        表示フォーマット関数

    Returns
    -------
    pd.DataFrame
    """
    cols = ["局"] + get_metric_columns(prefix)
    disp_df = area_df[cols].copy()
    disp_df.columns = ["局"] + ZONE_NAMES

    for z in ZONE_NAMES:
        disp_df[z] = disp_df[z].map(formatter)

    return disp_df


# =========================================================
# session_state 管理
# =========================================================
def init_area_state(areas):
    """
    エリア選択用 session_state 初期化
    """

    default_on_areas = ["関東", "関西", "中京"] # 海藤修正5/13（"中京"を追加）

    if "selected_area_map" not in st.session_state:
        st.session_state["selected_area_map"] = {}

    for area in areas:
        if area not in st.session_state["selected_area_map"]:
            # st.session_state["selected_area_map"][area] = False # 海藤コメント（ここ消していいですか？）
            st.session_state["selected_area_map"][area] = area in default_on_areas

        if f"top_{area}" not in st.session_state:
            st.session_state[f"top_{area}"] = st.session_state["selected_area_map"][area]

        if f"row_{area}" not in st.session_state:
            st.session_state[f"row_{area}"] = st.session_state["selected_area_map"][area]


def sync_from_top(area: str):
    """
    上部チェックボックス → 各エリア見出し横のチェックボックスへ同期
    """
    value = st.session_state.get(f"top_{area}", False)
    st.session_state[f"row_{area}"] = value
    st.session_state["selected_area_map"][area] = value


def sync_from_row(area: str):
    """
    各エリア見出し横のチェックボックス → 上部チェックボックスへ同期
    """
    value = st.session_state.get(f"row_{area}", False)
    st.session_state[f"top_{area}"] = value
    st.session_state["selected_area_map"][area] = value


def get_selected_areas():
    """
    現在選択中のエリア一覧を返す
    """
    return [
        area
        for area, selected in st.session_state["selected_area_map"].items()
        if selected
    ]

# 海藤修正5/14（関数追加）
def reset_to_default(area_list):
    """
    エリア選択をデフォルト（関東・関西・中京）に戻す
    """
    # デフォルト対象を定義
    default_on_areas = ["関東", "関西", "中京"]
    
    for area in area_list:
        # デフォルトに含まれるエリアならTrue、それ以外はFalse
        is_default = area in default_on_areas
        
        st.session_state[f"top_{area}"] = is_default
        st.session_state[f"row_{area}"] = is_default
        st.session_state["selected_area_map"][area] = is_default


# =========================================================
# データ読み込み・集計
# =========================================================
def read_cost_excel(uploaded_file):
    """
    エリア別コストExcelを読み込み、分析用DataFrameに整形する

    想定:
      A列: エリア（結合セルあり）
      B列: 局
      C:G  パーコスト
      H:L  ターゲットINDEX
      M:Q  ターゲットコスト
    """
    raw = pd.read_excel(uploaded_file, header=None)

    df = raw.iloc[2:, :17].copy()
    df.columns = [
        "エリア", "局",
        "パーコスト_全日", "パーコスト_ヨの字", "パーコスト_コの字", "パーコスト_逆L", "パーコスト_ATT",
        "ターゲットINDEX_全日", "ターゲットINDEX_ヨの字", "ターゲットINDEX_コの字", "ターゲットINDEX_逆L", "ターゲットINDEX_ATT",
        "ターゲットコスト_全日", "ターゲットコスト_ヨの字", "ターゲットコスト_コの字", "ターゲットコスト_逆L", "ターゲットコスト_ATT",
    ]

    # 結合セル対策
    df["エリア"] = df["エリア"].ffill()

    # 局がない行は除外
    df = df[df["局"].notna()].copy()

    # 文字列整形
    df["エリア"] = df["エリア"].astype(str).str.strip()
    df["局"] = df["局"].astype(str).str.strip()

    # 数値列を数値化
    num_cols = [c for c in df.columns if c not in ["エリア", "局"]]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def calc_area_avg_target_cost(df: pd.DataFrame):
    """
    エリアごとのターゲットコスト局平均を計算
    """
    cols = get_metric_columns("ターゲットコスト")

    area_avg_df = (
        df.groupby("エリア")[cols]
        .mean()
        .reset_index()
    )

    rename_map = {f"ターゲットコスト_{z}": z for z in ZONE_NAMES} 
    area_avg_df = area_avg_df.rename(columns=rename_map)

    return area_avg_df


def calc_selected_area_zone_sum(area_avg_df: pd.DataFrame):
    """
    # 選択されたエリアのターゲットコスト局平均をゾーンごとに合算し、×100する
    選択されたエリアのターゲットコスト局平均をゾーンごとに合算 # 海藤修正5/13（コメント修正）
    """
    selected_areas = get_selected_areas()

    if not selected_areas:
        return pd.Series({z: 0 for z in ZONE_NAMES})

    target_df = area_avg_df[area_avg_df["エリア"].isin(selected_areas)]
    # return target_df[ZONE_NAMES].sum() * 100
    return target_df[ZONE_NAMES].sum() # 海藤修正5/13（ここで100掛けない）


# =========================================================
# 表示処理
# =========================================================
# def render_summary_boxes(selected_zone_sum: pd.Series):
#     """
#     上部のゾーンサマリーボックスを表示
#     """
#     st.markdown("#### エリア平均パーコスト")

#     box_cols = st.columns(len(ZONE_NAMES))
#     for i, z in enumerate(ZONE_NAMES):
#         with box_cols[i]:
#             val = selected_zone_sum[z]
#             st.markdown(
#                 f"""
#                 <div style="
#                     background-color:#0b4a8b;
#                     color:white;
#                     text-align:center;
#                     padding:8px;
#                     border-radius:6px 6px 0 0;
#                     font-weight:bold;
#                 ">
#                     {z}
#                 </div>
#                 <div style="
#                     border:2px solid #0b4a8b;
#                     text-align:center;
#                     padding:10px;
#                     font-size:28px;
#                     border-radius:0 0 6px 6px;
#                     margin-bottom:8px;
#                 ">
#                     {format_num(val)}
#                 </div>
#                 """,
#                 unsafe_allow_html=True,
#             )


# 海藤修正5/14（関数を全体的に修正）
def render_summary_boxes(selected_zone_sum: pd.Series):
    """
    上部のゾーンサマリーボックスを表示
    """
    # 共通の箱描画用パーツ
    def _render_box(label, value):
        # 値が数値（int/float）ならフォーマット、それ以外（Noneや空文字）ならそのまま表示
        display_val = format_num(value) if isinstance(value, (int, float)) else ""        
        st.markdown(
            f"""
            <div style="
                background-color:#0b4a8b;
                color:white;
                text-align:center;
                padding:8px;
                border-radius:6px 6px 0 0;
                font-weight:bold;
            ">
                {label}
            </div>
            <div style="
                border:2px solid #0b4a8b;
                text-align:center;
                padding:10px;
                font-size:18px;
                border-radius:0 0 6px 6px;
                margin-bottom:8px;
                min-height: 52px; /* 中身が空でも高さを維持してガタつきを防ぐ */
                display: flex;
                align-items: center;
                justify-content: center;
                word-break: break-all; /* 数値が長すぎる場合に枠内で改行を許可 */            
            ">
                {display_val}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 1. エリア平均パーコストの表示
    box_cols = st.columns(len(ZONE_NAMES))
    for i, z in enumerate(ZONE_NAMES):
        with box_cols[i]:
            _render_box(z, selected_zone_sum[z])

    # 2. 案内文とGRP入力
    st.write("") 
    st.caption("概算コストを算出したい場合は、以下に任意のGRPを設定してください")

    # 比率を [1, 2] に変更し、入力欄の横幅を確保
    col_input, _ = st.columns([1, 2]) 
    with col_input:
        raw_grp = st.text_input(
            "設定GRP", 
            value="",  
            placeholder="数値を入力",
            label_visibility="collapsed", 
            key="input_grp"
        )

        try:
            grp = float(raw_grp) if raw_grp else None
        except ValueError:
            grp = None

    # 3. 概算コストの表示（合計値 * GRP）
    calc_cols = st.columns(len(ZONE_NAMES))
    for i, z in enumerate(ZONE_NAMES):
        with calc_cols[i]:
            # ここで * GRP を適用
            # grpが入力されていれば計算、空（None）ならNoneを渡す
            estimated_cost = selected_zone_sum[z] * grp if grp is not None else None
            _render_box(z, estimated_cost)


# def render_top_area_selector(area_list):
#     """
#     上部のエリア選択チェックボックス群を表示
#     """
#     st.markdown("#### 対象とするエリアを選択してください")
#     st.caption("上のエリア選択と、各エリア見出し横の☑が連動します")

#     n_cols = 10
#     rows = [area_list[i:i + n_cols] for i in range(0, len(area_list), n_cols)]

#     for row_areas in rows:
#         cols = st.columns(n_cols)
#         for i, area in enumerate(row_areas):
#             with cols[i]:
#                 st.checkbox(
#                     area,
#                     key=f"top_{area}",
#                     on_change=sync_from_top,
#                     args=(area,),
#                 )


# 海藤修正5/14（関数を全体的に修正）
def render_top_area_selector(area_list):
    """
    上部のエリア選択チェックボックス群を表示
    """
    # タイトルとボタンを横並びにする
    col_title, col_btn = st.columns([3, 1])
    
    with col_title:
        st.markdown("#### 対象とするエリアを選択してください")
    
    with col_btn:
        # 入力をクリア（デフォルトのエリア指定に戻す）するボタン
        st.button(
            "入力をクリア", 
            on_click=reset_to_default, 
            args=(area_list,),
            use_container_width=True
        )

    st.caption("上のエリア選択と、各エリア見出し横の☑が連動します")

    # チェックボックス描画処理
    n_cols = 10
    rows = [area_list[i:i + n_cols] for i in range(0, len(area_list), n_cols)]

    for row_areas in rows:
        cols = st.columns(n_cols)
        for i, area in enumerate(row_areas):
            with cols[i]:
                st.checkbox(
                    area,
                    key=f"top_{area}",
                    on_change=sync_from_top,
                    args=(area,),
                )


def render_area_header(area: str):
    """
    エリア見出し行（左にチェックボックス、右に見出し帯）を表示
    """
    header_cols = st.columns([0.01, 0.99], vertical_alignment="center")

    with header_cols[0]:
        st.markdown(
            """
            <style>
            div[data-testid="stCheckbox"] {
                margin-top: 0 !important;
                margin-bottom: 0 !important;
            }
            div[data-testid="stCheckbox"] > label {
                padding: 0 !important;
                margin: 0 !important;
                min-height: auto !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.checkbox(
            area,
            key=f"row_{area}",
            on_change=sync_from_row,
            args=(area,),
            label_visibility="collapsed",
        )

    with header_cols[1]:
        st.markdown(
            f"""
            <div style="
                background-color:#082b66;
                color:white;
                font-weight:bold;
                padding:8px 12px;
                border-radius:4px;
                margin-left:-6px;
                margin-bottom:6px;
            ">
                {area}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_area_tables(area_df: pd.DataFrame):
    """
    エリアごとの3テーブルを表示
    """
    per_cost_df = make_display_table(
        area_df=area_df,
        prefix="パーコスト",
        formatter=format_num,
    )

    target_index_df = make_display_table(
        area_df=area_df,
        prefix="ターゲットINDEX",
        formatter=lambda x: "-" if pd.isna(x) else f"{x:.1f}",
    )

    target_cost_df = make_display_table(
        area_df=area_df,
        prefix="ターゲットコスト",
        formatter=format_num,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### パーコスト")
        st.dataframe(per_cost_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### ターゲットINDEX")
        st.dataframe(target_index_df, use_container_width=True, hide_index=True)

    with col3:
        st.markdown("#### ターゲットコスト")
        st.dataframe(target_cost_df, use_container_width=True, hide_index=True)


def render_area_selected_caption(area: str, area_avg_df: pd.DataFrame):
    """
    エリアが選択中の場合、局平均の補足表示を出す
    """
    if not st.session_state["selected_area_map"].get(area, False):
        return

    area_avg_row = area_avg_df[area_avg_df["エリア"] == area]
    if area_avg_row.empty:
        return

    vals = area_avg_row.iloc[0]
    # 海藤修正5/14（「ターゲットコスト局平均」→「ターゲットコストのゾーン平均」）
    text = "選択中エリアのターゲットコストのゾーン平均: " + " / ".join(
        [f"{z}={format_num(vals[z])}" for z in ZONE_NAMES]
    )
    st.caption(text)


def render_area_block(area: str, df: pd.DataFrame, area_avg_df: pd.DataFrame):
    """
    エリア単位の表示ブロック
    """
    render_area_header(area)

    area_df = df[df["エリア"] == area].copy()
    render_area_tables(area_df)
    render_area_selected_caption(area, area_avg_df)

    st.markdown("<br>", unsafe_allow_html=True)