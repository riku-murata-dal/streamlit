import pandas as pd

def get_daily_search(file):
    """
    DS.insightの検索データを読み込み、
    REVISIO準拠の共通セグメントに変換した日別検索数を返す関数。

    ■ 処理概要
    1. ワイド形式（列：キーワード_セグメント）をロング形式に変換
    2. セグメントをREVISIO定義（F1/M1など）にマッピング
        - 一部セグメントは重み付きで分配（例：30代 → F1/F2に0.5ずつ）
    3. 日付×キーワード×セグメント単位で集計
    4. 全セグメント合算の「個人全体」を追加

    ■ 前提
    - 性年代別の検索量データが1シートに集約されていること
    - カラム名は「キーワード_セグメント」形式であること
    """

    # ----------------------------
    # データ読み込み
    # ----------------------------
    df = pd.read_excel(file)

    # 日付をdatetime → date型に変換（異常値はNaT → NaN扱い）
    df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.date

    # ----------------------------
    # 対象カラム抽出（キーワード_セグメント形式）
    # ----------------------------
    target_cols = [col for col in df.columns if "_" in col]

    # ワイド → ロング変換
    df_long = df.melt(
        id_vars=["日付"],
        value_vars=target_cols,
        var_name="元カラム名",
        value_name="検索数"
    )

    # ----------------------------
    # カラム分解（キーワード / セグメント）
    # ----------------------------
    split_cols = df_long["元カラム名"].str.split("_", n=1)
    df_long["キーワード"] = split_cols.str[0]
    df_long["セグメント"] = split_cols.str[1]

    # 数値変換（変換できないものはNaN）
    df_long["検索数"] = pd.to_numeric(df_long["検索数"], errors="coerce")

    # ----------------------------
    # セグメントマッピング定義
    # （REVISIOセグメントへ変換 + 重み分配）
    # ----------------------------
    segment_map = {
        "女性10代（13歳〜）": [("Teen", 1.0)],
        "男性10代（13歳〜）": [("Teen", 1.0)],
        "女性20代": [("F1", 1.0)],
        "女性30代": [("F1", 0.5), ("F2", 0.5)],  # 分配
        "女性40代": [("F2", 1.0)],
        "女性50代": [("F3", 1.0)],
        "女性60代": [("F3", 1.0)],
        "女性70代以上": [("F3", 1.0)],
        "男性20代": [("M1", 1.0)],
        "男性30代": [("M1", 0.5), ("M2", 0.5)],  # 分配
        "男性40代": [("M2", 1.0)],
        "男性50代": [("M3", 1.0)],
        "男性60代": [("M3", 1.0)],
        "男性70代以上": [("M3", 1.0)],
    }

    # ----------------------------
    # セグメント変換（重み付き展開）
    # ----------------------------
    records = []

    for _, row in df_long.iterrows():
        seg = row["セグメント"]

        # 未定義セグメントはスキップ（ここ重要）
        if seg not in segment_map:
            continue

        # 重みに応じて複数レコードへ展開
        for attr, weight in segment_map[seg]:
            records.append({
                "日付": row["日付"],
                "キーワード": row["キーワード"],
                "セグメント": attr,
                "検索数": row["検索数"] * weight if pd.notna(row["検索数"]) else pd.NA
            })

    df_mapped = pd.DataFrame(records)

    # ----------------------------
    # セグメント別集計
    # ----------------------------
    df_search_daily = df_mapped.groupby(
        ["日付", "キーワード", "セグメント"],
        as_index=False
    )["検索数"].sum()

    # ----------------------------
    # 個人全体（全セグメント合算）
    # ----------------------------
    df_total = df_search_daily.groupby(
        ["日付", "キーワード"],
        as_index=False
    )["検索数"].sum()

    df_total["セグメント"] = "個人全体"

    # ----------------------------
    # 結合（属性別 + 個人全体）
    # ----------------------------
    df_search_daily = pd.concat([df_search_daily, df_total], ignore_index=True)

    return df_search_daily