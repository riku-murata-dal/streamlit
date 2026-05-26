import pandas as pd

def get_daily_vr_rating(file):
    """
    VRのRAWデータを読み込み、
    REVISIOに合わせたセグメント単位で日別GRPを集計して返す関数
    """
    # 1. 17行目(index=16)をヘッダーとして読み込み
    df = pd.read_excel(file, header=16)

    # 2. カラム名のクリーニング
    # 改行コード(_x000D_\n)や余計な空白を除去
    df.columns = df.columns.astype(str).str.replace(r'[\r\n\s]|_x000D_', '', regex=True)

    # 3. 視聴率カラム（「番組平均視聴率」で始まるもの）を特定
    rating_cols = [col for col in df.columns if col.startswith("番組平均視聴率")]

    # 4. 横持ち → 縦持ち
    df_long = df.melt(
        id_vars=["出稿日付"],
        value_vars=rating_cols,
        var_name="セグメント",
        value_name="VR_視聴率"
    )

    # 5. カラム名の統一
    df_long = df_long.rename(columns={"出稿日付": "日付"})

    # 6. セグメント名の整形
    df_long["セグメント"] = (
        df_long["セグメント"]
        .str.replace("番組平均視聴率", "", regex=False)
        .str.strip()
    )

    # 7. VRセグメントをREVISIOのセグメントに合わせて変換
    segment_map = {
        "男女4－12才": "Child",
        "男女13－19才": "Teen",
        "女20－34才": "F1",
        "女35－49才": "F2",
        "女50才以上": "F3",
        "男20－34才": "M1",
        "男35－49才": "M2",
        "男50才以上": "M3",
        "個人全体4才以上": "個人全体",
        "世帯": "世帯"
    }

    df_long["セグメント"] = df_long["セグメント"].map(segment_map).fillna(df_long["セグメント"])

    # 8. 対象外セグメント（例: 世帯）は除外
    df_long = df_long[df_long["セグメント"]!="世帯"].copy()

    # 9. 数値化
    df_long["VR_視聴率"] = pd.to_numeric(df_long["VR_視聴率"], errors="coerce")

    # 10. 日付型に変換
    df_long["日付"] = pd.to_datetime(df_long["日付"], errors="coerce").dt.date

    # 11. 日付×セグメントで日次集計
    df_vr_daily = df_long.groupby(
        ["日付", "セグメント"],
        as_index=False
    )["VR_視聴率"].sum()

    return df_vr_daily