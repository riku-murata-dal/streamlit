import pandas as pd
import streamlit as st

# =========================
# 定数
# =========================
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
WEEKDAY_ONLY = ["月", "火", "水", "木", "金"]
WEEKEND = ["土", "日"]

ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]
TIMES = [f"{h:02d}:00" for h in range(5, 29)]

# =========================
# ゾーンごとの初期ONルール
# - 形式: (対象曜日, 開始時, 終了時)
# =========================
ZONE_RULES = {
    "ATT": [(WEEKDAYS, 5, 28)],
    "全日": [(WEEKDAYS, 5, 25)],
    "ヨの字": [
        (WEEKDAY_ONLY, 5, 8),
        (WEEKDAY_ONLY, 12, 13),
        (WEEKDAY_ONLY, 19, 25),
        (WEEKEND, 5, 25),
    ],
    "コの字": [
        (WEEKDAY_ONLY, 5, 8),
        (WEEKDAY_ONLY, 19, 25),
        (WEEKEND, 5, 25),
    ],
    "逆L": [
        (WEEKDAY_ONLY, 19, 25),
        (WEEKEND, 5, 25),
    ],
}


# =========================
# ゾーン初期データ作成
# =========================
def build_zone_preset(zone_name):
    """
    ゾーンの初期True / False表を作成する

    戻り値：
        index   = 時間帯
        columns = 曜日
        values  = True / False
    """

    # 全セルFalseで初期化
    zone_df = pd.DataFrame(
        False,
        index=TIMES,
        columns=WEEKDAYS
    )

    # ZONE_RULESに定義された条件に従ってTrueを設定
    for days, time_start, time_end in ZONE_RULES.get(zone_name, []):

        # 対象時間帯を抽出
        # 例: "19:00" → 19 に変換して比較
        target_times = [
            t for t in zone_df.index
            if time_start <= int(t.split(":")[0]) <= time_end
        ]

        # 対象曜日 × 対象時間帯をTrueに変更
        zone_df.loc[target_times, days] = True

    return zone_df


# =========================
# session_state 初期化
# =========================
def init_zone_state():
    """
    ゾーン関連のsession_stateを初期化する

    zone_filters:
        分析・集計で使用する確定済みゾーン

    zone_drafts:
        UI上で編集中の一時ゾーン

    zone_reset_requested:
        checkboxを初期状態に戻すためのフラグ
    """

    session = st.session_state

    # 確定データを初期化
    if "zone_filters" not in session:
        session["zone_filters"] = {
            z: build_zone_preset(z)
            for z in ZONE_NAMES
        }

    # 編集用データを初期化
    # 確定データをコピーして作成する
    if "zone_drafts" not in session:
        session["zone_drafts"] = {
            z: session["zone_filters"][z].copy()
            for z in ZONE_NAMES
        }

    # 各ゾーンのリセット要求フラグを初期化
    for z in ZONE_NAMES:
        session.setdefault(
            f"zone_reset_requested_{z}",
            False
        )
        
# =========================
# checkbox key 作成
# =========================
def zone_checkbox_key(zone_name, time_label, day_label):
    """
    checkboxごとの一意キーを作成する

    例：
        zone_checkbox_key("全日", "19:00", "月")
        → zone_chk_全日_19:00_月
    """

    return f"zone_chk_{zone_name}_{time_label}_{day_label}"


# =========================
# DataFrame → checkbox 同期
# =========================
def sync_draft_to_widgets(zone_name):
    """
    編集用DataFrameの内容をcheckboxに反映する

    主な役割：
    - zone_draftsのTrue / Falseをcheckboxに反映
    - 初期化時は既存checkbox状態を削除して再セット
    """

    session = st.session_state

    # 編集中のゾーンDataFrame
    draft_df = session["zone_drafts"][zone_name]

    # 初期化要求フラグ
    reset = session.get(f"zone_reset_requested_{zone_name}", False)

    # 時間帯 × 曜日ごとにcheckbox状態をセット
    for t in TIMES:
        for d in WEEKDAYS:

            key = zone_checkbox_key(zone_name, t, d)

            # 初期化時は既存のcheckbox状態を削除
            if reset and key in session:
                del session[key]

            # checkboxが未作成の場合のみ初期値をセット
            if key not in session:
                session[key] = bool(draft_df.loc[t, d])

    # リセット処理後はフラグを戻す
    if reset:
        session[f"zone_reset_requested_{zone_name}"] = False


