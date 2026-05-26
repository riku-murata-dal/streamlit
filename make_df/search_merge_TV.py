import pandas as pd

def merge_tv_data(df_revisio_daily, df_tval_daily, df_vr_daily):
    """
    TV系データ（REVISIO / TVAL / VR）を
    日付 × セグメント単位で横結合する関数

    ■ 処理概要
    1. 各データの「日付」型を統一（datetime → date）
    2. 日付 × セグメント をキーに外部結合（outer join）
       - どれか一部のデータが欠けていても落とさない
    3. 日付・セグメントでソート

    ■ 前提
    - 各DataFrameは「日付」「セグメント」列を持つこと
    - セグメント定義は事前に統一されていること（重要）

    ■ 注意
    - outer joinのため、欠損値（NaN）が発生する
    - セグメント不一致があると意図しない欠損が増える
    """

    # ----------------------------
    # 日付型を統一（結合キーのズレ防止）
    # ----------------------------
    for df in [df_revisio_daily, df_tval_daily, df_vr_daily]:
        df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.date

    # ----------------------------
    # データ結合（横持ち）
    # ----------------------------
    df_tv = (
        df_revisio_daily
        # REVISIO × TVAL
        .merge(df_tval_daily, on=["日付", "セグメント"], how="outer")
        # ↑ さらにVRを結合
        .merge(df_vr_daily, on=["日付", "セグメント"], how="outer")
        # 並び順を整理
        .sort_values(["日付", "セグメント"])
        # インデックス振り直し
        .reset_index(drop=True)
    )

    return df_tv