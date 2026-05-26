import pandas as pd

def merge_tv_search_for_keyword(df_tv, df_search_daily, keyword):
    """
    指定キーワードの検索数とTVデータを
    日付 × セグメント単位で結合する関数

    ■ 処理概要
    1. 検索データから対象キーワードのみ抽出
    2. 日付型を統一（datetime → date）
    3. 日付 × セグメントでTVデータと内部結合（inner join）
    4. ソートして整形

    ■ 目的
    - TV出稿（視聴率など）と検索数の関係分析

    ■ 前提
    - df_tv：日付 × セグメント粒度で統合済みTVデータ
    - df_search_daily：日付 × キーワード × セグメント粒度の検索データ

    ■ 注意
    - inner joinのため、どちらかに存在しない日付・セグメントは除外される
    - セグメント定義が一致していないとデータが落ちる
    """

    # ----------------------------
    # 指定キーワードの検索データ抽出
    # ----------------------------
    df_search_keyword = df_search_daily[
        df_search_daily["キーワード"] == keyword
    ].copy()

    # ----------------------------
    # 日付型を統一（結合キーのズレ防止）
    # ----------------------------
    df_search_keyword["日付"] = pd.to_datetime(
        df_search_keyword["日付"], errors="coerce"
    ).dt.date

    df_tv["日付"] = pd.to_datetime(
        df_tv["日付"], errors="coerce"
    ).dt.date

    # ----------------------------
    # TVデータ × 検索データを結合
    # ----------------------------
    df_merged = (
        df_tv.merge(
            # 必要なカラムのみ抽出（軽量化）
            df_search_keyword[["日付", "セグメント", "検索数"]],
            on=["日付", "セグメント"],
            how="inner"  # 両方に存在するデータのみ残す
        )
        # 並び順整理
        .sort_values(["日付", "セグメント"])
        # インデックス振り直し
        .reset_index(drop=True)
    )

    return df_merged