# =========================
# checkbox → DataFrame 同期
# =========================
def sync_widgets_to_draft(zone_name):
    """
    checkboxの現在値を編集用DataFrameに反映する

    主な役割：
    - UI上で変更されたcheckboxの状態を取得
    - zone_draftsへ保存
    """

    session = st.session_state

    # 全FalseのDataFrameを作成
    df = pd.DataFrame(
        False,
        index=TIMES,
        columns=WEEKDAYS
    )

    # checkboxの値をDataFrameへ反映
    for t in TIMES:
        for d in WEEKDAYS:
            df.loc[t, d] = bool(
                session.get(
                    zone_checkbox_key(zone_name, t, d),
                    False
                )
            )

    # 編集用データとして保存
    session["zone_drafts"][zone_name] = df


# =========================
# ゾーン初期化
# =========================
def reset_zone_draft(zone_name):
    """
    指定したゾーンを初期状態に戻す

    主な役割：
    - ZONE_RULESに基づいて初期状態を再作成
    - checkbox側も再初期化されるようにフラグを立てる
    """

    # 編集用DataFrameを初期状態に戻す
    st.session_state["zone_drafts"][zone_name] = build_zone_preset(zone_name)

    # checkbox状態を再初期化するためのフラグ
    st.session_state[f"zone_reset_requested_{zone_name}"] = True
    

# =========================
# 編集内容を確定
# =========================
def apply_all_zone_filters():
    """
    全ゾーンの編集内容を確定する

    主な役割：
    - checkboxの現在値をzone_draftsへ反映
    - zone_draftsをzone_filtersへコピー
    - 以降の分析・集計ではzone_filtersを使用
    """

    session = st.session_state

    for z in ZONE_NAMES:

        # checkbox → draft
        sync_widgets_to_draft(z)

        # draft → filters
        session["zone_filters"][z] = session["zone_drafts"][z].copy()


# =========================
# checkbox表 描画
# =========================
def render_zone_editor(zone_name):
    """
    指定ゾーンのcheckbox表を描画する

    表構成：
    - 行：時間帯
    - 列：曜日
    - セル：checkbox
    """

    # draftの内容をcheckboxへ反映
    sync_draft_to_widgets(zone_name)

    # ヘッダー行を作成
    header = st.columns([1.15] + [0.62] * len(WEEKDAYS))

    # 左上セルは空欄
    header[0].markdown(" ")

    # 曜日ヘッダーを中央寄せで表示
    for i, d in enumerate(WEEKDAYS):
        header[i + 1].markdown(
            f"<div style='text-align:center'>{d}</div>",
            unsafe_allow_html=True,
        )

    # 時間帯ごとにcheckbox行を描画
    for t in TIMES:

        row = st.columns([1.15] + [0.62] * len(WEEKDAYS))

        # 左端に時間帯を表示
        row[0].markdown(t)

        # 曜日ごとにcheckboxを表示
        for i, d in enumerate(WEEKDAYS):
            row[i + 1].checkbox(
                "",
                key=zone_checkbox_key(zone_name, t, d),
                label_visibility="collapsed",

                # ATTは固定ゾーンのため編集不可
                disabled=(zone_name == "ATT"),
            )


# =========================
# ゾーン単位UI 描画
# =========================
@st.fragment
def render_single_zone_fragment(zone_name):
    """
    ゾーン単位のUIを描画する

    主な役割：
    - ゾーン名を表示
    - checkbox表を表示
    - ATT以外は初期化ボタンを表示
    """

    # ゾーン名を表示
    st.markdown(f"### {zone_name}")

    # checkbox表を表示
    render_zone_editor(zone_name)

    # ATT以外は初期化可能
    if zone_name != "ATT":

        if st.button(
            "初期化",
            key=f"reset_zone_{zone_name}",
            use_container_width=True
        ):

            # draftを初期状態に戻す
            reset_zone_draft(zone_name)

            # このfragmentだけ再描画
            st.rerun(scope="fragment")