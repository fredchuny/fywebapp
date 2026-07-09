import streamlit as st
from supabase import create_client, Client

# 🔐 在 Streamlit Cloud，系統會自動從你設定的 Secrets 中抓取這兩個金鑰
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# 初始化 Supabase 雲端資料庫連線
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 網頁介面開始 ---
st.title("📊 PHQ-9 完整健康評估系統")
st.caption("數據將直接同步至 Supabase 雲端資料庫")

st.write("---")

# 填寫者基本資料輸入框
user_id = st.text_input("請輸入使用者 ID (例如: patient_001):", value="patient_test_02")
full_name = st.text_input("請輸入真實姓名:", value="王大同")

st.write("### 過去兩星期以來，您有多少天受以下問題困擾？")
st.write("---")

# 定義單選鈕的選項與對應的分數
options = {
    0: "0 - 完全沒有",
    1: "1 - 有幾天",
    2: "2 - 一半以上的天數",
    3: "3 - 幾乎天天"
}

# 完整 PHQ-9 九道題目（單選鈕水平排列）
q1_score = st.radio("1. 做任何事情都提不起勁或沒有樂趣", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q2_score = st.radio("2. 感到心情低落、沮喪或絕望", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q3_score = st.radio("3. 入睡困難、睡不安穩或睡太多", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q4_score = st.radio("4. 感到疲倦或沒有活力", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
st.write("---")
q5_score = st.radio("5. 食慾不振或吃得太多", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q6_score = st.radio("6. 覺得自己很糟、覺得自己很失敗，或讓家人失望", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q7_score = st.radio("7. 專注事情有困難，例如看報紙或看電視時", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
q8_score = st.radio("8. 動作或說話速度慢到別人察覺？或正好相反，煩躁不安到處走動？", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)
st.write("---")
q9_score = st.radio("9. 有自殺或傷害自己的想法", options=list(options.keys()), format_func=lambda x: options[x], horizontal=True)

# 整合 9 題分數並計算總分
q_list = [q1_score, q2_score, q3_score, q4_score, q5_score, q6_score, q7_score, q8_score, q9_score]  
total_score = sum(q_list)

st.write("---")
st.write(f"### 📊 目前評估總分：**{total_score} 分**")

# 根據總分給予初步的臨床提示
if total_score >= 20:
    st.warning("提示：重度憂鬱傾向，建議尋求專業醫療或心理諮商協助。")
elif total_score >= 15:
    st.warning("提示：中重度憂鬱傾向，請多留意自身心理狀態並尋求支持。")
elif total_score >= 10:
    st.info("提示：中度憂鬱傾向。")
elif total_score >= 5:
    st.info("提示：輕微憂鬱傾向。")
else:
    st.success("提示：情緒狀態良好。")

st.write("---")

# 送出問卷按鈕
if st.button("確認送出並上傳雲端"):
    if not user_id or not full_name:
        st.error("❌ 請填寫 ID 與姓名！")
    else:
        try:
            # 1. 寫入或更新使用者基本資料
            user_data = {"id": user_id, "full_name": full_name, "role": "patient"}
            supabase.table("phq9_users").upsert(user_data).execute()
            
            # 2. 完整寫入 9 題的分數與總分紀錄
            response_data = {
                "user_id": user_id,
                "q1": q1_score, "q2": q2_score, "q3": q3_score, "q4": q4_score, "q5": q5_score, 
                "q6": q6_score, "q7": q7_score, "q8": q8_score, "q9": q9_score,
                "total_score": total_score
            }
            supabase.table("phq9_responses").insert(response_data).execute()
            
            st.success(f"🎉 成功！數據已完整寫入雲端。使用者：{full_name}，總分：{total_score} 分。")
        except Exception as e:
            st.error(f"寫入失敗：{e}")


# ==================================================================
# 🔍 歷史紀錄查詢區塊 (新增功能)
# ==================================================================
st.write("## 🔍 歷史結果查詢")
st.caption("輸入上方的使用者 ID 後，點擊下方按鈕即可撈取雲端歷史病歷")

if st.button("查看我的歷史評估紀錄"):
    if not user_id:
        st.error("❌ 請先在上方「請輸入使用者 ID」欄位填入您的 ID 才能查詢！")
    else:
        try:
            with st.spinner("正在從雲端資料庫撈取資料..."):
                # 這裡使用了我們之前在 Colab 驗證成功的 desc=False 語法
                response = supabase.table("phq9_responses") \
                                   .select("created_at, total_score") \
                                   .eq("user_id", user_id) \
                                   .order("created_at", desc=False) \
                                   .execute()
            
            if response.data:
                st.success(f"🎉 成功找到該用戶的 {len(response.data)} 筆歷史紀錄：")
                
                # 用極簡、直覺的方式一筆一筆印出結果
                for index, record in enumerate(response.data, 1):
                    # 格式化雲端時間戳記 (移除毫秒，讓畫面乾淨)
                    clean_date = record['created_at'].split('.')[0].replace('T', ' ')
                    score = record['total_score']
                    
                    # 根據當時的分數標示嚴重度顏色
                    if score >= 15:
                        status = "🔴 中重度/重度"
                    elif score >= 10:
                        status = "🟡 中度"
                    else:
                        status = "🟢 輕微/良好"
                        
                    st.write(f"**第 {index} 次紀錄** | 📅 時間: `{clean_date}` | 📊 總分: **{score} 分** ({status})")
            else:
                st.info(f"查無此 ID (`{user_id}`) 的歷史紀錄。試著先在上方提交一筆問卷吧！")
                
        except Exception as e:
            st.error(f"撈取資料失敗，錯誤訊息：{e}")
