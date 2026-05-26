# ライブラリの読み込み
import streamlit as st
import pandas as pd
import io

# =========================================================
# 共通アップロードUI
# - 各種ファイルアップロード欄を共通関数で描画する
# - title        : 見出し
# - file_label   : file_uploader に表示する説明文
# - key          : session_state に保存するキー（データ本体用）
# - allowed_types: 許可する拡張子
# =========================================================
def make_upload_box(title, info_message, warning_message, error_message, key, allowed_types):

    # 見出し表示
    st.markdown(f"#### {title}")

    # file_uploader完全リセット用version
    # - file_uploaderはsession_state削除だけではUI表示が残ってしまう
    # - versionを変更することで新しいwidgetとして再生成する
    version_key = f"{key}_version"

    # 初回のみversion初期化
    if version_key not in st.session_state:
        st.session_state[version_key] = 0

    # file_uploader専用key生成
    # - version付きkeyにすることで
    #   削除時にfile_uploaderを完全リセットできる
    uploader_key = f"{key}_uploader_{st.session_state[version_key]}"

    # file_uploader表示
    uploaded_file = st.file_uploader(
        title,
        key=uploader_key,
        type=allowed_types,

        # labelを非表示
        # （別途info/warningで表示しているため）
        label_visibility="collapsed",
    )
    
    # 補足説明表示
    if info_message != None:
        st.info(f"{info_message}")

    if warning_message != None:
        st.warning(f"{warning_message}")
        
    if error_message != None:
        st.error(f"{error_message}")  

    # アップロード時の保存処理
    if uploaded_file is not None:

        # UploadedFileオブジェクトを
        # そのままsession_stateに保存すると不安定なため、
        # bytes形式に変換して保存する
        st.session_state[key] = {

            # 元ファイル名
            "name": uploaded_file.name,

            # バイナリデータ本体
            "bytes": uploaded_file.getvalue(),

            # MIMEタイプ
            "type": uploaded_file.type,
        }

    # 保存済みデータ取得
    saved_file = st.session_state.get(key)

    # UI表示（アップロード状態）
    if saved_file is not None:

        # アップロード成功表示
        st.success("アップロード完了")

        # 削除ボタン
        if st.button(
            "削除",
            key=f"delete_{key}",
            use_container_width=True,
        ):

            # 保存データ削除
            if key in st.session_state:
                del st.session_state[key]

            # file_uploader完全リセット
            # - versionを変更することで
            #   uploaderを新widgetとして再生成する
            st.session_state[version_key] += 1

            # UI再描画
            st.rerun()

    # 未アップロード表示
    else:
        st.warning("未アップロード")
        

# =========================================================
# session_stateに保存したファイルを復元する関数
# - key: 保存時に使ったキー
# - 戻り値: file-like object（pandasでそのまま読める）
# =========================================================
def get_uploaded_file_obj(key):

    # session_stateから取得
    saved_file = st.session_state.get(key)

    # 未アップロードの場合はNoneを返す
    if saved_file is None:
        return None

    # bytes → file-like object に復元
    # BytesIOを使うことで「ファイルのように扱えるオブジェクト」に変換
    file_obj = io.BytesIO(saved_file["bytes"])

    # ファイル名を付与（重要）
    # pandasや後続処理で拡張子判定する場合に必要
    file_obj.name = saved_file["name"]

    # 復元したファイルを返す
    return file_obj