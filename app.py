import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import bcrypt

# --- セッション初期化 ---
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- 共通ログイン情報（チーム用） ---
stored_user = "smileteam2025"
stored_hash = "$2b$12$effdZdl.BpS2HVDeNg0X6.nrJfzUcMNcu/dKO6w5YSoSm9iuaCHTC"  # ← ここに事前生成したハッシュを貼る

# --- ログアウト処理 ---
def logout():
    st.session_state.clear()
    st.rerun()

# --- DB設定 ---
DB_NAME = "inventory.db"
RECOMMEND_THRESHOLD = 50

# --- DB初期化 ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            name TEXT,
            category TEXT,
            cost_price REAL,
            selling_price REAL,
            stock INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- データ操作関数 ---
def get_items():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    return df

def add_item(sku, name, category, cost, price, stock):
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO items (sku, name, category, cost_price, selling_price, stock, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, category, cost, price, stock, now, now))
    conn.commit()
    conn.close()

def update_item(item_id, sku, name, category, cost, price, stock):
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items
        SET sku = ?, name = ?, category = ?, cost_price = ?, selling_price = ?, stock = ?, updated_at = ?
        WHERE id = ?
    """, (sku, name, category, cost, price, stock, now, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def export_csv(df):
    return df.to_csv(index=False).encode("utf-8")

def import_csv(file):
    df = pd.read_csv(file)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce")
    df["selling_price"] = pd.to_numeric(df["selling_price"], errors="coerce")
    df["stock"] = pd.to_numeric(df["stock"], errors="coerce").fillna(0).astype(int)

    for _, row in df.iterrows():
        add_item(
            row.get("sku", ""),
            row["name"],
            row["category"],
            row["cost_price"],
            row["selling_price"],
            int(row["stock"])
        )

# --- 在庫管理UI（ログイン後のみ表示） ---
def show_inventory_ui():
    init_db()
    st.set_page_config(page_title="在庫管理", page_icon="📦")
    st.sidebar.button("🔓 ログアウト", on_click=logout)
    st.title("SMILE☺BASE 在庫管理")

    # 商品登録
    with st.form("add_form"):
        st.subheader("🆕 商品登録")
        sku = st.text_input("SKU（商品コード）")
        name = st.text_input("商品名")
        category = st.text_input("カテゴリ")
        cost = st.number_input("仕入れ値", min_value=0.0)
        price = st.number_input("販売価格", min_value=0.0)
        stock = st.number_input("在庫数", min_value=0, step=1)
        submitted = st.form_submit_button("登録する")
        if submitted and name and sku:
            add_item(sku, name, category, cost, price, stock)
            st.success(f"✅ {name} を登録しました")

    # 商品一覧
    st.subheader("📦 商品一覧")
    df = get_items()

    if not df.empty:
        df["利益額"] = df["selling_price"] - df["cost_price"]
        df["利益率（%）"] = (df["利益額"] / df["cost_price"] * 100).round(2)
        df["おすすめ"] = df["利益率（%）"].apply(lambda x: "🌟おすすめ" if x >= RECOMMEND_THRESHOLD else "")
        st.dataframe(df)

        # 編集・削除
        st.subheader("✏️ 商品編集・削除")
        selected_id = st.selectbox("編集・削除する商品ID", df["id"])
        selected_row = df[df["id"] == selected_id].iloc[0]

        with st.form("edit_form"):
            new_sku = st.text_input("SKU", selected_row["sku"] or "")
            new_name = st.text_input("商品名", selected_row["name"] or "")
            new_category = st.text_input("カテゴリ", selected_row["category"] or "")
            new_cost = st.number_input("仕入れ値", value=float(selected_row["cost_price"] or 0))
            new_price = st.number_input("販売価格", value=float(selected_row["selling_price"] or 0))
            new_stock = st.number_input("在庫数", value=int(selected_row["stock"] or 0), step=1)

            update_btn = st.form_submit_button("更新する")
            delete_btn = st.form_submit_button("⚠️ 削除する")

            if update_btn:
                update_item(selected_id, new_sku, new_name, new_category, new_cost, new_price, new_stock)
                st.success("✅ 商品情報を更新しました")
            elif delete_btn:
                delete_item(selected_id)
                st.warning("⚠️ 商品を削除しました")

        # CSVエクスポート
        st.subheader("📤 CSVエクスポート")
        st.download_button(
            label="📁 CSVをダウンロード",
            data=export_csv(df),
            file_name="inventory.csv",
            mime="text/csv"
        )

        # おすすめ商品
        st.subheader("🌟 おすすめ商品一覧")
        recommend_df = df[df["おすすめ"] == "🌟おすすめ"]
        if not recommend_df.empty:
            st.dataframe(recommend_df)
        else:
            st.info("おすすめ商品はまだありません。")

    # CSVインポート
    st.subheader("📁 CSVインポート")
    csv_file = st.file_uploader("CSVファイルを選択", type=["csv"])
    if csv_file and st.button("インポートする"):
        import_csv(csv_file)
        st.success("✅ CSVから商品をインポートしました")

    # 全データ削除
    st.subheader("🗑️ 全データ削除")
    if st.button("⚠️ 全商品データを削除する"):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='items'")
        conn.commit()
        conn.close()
        st.warning("⚠️ 全商品データを削除し、IDをリセットしました")

# --- ログインUI ---
st.title("SMILE☺BASE ログイン")
username = st.text_input("ユーザー名")
password = st.text_input("パスワード", type="password")
login = st.button("ログイン")
# --- ログイン判定　---
if login:
    if username == stored_user and bcrypt.checkpw(password.encode(), stored_hash.encode()):
        st.session_state["authentication_status"] = True
        st.session_state["username"] = username
    else:
        st.session_state["authentication_status"] = False

# --- ログイン状態による分岐 ---
if st.session_state["authentication_status"] is None:
    st.warning("ユーザー名とパスワードを入力してください。")