#!/usr/bin/env python

from pathlib import PurePath
import pandas as pd

PARENT = PurePath(__file__).parent

URL = 'https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013168605&fileKind=4'
PREFECTURES = PARENT / 'data/prefectures.csv'

def load_population(excel_file):
    df = pd.read_excel(
        excel_file,
        sheet_name=0,
        usecols='C,E:T',
        index_col=0,
        skiprows=list(range(8)) + [9, 10] + list(range(58, 65))
    )

    df.rename(index=lambda x: str(x).replace(' ', ''), inplace=True)
    df.rename(columns=lambda x: f'Y{x}', inplace=True)
    df.index.name = '都道府県名'
    df.columns.name = '年'

    return df

def load_prefectures(csv_file):
    prefs = pd.read_csv(csv_file)
    prefs['都道府県名'] = prefs['都道府県名'].astype(str).str.replace(' ', '', regex=False)
    return prefs


def add_prefectures(pop, prefs):
    df = prefs.merge(
        pop,
        left_on='都道府県名',
        right_index=True,
        how='inner'
    )
    return df


if __name__ == '__main__':
    pop = load_population()
    prefs = add_prefectures(pop)

    print('都道府県:', list(pop.index))
    print(prefs)
    print(prefs.loc[['東京都', '神奈川県']])
    print(prefs.transpose())
