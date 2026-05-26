# ライブラリの読み込み
import streamlit as st
import numpy as np
import pandas as pd
import io
import re
import openpyxl
from datetime import datetime, time, timedelta
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go

# 自作関数の読み込み
from other.component import make_upload_box # 各種ファイルアップロード用関数
from other.component import get_uploaded_file_obj 

from make_df.heatmap_VR import make_df_heatmap_VR # ヒートマップVRローデータの整形用の関数
from make_df.heatmap_TVAL import make_df_heatmap_TVAL # ヒートマップTVALローデータの整形用の関数
from make_df.heatmap_REVISIO import make_df_heatmap_REVISIO # ヒートマップREVISIOローデータの整形用の関数
from make_df.heatmap_merge import make_df_heatmap_all # ヒートマップデータ結合用関数
from make_df.search_VR import get_daily_vr_rating # VR日別視聴率ローデータの整形用の関数
from make_df.search_TVAL import get_daily_tval_rating # TVAL日別視聴率ローデータの整形用の関数
from make_df.search_REVISIO import get_daily_revisio_rating # REVISIO日別視聴率ローデータの整形用の関数
from make_df.search_DSInsight import get_daily_search # DS.Insight日別検索数ローデータの整形用の関数
from make_df.search_merge_TV import merge_tv_data # 日別視聴率ローデータのTVデータ結合用の関数
from make_df.search_merge_all import merge_tv_search_for_keyword # 日別視聴率TV結合データと検索数の結合用の関数
from make_df.targetcost_percost import make_df_percost # ターゲットコストで使用するのパーコストデータ整形用の関数

import make_df.heatmap_INDEX # ヒートマップのINDEX算出用の関数
import heatmap.heatmap # ヒートマップ可視化用の関数

import zone.zone_tab
import wish.wish_tab
import area_per_cost.area_per_cost
import reach.reach
import frequency.frequency

####################################################################################################################################################
# =========================
# 画面全体の基本設定
# =========================
# アプリのページ設定（タイトル・レイアウト）
# layout="wide" にすることで横幅を最大限使用（ヒートマップなど横長UIに最適）
st.set_page_config(page_title="MIMツール", layout="wide")

# アプリタイトル表示
st.title("MIMツール")

# =========================
# 定数定義
# =========================

# 曜日順（ヒートマップや並び順制御で使用）
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# ゾーン名一覧（UIのフィルターやラジオボタンで使用）
ZONE_NAMES = ["全日", "ヨの字", "コの字", "逆L", "ATT"]

####################################################################################################################################################

# =========================================================
# メニュー選択
# =========================================================
user_select = st.selectbox("項目を選択してください", 
                         ["📅ゾーン・枠",
                          "📍エリア平均パーコスト",
                          "🔍視聴率×検索数",
                          "👥リーチ・FQ",
                          ])

