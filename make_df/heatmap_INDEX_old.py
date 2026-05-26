import pandas as pd
import numpy as np

# 放送局の表示順
STATION_ORDER = ["NTV", "TBS", "CX", "EX", "TX"]

# 曜日の表示順
DAY_ORDER = ["月", "火", "水", "木", "金", "土", "日"]

# =========================================================
# 安全な割り算
# - 分母が0のときは inf にする
# - 数値に変換できない値は NaN にする
# =========================================================
def safe_divide_df(numerator_df, denominator_df):
    # 列ごとに数値化し、最後に float にそろえる
    num = numerator_df.apply(pd.to_numeric, errors="coerce").astype(float)
    den = denominator_df.apply(pd.to_numeric, errors="coerce").astype(float)

    with np.errstate(divide="ignore", invalid="ignore"):
        result = num.divide(den)

    # 分母が0で分子に値がある場合は inf
    zero_mask = den.eq(0) & num.notna()
    # result = result.mask(zero_mask, np.inf)
    result = result.mask(zero_mask, 0)

    # -inf は inf に寄せる
    result = result.replace([-np.inf], np.inf)

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

    # np.isinf は ndarray に対して使う
    inf_mask = np.isinf(left.to_numpy()) | np.isinf(right.to_numpy())

    # DataFrame の mask に戻す
    inf_mask_df = pd.DataFrame(
        inf_mask,
        index=left.index,
        columns=left.columns,
    )

    result = result.mask(inf_mask_df, np.inf)
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

        # データがない局は空の DataFrame を入れておく
        if station_df.empty:
            heatmap_map[station] = pd.DataFrame(columns=DAY_ORDER)
            continue

        # 時間帯を index、曜日を列にしたヒートマップ用の形に整形
        pivot_df = (
            station_df[["時間帯"] + DAY_ORDER]
            .sort_values("時間帯")
            .set_index("時間帯")
        )

        # 曜日順を固定
        pivot_df = pivot_df.reindex(columns=DAY_ORDER)
        heatmap_map[station] = pivot_df

    return heatmap_map

# =========================================================
# heatmap map 同士の割り算
# - 放送局ごとに対応する DataFrame を割り算
# - 分母側の index / columns に合わせて整列してから計算
# =========================================================
# heatmap map 同士の割り算
def divide_heatmap_maps(numerator_map, denominator_map):
    result_map = {}

    for station in STATION_ORDER:
        num_df = numerator_map.get(station, pd.DataFrame())
        den_df = denominator_map.get(station, pd.DataFrame())

        # 分母側の形に合わせて分子を整列
        aligned_num = num_df.reindex(index=den_df.index, columns=den_df.columns)

        # 安全な割り算を実行
        ratio_df = safe_divide_df(aligned_num, den_df)

        result_map[station] = ratio_df

    return result_map


# =========================================================
# heatmap map 同士の掛け算
# - 放送局ごとに対応する DataFrame を掛け算
# - map1 側の index / columns に合わせて map2 を整列してから計算
# =========================================================
def multiply_heatmap_maps(map1, map2):
    result_map = {}

    for station in STATION_ORDER:
        df1 = map1.get(station, pd.DataFrame())
        df2 = map2.get(station, pd.DataFrame())

        # map1 側の形に合わせて整列
        aligned_df2 = df2.reindex(index=df1.index, columns=df1.columns)

        # 安全な掛け算を実行
        product_df = multiply_df(df1, aligned_df2)

        result_map[station] = product_df

    return result_map


