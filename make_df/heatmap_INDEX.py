import pandas as pd
import numpy as np

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# 曜日の表示順
DAY_ORDER = ["月", "火", "水", "木", "金", "土", "日"]

# 出力列
OUTPUT_COLUMNS = ["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "指標"]


# =========================================================
# 空データ判定
# - 空DataFrame
# - 全セルNaNのDataFrame
# を「使えないデータ」として扱う
# =========================================================
def is_empty_or_all_nan(df):
    if df is None or df.empty:
        return True

    return df.isna().all().all()


# # =========================================================
# # 安全な割り算
# # - 分母が0のときは 0 にする
# # - 数値に変換できない値は NaN にする
# # =========================================================
# def safe_divide_df(numerator_df, denominator_df):
#     # 列ごとに数値化し、最後に float にそろえる
#     num = numerator_df.apply(pd.to_numeric, errors="coerce").astype(float)
#     den = denominator_df.apply(pd.to_numeric, errors="coerce").astype(float)

#     with np.errstate(divide="ignore", invalid="ignore"):
#         result = num.divide(den)

#     # 分母が0で分子に値がある場合は 0
#     zero_mask = den.eq(0) & num.notna()
#     result = result.mask(zero_mask, 0)

#     # -inf は inf に寄せる
#     result = result.replace([-np.inf], np.inf)

#     return result

# =========================================================
# 安全な割り算
# - 分母が0のときは -inf にする
#   → 数値型を維持しつつ、WORST 1位として扱える
# - 表示時だけ "-" に変換する
# =========================================================
def safe_divide_df(numerator_df, denominator_df):
    num = numerator_df.apply(pd.to_numeric, errors="coerce").astype(float)
    den = denominator_df.apply(pd.to_numeric, errors="coerce").astype(float)

    with np.errstate(divide="ignore", invalid="ignore"):
        result = num.divide(den)

    # 分母が0の場合は -inf
    # → nsmallest / WORST判定で最小値として扱われる
    zero_mask = den.eq(0) & num.notna()
    result = result.mask(zero_mask, -np.inf)

    return result


# =========================================================
# 掛け算
# - 数値変換してから DataFrame 同士を掛け算する
# - inf を含む場合は結果も inf にする
# =========================================================
def multiply_df(df1, df2):
    # 列ごとに数値化し、最後に float にそろえる
    left = df1.apply(pd.to_numeric, errors="coerce").astype(float)
    right = df2.apply(pd.to_numeric, errors="coerce").astype(float)

    with np.errstate(invalid="ignore"):
        result = left.multiply(right)

    # どちらかに inf が含まれるセルは inf にする
    inf_mask = np.isinf(left.to_numpy()) | np.isinf(right.to_numpy())

    inf_mask_df = pd.DataFrame(
        inf_mask,
        index=left.index,
        columns=left.columns,
    )

    result = result.mask(inf_mask_df, np.inf)

    # -inf は inf に寄せる
    result = result.replace([-np.inf], np.inf)

    return result


# =========================================================
# df_heatmap_all から heatmap map を作成
# - 指定したデータ種別 × カテゴリー のデータだけ抽出
# - 放送局ごとに 時間帯 × 曜日 のピボット形式にする
# - 戻り値は {局名: pivot_df} の辞書
# =========================================================
def make_heatmap_map_from_df(df, data_type, category):
    # 対象データのみ抽出
    sub = df[
        (df["データ種別"] == data_type) &
        (df["カテゴリー"] == category)
    ].copy()

    heatmap_map = {}

    # 放送局ごとに pivot を作成
    for station in STATION_ORDER:
        station_df = sub[sub["局"] == station].copy()

        # データがない局は空のDataFrameを入れる
        if station_df.empty:
            heatmap_map[station] = pd.DataFrame()
            continue

        # 時間帯を index、曜日を列にしたヒートマップ用の形に整形
        pivot_df = (
            station_df[["時間帯"] + DAY_ORDER]
            .sort_values("時間帯")
            .set_index("時間帯")
        )

        # 曜日順を固定
        pivot_df = pivot_df.reindex(columns=DAY_ORDER)

        # 全部NaNなら空扱いにする
        if is_empty_or_all_nan(pivot_df):
            heatmap_map[station] = pd.DataFrame()
        else:
            heatmap_map[station] = pivot_df

    return heatmap_map


# =========================================================
# heatmap map 同士の割り算
# - 放送局ごとに対応する DataFrame を割り算
# - 分母側の index / columns に合わせて整列してから計算
# - 分子または分母がない場合は計算しない
# =========================================================
def divide_heatmap_maps(numerator_map, denominator_map):
    result_map = {}

    for station in STATION_ORDER:
        num_df = numerator_map.get(station, pd.DataFrame())
        den_df = denominator_map.get(station, pd.DataFrame())

        # 分子または分母が空なら計算しない
        if is_empty_or_all_nan(num_df) or is_empty_or_all_nan(den_df):
            result_map[station] = pd.DataFrame()
            continue

        # 分母側の形に合わせて分子を整列
        aligned_num = num_df.reindex(
            index=den_df.index,
            columns=den_df.columns,
        )

        # 安全な割り算を実行
        ratio_df = safe_divide_df(aligned_num, den_df)

        # 計算結果が全部NaNなら空扱い
        if is_empty_or_all_nan(ratio_df):
            result_map[station] = pd.DataFrame()
        else:
            result_map[station] = ratio_df

    return result_map


# =========================================================
# heatmap map 同士の掛け算
# - 放送局ごとに対応する DataFrame を掛け算
# - map1 側の index / columns に合わせて map2 を整列してから計算
# - どちらかがない場合は計算しない
# =========================================================
def multiply_heatmap_maps(map1, map2):
    result_map = {}

    for station in STATION_ORDER:
        df1 = map1.get(station, pd.DataFrame())
        df2 = map2.get(station, pd.DataFrame())

        # どちらかが空なら計算しない
        if is_empty_or_all_nan(df1) or is_empty_or_all_nan(df2):
            result_map[station] = pd.DataFrame()
            continue

        # map1 側の形に合わせて map2 を整列
        aligned_df2 = df2.reindex(
            index=df1.index,
            columns=df1.columns,
        )

        # 掛け算を実行
        product_df = multiply_df(df1, aligned_df2)

        # 計算結果が全部NaNなら空扱い
        if is_empty_or_all_nan(product_df):
            result_map[station] = pd.DataFrame()
        else:
            result_map[station] = product_df

    return result_map


# =========================================================
# heatmap map → DataFrame
# - {局名: pivot_df} の辞書を縦持ち DataFrame に戻す
# - 指標名も一緒に付与する
# - 全曜日NaNの時間帯はレコード化しない
# =========================================================
def heatmap_map_to_dataframe(heatmap_map, section_title):
    rows = []

    for station in STATION_ORDER:
        data = heatmap_map.get(station)

        # データがない局はスキップ
        if is_empty_or_all_nan(data):
            continue

        # 曜日順を固定
        data = data.reindex(columns=DAY_ORDER)

        # 1時間帯ずつレコード化
        for time_label, row in data.iterrows():

            # 月〜日が全部NaNならスキップ
            if row[DAY_ORDER].isna().all():
                continue

            record = {
                "時間帯": time_label,
                "局": station,
                "指標": section_title,
            }

            for day in DAY_ORDER:
                record[day] = row.get(day, np.nan)

            rows.append(record)

    # 1件もなければ空の定型DataFrameを返す
    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # DataFrame化
    df_result = pd.DataFrame(rows)

    # 局の並び順を固定
    df_result["局"] = pd.Categorical(
        df_result["局"],
        categories=STATION_ORDER,
        ordered=True,
    )

    # 指標 → 局 → 時間帯 の順で並べ替え
    df_result = df_result.sort_values(
        ["指標", "局", "時間帯"]
    ).reset_index(drop=True)

    # 列順を固定
    df_result = df_result[OUTPUT_COLUMNS]

    return df_result


# =========================================================
# df_heatmap_all → INDEX用 DataFrame
# - 元データから必要なヒートマップを作成
# - 指定の5指標を計算
# - 必要データがない指標は作成しない
# - 最後に1つのDataFrameに結合して返す
# =========================================================
def make_df_heatmap_index(df_heatmap_all):
    df = df_heatmap_all.copy()

    # 元データから map を作成
    vr_base_map = make_heatmap_map_from_df(df, "VR", "個人全体")
    vr_target_map = make_heatmap_map_from_df(df, "VR", "ターゲット")
    tval_base_map = make_heatmap_map_from_df(df, "TVAL", "個人全体")
    tval_target_map = make_heatmap_map_from_df(df, "TVAL", "ターゲット")
    revisio_attention_map = make_heatmap_map_from_df(df, "REVISIO", "注視")
    revisio_stay_map = make_heatmap_map_from_df(df, "REVISIO", "滞在")
    revisio_household_map = make_heatmap_map_from_df(df, "REVISIO", "世帯")
    revisio_tval_attention_map = make_heatmap_map_from_df(df, "TVAL×REVISIO補正", "注視補正")
    revisio_tval_stay_map = make_heatmap_map_from_df(df, "TVAL×REVISIO補正", "滞在補正")

    df_list = []

    # =====================================================
    # 1. TVAL（ターゲット）÷ VR（個人全体/世帯）
    # =====================================================
    ratio_1 = divide_heatmap_maps(tval_target_map, vr_base_map)

    df_1 = heatmap_map_to_dataframe(
        ratio_1,
        "TVAL（ターゲット）÷ VR（個人全体/世帯）",
    )

    if not df_1.empty:
        df_list.append(df_1)

    # =====================================================
    # 2. VR（ターゲット）÷ VR（個人全体/世帯）
    # =====================================================
    ratio_2 = divide_heatmap_maps(vr_target_map, vr_base_map)

    df_2 = heatmap_map_to_dataframe(
        ratio_2,
        "VR（ターゲット）÷ VR（個人全体/世帯）",
    )

    if not df_2.empty:
        df_list.append(df_2)

    # =====================================================
    # 3. TVAL（ターゲット）÷ TVAL（個人全体/世帯）
    # =====================================================
    ratio_3 = divide_heatmap_maps(tval_target_map, tval_base_map)

    df_3 = heatmap_map_to_dataframe(
        ratio_3,
        "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
    )

    if not df_3.empty:
        df_list.append(df_3)
        
    # =====================================================
    # 4. REVISIO（注視）÷ REVISIO（世帯）
    # =====================================================
    ratio_4 = divide_heatmap_maps(revisio_attention_map, revisio_household_map)

    df_4 = heatmap_map_to_dataframe(
        ratio_4,
        "REVISIO（注視）÷ REVISIO（世帯）",
    )

    if not df_4.empty:
        df_list.append(df_4)
        
    # =====================================================
    # 5. REVISIO（滞在）÷ REVISIO（世帯）
    # =====================================================
    ratio_5 = divide_heatmap_maps(revisio_stay_map, revisio_household_map)

    df_5 = heatmap_map_to_dataframe(
        ratio_5,
        "REVISIO（滞在）÷ REVISIO（世帯）",
    )

    if not df_5.empty:
        df_list.append(df_5)
        
    # =====================================================
    # 6. REVISIO（注視）÷ VR（個人全体/世帯）
    # =====================================================
    ratio_6 = divide_heatmap_maps(revisio_attention_map, vr_base_map)

    df_6 = heatmap_map_to_dataframe(
        ratio_6,
        "REVISIO（注視）÷ VR（個人全体/世帯）",
    )

    if not df_6.empty:
        df_list.append(df_6)
        
    # =====================================================
    # 7. REVISIO（滞在）÷ VR（個人全体/世帯）
    # =====================================================
    ratio_7 = divide_heatmap_maps(revisio_stay_map, vr_base_map)

    df_7 = heatmap_map_to_dataframe(
        ratio_7,
        "REVISIO（滞在）÷ VR（個人全体/世帯）",
    )

    if not df_7.empty:
        df_list.append(df_7)
        
    # =====================================================
    # 8. TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）
    # =====================================================
    ratio_8 = divide_heatmap_maps(revisio_tval_attention_map, vr_base_map)

    df_8 = heatmap_map_to_dataframe(
        ratio_8,
        "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
    )

    if not df_8.empty:
        df_list.append(df_8)
        
    # =====================================================
    # 9. TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）
    # =====================================================
    ratio_9 = divide_heatmap_maps(revisio_tval_stay_map, vr_base_map)

    df_9 = heatmap_map_to_dataframe(
        ratio_9,
        "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）",
    )

    if not df_9.empty:
        df_list.append(df_9)

    # 作成できるINDEXが1つもない場合
    if not df_list:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # 作成できたINDEXだけ結合
    df_index = pd.concat(df_list, ignore_index=True)

    # 列順を固定
    df_index = df_index[OUTPUT_COLUMNS]

    return df_index