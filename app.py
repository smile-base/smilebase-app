import sqlite3
from datetime import datetime
import streamlit as st
import pandas as pd

DB_NAME = "inventory.db"
LOW_STOCK_THRESHOLD = 5

# DB接続と初期化
def connect_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category TEXT,
            price REAL,
            quantity INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn

# 商品追加
def add_item(name, sku, category, price, quantity):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO items (name, sku, category, price, quantity, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, sku, category, price, quantity, datetime.now().isoformat()))
        conn.commit()
        st.success(f"✅ {name} を追加しました")
    except sqlite3.IntegrityError:
        st.error("❌ SKUが重複しています")
    finally:
        conn.close()

# 商品取得（検索）
def get_inventory(keyword=""):
    conn = connect_db()
    cursor = conn.cursor()
    if keyword:
        cursor.execute("""
            SELECT name, sku, category, price, quantity FROM items
            WHERE name LIKE ? OR sku LIKE ?
        """, (f"%{keyword}%", f"%{keyword}%"))
    else:
        cursor.execute("SELECT name, sku, category, price, quantity FROM items")
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["商品名", "SKU", "カテゴリ", "価格", "在庫数"])

# 在庫更新
def update_quantity(sku, amount):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items
        SET quantity = quantity + ?, updated_at = ?
        WHERE sku = ?
    """, (amount, datetime.now().isoformat(), sku))
    conn.commit()
    conn.close()

# 商品取得（SKU指定）
def get_item_by_sku(sku):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, category, price, quantity FROM items WHERE sku = ?", (sku,))
    item = cursor.fetchone()
    conn.close()
    return item

# 商品編集
def edit_item(sku, name, category, price, quantity):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items
        SET name = ?, category = ?, price = ?, quantity = ?, updated_at = ?
        WHERE sku = ?
    """, (name, category, price, quantity, datetime.now().isoformat(), sku))
    conn.commit()
    conn.close()

# 商品削除
def delete_item(sku):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE sku = ?", (sku,))
    conn.commit()
    conn.close()

# 在庫少ない商品取得
def get_low_stock_items():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, sku, category, price, quantity FROM items
        WHERE quantity < ?
    """, (LOW_STOCK_THRESHOLD,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["商品名", "SKU", "カテゴリ", "価格", "在庫数"])

# カテゴリ一覧取得
def get_categories():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

# 最近追加された商品
def get_recent_items(limit=5):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, sku, category, price, quantity, updated_at
        FROM items
        ORDER BY datetime(updated_at) DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["商品名", "SKU", "カテゴリ", "価格", "在庫数", "更新日時"])

# Streamlit UI
st.set_page_config(page_title="在庫管理", page_icon="📦")
st.title("SMILE☻BASE 在庫管理")

# 商品追加フォームと在庫検索を左右に分割
col1, col2 = st.columns([1, 2])

with col1:
    with st.form("add_form"):
        st.markdown("### ➕ 商品追加")
        name = st.text_input("商品名")
        sku = st.text_input("SKU")
        category = st.text_input("カテゴリ")
        price = st.number_input("価格", min_value=0.0, format="%.2f")
        quantity = st.number_input("数量", min_value=0, step=1)
        submitted = st.form_submit_button("追加")
        if submitted:
            if name and sku:
                add_item(name, sku, category, price, quantity)
            else:
                st.error("❌ 商品名とSKUは必須です")

with col2:
    st.markdown("### 🔍 在庫検索")
    keyword = st.text_input("商品名またはSKUで検索")
    df = get_inventory(keyword)

st.markdown("### 🆕 最近追加された商品")
recent_df = get_recent_items(limit=5)
if not recent_df.empty:
    st.dataframe(recent_df.style.highlight_max(axis=0, color="#D1C4E9"))
else:
    st.info("最近追加された商品はまだありません。")

# CSVエクスポート（検索結果）
st.markdown("### 📤 CSVエクスポート")
if not df.empty:
    filename = f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 検索結果をCSVでダウンロード", csv, filename, mime="text/csv")
else:
    st.info("検索結果が空です。CSV出力できません。")

# 色分け表示
styled_df = df.style.applymap(
    lambda val: 'background-color: #ffe6e6' if isinstance(val, int) and val < LOW_STOCK_THRESHOLD else ''
)
st.dataframe(styled_df)

# 在庫追加
if not df.empty:
    selected_sku = st.selectbox("SKUを選択して在庫追加", df["SKU"])
    amount = st.number_input("追加する在庫数", min_value=1, step=1)
    if st.button("在庫を追加"):
        update_quantity(selected_sku, amount)
        st.success(f"✅ {selected_sku} の在庫を {amount} 個追加しました！")
        df = get_inventory(keyword)
        st.dataframe(df)

# 商品編集・削除
st.markdown("### ✏️ 商品編集・削除")
if not df.empty:
    sku_list = df["SKU"].tolist()
    selected_edit_sku = st.selectbox("編集するSKUを選択", sku_list)
    item = get_item_by_sku(selected_edit_sku)
    if item:
        name_edit = st.text_input("商品名（編集）", item[0])
        category_edit = st.text_input("カテゴリ（編集）", item[1])
        price_edit = st.number_input("価格（編集）", value=item[2], format="%.2f")
        quantity_edit = st.number_input("在庫数（編集）", value=item[3], step=1)

        if st.button("更新する"):
            edit_item(selected_edit_sku, name_edit, category_edit, price_edit, quantity_edit)
            st.success("✅ 商品情報を更新しました")

        if st.button("⚠️ 商品を削除する"):
            delete_item(selected_edit_sku)
            st.warning("⚠️ 商品を削除しました")

# 在庫警告表示
st.markdown("### 🚨 在庫が少ない商品")
low_stock_df = get_low_stock_items()
if not low_stock_df.empty:
    st.warning("⚠️ 在庫が少ない商品があります！")
    st.dataframe(low_stock_df.style.highlight_max(axis=0, color="red"))
else:
    st.info("✅ すべての在庫は十分です")

# カテゴリ別表示とCSV出力
st.markdown("### 📁 カテゴリ別表示")
categories = get_categories()
selected_categories = st.multiselect("表示するカテゴリを選択", categories)

for cat in selected_categories:
    st.markdown(f"## 📁 {cat}")
    cat_df = df[df["カテゴリ"] == cat]
    st.dataframe(cat)