# =========================================================
# heatmap map → DataFrame
# - {局名: pivot_df} の辞書を縦持ち DataFrame に戻す
# - 指標名も一緒に付与する
# =========================================================
def heatmap_map_to_dataframe(heatmap_map, section_title):
    rows = []

    for station in STATION_ORDER:
        data = heatmap_map.get(station)

        # データがない局はスキップ
        if data is None or data.empty:
            continue

        # 曜日順を固定
        data = data.reindex(columns=DAY_ORDER)

        # 1時間帯ずつレコード化
        for time_label, row in data.iterrows():
            record = {
                "時間帯": time_label,
                "局": station,
                "指標": section_title,
            }

            for day in DAY_ORDER:
                record[day] = row.get(day, np.nan)

            rows.append(record)

    # 1件もなければ空の定型 DataFrame を返す
    if not rows:
        return pd.DataFrame(
            columns=["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "指標"]
        )

    # DataFrame 化
    df_result = pd.DataFrame(rows)

    # 局の並び順を固定
    df_result["局"] = pd.Categorical(
        df_result["局"],
        categories=STATION_ORDER,
        ordered=True
    )

    # 指標 → 局 → 時間帯 の順で並べ替え
    df_result = df_result.sort_values(["指標", "局", "時間帯"]).reset_index(drop=True)

    return df_result


# =========================================================
# df_heatmap_all → INDEX用 DataFrame
# - 元データから必要なヒートマップを作成
# - 指定の5指標を計算
# - 最後に1つの DataFrame に結合して返す
# =========================================================
def make_df_heatmap_index(df_heatmap_all):
    df = df_heatmap_all.copy()

    vr_base_map = make_heatmap_map_from_df(df, "VR", "個人全体")
    vr_target_map = make_heatmap_map_from_df(df, "VR", "ターゲット")
    tval_base_map = make_heatmap_map_from_df(df, "TVAL", "個人全体")
    tval_target_map = make_heatmap_map_from_df(df, "TVAL", "ターゲット")
    revisio_base_map = make_heatmap_map_from_df(df, "REVISIO", "個人全体")

    df_list = []

    # 1. TVAL（ターゲット）÷ VR（個人全体/世帯）
    ratio_1 = divide_heatmap_maps(tval_target_map, vr_base_map)
    df_list.append(
        heatmap_map_to_dataframe(
            ratio_1,
            "TVAL（ターゲット）÷ VR（個人全体/世帯）"
        )
    )

    # 2. REVISIO（個人全体）÷ VR（個人全体/世帯）
    ratio_2 = divide_heatmap_maps(revisio_base_map, vr_base_map)
    df_list.append(
        heatmap_map_to_dataframe(
            ratio_2,
            "REVISIO（個人全体）÷ VR（個人全体/世帯）"
        )
    )

    # 3. ［TVAL（ターゲット）× REVISIO（個人全体）］÷ VR（個人全体/世帯）
    product_3 = multiply_heatmap_maps(tval_target_map, revisio_base_map)
    ratio_3 = divide_heatmap_maps(product_3, vr_base_map)
    df_list.append(
        heatmap_map_to_dataframe(
            ratio_3,
            "［TVAL（ターゲット）× REVISIO（個人全体）］÷ VR（個人全体/世帯）"
        )
    )

    # 4. VR（ターゲット）÷ VR（個人全体/世帯）
    ratio_4 = divide_heatmap_maps(vr_target_map, vr_base_map)
    df_list.append(
        heatmap_map_to_dataframe(
            ratio_4,
            "VR（ターゲット）÷ VR（個人全体/世帯）"
        )
    )

    # 5. TVAL（ターゲット）÷ TVAL（個人全体/世帯）
    ratio_5 = divide_heatmap_maps(tval_target_map, tval_base_map)
    df_list.append(
        heatmap_map_to_dataframe(
            ratio_5,
            "TVAL（ターゲット）÷ TVAL（個人全体/世帯）"
        )
    )

    df_list = [x for x in df_list if x is not None and not x.empty]

    if not df_list:
        return pd.DataFrame(
            columns=["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "指標"]
        )

    df_index = pd.concat(df_list, ignore_index=True)
    df_index = df_index[["時間帯", "月", "火", "水", "木", "金", "土", "日", "局", "指標"]]

    return df_index