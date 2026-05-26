import pandas as pd

def get_daily_revisio_rating(file):
    """
    REVISIOのRAWデータを読み込み、
    属性（セグメント）ごとに日別のGRP（視聴率）を集計して返す関数
    """
    # 1. 17行目(index=16)をヘッダーとして読み込み
    df = pd.read_excel(file, header=16)

    # 2. カラム名の整形
    # 前後の空白を除去し、GRP* の「*」も削除して「GRP」に統一
    df.columns = df.columns.str.strip().str.replace("*", "", regex=False)

    # 3. 放送時間を日付型に変換
    if "放送時間" in df.columns:
        # Excelのシリアル値や日時形式を「日付のみ」に変換
        df["日付"] = pd.to_datetime(df["放送時間"], errors="coerce").dt.date

    # 4. GRPの数値化（念のため文字列混入対策）
    if "GRP" in df.columns:
        df["REVISIO_GRP"] = pd.to_numeric(df["GRP"], errors="coerce")

    # 5. 「日付」と「属性」ごとにGRPを合計
    df_revisio_daily = df.groupby(["日付", "属性"], as_index=False)["REVISIO_GRP"].sum()

    # 6. カラム名の変更
    df_revisio_daily = df_revisio_daily.rename(columns={"属性":"セグメント"})

    return df_revisio_daily