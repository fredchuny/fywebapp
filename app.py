import streamlit as st
from supabase import create_client, Client

# 🔐 在 Streamlit Cloud，系統會自動從你剛才在 Advanced settings 設定的 Secrets 中抓取這兩個金鑰
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# 初始化 Supabase 雲端資料庫連線
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 網頁介面開始 ---
st.title("📊 PHQ-9 簡易評估系統")
st.caption("數據將直接同步至 Supabase 雲端資料庫")

st.write("---")

# 填寫者基本資料輸入框
user_id = st.text_input("請輸入使用者 ID (例如: patient_001):", value="patient_test_02")
full_name = st.text_input("請輸入真實姓名:", value="王大同")

st.write("### 評估題目 (請輸入 0 ~ 3 分)")
st.caption("0: 完全沒有 | 1: 有幾天 | 2: 一半以上的天數 | 3: 幾乎天天")

# 用最基礎的數字輸入框，確保載入速度極快
q1 = st.number_input("1. 做任何事都提不起勁或沒有樂趣", min_value=0, max_value=3, value=0)
q2 = st.number_input("2. 感到心情 low、沮喪或絕望", min_value=0, max_value=3, value=0)
q3 = st.number_input("3. 入睡困難、睡不安穩或睡太多", min_value=0, max_value=3, value=0)

# 計算總分 (目前示範前 3 題，未來你可以隨時在 GitHub 修改補滿到 q9)
q_list = [q1, q2, q3]  
total_score = sum(q_list)

st.write(f"**目前累計總分：{total_score} 分**")

# 送出按鈕
if st.button("確認送出並上傳雲端"):
    if not user_id or not full_name:
        st.error("❌ 請填寫 ID 與姓名！")
    else:
        try:
            # 1. 寫入或更新使用者資料
            user_data = {"id": user_id, "full_name": full_name, "role": "patient"}
            supabase.table("phq9_users").upsert(user_data).execute()
            
            # 2. 寫入分數紀錄 (後續欄位先預設填 0)
            response_data = {
                "user_id": user_id,
                "q1": q1, "q2": q2, "q3": q3,
                "q4": 0, "q5": 0, "q6": 0, "q7": 0, "q8": 0, "q9": 0,
                "total_score": total_score
            }
            supabase.table("phq9_responses").insert(response_data).execute()
            
            st.success(f"🎉 成功！資料已寫入雲端。使用者：{full_name}，總分：{total_score} 分。")
        except Exception as e:
            st.error(f"寫入失敗：{e}")
