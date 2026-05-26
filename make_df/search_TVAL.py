import pandas as pd

def get_daily_tval_rating(file):
    """
    TVALのRAWデータを読み込み、
    REVISIOに合わせたセグメント×CM単位で視聴率を集計して返す関数
    """
    # 1. 20行目(index=19)をヘッダーとして読み込み
    df = pd.read_excel(file, header=19)

    # 2. 視聴率カラム（「視聴率：」で始まるもの）を特定
    rating_cols = [col for col in df.columns if col.startswith("視聴率：")]

    # 3. 横持ち → 縦持ち
    df_long = df.melt(
        id_vars=["日付"],
        value_vars=rating_cols,
        var_name="セグメント",
        value_name="TVAL_視聴率"
    )

    # 4. セグメント名の整形
    df_long["セグメント"] = df_long["セグメント"].str.replace("視聴率：", "", regex=False).str.strip()

    # 5. TVALセグメントをREVISIOのセグメントに合わせて変換
    segment_map = {
        "FC": "Child",
        "MC": "Child",
        "FT": "Teen",
        "MT": "Teen",
        "F1": "F1",
        "F2": "F2",
        "F3-": "F3",
        "F3+": "F3",
        "M1": "M1",
        "M2": "M2",
        "M3-": "M3",
        "M3+": "M3",
        "個人全体": "個人全体",
        "世帯": "世帯"
    }

    df_long["セグメント"] = df_long["セグメント"].map(segment_map).fillna(df_long["セグメント"])

    # 6. 対象外セグメント（例: 世帯）は除外
    df_long = df_long[df_long["セグメント"]!="世帯"].copy()

    # 7. 数値化
    df_long["TVAL_視聴率"] = pd.to_numeric(df_long["TVAL_視聴率"], errors="coerce")

    # 8. 日付×セグメントで日次集計
    df_tval_daily = df_long.groupby(
        ["日付", "セグメント"],
        as_index=False
    )["TVAL_視聴率"].sum()

    # 9. 日付型に変更
    df_tval_daily["日付"] = pd.to_datetime(df_tval_daily["日付"], errors="coerce").dt.date

    return df_tval_daily