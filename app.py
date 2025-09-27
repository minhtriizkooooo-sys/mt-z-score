import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import io

# ==========================
# Cấu hình trang
# ==========================
st.set_page_config(page_title="Phân Tích Điểm Bất Thường", layout="wide", page_icon="📊")

# CSS tùy chỉnh
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    .stFileUploader>label { font-weight: bold; }
    .css-1d391kg { background-color: #ffffff; border-radius: 10px; padding: 20px; }
    h1 { color: #2c3e50; }
    h2 { color: #34495e; }
    .stAlert { border-radius: 5px; }
    footer { visibility: hidden; }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #2c3e50;
        color: white;
        text-align: center;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================
# Header với logo
# ==========================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        st.image("Logo_Marie_Curie.png", width=100)
    except:
        st.write("🏫 THPT Marie Curie")
with col_title:
    st.title("📊 Phân Tích Điểm Số Bất Thường Sử Dụng Z-Score")

st.markdown("""
Ứng dụng này phân tích điểm số bất thường của học sinh dựa trên z-score.  
- **Yêu cầu file CSV**: Có header (ví dụ: "MaHS", "Lop", "Toán", "Lý", "Hóa").  
- **Z-Score**: Điểm bất thường nếu |z-score| > ngưỡng (mặc định 2).  
- **Hỗ trợ UTF-8**.
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài Đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
    st.markdown("---")
    st.info("File CSV cần có cột số cho điểm (ví dụ: Toán, Lý, Hóa) và mã hóa UTF-8.")

# ==========================
# Upload file
# ==========================
uploaded_file = st.file_uploader("📂 Upload bảng điểm (CSV)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='latin1')
        st.warning("File không phải UTF-8, đã thử mã hóa latin1.")
    except Exception as e:
        st.error(f"Lỗi khi xử lý file: {str(e)}")
        st.stop()

    # Chọn các cột số
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(numeric_cols) == 0:
        st.error("Không tìm thấy cột số trong file.")
        st.stop()

    # Sidebar nâng cao: chọn multi lớp + multi môn
    with st.sidebar:
        selected_classes = st.multiselect("Chọn lớp", options=sorted(df['Lop'].unique()) if 'Lop' in df.columns else [], default=None)
        selected_subjects = st.multiselect("Chọn môn", options=numeric_cols, default=numeric_cols)

    # Tính DiemTB & Zscore dựa trên các môn được chọn
    df['DiemTB'] = df[selected_subjects].mean(axis=1)
    df['Zscore'] = stats.zscore(df['DiemTB'].fillna(0))

    # Lọc theo lớp
    if selected_classes:
        df_filtered = df[df['Lop'].isin(selected_classes)]
    else:
        df_filtered = df.copy()

    # ==========================
    # Hai bảng: tất cả & bất thường
    # ==========================
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("📋 Bảng điểm học sinh")
        st.dataframe(df_filtered.style.format({col:"{:.2f}" for col in selected_subjects}), use_container_width=True)
        csv_buf = io.StringIO()
        df_filtered.to_csv(csv_buf, index=False, encoding='utf-8')
        st.download_button("📥 Xuất CSV học sinh gốc", csv_buf.getvalue(), file_name="AllStudents.csv")

        # Học sinh bất thường
        anomalies = df_filtered[abs(df_filtered['Zscore']) > z_threshold]
        st.subheader("⚠️ Học sinh bất thường")
        st.dataframe(anomalies.style.apply(
            lambda row: ['background-color:#FF5252' if abs(row['Zscore']) > z_threshold else '' for _ in row], axis=1
        ).format({col:"{:.2f}" for col in selected_subjects}), use_container_width=True)
        csv_buf2 = io.StringIO()
        anomalies.to_csv(csv_buf2, index=False, encoding='utf-8')
        st.download_button("📥 Xuất CSV học sinh bất thường", csv_buf2.getvalue(), file_name="Anomalies.csv")

    # ==========================
    # Biểu đồ cột tổng học sinh vs học sinh bất thường theo lớp
    # ==========================
    if 'Lop' in df.columns:
        st.subheader("📈 Tổng học sinh vs học sinh bất thường theo lớp")

        total_per_class = df.groupby('Lop').size().reset_index(name='Tổng học sinh')
        anomalies_per_class = df[abs(df['Zscore']) > z_threshold].groupby('Lop').size().reset_index(name='Số bất thường')
        class_summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left').fillna(0)

        fig_bar = px.bar(
            class_summary,
            x='Lop',
            y=['Tổng học sinh','Số bất thường'],
            barmode='group',
            color_discrete_map={'Tổng học sinh':'#4CAF50','Số bất thường':'#FF5252'},
            labels={'value':'Số học sinh', 'Lop':'Lớp'},
            title="Tổng học sinh và học sinh bất thường theo lớp"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================
    # Scatter + Histogram theo môn
    # ==========================
    for subj in selected_subjects:
        st.subheader(f"📊 Phân bố {subj} (Z-score)")

        df_filtered[f'Z_{subj}'] = stats.zscore(df_filtered[subj].fillna(0))
        fig_scat = px.scatter(
            df_filtered,
            x='MaHS', y=subj,
            color=f'Z_{subj}',
            size=f'Z_{subj}',
            color_continuous_scale='RdYlGn_r',
            title=f"Scatter {subj} (Z-score gradient)"
        )
        st.plotly_chart(fig_scat, use_container_width=True)

        fig_hist = px.histogram(
            df_filtered,
            x=subj,
            nbins=20,
            color_discrete_sequence=['#4CAF50'],
            title=f"Histogram {subj}"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("Vui lòng upload file CSV để bắt đầu phân tích.")

# ==========================
# Footer
# ==========================
st.markdown("""
<div class="footer">
    <p><b>Nhóm Thực Hiện:</b> Lại Nguyễn Minh Trí và những người bạn</p>
    <p>📞 Liên hệ: 0908-083566 | 📧 Email: laingminhtri@gmail.com</p>
    <p>© 2025 Trường THPT Marie Curie - Dự án Phân Tích Điểm Bất Thường</p>
</div>
""", unsafe_allow_html=True)
