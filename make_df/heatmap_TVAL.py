import pandas as pd

def make_df_heatmap_TVAL(file):

    # 同じ uploaded file を再利用しても先頭から読めるようにする！（TVALはcsvなのでうまくいかない？？）
    if hasattr(file, "seek"):
        file.seek(0)

    """
    TVALデータ（局名が上段にある形式）を整形し、
    ヒートマップ用のデータフレームを作成する関数

    Parameters
    ----------
    file : str or file-like object
        CSVファイル（utf-8-sig想定）またはStreamlitのuploaded_file

    Returns
    -------
    df_heatmap_TVAL : pandas.DataFrame
        カラム構成：
        時間帯, 月, 火, 水, 木, 金, 土, 日, 局
    """

    # =========================
    # CSV読み込み
    # 先頭11行を飛ばし、AW列以降の崩れを避けるため
    # A～AV列（48列）のみを対象に読み込む
    # =========================
    df = pd.read_csv(
        file,
        skiprows=11,
        header=None,
        usecols=range(48)
    )

    # =========================
    # 局名変換マップ（正式名 → 略称）
    # =========================
    station_map = {
        "NHK総合": None,       # 使用しないためNone
        "日本テレビ": "NTV",
        "テレビ朝日": "EX",
        "TBS": "TBS",
        "テレビ東京": "TX",
        "フジテレビ": "CX"
    }

    result = []

    # =========================
    # 行位置の定義（skiprows=11後の相対位置）
    # 元ファイル:
    # 12行目 = 局名行
    # 13行目 = 曜日行
    # 14行目以降 = データ
    # ↓
    # 読み込み後:
    # 0行目 = 局名行
    # 1行目 = 曜日行
    # 2行目以降 = データ
    # =========================
    station_row = 0
    day_row = 1
    data_start = 2

    # 曜日カラム
    value_cols = ["月", "火", "水", "木", "金", "土", "日"]

    # =========================
    # 時間帯は左端列から取得（全局共通）
    # =========================
    time_col = df.iloc[data_start:, 0]

    # =========================
    # 列方向にスキャンして局ブロックを検出
    # =========================
    col = 0
    while col < df.shape[1]:

        # 局名取得
        station = df.iloc[station_row, col]

        # 空ならスキップ
        if pd.isna(station):
            col += 1
            continue

        station = str(station).strip()

        # =========================
        # 曜日行でブロック判定
        # =========================
        days = df.iloc[day_row, col:col+7].tolist()
        days = [str(x).strip() if pd.notna(x) else "" for x in days]

        if days == value_cols:

            # =========================
            # 該当局のデータ抽出
            # =========================
            sub_df = df.iloc[data_start:, col:col+7].copy()
            sub_df.columns = value_cols

            # 時間帯付与
            sub_df["時間帯"] = time_col.values

            # 局情報付与
            sub_df["局名"] = station
            sub_df["局"] = station_map.get(station, station)

            # カラム順整理
            sub_df = sub_df[["局名", "局", "時間帯"] + value_cols]

            # 時間帯が空の行を除外
            sub_df = sub_df[sub_df["時間帯"].notna()].copy()

            result.append(sub_df)

            # 次の局ブロックへ（7列分スキップ）
            col += 7

        else:
            col += 1

    # =========================
    # ブロックが1つも取れなかった場合
    # =========================
    if not result:
        return pd.DataFrame(columns=["局名", "局", "時間帯"] + value_cols)

    # =========================
    # 全局データ結合
    # =========================
    df_heatmap_TVAL = pd.concat(result, ignore_index=True)

    # =========================
    # 時間帯フォーマット調整
    # 例：28:00:00 → 28:00
    # =========================
    df_heatmap_TVAL["時間帯"] = (
        df_heatmap_TVAL["時間帯"]
        .astype(str)
        .str.slice(0, 5)
        .str.replace(r"^(\d):", r"0\1:", regex=True)
    )

    # =========================
    # NHKなど不要局の除外（局=None）
    # =========================
    df_heatmap_TVAL = df_heatmap_TVAL[df_heatmap_TVAL["局"].notna()].copy()

    # =========================
    # カラム順整理（分析用）
    # =========================
    df_heatmap_TVAL = df_heatmap_TVAL[
        ["時間帯", "月", "火", "水", "木", "金", "土", "日", "局"]
    ]

    # =========================
    # 数値化（視聴率）
    # =========================
    for c in value_cols:
        df_heatmap_TVAL[c] = pd.to_numeric(df_heatmap_TVAL[c], errors="coerce")

    return df_heatmap_TVAL