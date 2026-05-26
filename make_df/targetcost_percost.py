import pandas as pd

ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]

def make_df_percost(file):
    """
    Excelからパーコスト表を読み込み、
    局 × ゾーン × パーコスト の縦持ちDataFrameに整形して返す
    """

    # Excel読み込み
    df_percost = pd.read_excel(file)

    # 1列目を局名として使う想定
    df_percost = df_percost.rename(columns={df_percost.columns[0]: "局"})

    # 縦持ちに変換
    df_percost = df_percost.melt(
        id_vars="局",
        value_vars=ZONE_NAMES,
        var_name="ゾーン",
        value_name="パーコスト",
    )

    return df_percost