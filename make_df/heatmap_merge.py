import pandas as pd
from .heatmap_VR import make_df_heatmap_VR
from .heatmap_TVAL import make_df_heatmap_TVAL
from .heatmap_REVISIO import make_df_heatmap_REVISIO

day_cols = ["月", "火", "水", "木", "金", "土", "日"]

# =========================
# TVAL × REVISIO補正指標を追加
# =========================
def add_tval_revisio_adjusted(df_base, revisio_category, output_category):
    """
    TVAL（ターゲット） × [REVISIO（各セル） ÷ REVISIO（局単位の全セル平均）]
    """

    # TVALターゲット
    tval_df = df_base[
        (df_base["データ種別"] == "TVAL") &
        (df_base["カテゴリー"] == "ターゲット")
    ].copy()

    # REVISIO対象カテゴリ
    revisio_df = df_base[
        (df_base["データ種別"] == "REVISIO") &
        (df_base["カテゴリー"] == revisio_category)
    ].copy()

    if tval_df.empty or revisio_df.empty:
        return pd.DataFrame(columns=df_base.columns)

    # 数値化
    for col in day_cols:
        tval_df[col] = pd.to_numeric(tval_df[col], errors="coerce")
        revisio_df[col] = pd.to_numeric(revisio_df[col], errors="coerce")

    # 局単位のREVISIO全セル平均
    revisio_long = revisio_df.melt(
        id_vars=["時間帯", "局"],
        value_vars=day_cols,
        var_name="曜日",
        value_name="revisio_value"
    )

    station_mean = (
        revisio_long
        .groupby("局", as_index=False)["revisio_value"]
        .mean()
        .rename(columns={"revisio_value": "revisio_station_mean"})
    )

    # TVALとREVISIOを 時間帯×局 で結合
    merged = tval_df.merge(
        revisio_df[["時間帯", "局"] + day_cols],
        on=["時間帯", "局"],
        suffixes=("_tval", "_revisio")
    )

    # 局単位平均を付与
    merged = merged.merge(station_mean, on="局", how="left")

    # 補正値を計算
    result = merged[["時間帯", "局"]].copy()

    for col in day_cols:
        tval_col = f"{col}_tval"
        revisio_col = f"{col}_revisio"

        result[col] = (
            merged[tval_col] *
            (merged[revisio_col] / merged["revisio_station_mean"])
        )

    result["データ種別"] = "TVAL×REVISIO補正"
    result["カテゴリー"] = output_category

    return result[["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "データ種別", "カテゴリー"]]


def make_df_heatmap_all(
    vr_all_file=None,
    vr_target_file=None,
    tval_all_file=None,
    tval_target_file=None,
    revisio_file=None
):
    """
    VR / TVAL / REVISIO を結合する関数（個人全体・ターゲット対応）

    Returns
    -------
    pandas.DataFrame
        時間帯, 月〜日, 局, データ種別, カテゴリー
    """

    df_list = []

    # =========================
    # VR
    # =========================
    if vr_all_file is not None:
        df = make_df_heatmap_VR(vr_all_file).copy()
        df["データ種別"] = "VR"
        df["カテゴリー"] = "個人全体"
        df_list.append(df)

    if vr_target_file is not None:
        df = make_df_heatmap_VR(vr_target_file).copy()
        df["データ種別"] = "VR"
        df["カテゴリー"] = "ターゲット"
        df_list.append(df)

    # =========================
    # TVAL
    # =========================
    if tval_all_file is not None:
        df = make_df_heatmap_TVAL(tval_all_file).copy()
        df["データ種別"] = "TVAL"
        df["カテゴリー"] = "個人全体"
        df_list.append(df)

    if tval_target_file is not None:
        df = make_df_heatmap_TVAL(tval_target_file).copy()
        df["データ種別"] = "TVAL"
        df["カテゴリー"] = "ターゲット"
        df_list.append(df)

    # =========================
    # REVISIO
    # =========================
    if revisio_file is not None:
        for column in ["GRP", "注視TRP", "滞在TRP"]:

            df = make_df_heatmap_REVISIO(revisio_file, column).copy()
            df["データ種別"] = "REVISIO"

            # カテゴリー名を整形
            if column == "GRP":
                df["カテゴリー"] = "世帯"

            elif column == "注視TRP":
                df["カテゴリー"] = "注視"

            elif column == "滞在TRP":
                df["カテゴリー"] = "滞在"

            df_list.append(df)

    # =========================
    # 空チェック
    # =========================
    if not df_list:
        return pd.DataFrame(
            columns=["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "データ種別", "カテゴリー"]
        )

    # =========================
    # カラム揃え
    # =========================
    base_cols = ["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "データ種別", "カテゴリー"]

    aligned = []
    for df in df_list:
        for col in base_cols:
            if col not in df.columns:
                df[col] = pd.NA
        aligned.append(df[base_cols])

    # =========================
    # 結合
    # =========================
    df_heatmap_real = pd.concat(aligned, ignore_index=True)

    # 注視TRP補正
    df_attention_adjusted = add_tval_revisio_adjusted(
        df_heatmap_real,
        revisio_category="注視",
        output_category="注視補正"
    )

    # 滞在TRP補正
    df_stay_adjusted = add_tval_revisio_adjusted(
        df_heatmap_real,
        revisio_category="滞在",
        output_category="滞在補正"
    )

    # 元データに追加
    df_heatmap_real = pd.concat(
        [df_heatmap_real, df_attention_adjusted, df_stay_adjusted],
        ignore_index=True
    )

    # =========================
    # 並び順を指定
    # =========================
    data_type_order = ["VR", "TVAL", "REVISIO", "TVAL×REVISIO補正"]
    category_order = ["個人全体", "ターゲット", "注視", "滞在", "世帯", "注視補正", "滞在補正"]
    station_order = ["NTV", "TBS", "CX", "EX", "TX"]

    # カテゴリ順を設定
    df_heatmap_real["データ種別"] = pd.Categorical(
        df_heatmap_real["データ種別"],
        categories=data_type_order,
        ordered=True
    )

    df_heatmap_real["カテゴリー"] = pd.Categorical(
        df_heatmap_real["カテゴリー"],
        categories=category_order,
        ordered=True
    )

    df_heatmap_real["局"] = pd.Categorical(
        df_heatmap_real["局"],
        categories=station_order,
        ordered=True
    )

    # 時間帯ソート用
    df_heatmap_real["_sort_time"] = (
        df_heatmap_real["時間帯"]
        .astype(str)
        .str.strip()
        .str.replace(":", "", regex=False)
        .astype(int)
    )

    # 並び替え
    df_heatmap_real = (
        df_heatmap_real.sort_values(["データ種別", "カテゴリー", "局", "_sort_time"])
        .drop(columns="_sort_time")
        .reset_index(drop=True)
    )

    return df_heatmap_real

