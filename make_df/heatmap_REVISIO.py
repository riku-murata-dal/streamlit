import pandas as pd

def make_df_heatmap_REVISIO(file, column):
    """
    GRPデータをヒートマップ用に整形する関数

    Parameters
    ----------
    file : str or file-like object
        Excelファイルのパス、またはStreamlitのuploaded_file

    Returns
    -------
    pandas.DataFrame
        カラム構成：
        時間帯, 月, 火, 水, 木, 金, 土, 日, 局
    """
    
    # 「ノーム」を含むシート名を取得
    excel_file = pd.ExcelFile(file)

    target_sheet = next(
        (sheet for sheet in excel_file.sheet_names if "ノーム" in sheet),
        None
    )

    # シートが見つからなかった場合
    if target_sheet is None:
        raise ValueError("『ノーム』を含むシートが見つかりません。")

    # 対象シートを読み込み
    df = pd.read_excel(file, sheet_name=target_sheet)
    

    # =========================
    # 読み込み
    # =========================
    # df = pd.read_excel(file)

    # =========================
    # 必要列だけ抽出
    # =========================
    df = df[["放送局", "時間帯範囲", "曜日", column]].copy()
    df = df.rename(columns={"放送局":"局"})

    # =========================
    # 時間帯作成
    # 例: 05:00~06:00 → 5:00
    #     28:00~29:00 → 28:00
    # =========================
    df["時間帯"] = (
        df["時間帯範囲"]
        .astype(str)
        .str.split("~")
        .str[0]
        .str.strip()
    )

    # =========================
    # GRP数値化
    # =========================
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    # =========================
    # 局 × 時間帯 × 曜日 で集計
    # =========================
    df_grp = (
        df.groupby(["局", "時間帯", "曜日"], as_index=False)[column]
        .sum()
    )

    # =========================
    # 横持ち化（月〜日）
    # =========================
    weekday_order = ["月", "火", "水", "木", "金", "土", "日"]

    df_heatmap_REVISIO = (
        df_grp.pivot_table(
            index=["局", "時間帯"],
            columns="曜日",
            values=column,
            aggfunc="sum",
            fill_value=0
        )
        .reindex(columns=weekday_order, fill_value=0)
        .reset_index()
    )

    # =========================
    # カラム順整理
    # =========================
    df_heatmap_REVISIO = df_heatmap_REVISIO[
        ["時間帯", "月", "火", "水", "木", "金", "土", "日", "局"]
    ]

    return df_heatmap_REVISIO