# =========================================================
# 📅ゾーン・枠
# =========================================================
if user_select == "📅ゾーン・枠":
    
    # タブ構成
    tab_upload, tab_zone, tab_heatmap_rating, tab_heatmap_index, tab_wish_rating, tab_wish_index, tab_wish_mix, tab_target_cost, tab_station_compare = st.tabs(
        [
            "📁データアップロード", 
            "⏰ゾーン指定", 
            "📊ヒートマップ｜視聴率", 
            "📊ヒートマップ｜INDEX", 
            "📊希望枠｜視聴率", 
            "📊希望枠｜INDEX", 
            "📊希望枠｜視聴率×INDEX", 
            "💰ターゲットコスト", 
            "📅局比較"
         ])
    
    # =========================================================
    # 📁データアップロード
    # =========================================================
    with tab_upload:
        
        with st.container(border=True):
            
            st.error(
                """
                ⚠️ブラウザをリロードするとリセットされます  
                ⚠️リロードされなければアップロードデータや各種設定は維持されますが、セッションが切れるとエラーが表示されます  
                ⚠️一度アップロードしたファイルを削除する場合は、「削除」ボタンを押してリセットしてください（置き換える場合は再度アップロードで差し替わります）
                """,
                icon=None
            )
            
            st.error(
                """
                ⚠️REVISIOのデータは、REVISIO社直契約クライアントへの提案は契約違反となります  
                ⚠️REVISIOデータを用いた提案を行う際は、必ず提案前に銘柄をMADへ連絡し提案可否を確認してください  
                """,
                icon=None
            )
            
            st.warning(
                """
                📁パーコストデータのフォーマット格納先  
                http://box・・・・・・・
                """,
                icon=None
            )

            top_cols = st.columns(6)

            with top_cols[0]:
                make_upload_box(
                    title = "VR（個人全体/世帯）",
                    info_message = "Rating-Navi@WEB時間帯視聴率分析",
                    warning_message = None,
                    error_message = "⚠️シートが複数抽出されるため、不要シートを削除し、該当シートのみにしてからアップロードしてください",
                    key = "vr_all_file",
                    allowed_types = ["xlsx", "xlsm"]
                )

            with top_cols[1]:
                make_upload_box(
                    title = "VR（ターゲット）",
                    info_message = "Rating-Navi@WEB時間帯視聴率分析",
                    warning_message = None,
                    error_message = "⚠️シートが複数抽出されるため、不要シートを削除し、該当シートのみにしてからアップロードしてください",
                    key = "vr_target_file",
                    allowed_types = ["xlsx", "xlsm"]
                )

            with top_cols[2]:
                make_upload_box(
                    title = "TVAL（個人全体/世帯）",
                    info_message = "TVAL>TVデータサーチ>ターゲットヒートマップ",
                    warning_message = None,
                    error_message = None,
                    key = "tval_all_file",
                    allowed_types = ["csv", "xlsx", "xlsm"]
                )

            with top_cols[3]:
                make_upload_box(
                    title = "TVAL（ターゲット）",
                    info_message = "TVAL>TVデータサーチ>ターゲットヒートマップ",
                    warning_message = None,
                    error_message = None,
                    key = "tval_target_file",
                    allowed_types = ["csv", "xlsx", "xlsm"]
                )
                
            with top_cols[4]:
                make_upload_box(
                    title = "REVISIO（注視・滞在・世帯）",
                    info_message = "REVISIO One＞【アップデート版】地上派レビュー（ユニークリーチ＆フリークエンシーあり）＞各局ヒートマップ（アクション指標）",
                    warning_message = None,
                    error_message = "⚠️絵柄選択を「1曜日×1選択」にしてください",
                    key = "revisio_file",
                    allowed_types = ["csv", "xlsx", "xlsm"]
                )
            
            with top_cols[5]:
                make_upload_box(
                    title = "パーコストデータ",
                    info_message = None,
                    warning_message = "指定フォーマットへ入力",
                    error_message = None,
                    key = "per_cost_file",
                    allowed_types = ["xlsx", "xlsm"],
            )
  
    # =========================================================
    # ⏰ゾーン指定
    # =========================================================                 
    with tab_zone:
        # ゾーン設定画面
        # - 各ゾーン（全日 / ヨの字 / コの字 / 逆L / ATT）について、「曜日 × 時間帯」のON / OFFを設定する

        # zone_state 初期化
        # - zone_filters（確定版）
        # - zone_drafts（編集中）
        # - resetフラグ
        # を初回のみ作成する
        zone.zone_tab.init_zone_state()

        # ゾーン設定時の注意書き
        st.info(
            """
            ⚠️デフォルト設定は下記の通りです。変更する場合は、✅をON/OFFしてご自身でゾーン設定を行ってください  
            ⚠️変更後は、ページ下部の「ゾーンを反映」ボタンを押してから各ページへ進んでください
            
            全日：全曜日 05:00-26:00  
            ヨの字：平日 05:00-08:00 / 12:00-13:00 / 19:00-26:00、土日 05:00-26:00  
            コの字：平日 05:00-08:00 / 19:00-26:00、土日 05:00-26:00  
            逆L：平日 19:00-26:00、土日 05:00-26:00  
            ATT：全時間帯（編集不可）  
             """
        )

        # checkbox 表示用CSS
        # - checkboxの余白削減
        # - 中央寄せ
        # - テキスト非表示
        # - ヒートマップ風のコンパクトUIに調整
        st.markdown(
            """
            <style>
            /* チェックボックス全体の余白削除・中央寄せ */
            [class*="st-key-zone_chk_"] div[data-testid="stCheckbox"] {
                margin: 0 !important;
                padding: 0 !important;
                display: flex;
                justify-content: center;
            }

            /* ラベル領域の高さ・余白を最小化 */
            [class*="st-key-zone_chk_"] label {
                padding: 0 !important;
                min-height: 1.15rem !important;
            }

            /* チェックボックス横のテキスト非表示 */
            [class*="st-key-zone_chk_"] div[data-testid="stCheckbox"] p {
                display: none !important;
            }

            /* form枠の余白・枠線削除（fragment使用のため念のため） */
            div[data-testid="stForm"] {
                border: none !important;
                padding: 0 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ゾーンUI描画
        # - 各ゾーンを横並び表示
        zone_cols = st.columns(len(ZONE_NAMES), gap="small")

        # 各ゾーン描画
        for zone_name, container in zip(ZONE_NAMES, zone_cols):
            with container:
                with st.container(border=True):
                    # ゾーン単位UI描画
                    # - ゾーン名
                    # - checkbox表
                    # - 初期化ボタン
                    # fragment化されているため、初期化時などはそのゾーンのみ再描画される
                    zone.zone_tab.render_single_zone_fragment(zone_name)

        # 全ゾーン一括反映
        # - checkbox状態を正式データへ保存する
        
        # 中央寄せ用3カラム
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            # ゾーン反映ボタン
            if st.button("ゾーンを反映", 
                         key="apply_all_zone_filters", 
                         use_container_width=True):
                
                # 編集内容を正式反映
                zone.zone_tab.apply_all_zone_filters()
                
                # 完了メッセージ
                st.success("ゾーンを反映しました。")


        # デバッグ用：zone_filters確認
        # 各ゾーンの最終的なON/OFF状態をDataFrameで確認
        # 本番では不要なため、後で削除予定
        st.markdown("### zone_filters 確認 ※開発用（後に削除）")

        with st.expander("zone_filters 確認", expanded=False):
            for zone_name in ZONE_NAMES:
                st.markdown(f"#### {zone_name}")

                st.dataframe(
                    st.session_state["zone_filters"][zone_name],
                    use_container_width=True,
                )
                
    # =========================================================
    # session_stateに保存したファイルを復元する関数 
    # ========================================================= 
    vr_all_file = get_uploaded_file_obj("vr_all_file")
    vr_target_file = get_uploaded_file_obj("vr_target_file")
    tval_all_file = get_uploaded_file_obj("tval_all_file")
    tval_target_file = get_uploaded_file_obj("tval_target_file")
    revisio_file = get_uploaded_file_obj("revisio_file")

    # 各ファイルの有無を判定
    has_vr_all = vr_all_file is not None
    has_vr_target = vr_target_file is not None
    has_tval_all = tval_all_file is not None
    has_tval_target = tval_target_file is not None
    has_revisio = revisio_file is not None

    # 変数の宣言（※これをしないとエラーが起きる）
    df_heatmap_all = None
    df_heatmap_index = None
                
    # =========================================================
    # 📊ヒートマップ｜視聴率
    # =========================================================     
    with tab_heatmap_rating:

        # 必要データがなければ処理しない
        if not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):
            st.info("先に『アップロード』タブで視聴率ヒートマップ対象データをアップロードしてください。")

        # いずれかのファイルがある場合は可視化処理を実行
        else:
            try:
                # ヒートマップ描画用の統合データを作成（各アップロードファイルを整形・結合してヒートマップ表示用のDataFrameを生成する）
                df_heatmap_all = make_df_heatmap_all(
                    vr_all_file,
                    vr_target_file,
                    tval_all_file,
                    tval_target_file,
                    revisio_file
                )

                with st.expander("使用データ"):
                    # 生成した元データを確認用に表示
                    st.dataframe(df_heatmap_all, use_container_width=True)

                # 視聴率ヒートマップを描画
                heatmap.heatmap.render_rating_heatmap_from_df(
                    df=df_heatmap_all,
                    vr_all_file=vr_all_file,
                    vr_target_file=vr_target_file,
                    tval_all_file=tval_all_file,
                    tval_target_file=tval_target_file,
                    revisio_file=revisio_file
                    )

            except Exception as e:
                # # エラー時のメッセージ表示
                st.error(f"処理中にエラーが発生: {e}")
     
    # =========================================================
    # 📊ヒートマップ｜INDEX
    # =========================================================              
    with tab_heatmap_index:

        # INDEXヒートマップ表示前チェック（元になるdf_heatmap_allが必要）
        if not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):
            st.info("先に『アップロード』タブでINDEXヒートマップ対象データをアップロードしてください。")

        else:
            try:
                # df_heatmap_allが未作成ならここで生成（tab_heatmap_ratingを開いていなくてもtab_heatmap_index単独で動くようにする）
                if df_heatmap_all is None:
                    df_heatmap_all = make_df_heatmap_all(
                        vr_all_file,
                        vr_target_file,
                        tval_all_file,
                        tval_target_file,
                        revisio_file,
                    )

                # INDEXヒートマップ用 DataFrame を生成（df_heatmap_allをもとにINDEX指標を作成）
                df_heatmap_index = make_df.heatmap_INDEX.make_df_heatmap_index(df_heatmap_all)

                # 生成した元データを確認用に表示
                if not df_heatmap_index.empty:
                    with st.expander("使用データ"):
                        st.dataframe(df_heatmap_index, use_container_width=True)

                # INDEXヒートマップを描画
                heatmap.heatmap.render_index_heatmap_from_df(
                    df_index=df_heatmap_index,
                    vr_all_file=vr_all_file,
                    vr_target_file=vr_target_file,
                    tval_all_file=tval_all_file,
                    tval_target_file=tval_target_file,
                    revisio_file=revisio_file,
                )

            except Exception as e:
                # エラー時のメッセージ表示
                st.error(f"処理中にエラーが発生: {e}")
                
    # =========================================================
    # 📊希望枠｜視聴率
    # =========================================================
    with tab_wish_rating:

        # ファイルが1つもない場合
        if not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):
            st.info("先に『アップロード』タブで視聴率ヒートマップ対象データをアップロードしてください。")

        # いずれかのファイルがある場合は可視化処理を実行
        else:
            try:
                # =================================================
                # df_heatmap_all が未作成ならここで生成
                # =================================================
                if df_heatmap_all is None:

                    df_heatmap_all = make_df_heatmap_all(
                        vr_all_file,
                        vr_target_file,
                        tval_all_file,
                        tval_target_file,
                        revisio_file,
                    )

                # =================================================
                # zone_tab 側の session_state を初期化
                # =================================================
                wish.wish_tab.init_zone_state()

                # =================================================
                # 元データがない場合は終了
                # =================================================
                if df_heatmap_all is None or df_heatmap_all.empty:

                    st.info("希望枠用データがありません。")
                    
                else:
                    # =================================================
                    # 共通コントロール
                    # =================================================
                    selected_zone, top_rate, worst_rate = wish.wish_tab.render_shared_wish_controls("wish")
                
                    # =================================================
                    # 表示用セクション列を追加
                    # =================================================
                    df = wish.wish_tab.add_rating_section_col(df_heatmap_all)

                    # セクションが付与された行だけ残す
                    df = df[df["セクション"].notna()].copy()

                    # =================================================
                    # 実際に存在するセクションだけ抽出
                    # =================================================
                    available_sections = df["セクション"].dropna().unique().tolist()

                    # =================================================
                    # 表示順の基準
                    # =================================================
                    section_master = [
                        "VR（個人全体/世帯）",
                        "VR（ターゲット）",
                        "TVAL（個人全体/世帯）",
                        "TVAL（ターゲット）",
                        "REVISIO（個人全体/世帯）",
                        "REVISIO（注視）",
                        "REVISIO（滞在）",
                        "REVISIO（世帯）",
                        "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
                        "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]"
                    ]

                    # =================================================
                    # 存在するセクションだけ表示順に並べる
                    # =================================================
                    section_order = [
                        s for s in section_master
                        if s in available_sections
                    ]

                    # =================================================
                    # セグメント絞り込みフィルター
                    # =================================================
                    section_order = wish.wish_tab.build_segment_filter(
                        section_order=section_order,
                        prefix="wish_rating",
                    )

                    # =================================================
                    # 表示可能セクションがなければ終了
                    # =================================================
                    if section_order:
                        
                        # =================================================
                        # 反映済みゾーン設定を取得
                        # =================================================
                        zone_df = wish.wish_tab.get_wish_zone_df(selected_zone)

                        # =================================================
                        # ページ全体CSV用の縦持ちデータを作成
                        # =================================================
                        all_wish_df = wish.wish_tab.build_all_wish_frames_long(
                            df=df,
                            section_order=section_order,
                            top_rate=top_rate,
                            worst_rate=worst_rate,
                            zone_df=zone_df,
                        )

                        # =================================================
                        # 出力条件もCSVに付与
                        # =================================================
                        all_wish_df["対象ゾーン"] = selected_zone
                        all_wish_df["TOP割合"] = top_rate
                        all_wish_df["WORST割合"] = worst_rate

                        # =================================================
                        # 使用データ表示
                        # =================================================
                        with st.expander("使用データ", expanded=False):

                            st.dataframe(
                                all_wish_df,
                                use_container_width=True,
                            )

                        # =================================================
                        # ページ全体CSVダウンロード
                        # =================================================
                        st.download_button(
                            label="ページ全体CSV",
                            data=wish.wish_tab.dataframe_to_csv_bytes(all_wish_df),
                            file_name=f"wish_all_{selected_zone}.csv",
                            mime="text/csv",
                            key="wish_csv_all",
                            use_container_width=False,
                            on_click="ignore",
                        )
                
                        # =================================================
                        # 凡例表示
                        # =================================================
                        wish.wish_tab.render_simple_wish_legend(
                            wish_text="希望枠：TOP割合に入る枠",
                            normal_text="普通枠：TOP / WORSTのどちらにも該当しない枠",
                            reject_text="拒否枠：WORST割合に入る枠",
                        )

                        st.markdown("---")

                        # =================================================
                        # セクションごとに希望枠を描画
                        # =================================================
                        for i, section_title in enumerate(section_order):

                            wish.wish_tab.render_wish_row(
                                section_title=section_title,
                                df=df,
                                top_rate=top_rate,
                                worst_rate=worst_rate,
                                zone_df=zone_df,
                                file_name_builder=lambda sec, station: f"{sec}_{station}_wish.csv",
                            )

                            # セクション間の区切り線
                            if i < len(section_order) - 1:

                                st.markdown("---")

            except Exception as e:

                st.error(f"処理中にエラーが発生: {e}")


    # =========================================================
    # 📊希望枠｜INDEX
    # =========================================================
    with tab_wish_index:
        # INDEX希望枠表示前チェック（元になるdf_heatmap_allが必要）
        if not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):
            st.info("先に『アップロード』タブでINDEXヒートマップ対象データをアップロードしてください。")
            
        else:
            try:
                # =========================================================
                # INDEX用希望枠タブ
                # =========================================================
                zone.zone_tab.init_zone_state()

                # =========================================================
                # INDEX用データがない場合は終了
                # =========================================================
                if df_heatmap_index is None or df_heatmap_index.empty:

                    st.info("INDEX希望枠用データがありません。")
                    
                else:
                    # =================================================
                    # 共通コントロール
                    # =================================================
                    selected_zone, top_rate, worst_rate = wish.wish_tab.render_shared_wish_controls("wish_index")
                    
                    # =====================================================
                    # df_heatmap_index に存在する指標一覧を取得
                    # =====================================================
                    available_sections = df_heatmap_index["指標"].dropna().unique().tolist()

                    # =====================================================
                    # 表示順の基準
                    # =====================================================
                    section_master = []

                    # 1. TVAL（ターゲット）÷ VR（個人全体/世帯）
                    if vr_all_file is not None and tval_target_file is not None:
                        section_master.append("TVAL（ターゲット）÷ VR（個人全体/世帯）")
                        
                    # 2. VR（ターゲット）÷ VR（個人全体/世帯）
                    if vr_all_file is not None and vr_target_file is not None:
                        section_master.append("VR（ターゲット）÷ VR（個人全体/世帯）")
                        
                    # 3. TVAL（ターゲット）÷ TVAL（個人全体/世帯）
                    if tval_all_file is not None and tval_target_file is not None:
                        section_master.append("TVAL（ターゲット）÷ TVAL（個人全体/世帯）")
                        
                    # 4. REVISIO（注視）÷ REVISIO（世帯）
                    if revisio_file is not None:
                        section_master.append("REVISIO（注視）÷ REVISIO（世帯）")
                        
                    # 5. REVISIO（滞在）÷ REVISIO（世帯）
                    if revisio_file is not None:
                        section_master.append("REVISIO（滞在）÷ REVISIO（世帯）")
                        
                    # 6. REVISIO（注視）÷ VR（個人全体/世帯）
                    if revisio_file is not None and vr_all_file is not None:
                        section_master.append("REVISIO（注視）÷ VR（個人全体/世帯）")
                        
                    # 7. REVISIO（滞在）÷ VR（個人全体/世帯）
                    if revisio_file is not None and vr_all_file is not None:
                        section_master.append("REVISIO（滞在）÷ VR（個人全体/世帯）")

                    # 8. TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）
                    if tval_target_file is not None and revisio_file is not None and vr_all_file is not None:
                        section_master.append("TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）")

                    # 9. TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）
                    if tval_target_file is not None and revisio_file is not None and vr_all_file is not None:
                        section_master.append("TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）")
                        
                    # =====================================================
                    # 実際に存在する指標だけ表示順に並べる
                    # =====================================================
                    section_order = [
                        s for s in section_master
                        if s in available_sections
                    ]

                    # =====================================================
                    # セグメント絞り込みフィルター
                    # =====================================================
                    section_order = wish.wish_tab.build_segment_filter(
                        section_order=section_order,
                        prefix="wish_index",
                    )
                    
                    # =====================================================
                    # 表示可能な指標がない場合は終了
                    # =====================================================
                    if section_order:

                        # =================================================
                        # 反映済みゾーン設定を取得
                        # =================================================
                        zone_df = wish.wish_tab.get_wish_zone_df(selected_zone)
                        
                        # =================================================
                        # ページ全体CSV用の縦持ちデータを作成
                        # =================================================
                        all_wish_df = wish.wish_tab.build_all_wish_frames_long_index(
                            df=df_heatmap_index,
                            section_order=section_order,
                            top_rate=top_rate,
                            worst_rate=worst_rate,
                            zone_df=zone_df,
                        )
                        
                        # =================================================
                        # 出力条件もCSVに付与
                        # =================================================
                        all_wish_df["対象ゾーン"] = selected_zone
                        all_wish_df["TOP割合"] = top_rate
                        all_wish_df["WORST割合"] = worst_rate
                        
                        # =================================================
                        # 使用データを表示
                        # =================================================
                        with st.expander("使用データ", expanded=False):

                            st.dataframe(
                                all_wish_df,
                                use_container_width=True,
                            )
                            
                        # =================================================
                        # ページ全体CSVダウンロード
                        # =================================================
                        st.download_button(
                            label="ページ全体CSV",
                            data=wish.wish_tab.dataframe_to_csv_bytes(all_wish_df),
                            file_name=f"wish_index_all_{selected_zone}.csv",
                            mime="text/csv",
                            key="wish_index_csv_all",
                            use_container_width=False,
                            on_click="ignore",
                        )

                        # =========================================================
                        # 凡例表示
                        # =========================================================
                        wish.wish_tab.render_simple_wish_legend(
                            wish_text="希望枠：TOP割合に入る枠",
                            normal_text="普通枠：TOP / WORSTのどちらにも該当しない枠",
                            reject_text="拒否枠：WORST割合に入る枠",
                        )

                        st.markdown("---")  

                        # =================================================
                        # 指標ごとに希望枠を描画
                        # =================================================
                        for i, section_title in enumerate(section_order):

                            wish.wish_tab.render_wish_row_index(
                                section_title=section_title,
                                df=df_heatmap_index,
                                top_rate=top_rate,
                                worst_rate=worst_rate,
                                zone_df=zone_df,
                                file_name_builder=lambda sec, station: f"{sec}_{station}_wish_index.csv",
                            )

                            # セクション間の区切り線
                            if i < len(section_order) - 1:

                                st.markdown("---")
                                
            except Exception as e:
                st.error(f"処理中にエラーが発生: {e}")
                            

    # =========================================================
    # 📊希望枠｜視聴率×INDEX
    # =========================================================
    with tab_wish_mix:

        # =========================================================
        # 視聴率×INDEXの希望枠タブ
        # =========================================================
        wish.wish_tab.render_wish_mix_tab(
            df_heatmap_all,
            df_heatmap_index,
        )
        
    
    # =========================================================
    # 💰ターゲットコスト
    # =========================================================     
    with tab_target_cost:

        # =========================================================
        # 0. 必要データの確認
        # =========================================================
        per_cost_file = get_uploaded_file_obj("per_cost_file")

        if per_cost_file is None:
            st.info("先に『アップロード』タブでパーコストデータをアップロードしてください。")

        elif not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):
            st.info("先に『アップロード』タブでINDEXヒートマップ対象データをアップロードしてください。")

        else:
            try:
                # =========================================================
                # 1. 元データの作成
                # =========================================================
                if df_heatmap_all is None:
                    df_heatmap_all = make_df_heatmap_all(
                        vr_all_file,
                        vr_target_file,
                        tval_all_file,
                        tval_target_file,
                        revisio_file,
                    )

                # INDEXデータ作成
                df_heatmap_index = make_df.heatmap_INDEX.make_df_heatmap_index(df_heatmap_all)

                # パーコスト読み込み
                df_percost = make_df_percost(per_cost_file).copy()

                # =========================================================
                # 2. 表示対象の指標を決定
                # =========================================================
                target_index_sections = [
                    "TVAL（ターゲット）÷ VR（個人全体/世帯）",
                    "VR（ターゲット）÷ VR（個人全体/世帯）",
                    "TVAL（ターゲット）÷ TVAL（個人全体/世帯）",
                    "REVISIO（注視）÷ REVISIO（世帯）",
                    "REVISIO（滞在）÷ REVISIO（世帯）",
                    "REVISIO（注視）÷ VR（個人全体/世帯）",
                    "REVISIO（滞在）÷ VR（個人全体/世帯）",
                    "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）] ÷ VR（個人全体/世帯）",
                    "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）] ÷ VR（個人全体/世帯）"
                ]
                
                df_heatmap_index2 = df_heatmap_index.replace(-np.inf,np.nan)

                available_sections = df_heatmap_index2["指標"].dropna().unique().tolist()
                target_index_sections = [s for s in target_index_sections if s in available_sections]
                
                # =========================================================
                # セグメント絞り込みフィルター
                # =========================================================
                selected_target_index_sections = st.multiselect(
                    "絞り込み",
                    options=target_index_sections,
                    # default=target_index_sections,
                    default=[],
                    key="target_cost_segment_filter",
                )

                if not selected_target_index_sections:
                    st.warning("表示するセクションを1つ以上選択してください。")
                    
                else:
                    target_index_sections = selected_target_index_sections

                    # =========================================================
                    # 3. zone_filters を 1つのDataFrameにまとめる
                    # =========================================================
                    zone_filters = st.session_state["zone_filters"]
                    df_zone_list = []

                    for zone_name, df_zone in zone_filters.items():
                        df_tmp = df_zone.reset_index()
                        df_tmp["ゾーン"] = zone_name
                        df_zone_list.append(df_tmp)

                    df_zone_all = pd.concat(df_zone_list, ignore_index=True)

                    # =========================================================
                    # 4. 数値データを縦持ち化
                    # - 時間帯 × 局 × 指標 × 曜日 × 値
                    # =========================================================
                    df_heatmap_index_long = df_heatmap_index2.melt(
                        id_vars=["時間帯", "局", "指標"],
                        value_vars=["月", "火", "水", "木", "金", "土", "日"],
                        var_name="曜日",
                        value_name="値",
                    )

                    df_heatmap_index_long["値"] = pd.to_numeric(df_heatmap_index_long["値"], errors="coerce")

                    # =========================================================
                    # 5. zoneデータを縦持ち化
                    # - 時間帯 × ゾーン × 曜日 × フラグ
                    # =========================================================
                    df_zone_long = df_zone_all.rename(columns={"index": "時間帯"}).melt(
                        id_vars=["時間帯", "ゾーン"],
                        value_vars=["月", "火", "水", "木", "金", "土", "日"],
                        var_name="曜日",
                        value_name="フラグ",
                    )

                    # bool に寄せる
                    df_zone_long["フラグ"] = df_zone_long["フラグ"].astype(bool)

                    # =========================================================
                    # 6. 数値データとゾーンデータを結合
                    # - 時間帯 × 曜日 で結合
                    # - ゾーン情報を付与
                    # =========================================================
                    df_heatmap_index_zone_long = df_heatmap_index_long.merge(
                        df_zone_long,
                        on=["時間帯", "曜日"],
                        how="left",
                    )

                    # zone=True のみ残す
                    df_heatmap_index_zone_long = df_heatmap_index_zone_long[df_heatmap_index_zone_long["フラグ"] == True].copy()

                    # 値が欠損のものは平均対象外
                    df_heatmap_index_zone_long = df_heatmap_index_zone_long.dropna(subset=["値"])

                    # =========================================================
                    # 7. ゾーン × 局 × 指標 で平均INDEXを算出
                    # =========================================================
                    df_heatmap_index_zone_avg = (
                        df_heatmap_index_zone_long
                        .groupby(["ゾーン", "局", "指標"], as_index=False)["値"]
                        .mean()
                        .rename(columns={"値": "平均値"})
                    )

                    # =========================================================
                    # 8. パーコストを結合
                    # - make_df_percost は縦持ち想定:
                    #   局 | ゾーン | パーコスト
                    # =========================================================
                    df_heatmap_index_zone_avg = df_heatmap_index_zone_avg.merge(
                        df_percost,
                        on=["局", "ゾーン"],
                        how="left",
                    )

                    # =========================================================
                    # 9. ターゲットコストを算出
                    # - ターゲットコスト = パーコスト ÷ 平均値
                    # =========================================================
                    df_heatmap_index_zone_avg["ターゲットコスト"] = df_heatmap_index_zone_avg["パーコスト"] / df_heatmap_index_zone_avg["平均値"]

                    # =========================================================
                    # 10. デバッグ確認用
                    # =========================================================
                    # 生成した元データを確認用に表示
                    if not df_heatmap_index_zone_avg.empty:
                        with st.expander("使用データ"):
                            st.dataframe(df_heatmap_index_zone_avg, use_container_width=True)

                    # =========================================================
                    # 11. 可視化
                    # - 指標ごとに
                    #   ①ターゲットINDEX
                    #   ②パーコスト
                    #   ③ターゲットコスト
                    #   を 行=局、列=ゾーン で表示
                    # =========================================================
                    for section in target_index_sections:
                        st.markdown(f"### {section}")

                        df_section = df_heatmap_index_zone_avg[df_heatmap_index_zone_avg["指標"] == section].copy()

                        if df_section.empty:
                            st.info("この指標のデータはありません。")
                            st.markdown("---")
                            continue

                        # ターゲットINDEX
                        df_mean_wide = df_section.pivot(
                            index="局",
                            columns="ゾーン",
                            values="平均値",
                        ).reset_index()

                        # パーコスト
                        df_percost_wide = df_section.pivot(
                            index="局",
                            columns="ゾーン",
                            values="パーコスト",
                        ).reset_index()

                        # ターゲットコスト
                        df_target_cost_wide = df_section.pivot(
                            index="局",
                            columns="ゾーン",
                            values="ターゲットコスト",
                        ).reset_index()

                        # 局順をそろえる
                        station_display_order = ["NTV", "TBS", "CX", "EX", "TX"]

                        def sort_station_order(df):
                            df = df.copy()
                            df["局"] = pd.Categorical(
                                df["局"],
                                categories=station_display_order,
                                ordered=True,
                            )
                            df = df.sort_values("局").reset_index(drop=True)
                            df["局"] = df["局"].astype(str)
                            return df

                        df_mean_wide = sort_station_order(df_mean_wide)
                        df_percost_wide = sort_station_order(df_percost_wide)
                        df_target_cost_wide = sort_station_order(df_target_cost_wide)

                        # 列順をそろえる
                        zone_display_order = [z for z in ZONE_NAMES if z in df_section["ゾーン"].dropna().unique().tolist()]

                        mean_cols = ["局"] + [z for z in zone_display_order if z in df_mean_wide.columns]
                        percost_cols = ["局"] + [z for z in zone_display_order if z in df_percost_wide.columns]
                        target_cost_cols = ["局"] + [z for z in zone_display_order if z in df_target_cost_wide.columns]

                        df_mean_wide = df_mean_wide[mean_cols]
                        df_percost_wide = df_percost_wide[percost_cols]
                        df_target_cost_wide = df_target_cost_wide[target_cost_cols]

                        # 表示用整形
                        for col in df_mean_wide.columns:
                            if col != "局":
                                df_mean_wide[col] = pd.to_numeric(df_mean_wide[col], errors="coerce").round(2)

                        for col in df_percost_wide.columns:
                            if col != "局":
                                df_percost_wide[col] = pd.to_numeric(df_percost_wide[col], errors="coerce").round(0)
                                df_percost_wide[col] = df_percost_wide[col].apply(
                                    lambda x: f"¥{x:,.0f}" if pd.notna(x) else ""
                                )

                        for col in df_target_cost_wide.columns:
                            if col != "局":
                                df_target_cost_wide[col] = pd.to_numeric(df_target_cost_wide[col], errors="coerce").round(0)
                                df_target_cost_wide[col] = df_target_cost_wide[col].apply(
                                    lambda x: f"¥{x:,.0f}" if pd.notna(x) else ""
                                )

                        # 横並び表示
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("#### パーコスト")
                            st.dataframe(df_percost_wide, use_container_width=True, hide_index=True)

                        with col2:
                            st.markdown("#### ターゲットINDEX")
                            st.dataframe(df_mean_wide, use_container_width=True, hide_index=True)

                        with col3:
                            st.markdown("#### ターゲットコスト")
                            st.dataframe(df_target_cost_wide, use_container_width=True, hide_index=True)

                        st.markdown("---")

            except Exception as e:
                st.error(f"処理中にエラーが発生: {e}")
                
    # =========================================================
    # 📅局比較
    # =========================================================    
    with tab_station_compare:

        if not (has_vr_all or has_tval_all or has_revisio or has_vr_target or has_tval_target):

            st.info("先に『アップロード』タブで視聴率ヒートマップ対象データをアップロードしてください。")
            
        elif per_cost_file is None:

            st.info("先に『アップロード』タブでパーコストデータをアップロードしてください。")

        else:

            try:

                # =========================================================
                # 1. df_heatmap_all / df_heatmap_index を作成
                # =========================================================
                if df_heatmap_all is None:

                    df_heatmap_all = make_df_heatmap_all(
                        vr_all_file,
                        vr_target_file,
                        tval_all_file,
                        tval_target_file,
                        revisio_file,
                    )

                if df_heatmap_index is None:

                    df_heatmap_index = make_df.heatmap_INDEX.make_df_heatmap_index(
                        df_heatmap_all
                    )

                # =========================================================
                # 2. zone_filters を縦持ち化
                # =========================================================
                zone_filters = st.session_state["zone_filters"]
                df_zone_list = []

                for zone_name, df_zone in zone_filters.items():

                    df_tmp = df_zone.reset_index()
                    df_tmp["ゾーン"] = zone_name
                    df_zone_list.append(df_tmp)

                df_zone_all = pd.concat(
                    df_zone_list,
                    ignore_index=True,
                )

                df_zone_long = (
                    df_zone_all
                    .rename(columns={"index": "時間帯"})
                    .melt(
                        id_vars=["時間帯", "ゾーン"],
                        value_vars=["月", "火", "水", "木", "金", "土", "日"],
                        var_name="曜日",
                        value_name="フラグ",
                    )
                )

                df_zone_long["フラグ"] = df_zone_long["フラグ"].astype(bool)

                # =========================================================
                # 3. 実数値データを縦持ち化
                # =========================================================
                df_heatmap_all_long = df_heatmap_all.melt(
                    id_vars=["時間帯", "局", "データ種別", "カテゴリー"],
                    value_vars=["月", "火", "水", "木", "金", "土", "日"],
                    var_name="曜日",
                    value_name="値",
                )

                df_heatmap_all_long["値"] = pd.to_numeric(
                    df_heatmap_all_long["値"],
                    errors="coerce",
                )

                df_heatmap_all_zone_long = df_heatmap_all_long.merge(
                    df_zone_long,
                    on=["時間帯", "曜日"],
                    how="left",
                )

                df_heatmap_all_zone_long = df_heatmap_all_zone_long[
                    df_heatmap_all_zone_long["フラグ"] == True
                ].copy()

                df_heatmap_all_zone_long = df_heatmap_all_zone_long.dropna(
                    subset=["値"]
                )

                # =========================================================
                # 4. ゾーン × 局 × 実数値指標で合計
                # =========================================================
                df_heatmap_all_zone_sum = (
                    df_heatmap_all_zone_long
                    .groupby(
                        ["ゾーン", "局", "データ種別", "カテゴリー"],
                        as_index=False,
                    )["値"]
                    .sum()
                    .rename(columns={"値": "合計値"})
                )

                # df_heatmap_all_zone_sum["表示指標"] = (
                #     df_heatmap_all_zone_sum["データ種別"].astype(str)
                #     + "（"
                #     + df_heatmap_all_zone_sum["カテゴリー"].astype(str)
                #     + "）"
                # )
                
                df_heatmap_all_zone_sum["表示指標"] = np.where(
                    (df_heatmap_all_zone_sum["データ種別"] == "TVAL×REVISIO補正") &
                    (df_heatmap_all_zone_sum["カテゴリー"] == "注視補正"),
                    "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
                    
                    np.where(
                        (df_heatmap_all_zone_sum["データ種別"] == "TVAL×REVISIO補正") &
                        (df_heatmap_all_zone_sum["カテゴリー"] == "滞在補正"),
                        "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
                        
                        df_heatmap_all_zone_sum["データ種別"].astype(str)
                        + "（"
                        + df_heatmap_all_zone_sum["カテゴリー"].astype(str)
                        + "）"
                    )
                )

                # =========================================================
                # 5. INDEXデータを縦持ち化
                # =========================================================
                df_heatmap_index2 = df_heatmap_index.replace(
                    -np.inf,
                    np.nan,
                )

                df_heatmap_index_long = df_heatmap_index2.melt(
                    id_vars=["時間帯", "局", "指標"],
                    value_vars=["月", "火", "水", "木", "金", "土", "日"],
                    var_name="曜日",
                    value_name="値",
                )

                df_heatmap_index_long["値"] = pd.to_numeric(
                    df_heatmap_index_long["値"],
                    errors="coerce",
                )

                df_heatmap_index_zone_long = df_heatmap_index_long.merge(
                    df_zone_long,
                    on=["時間帯", "曜日"],
                    how="left",
                )

                df_heatmap_index_zone_long = df_heatmap_index_zone_long[
                    df_heatmap_index_zone_long["フラグ"] == True
                ].copy()

                df_heatmap_index_zone_long = df_heatmap_index_zone_long.dropna(
                    subset=["値"]
                )

                # =========================================================
                # 6. ゾーン × 局 × INDEX指標で平均
                # =========================================================
                df_heatmap_index_zone_avg = (
                    df_heatmap_index_zone_long
                    .groupby(
                        ["ゾーン", "局", "指標"],
                        as_index=False,
                    )["値"]
                    .mean()
                    .rename(columns={"値": "平均値"})
                )

                # =========================================================
                # 7. 実数値ベースの偏差値
                # =========================================================
                df_heatmap_all_zone_sum["平均"] = (
                    df_heatmap_all_zone_sum
                    .groupby(["ゾーン", "データ種別", "カテゴリー"])["合計値"]
                    .transform("mean")
                )

                df_heatmap_all_zone_sum["標準偏差"] = (
                    df_heatmap_all_zone_sum
                    .groupby(["ゾーン", "データ種別", "カテゴリー"])["合計値"]
                    .transform("std")
                )

                df_heatmap_all_zone_sum["偏差値"] = (
                    (df_heatmap_all_zone_sum["合計値"] - df_heatmap_all_zone_sum["平均"])
                    / df_heatmap_all_zone_sum["標準偏差"]
                    * 10
                    + 50
                )

                df_heatmap_all_zone_sum["偏差値"] = (
                    df_heatmap_all_zone_sum["偏差値"]
                    .replace([np.inf, -np.inf], np.nan)
                    .fillna(50)
                )

                # =========================================================
                # 8. INDEXベースの偏差値
                # =========================================================
                df_heatmap_index_zone_avg["平均値"] = pd.to_numeric(
                    df_heatmap_index_zone_avg["平均値"],
                    errors="coerce",
                )

                df_heatmap_index_zone_avg["平均"] = (
                    df_heatmap_index_zone_avg
                    .groupby(["ゾーン", "指標"])["平均値"]
                    .transform("mean")
                )

                df_heatmap_index_zone_avg["標準偏差"] = (
                    df_heatmap_index_zone_avg
                    .groupby(["ゾーン", "指標"])["平均値"]
                    .transform("std")
                )

                df_heatmap_index_zone_avg["偏差値"] = (
                    (df_heatmap_index_zone_avg["平均値"] - df_heatmap_index_zone_avg["平均"])
                    / df_heatmap_index_zone_avg["標準偏差"]
                    * 10
                    + 50
                )

                df_heatmap_index_zone_avg["偏差値"] = (
                    df_heatmap_index_zone_avg["偏差値"]
                    .replace([np.inf, -np.inf], np.nan)
                    .fillna(50)
                )

                # =========================================================
                # 9. 表示順
                # =========================================================
                station_order = ["NTV", "TBS", "CX", "EX", "TX"]

                actual_col_order = [
                    "VR（個人全体）",
                    "TVAL（個人全体）",
                    "VR（ターゲット）",
                    "TVAL（ターゲット）",
                    "REVISIO（注視）",
                    "REVISIO（滞在）",
                    "REVISIO（世帯）",
                    "TVAL（ターゲット）× [REVISIO（各セル注視）÷ REVISIO（局単位の注視全値の平均）]",
                    "TVAL（ターゲット）× [REVISIO（各セル滞在）÷ REVISIO（局単位の滞在全値の平均）]",
                ]

                # =========================================================
                # 10. フィルター
                # =========================================================
                zone_list = [
                    z for z in ZONE_NAMES
                    if z in df_heatmap_all_zone_sum["ゾーン"].unique()
                ]

                selected_zone = st.radio(
                    "対象ゾーン",
                    zone_list,
                    index=0,
                    horizontal=True,
                    key="station_compare_zone",
                )

                actual_metric_list = [
                    c for c in actual_col_order
                    if c in df_heatmap_all_zone_sum["表示指標"].dropna().unique().tolist()
                ]

                selected_actual_metrics = st.multiselect(
                    "実数値指標",
                    options=actual_metric_list,
                    default=actual_metric_list,
                    key="station_compare_actual_metrics",
                )

                index_metric_list = sorted(
                    df_heatmap_index_zone_avg["指標"]
                    .dropna()
                    .unique()
                    .tolist()
                )

                selected_index_metrics = st.multiselect(
                    "効率指標",
                    options=index_metric_list,
                    default=index_metric_list,
                    key="station_compare_index_metrics",
                )

                # =========================================================
                # 11. 実数値テーブル
                # =========================================================
                df_actual = df_heatmap_all_zone_sum[
                    (df_heatmap_all_zone_sum["ゾーン"] == selected_zone) &
                    (df_heatmap_all_zone_sum["表示指標"].isin(selected_actual_metrics))
                ].copy()

                df_actual_table = (
                    df_actual
                    .pivot_table(
                        index="局",
                        columns="表示指標",
                        values="合計値",
                        aggfunc="first",
                    )
                    .reset_index()
                )

                df_actual_table["局"] = pd.Categorical(
                    df_actual_table["局"],
                    categories=station_order,
                    ordered=True,
                )

                df_actual_table = df_actual_table.sort_values("局").reset_index(drop=True)

                actual_existing_cols = [
                    "局"
                ] + [
                    c for c in actual_col_order
                    if c in df_actual_table.columns
                ]

                df_actual_table = df_actual_table[actual_existing_cols]
                df_actual_table = df_actual_table.round(1)

                # =========================================================
                # 12. 偏差値｜実数値ベース
                # =========================================================
                df_actual_score = df_heatmap_all_zone_sum[
                    (df_heatmap_all_zone_sum["ゾーン"] == selected_zone) &
                    (df_heatmap_all_zone_sum["表示指標"].isin(selected_actual_metrics))
                ].copy()

                df_actual_score_table = (
                    df_actual_score
                    .pivot_table(
                        index="局",
                        columns="表示指標",
                        values="偏差値",
                        aggfunc="first",
                    )
                    .reset_index()
                )

                df_actual_score_table["局"] = pd.Categorical(
                    df_actual_score_table["局"],
                    categories=station_order,
                    ordered=True,
                )

                df_actual_score_table = df_actual_score_table.sort_values("局").reset_index(drop=True)

                actual_score_existing_cols = [
                    "局"
                ] + [
                    c for c in actual_col_order
                    if c in df_actual_score_table.columns
                ]

                df_actual_score_table = df_actual_score_table[actual_score_existing_cols]
                df_actual_score_table = df_actual_score_table.round(1)

                # =========================================================
                # 13. 効率テーブル
                # =========================================================
                df_index = df_heatmap_index_zone_avg[
                    (df_heatmap_index_zone_avg["ゾーン"] == selected_zone) &
                    (df_heatmap_index_zone_avg["指標"].isin(selected_index_metrics))
                ].copy()

                df_index_table = (
                    df_index
                    .pivot_table(
                        index="局",
                        columns="指標",
                        values="平均値",
                        aggfunc="first",
                    )
                    .reset_index()
                )

                df_index_table["局"] = pd.Categorical(
                    df_index_table["局"],
                    categories=station_order,
                    ordered=True,
                )

                df_index_table = df_index_table.sort_values("局").reset_index(drop=True)
                df_index_table = df_index_table.round(1)

                # =========================================================
                # 14. 偏差値｜効率ベース
                # =========================================================
                df_index_score = df_heatmap_index_zone_avg[
                    (df_heatmap_index_zone_avg["ゾーン"] == selected_zone) &
                    (df_heatmap_index_zone_avg["指標"].isin(selected_index_metrics))
                ].copy()

                df_index_score_table = (
                    df_index_score
                    .pivot_table(
                        index="局",
                        columns="指標",
                        values="偏差値",
                        aggfunc="first",
                    )
                    .reset_index()
                )

                df_index_score_table["局"] = pd.Categorical(
                    df_index_score_table["局"],
                    categories=station_order,
                    ordered=True,
                )

                df_index_score_table = df_index_score_table.sort_values("局").reset_index(drop=True)
                df_index_score_table = df_index_score_table.round(1)

                # =========================================================
                # 15. 総合偏差値
                # =========================================================
                df_total_actual = df_actual_score[["局", "偏差値"]].copy()
                df_total_index = df_index_score[["局", "偏差値"]].copy()

                df_total = pd.concat(
                    [df_total_actual, df_total_index],
                    ignore_index=True,
                )

                df_total_score = (
                    df_total
                    .groupby("局", as_index=False)["偏差値"]
                    .mean()
                    .rename(columns={"偏差値": "総合偏差値"})
                )

                df_total_score["局"] = pd.Categorical(
                    df_total_score["局"],
                    categories=station_order,
                    ordered=True,
                )

                df_total_score = df_total_score.sort_values("局").reset_index(drop=True)
                df_total_score = df_total_score.round(1)

                # =========================================================
                # 16. 表示
                # =========================================================
                st.markdown("### 実数値")
                st.dataframe(
                    df_actual_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### 効率（INDEX）")
                st.dataframe(
                    df_index_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### 偏差値｜実数値ベース")
                st.dataframe(
                    df_actual_score_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### 偏差値｜効率（INDEX）")
                st.dataframe(
                    df_index_score_table,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### 総合偏差値")
                st.dataframe(
                    df_total_score,
                    use_container_width=True,
                    hide_index=True,
                )

            except Exception as e:

                st.error(f"処理中にエラーが発生: {e}")
        

###################################################################################################################################################

# =========================================================
# 📍エリア平均パーコスト
# =========================================================

elif user_select == "📍エリア平均パーコスト":
    tab_upload, tab_area_cost = st.tabs(["📁データアップロード", "🗾エリア平均パーコスト"])

    # =========================================================
    # 📁データアップロード
    # =========================================================
    with tab_upload:
        with st.container(border=True): 
            
            st.warning(
                """
                📁各エリアコスト・INDEXのフォーマット格納先  
                http://box・・・・・・・
                """,
                icon=None
            )

            bottom_cols = st.columns(1)

            with bottom_cols[0]:
                
                make_upload_box(
                    title = "エリア平均パーコストデータ",
                    info_message = None,
                    warning_message = "指定フォーマットへ入力",
                    error_message = None,
                    key = "area_cost_file",
                    allowed_types = ["xlsx", "xlsm"]
                )
                
    # =========================================================
    # 🗾エリア平均パーコスト
    # =========================================================
    with tab_area_cost:

        area_cost_file = get_uploaded_file_obj("area_cost_file")

        if area_cost_file is None:
            st.info("エリアパーコストデータをアップロードしてください。")

        else:
            df = area_per_cost.area_per_cost.read_cost_excel(area_cost_file)

            area_list = df["エリア"].dropna().unique().tolist()
            area_per_cost.area_per_cost.init_area_state(area_list)

            area_avg_df = area_per_cost.area_per_cost.calc_area_avg_target_cost(df)
            selected_zone_sum = area_per_cost.area_per_cost.calc_selected_area_zone_sum(area_avg_df)

            # -------------------------
            # 上部サマリー
            # -------------------------
            left_col, right_col = st.columns([1.2, 1.8])

            with left_col:
                area_per_cost.area_per_cost.render_summary_boxes(selected_zone_sum)

            with right_col:
                area_per_cost.area_per_cost.render_top_area_selector(area_list)

            st.divider()

            # -------------------------
            # エリア別表示
            # -------------------------
            for area in area_list:
                area_per_cost.area_per_cost.render_area_block(area, df, area_avg_df)
        
# =========================================================
# 🔍視聴率×検索数
# =========================================================
        
elif user_select == "🔍視聴率×検索数":
    tab_upload, tab_search_01, tab_search_02 = st.tabs(["📁データアップロード", "📈推移・相関・散布図", "📊年齢区分別相関比較"])
    
    # =========================================================
    # 📁データアップロード
    # =========================================================
    with tab_upload:
        with st.container(border=True):
            st.markdown("### ファイルをアップロード")

            middle_cols = st.columns(4)

            with middle_cols[0]:
                make_upload_box(
                    "VR日別視聴率データ",
                    "VR日別視聴率データのExcelファイルを選択してください",
                    "vr_daily_file",
                    ["xlsx", "xlsm"],
                )

            with middle_cols[1]:
                make_upload_box(
                    "TVAL日別視聴率データ",
                    "TVAL日別視聴率データのExcelファイルを選択してください",
                    "tval_daily_file",
                    ["xlsx", "xlsm"],
                )

            with middle_cols[2]:
                make_upload_box(
                    "REVISIO日別視聴率データ",
                    "REVISIO日別視聴率データのファイルを選択してください",
                    "revisio_daily_file",
                    ["csv", "xlsx", "xlsm"],
                )

            with middle_cols[3]:
                make_upload_box(
                    "DS.Insight検索数データ",
                    "DS.Insight検索数データのファイルを選択してください",
                    "search_daily_file",
                    ["csv", "xlsx", "xlsm"],
                )

    # =========================================================
    # 📈推移・相関・散布図
    # =========================================================                 
    with tab_search_01:

        # =========================
        # メイン処理
        # =========================

        # 各アップロードファイルを取得        
        vr_file = get_uploaded_file_obj("vr_daily_file")
        tval_file = get_uploaded_file_obj("tval_daily_file")
        revisio_file = get_uploaded_file_obj("revisio_daily_file")
        search_file = get_uploaded_file_obj("search_daily_file")

        # ファイルのアップロード有無を判定
        has_vr = vr_file is not None
        has_tval = tval_file is not None
        has_revisio = revisio_file is not None
        has_search = search_file is not None

        # TV系ファイル（VR / TVAL / REVISIO）のいずれかがあるか
        has_any_tv = has_vr or has_tval or has_revisio

        # 何らかのファイルが1つでもアップロードされているか
        # → 折れ線グラフ表示可否の判定に利用
        has_any_file = has_any_tv or has_search

        if has_any_file:

            try:
                # -------------------------
                # データ生成（アップロードされているもののみ）
                # -------------------------

                # 初期化（未アップロードの場合はNoneのまま扱う）
                df_vr = None
                df_tval = None
                df_revisio = None
                df_search = None

                # -------------------------
                # VRデータ
                # -------------------------
                if has_vr:
                    # 日次×セグメント粒度に変換
                    df_vr = get_daily_vr_rating(vr_file)
                    # 日付型を統一
                    df_vr["日付"] = pd.to_datetime(df_vr["日付"], errors="coerce")

                # -------------------------
                # TVALデータ
                # -------------------------
                if has_tval:
                    df_tval = get_daily_tval_rating(tval_file)
                    df_tval["日付"] = pd.to_datetime(df_tval["日付"], errors="coerce")

                # -------------------------
                # REVISIOデータ
                # -------------------------
                if has_revisio:
                    df_revisio = get_daily_revisio_rating(revisio_file)
                    df_revisio["日付"] = pd.to_datetime(df_revisio["日付"], errors="coerce")

                # -------------------------
                # 検索データ
                # -------------------------
                if has_search:
                    # 性年代 → 共通セグメントに変換済みの日次検索データ
                    df_search = get_daily_search(search_file)
                    df_search["日付"] = pd.to_datetime(df_search["日付"], errors="coerce")

                # -------------------------
                # TVデータ結合（アップロードされているもののみ）
                # -------------------------
                # REVISIO / TVAL / VR のうち、存在するデータだけを結合対象にする
                tv_dfs = []

                if df_revisio is not None:
                    tv_dfs.append(df_revisio)

                if df_tval is not None:
                    tv_dfs.append(df_tval)

                if df_vr is not None:
                    tv_dfs.append(df_vr)

                df_tv = None

                # TVデータが1つだけの場合はそのまま使用
                if len(tv_dfs) == 1:
                    df_tv = tv_dfs[0].copy()

                # TVデータが複数ある場合は
                # 日付 × セグメント をキーに外部結合する
                elif len(tv_dfs) >= 2:
                    df_tv = tv_dfs[0].copy()
                    for df_tmp in tv_dfs[1:]:
                        df_tv = df_tv.merge(df_tmp, on=["日付", "セグメント"], how="outer")
                    df_tv = df_tv.sort_values(["日付", "セグメント"]).reset_index(drop=True)

                # -------------------------
                # 分析条件の選択UI
                # -------------------------
                st.markdown("---")
                st.subheader("分析条件")

                # キーワード選択欄 / セグメント選択欄を横並びで表示
                condition_col1, condition_col2 = st.columns(2)

                # -------------------------
                # キーワード候補の作成
                # -------------------------
                # 検索データがある場合のみ、キーワード一覧を作成
                keyword_list = []
                if df_search is not None and "キーワード" in df_search.columns:
                    keyword_list = sorted(df_search["キーワード"].dropna().unique().tolist())

                # -------------------------
                # セグメント候補の作成
                # -------------------------
                # 表示順を固定したいセグメント順
                segment_order = ["個人全体", "Child", "Teen", "F1", "F2", "F3", "M1", "M2", "M3"]
                segment_candidates = []

                # TVデータに存在するセグメントを候補に追加
                if df_tv is not None and "セグメント" in df_tv.columns:
                    segment_candidates.extend(df_tv["セグメント"].dropna().unique().tolist())

                # 検索データに存在するセグメントも候補に追加
                if df_search is not None and "セグメント" in df_search.columns:
                    segment_candidates.extend(df_search["セグメント"].dropna().unique().tolist())

                # 重複を除去しつつ順序を維持
                existing_segments = list(dict.fromkeys(segment_candidates))

                # まずは定義済み順（個人全体 → Child → Teen ...）で並べる
                segment_list = [seg for seg in segment_order if seg in existing_segments]

                # 定義外セグメントがあれば末尾に追加
                segment_list += [seg for seg in existing_segments if seg not in segment_list]

                # -------------------------
                # キーワード選択UI
                # -------------------------
                with condition_col1:
                    if keyword_list:
                        # 候補がある場合は通常の選択ボックスを表示
                        selected_keyword = st.selectbox(
                            "キーワード",
                            keyword_list,
                            index=0
                        )
                    else:
                        # 検索データ未アップロード時は選択不可にする
                        selected_keyword = None
                        st.selectbox(
                            "キーワード", 
                            ["検索データ未アップロード"], 
                            index=0, 
                            disabled=True)
                        
                # -------------------------
                # セグメント選択UI
                # -------------------------
                with condition_col2:
                    if segment_list:
                        # 「個人全体」があればデフォルト選択にする
                        default_segment_index = segment_list.index("個人全体") if "個人全体" in segment_list else 0
                        selected_segment = st.selectbox(
                            "セグメント",
                            segment_list,
                            index=default_segment_index
                        )
                    else:
                        # セグメント候補がない場合は選択不可にする
                        selected_segment = None
                        st.selectbox(
                            "セグメント", 
                            ["セグメントなし"], 
                            index=0, 
                            disabled=True)

                # -------------------------
                # 折れ線グラフ用データ作成
                # -------------------------
                # 選択されたセグメントに絞って、
                # 検索数データ・TVデータを日付単位で横結合する
                df_plot = None

                if selected_segment is not None:
                    plot_parts = []

                    # -------------------------
                    # 検索データ
                    # -------------------------
                    # 指定キーワード × 指定セグメントの検索数のみ抽出
                    if df_search is not None and selected_keyword is not None:
                        df_search_plot = df_search[
                            (df_search["キーワード"] == selected_keyword) &
                            (df_search["セグメント"] == selected_segment)
                        ][["日付", "検索数"]].copy()
                        plot_parts.append(df_search_plot)

                    # -------------------------
                    # TVデータ
                    # -------------------------
                    # 指定セグメントのTV指標のみ抽出
                    if df_tv is not None:
                        tv_cols = ["日付", "セグメント"]

                        # アップロードされているTV指標だけ対象にする
                        for col in ["VR_視聴率", "TVAL_視聴率", "REVISIO_GRP"]:
                            if col in df_tv.columns:
                                tv_cols.append(col)

                        df_tv_plot = df_tv[df_tv["セグメント"] == selected_segment][tv_cols].copy()

                        # 結合時に不要なためセグメント列は削除
                        df_tv_plot = df_tv_plot.drop(columns=["セグメント"], errors="ignore")
                        plot_parts.append(df_tv_plot)

                    # -------------------------
                    # 検索数・TV指標を日付で結合
                    # -------------------------
                    if plot_parts:
                        df_plot = plot_parts[0].copy()

                        # 複数データがある場合は日付で外部結合
                        # → どちらか一方しかない日も残す
                        for part in plot_parts[1:]:
                            df_plot = df_plot.merge(part, on="日付", how="outer")

                        # 日付順に並べ替え
                        df_plot["日付"] = pd.to_datetime(df_plot["日付"], errors="coerce")
                        df_plot = df_plot.sort_values("日付").reset_index(drop=True)

                        # 数値列を明示的に数値型へ変換
                        for col in ["検索数", "VR_視聴率", "TVAL_視聴率", "REVISIO_GRP"]:
                            if col in df_plot.columns:
                                df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")

                # -------------------------
                # データ確認（デバッグ / 中間データの可視化）
                # -------------------------
                # 使用している元データ・加工後データを確認できるようにする
                # ※ 分析結果の裏側を確認・検証するためのUI
                with st.expander("使用データを確認"):

                    # -------------------------
                    # TV結合データ
                    # -------------------------
                    # REVISIO / TVAL / VR を統合したデータ
                    if df_tv is not None:
                        st.markdown("#### TV結合データ")
                        st.dataframe(df_tv, use_container_width=True)

                    # -------------------------
                    # 検索データ
                    # -------------------------
                    # セグメント変換済みの日次検索データ
                    if df_search is not None:
                        st.markdown("#### 検索データ")
                        st.dataframe(df_search, use_container_width=True)

                    # -------------------------
                    # 可視化用データ
                    # -------------------------
                    # 折れ線グラフ・相関分析に使用する最終データ
                    if df_plot is not None:
                        st.markdown("#### 可視化用データ")
                        st.dataframe(df_plot, use_container_width=True)

                # -------------------------
                # 折れ線グラフ（時系列の可視化）
                # -------------------------
                # 検索数とTV指標を同一の時間軸で表示し、
                # TV出稿と検索の動きの関係を直感的に確認する
                # ※ 検索のみ / TVのみでも描画可能（どれか1つでもあれば表示）
                st.markdown("---")
                st.subheader("推移")

                # 描画対象データがない場合は警告
                if df_plot is None or df_plot.empty:
                    st.warning("折れ線グラフを表示できるデータがありません。")
                else:
                    # 2軸グラフ（左：検索数、右：TV指標）を作成
                    fig_ts = make_subplots(specs=[[{"secondary_y": True}]])

                    # -------------------------
                    # 左軸：検索数
                    # -------------------------
                    if "検索数" in df_plot.columns:
                        fig_ts.add_trace(
                            go.Scatter(
                                x=df_plot["日付"],
                                y=df_plot["検索数"],
                                name="検索数",
                                mode="lines+markers"
                            ),
                            secondary_y=False
                        )

                    # -------------------------
                    # 右軸：TV指標（VR / TVAL / REVISIO）
                    # -------------------------
                    # アップロードされている指標のみ描画
                    has_tv_trace = False
                    for col in ["VR_視聴率", "TVAL_視聴率", "REVISIO_GRP"]:
                        if col in df_plot.columns:
                            fig_ts.add_trace(
                                go.Scatter(
                                    x=df_plot["日付"],
                                    y=df_plot[col],
                                    name=col,
                                    mode="lines+markers"
                                ),
                                secondary_y=True
                            )
                            has_tv_trace = True

                    # -------------------------
                    # レイアウト調整
                    # -------------------------
                    fig_ts.update_layout(
                        height=500,
                        legend_title="指標",
                         # 凡例サイズ調整のため追加
                        legend=dict(
                            title_font=dict(size=18), 
                            font=dict(size=16),
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)
                    )

                    # 2026/4/16追加　※年月を2026/4のように表示
                    fig_ts.update_xaxes(
                        tickformat="%Y/%-m",
                        hoverformat="%Y/%-m/%-d"
                    )

                    # 軸ラベル設定（存在するデータのみ）
                    if "検索数" in df_plot.columns:
                        fig_ts.update_yaxes(title_text="検索数", secondary_y=False)
                    if has_tv_trace:
                        fig_ts.update_yaxes(title_text="視聴率 / GRP", secondary_y=True)

                    # 描画
                    st.plotly_chart(fig_ts, use_container_width=True)

                # -------------------------
                # 相関・散布図（関係性の定量化）
                # -------------------------
                # 検索数とTV指標の関係を分析する
                # ※ 検索数 + TV指標（いずれか1つ以上）が存在する場合のみ実施
                can_analyze_relation = (
                    df_plot is not None
                    and not df_plot.empty
                    and "検索数" in df_plot.columns
                    and any(col in df_plot.columns for col in ["VR_視聴率", "TVAL_視聴率", "REVISIO_GRP"])
                )

                if can_analyze_relation:
                   # -------------------------
                    # 相関係数（線形関係の強さ）
                    # -------------------------
                    # 検索数と各TV指標の相関を算出し、
                    # 「TVが増えると検索が増えるか」を定量的に確認
                    st.markdown("---")
                    st.subheader("相関係数")

                    # 利用可能なTV指標のみ対象にする
                    available_metric_map = [
                        (metric_col, label)
                        for metric_col, label in [
                            ("VR_視聴率", "VR×検索数"),
                            ("TVAL_視聴率", "TVAL×検索数"),
                            ("REVISIO_GRP", "REVISIO×検索数"),
                        ]
                        if metric_col in df_plot.columns
                    ]

                    # 指標ごとに横並びで表示
                    corr_cols = st.columns(max(len(available_metric_map), 1))

                    for i, (metric_col, label) in enumerate(available_metric_map):
                        with corr_cols[i]:
                            # 欠損値を除去したデータで相関を算出
                            valid_df = df_plot[["検索数", metric_col]].dropna()

                            # 相関係数が計算できる条件をチェック
                            # ・データ数が2以上
                            # ・双方に変動がある（一定値だと相関が出ない）
                            if len(valid_df) >= 2 and valid_df["検索数"].nunique() > 1 and valid_df[metric_col].nunique() > 1:
                                corr_val = valid_df["検索数"].corr(valid_df[metric_col])
                                st.metric(label=label, value=f"{corr_val:.2f}")
                            else:
                                # データ不足・変動なしの場合は表示不可
                                st.metric(label=label, value="-")

                    # -------------------------
                    # 散布図（検索数 × TV指標の関係を可視化）
                    # -------------------------
                    # 相関係数だけでは関係の形が分からないため、
                    # 散布図と回帰直線を使って線形傾向を確認する
                    st.markdown("---")
                    st.subheader("散布図")

                    # 利用可能なTV指標ごとに横並びで表示
                    scatter_cols = st.columns(max(len(available_metric_map), 1))

                    for i, (metric_col, title) in enumerate(available_metric_map):
                        with scatter_cols[i]:
                            # 欠損値を除去したデータを使用
                            valid_df = df_plot[["検索数", metric_col]].dropna()

                            # 点が2件未満だと散布図として意味を持たないため表示しない
                            if len(valid_df) < 2:
                                st.info(f"{title} の描画対象データがありません。")
                            else:
                                # 検索数を横軸、TV指標を縦軸にして散布図を作成
                                # trendline="ols" で回帰直線を表示
                                fig_scatter = px.scatter(
                                    valid_df,
                                    x="検索数",
                                    y=metric_col,
                                    title=title,
                                    trendline="ols"
                                )
                                fig_scatter.update_layout(
                                    height=350,
                                    margin=dict(l=20, r=20, t=50, b=20)
                                )
                                st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    # -------------------------
                    # 相関・散布図を表示できない場合
                    # -------------------------
                    # 検索数データとTVデータの両方がそろっていないため、
                    # 関係性の分析はスキップする
                    st.markdown("---")
                    st.subheader("相関・散布図")
                    st.info("相関・散布図は、検索数データとTVデータ（VR / TVAL / REVISIOのいずれか）が必要です。")

            # -------------------------
            # エラーハンドリング
            # -------------------------
            # データ処理中にエラーが発生した場合、
            # ユーザーに内容を表示して処理を停止
            except Exception as e:
                st.error(f"処理中にエラーが発生: {e}")

        else:
            # -------------------------
            # ファイル未アップロード時のガイド
            # -------------------------
            # いずれのデータもアップロードされていない場合、
            # 可視化が開始されない旨をユーザーに案内
            st.info("VR/TVAL/REVISIOの日別データまたはDS.Insightの検索数データのファイルをアップロードすると可視化を開始します。")

    # =========================================================
    # 📊年齢区分別相関比較
    # =========================================================   
    with tab_search_02:
        st.markdown("## 検索数とTVALの相関")

        # =========================
        # アップロードファイルの取得
        # =========================
        tval_file = get_uploaded_file_obj("tval_daily_file")
        search_file = get_uploaded_file_obj("search_daily_file")

        # 必須ファイルの有無を判定
        has_tval = tval_file is not None
        has_search = search_file is not None

        if not (has_tval and has_search):
            st.info("このタブでは、TVAL日別データとDS.Insightの検索数データをアップロードすると可視化を開始します。")
        else:
            try:
                # =========================
                # データ生成
                # =========================
                df_tval = get_daily_tval_rating(tval_file)
                df_search = get_daily_search(search_file)

                # 日付型を統一
                df_tval["日付"] = pd.to_datetime(df_tval["日付"], errors="coerce")
                df_search["日付"] = pd.to_datetime(df_search["日付"], errors="coerce")

                # TVAL視聴率を数値型に変換
                df_tval["TVAL_視聴率"] = pd.to_numeric(df_tval["TVAL_視聴率"], errors="coerce")
                df_search["検索数"] = pd.to_numeric(df_search["検索数"], errors="coerce")

                # =========================
                # 選択肢作成
                # =========================
                # セグメント候補は TVAL / 検索 の両方から取得
                segment_order = ["個人全体", "Child", "Teen", "F1", "F2", "F3", "M1", "M2", "M3"]
                segment_candidates = []

                if "セグメント" in df_tval.columns:
                    segment_candidates.extend(df_tval["セグメント"].dropna().unique().tolist())

                if "セグメント" in df_search.columns:
                    segment_candidates.extend(df_search["セグメント"].dropna().unique().tolist())

                existing_segments = list(dict.fromkeys(segment_candidates))
                segment_list = [seg for seg in segment_order if seg in existing_segments]
                segment_list += [seg for seg in existing_segments if seg not in segment_list]

                # キーワード候補
                keyword_list = sorted(df_search["キーワード"].dropna().unique().tolist())

                # 分析可能期間はTVALと検索の共通期間
                min_date_tval = df_tval["日付"].min()
                max_date_tval = df_tval["日付"].max()
                min_date_search = df_search["日付"].min()
                max_date_search = df_search["日付"].max()

                min_date = max(min_date_tval, min_date_search)
                max_date = min(max_date_tval, max_date_search)

                # =========================
                # 条件UI
                # =========================
                filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 2])

                with filter_col1:
                    selected_segments = st.multiselect(
                        "セグメント選択",
                        options=segment_list,
                        default=[seg for seg in ["M1", "M2", "M3", "F1", "F2", "F3"] if seg in segment_list],
                        key="search02_segments"
                    )

                with filter_col2:
                    selected_keywords = st.multiselect(
                        "キーワード選択（最大10件推奨）",
                        options=keyword_list,
                        default=keyword_list[:2] if len(keyword_list) >= 2 else keyword_list,
                        key="search02_keywords"
                    )

                with filter_col3:
                    selected_date_range = st.date_input(
                        "期間選択",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date(),
                        key="search02_date_range"
                    )

                if not selected_segments:
                    st.warning("セグメントを1つ以上選択してください。")
                    st.stop()

                if not selected_keywords:
                    st.warning("キーワードを1つ以上選択してください。")
                    st.stop()

                if len(selected_keywords) > 10:
                    st.warning("キーワードは10件以内を推奨。")

                # -------------------------
                # 日付範囲の安全な処理
                # -------------------------
                # st.date_input は以下の形式で値が返る可能性がある
                # ・範囲選択： (開始日, 終了日)
                # ・単日選択： 日付オブジェクト
                # ・範囲選択途中： (開始日, None)
                # → どのケースでも安全に扱えるように分岐する

                if isinstance(selected_date_range, tuple):
                    # 開始日は必ず存在
                    start_date = selected_date_range[0]

                    # 終了日が未選択（None）の場合は開始日と同一日にする
                    # → フィルタが壊れないようにするため
                    end_date = selected_date_range[1] if selected_date_range[1] is not None else start_date
                else:
                    # 単日選択の場合は開始日＝終了日として扱う
                    start_date = selected_date_range
                    end_date = selected_date_range

                # pandasのTimestamp型に変換（後続の比較処理で使用するため）
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)

                # =========================
                # フィルタ
                # =========================
                df_tval_filtered = df_tval[
                    (df_tval["日付"] >= start_date) &
                    (df_tval["日付"] <= end_date) &
                    (df_tval["セグメント"].isin(selected_segments))
                ].copy()

                df_search_filtered = df_search[
                    (df_search["日付"] >= start_date) &
                    (df_search["日付"] <= end_date) &
                    (df_search["セグメント"].isin(selected_segments)) &
                    (df_search["キーワード"].isin(selected_keywords))
                ].copy()

                # =========================
                # KPI用
                # =========================
                # 検索日付を母集団にし、TVALがない日は0として扱う
                search_daily_base = (
                    df_search_filtered[["日付"]]
                    .dropna()
                    .drop_duplicates()
                    .sort_values("日付")
                    .reset_index(drop=True)
                )

                # 日付単位でTVALを集計
                tval_daily = (
                    df_tval_filtered.groupby("日付", as_index=False)["TVAL_視聴率"]
                    .sum()
                )
                tval_daily["TVAL_視聴率"] = pd.to_numeric(
                    tval_daily["TVAL_視聴率"], errors="coerce"
                )

                # 検索日付を基準にTVALを結合
                # → TVALが存在しない日はNaNになる
                tv_active_days = search_daily_base.merge(
                    tval_daily,
                    on="日付",
                    how="left"
                )

                # TVALがない日は出稿0として扱う
                tv_active_days["TVAL_視聴率"] = tv_active_days["TVAL_視聴率"].fillna(0)

                # 出稿あり / なし判定
                tv_active_days["出稿あり"] = tv_active_days["TVAL_視聴率"] > 0

                # KPI
                analysis_day_count = len(tv_active_days)
                active_day_count = int(tv_active_days["出稿あり"].sum())
                no_active_day_count = int((~tv_active_days["出稿あり"]).sum())

                kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
                with kpi_col1:
                    st.metric("分析対象日数", analysis_day_count)
                with kpi_col2:
                    st.metric("出稿あり日数", active_day_count)
                with kpi_col3:
                    st.metric("出稿なし日数", no_active_day_count)

                # =========================
                # 相関計算（検索数 × TVAL）
                # =========================
                # セグメント × キーワードごとに、
                # 「検索数」と「TVAL視聴率（出稿なし日は0）」の関係性（相関）を算出する
                result_list = []

                for seg in selected_segments:
                    # -------------------------
                    # TVALデータ（セグメント単位）
                    # -------------------------
                    # 指定セグメントのTVALデータを抽出
                    # 日付単位で扱うため必要な列のみ残す
                    df_tval_seg = df_tval_filtered[
                        df_tval_filtered["セグメント"] == seg
                    ][["日付", "セグメント", "TVAL_視聴率"]].copy()

                    # TVALは数値化し、欠損は0補完
                    # → 出稿なし日を「0」として扱うため
                    df_tval_seg["TVAL_視聴率"] = pd.to_numeric(
                        df_tval_seg["TVAL_視聴率"], errors="coerce"
                    ).fillna(0)

                    for kw in selected_keywords:
                        # -------------------------
                        # 検索データ（セグメント × キーワード）
                        # -------------------------
                        # 指定セグメントかつ指定キーワードの検索数データを抽出
                        df_search_kw = df_search_filtered[
                            (df_search_filtered["セグメント"] == seg) &
                            (df_search_filtered["キーワード"] == kw)
                        ][["日付", "セグメント", "キーワード", "検索数"]].copy()

                        # 検索数を数値型に変換
                        df_search_kw["検索数"] = pd.to_numeric(
                            df_search_kw["検索数"], errors="coerce"
                        )

                        # -------------------------
                        # データ結合（検索ベース）
                        # -------------------------
                        # 検索データを基準にTVALを結合
                        # → 検索はあるがTVALがない日は NaN になる
                        df_merge = df_search_kw.merge(
                            df_tval_seg,
                            on=["日付", "セグメント"],
                            how="left"
                        )

                        # TVAL欠損を0補完
                        # → 「出稿なし」を明示的に0として扱う
                        df_merge["TVAL_視聴率"] = pd.to_numeric(
                            df_merge["TVAL_視聴率"], errors="coerce"
                        ).fillna(0)

                        # -------------------------
                        # 相関計算用データ作成
                        # -------------------------
                        # 検索数・TVALの両方が存在するデータのみ使用
                        valid = df_merge[["検索数", "TVAL_視聴率"]].dropna()

                        # -------------------------
                        # 相関係数の計算
                        # -------------------------
                        # ・データ数が少なすぎる場合は計算不可
                        # ・どちらかが一定値（分散0）の場合も相関は計算不可
                        if len(valid) < 2:
                            corr_val = None
                        elif valid["検索数"].nunique() <= 1 or valid["TVAL_視聴率"].nunique() <= 1:
                            corr_val = None
                        else:
                            # ピアソン相関係数を算出
                            corr_val = valid["検索数"].corr(valid["TVAL_視聴率"])

                        # -------------------------
                        # 結果格納
                        # -------------------------
                        result_list.append({
                            "セグメント": seg,
                            "キーワード": kw,
                            "相関": corr_val,
                            "データ数": len(valid)
                        })

                # DataFrame化（可視化・テーブル表示用）
                df_corr = pd.DataFrame(result_list)

                # =========================
                # データ確認
                # =========================
                with st.expander("使用データを確認"):
                    st.markdown("#### TVALデータ")
                    st.dataframe(df_tval, use_container_width=True)

                    st.markdown("#### 検索データ")
                    st.dataframe(df_search, use_container_width=True)

                    # st.markdown("#### KPI判定用データ")
                    # st.dataframe(tv_active_days, use_container_width=True)

                    st.markdown("#### 相関結果データ")
                    st.dataframe(df_corr, use_container_width=True)

                # =========================
                # 棒グラフ
                # =========================
                st.markdown("### 相関係数")

                if df_corr.empty or df_corr["相関"].dropna().empty:
                    st.warning("相関を計算できる組み合わせがありません。")
                else:
                    fig_corr = px.bar(
                        df_corr.dropna(subset=["相関"]),
                        x="セグメント",
                        y="相関",
                        color="キーワード",
                        barmode="group",
                        text="相関"
                    )
                    fig_corr.update_traces(
                        texttemplate="%{text:.2f}",
                        textposition="outside",
                        # 小数の桁数を調整 2026/4/16追加
                        hovertemplate=(
                            "キーワード: %{fullData.name}<br>"
                            "セグメント: %{x}<br>"
                            "相関: %{y:.3f}<extra></extra>"
                        )
                    )
                    fig_corr.update_layout(
                        height=500,
                        yaxis_title="相関係数",
                        xaxis_title="セグメント",
                        legend_title="キーワード",
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)

                # # =========================
                # # 結果テーブル
                # # =========================
                # with st.expander("相関結果テーブルを表示"):
                #     st.dataframe(
                #         df_corr.sort_values(["セグメント", "キーワード"]).reset_index(drop=True),
                #         use_container_width=True
                #     )

                # # =========================
                # # 補足
                # # =========================
                # st.caption("※ 相関は TVAL_視聴率 と検索数の日次相関。")
                # st.caption("※ 検索のみ存在する日は、TVAL_視聴率を0として扱う。")
                # st.caption("※ 分析対象日数は、検索データが存在する日付数。")
                # st.caption("※ 出稿あり/なし日数は、検索日付を母集団にしてTVALを0補完した上で判定。")

            except Exception as e:
                st.error(f"処理中にエラーが発生: {e}")

# =========================================================
# 👥リーチ・FQ
# =========================================================
else:
    tab_upload, tab_reach, tab_frequency = st.tabs(["📁データアップロード", "📈リーチ", "📈フリークエンシー"])
    
    # =========================================================
    # 📁データアップロード
    # =========================================================
    with tab_upload:
        with st.container(border=True):
            st.markdown("### ファイルをアップロード")

            bottom_cols = st.columns(2)

            with bottom_cols[0]:
                make_upload_box(
                    title = "TVAL リーチデータ",
                    info_message = "TVAL>エフェクティブリーチ＞リーチ分析＞エフェクティブリーチ＞ヒストグラム",
                    warning_message = None,
                    error_message = None,
                    key = "tval_reach_file",
                    allowed_types = ["xlsx", "xlsm", "csv"]
                )
                
            with bottom_cols[1]:
                make_upload_box(
                    title = "TVAL FQデータ",
                    info_message = "TVAL>エフェクティブリーチ＞リーチ分析＞フリークエンシー",
                    warning_message = None,
                    error_message = None,
                    key = "tval_frequency_file",
                    allowed_types = ["xlsx", "xlsm", "csv"]
                )
                
                
    # =========================================================
    # 📈リーチ
    # =========================================================
    # 2026/4/17追加
    # @st.fragment
    with tab_reach:
        @st.fragment # 2026/4/20追加
        def render_reach_fragment(): # 2026/4/20追加
            
            # st.subheader("リーチ")
            
            reach_file = get_uploaded_file_obj("tval_reach_file")

            if reach_file is None:
                st.info("先に『アップロード』タブで TVALリーチデータ をアップロードしてください。")
            else:
                try:
                    reach_data = reach.reach.read_tval_reach_data(reach_file)

                    series_options = list(dict.fromkeys(
                        s["segment_name_only"]
                        for s in reach_data["segments"]
                    ))

                    # 海藤修正5/14
                    # データの数だけでなく、内容（hash）を見ることで、ファイル変更時に確実にUIをリセットします
                    filter_key = f"reach_filter_{hash(tuple(series_options))}"

                    # 海藤修正5/14（列を3つに分けて上限入力用のカラムを確保）
                    control_col1, control_col2, control_col3 = st.columns([1.2, 0.4, 1.6])

                    with control_col1:
                        grp_tick_step = st.radio(
                            "累計出稿量（横軸）の刻み", # 海藤修正5/14（文言修正）
                            options=[10, 50, 100], # 海藤修正5/14（10を追加）
                            index=1, # 海藤修正5/14（初期値を「50」に固定）
                            horizontal=True,
                            key="reach_grp_tick_step",
                        )

                    with control_col2:
                        # 海藤修正5/14（追加した入力ボックス）
                        raw_x_limit = st.text_input(
                            "累計出稿量上限",
                            value="",
                            placeholder="自動",
                            key="reach_x_axis_limit_text"
                        )
                        try:
                            x_axis_limit = float(raw_x_limit) if raw_x_limit else None
                        except ValueError:
                            x_axis_limit = None

                    with control_col3:
                        selected_segment_names = st.multiselect(
                            "表示する系列",
                            options=series_options,
                            default=series_options,
                            key=filter_key, # 海藤修正5/14（この行を修正）
                        )

                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        st.markdown("#### リーチ率（%）")
                        fig_rate = reach.reach.build_reach_line_figure(
                            reach_data,
                            selected_segment_names=selected_segment_names,
                            grp_tick_step=grp_tick_step,
                            y_field="reach_rate",
                            y_axis_title="リーチ率（%）",
                            hover_value_label="リーチ率",
                            hover_increase_label="上昇ポイント",
                            increase_unit="ポイント",
                            y_max=100,
                            value_decimals=2,
                            value_suffix="%",
                            use_comma_for_value=False,
                            use_comma_for_increase=False,
                            x_max_limit=x_axis_limit, # 海藤修正5/14（この行を追加）
                        )

                        st.plotly_chart(
                            fig_rate,
                            use_container_width=True,
                            config={"displaylogo": False},
                            key="tval_reach_rate_chart",
                        )

                    with chart_col2:
                        st.markdown("#### リーチ数（人）")
                        fig_count = reach.reach.build_reach_line_figure(
                            reach_data,
                            selected_segment_names=selected_segment_names,
                            grp_tick_step=grp_tick_step,
                            y_field="reach_count",
                            y_axis_title="リーチ数（人）",
                            hover_value_label="リーチ数",
                            hover_increase_label="増加人数",
                            increase_unit="人",
                            y_max=None,
                            value_decimals=0,
                            value_suffix="人",
                            use_comma_for_value=True,
                            use_comma_for_increase=True,
                            y_tickformat=",.0f",
                            x_max_limit=x_axis_limit, # 海藤修正5/14（この行を追加）
                        )

                        st.plotly_chart(
                            fig_count,
                            use_container_width=True,
                            config={"displaylogo": False},
                            key="tval_reach_count_chart",
                        )

                except Exception as e:
                    st.error("TVALリーチデータの読み取りまたはグラフ生成に失敗しました。")
                    st.exception(e)
                # st.rerun(scope="fragment") # 2026/4/17追加
        render_reach_fragment() # 2026/4/20追加

    # =========================================================
    # 📈フリークエンシー
    # =========================================================
    with tab_frequency:
        @st.fragment # 2026/4/20追加
        def render_frequency_fragment(): # 2026/4/20追加
            # st.subheader("フリークエンシー")

            fq_file = get_uploaded_file_obj("tval_frequency_file")

            if fq_file is None:
                st.info("先に『アップロード』タブで TVALフリークエンシーデータ をアップロードしてください。")
            else:
                try:
                    freq_data = frequency.frequency.read_tval_frequency_data(fq_file)

                    segment_name_options = list(dict.fromkeys(
                        s["segment_name_only"] for s in freq_data["segments"]
                    ))

                    selected_segment_names = st.multiselect(
                        "表示するセグメント",
                        options=segment_name_options,
                        default=segment_name_options,
                        key="frequency_segment_filter",
                    )

                    fig = frequency.frequency.build_frequency_stacked_bar_figure(
                        freq_data,
                        selected_segment_names=selected_segment_names,
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={"displaylogo": False},
                        key="tval_frequency_chart",
                    )
                except Exception as e:
                    st.error("TVALフリークエンシーデータの読み取りまたはグラフ生成に失敗しました。")
                    st.exception(e)
        render_frequency_fragment() # 2026/4/20追加