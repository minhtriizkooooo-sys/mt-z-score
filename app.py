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

# ==========================
# CSS
# ==========================
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
# Header logo
# ==========================
col_logo, col_title = st.columns([1,6])
with col_logo:
    try:
        st.image("Logo_Marie_Curie.png", width=100)
    except:
        st.write("🏫 THPT Marie Curie")
with col_title:
    st.title("📊 Phân Tích Điểm Số Bất Thường Sử Dụng Z-Score")

st.markdown("""
Ứng dụng phân tích điểm bất thường dựa trên Z-score.  
- **Yêu cầu file CSV**: Có header (ví dụ: "MaHS", "Lop", "Toán", "Lý", "Hóa").  
- **Z-Score**: |z| > ngưỡng => bất thường.  
- Hỗ trợ UTF-8.
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
    st.markdown("---")
    st.info("File CSV cần có các cột số và mã hóa UTF-8.")

# ==========================
# Upload file
# ==========================
uploaded_file = st.file_uploader("📂 Upload bảng điểm (CSV)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='latin1')
        st.warning("File không phải UTF-8, đã thử latin1.")
    except Exception as e:
        st.error(f"Lỗi xử lý file: {e}")
        st.stop()

    # Các cột số
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(numeric_cols)==0:
        st.error("Không tìm thấy cột số.")
        st.stop()

    # Multi môn & multi lớp
    subjects = st.multiselect("Chọn môn phân tích", numeric_cols, default=numeric_cols)
    classes = st.multiselect("Chọn lớp để lọc", sorted(df['Lop'].unique()), default=sorted(df['Lop'].unique()))

    # Lọc lớp
    df_filtered = df[df['Lop'].isin(classes)].copy()

    # Tính Z-score từng môn & highlight
    for subj in subjects:
        df_filtered[f'Z_{subj}'] = stats.zscore(df_filtered[subj].fillna(0))
        df_filtered[f'Highlight_{subj}'] = np.where(df_filtered[f'Z_{subj}'].abs()>z_threshold,'Extremely Abnormal','Normal')
        df_filtered[f'Size_{subj}'] = df_filtered[f'Z_{subj}'].abs() * 10 + 5

    # ==========================
    # Bảng tổng hợp
    # ==========================
    st.subheader("📋 Bảng học sinh gốc")
    st.dataframe(df_filtered, use_container_width=True)
    csv_buffer = io.StringIO()
    df_filtered.to_csv(csv_buffer, index=False, encoding='utf-8')
    st.download_button("📥 Xuất CSV học sinh gốc", csv_buffer.getvalue(), "Original_Students.csv")

    # Bảng học sinh bất thường
    anomaly_mask = np.zeros(len(df_filtered),dtype=bool)
    for subj in subjects:
        anomaly_mask |= df_filtered[f'Z_{subj}'].abs()>z_threshold
    anomalies = df_filtered[anomaly_mask]

    st.subheader(f"⚠️ Học sinh bất thường (|Z| > {z_threshold})")
    st.dataframe(anomalies, use_container_width=True)
    csv_buffer2 = io.StringIO()
    anomalies.to_csv(csv_buffer2,index=False,encoding='utf-8')
    st.download_button("📥 Xuất CSV học sinh bất thường", csv_buffer2.getvalue(), "Anomalies_Students.csv")

    # ==========================
    # Biểu đồ cột theo lớp
    # ==========================
    st.subheader("📈 Biểu đồ cột: Tổng học sinh vs Học sinh bất thường theo lớp")
    total_per_class = df_filtered.groupby('Lop').size().reset_index(name='Tổng học sinh')
    anomalies_per_class = anomalies.groupby('Lop').size().reset_index(name='Số bất thường')
    class_summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left')
    class_summary['Số bất thường'] = class_summary['Số bất thường'].fillna(0)

    fig_bar = px.bar(
        class_summary,
        x='Lop',
        y=['Tổng học sinh','Số bất thường'],
        barmode='group',
        color_discrete_map={'Tổng học sinh':'#4CAF50','Số bất thường':'#FF5252'},
        title="Tổng số học sinh và số học sinh bất thường theo lớp"
    )
    fig_bar.update_layout(xaxis_tickangle=-45, legend_title_text='')
    st.plotly_chart(fig_bar,use_container_width=True)

    # ==========================
    # Scatter + histogram
    # ==========================
    for subj in subjects:
        st.subheader(f"🔹 Scatter & Histogram: {subj}")

        # Scatter
        fig_scat = px.scatter(
            df_filtered,
            x='MaHS',
            y=subj,
            color=f'Highlight_{subj}',
            size=f'Size_{subj}',
            color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
            title=f"Scatter {subj} (Z-score gradient + highlight cực bất thường)",
            hover_data=['MaHS', subj, f'Z_{subj}', 'Lop']
        )
        st.plotly_chart(fig_scat,use_container_width=True)

        # Histogram
        fig_hist = px.histogram(
            df_filtered,
            x=subj,
            nbins=20,
            color=f'Highlight_{subj}',
            color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
            title=f"Histogram {subj} phân bố điểm & bất thường"
        )
        st.plotly_chart(fig_hist,use_container_width=True)

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
