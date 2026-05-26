import pandas as pd
import unicodedata

def make_df_heatmap_VR(file):
    
    """
    ヒートマップ用の視聴率データを整形する関数

    Parameters
    ----------
    file : str or file-like object
        Excelファイルのパス、またはStreamlitのuploaded_file

    Returns
    -------
    df_heatmap_VR : pandas.DataFrame
        各ブロックを結合した整形後データ
        カラム例：
        時間帯, 月, 火, 水, 木, 金, 土, 日, 局
    """

    # =========================
    # 読み込み設定
    # =========================
    # 各ブロックのヘッダー行
    headers = [5, 5, 5, 31, 31]

    # 各ブロックの開始列
    start_cols = [0, 13, 26, 0, 13]

    # 各ブロックの終了列（rangeなのでこの列は含まない）
    end_cols = [8, 21, 34, 8, 21]

    # 各ブロックのデータを格納するリスト
    result = []

    # =========================
    # 各ブロックを順番に読み込み
    # =========================
    for header, start_col, end_col in zip(headers, start_cols, end_cols):

        # 指定した範囲だけExcelから読み込み
        df = pd.read_excel(
            file,
            header=header,
            usecols=range(start_col, end_col),
            nrows=25
        )

        # pandasが重複列名に自動付与する「.1」「.2」を削除
        df.columns = df.columns.astype(str).str.replace(r"\.\d+$", "", regex=True)

        # 1列目の列名を局として保持
        category = df.columns[0]

        # 1列目の列名を「時間帯」に統一
        df = df.rename(columns={df.columns[0]: "時間帯"})

        # 局列を追加
        df["局"] = category

        # 結果リストに追加
        result.append(df)

    # =========================
    # 全ブロックを縦結合
    # =========================
    df_heatmap_VR = pd.concat(result, ignore_index=True)
    df_heatmap_VR["局"] = df_heatmap_VR["局"].astype(str).apply(lambda x: unicodedata.normalize("NFKC", x))

    # =========================
    # 時間帯を 5:00 → 05:00 に統一
    # =========================
    df_heatmap_VR["時間帯"] = (
        df_heatmap_VR["時間帯"]
        .astype(str)
        .str.strip()
        .str.replace(r"^(\d):", r"0\1:", regex=True)
    )

    return df_heatmap_VR