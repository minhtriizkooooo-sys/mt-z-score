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
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #2c3e50; color: white; text-align: center; padding: 10px; }
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
Ứng dụng phân tích điểm bất thường dựa trên Z-score.  
- File CSV cần có header (ví dụ: "MaHS", "Lop", "Toán", "Lý", "Hóa").  
- Z-Score: |z-score| > ngưỡng là bất thường.  
- Hỗ trợ UTF-8.
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài Đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
    st.markdown("---")
    st.info("File CSV phải có cột số (ví dụ: Toán, Lý, Hóa) và mã hóa UTF-8.")

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

    # Cột số
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if not numeric_cols:
        st.error("Không tìm thấy cột số để tính Z-score.")
        st.stop()

    # Sidebar filter nâng cao
    st.sidebar.subheader("⚙️ Filter nâng cao")
    if 'Lop' in df.columns:
        selected_classes = st.sidebar.multiselect("Chọn lớp", options=sorted(df['Lop'].unique()), default=sorted(df['Lop'].unique()))
    else:
        selected_classes = []

    selected_subjects = st.sidebar.multiselect("Chọn môn", options=numeric_cols, default=numeric_cols)

    # Filter dữ liệu
    df_filtered = df.copy()
    if selected_classes and 'Lop' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Lop'].isin(selected_classes)]

    # Tính Z-score theo từng môn
    for col in selected_subjects:
        df_filtered[f"Z_{col}"] = stats.zscore(df_filtered[col].fillna(0))

    # Tính Z-score trung bình
    df_filtered['DiemTB'] = df_filtered[selected_subjects].mean(axis=1)
    df_filtered['Zscore'] = stats.zscore(df_filtered['DiemTB'].fillna(0))

    # Bảng gốc + bảng bất thường
    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("📋 Bảng điểm học sinh")
        st.dataframe(df_filtered, use_container_width=True)

    anomalies = df_filtered[(df_filtered[[f"Z_{sub}" for sub in selected_subjects]]).abs() > z_threshold].any(axis=1)
    df_anomalies = df_filtered[anomalies]

    with col2:
        st.subheader("⚠️ Học sinh bất thường")
        st.dataframe(df_anomalies, use_container_width=True)
        if not df_anomalies.empty:
            csv_buffer = io.StringIO()
            df_anomalies.to_csv(csv_buffer, index=False, encoding='utf-8')
            st.download_button("📥 Xuất CSV học sinh bất thường", data=csv_buffer.getvalue(), file_name="Students_BatThuong.csv")

    # ==========================
    # Biểu đồ cột: Tổng học sinh vs học sinh bất thường theo lớp
    # ==========================
    if 'Lop' in df_filtered.columns:
        st.subheader("📈 Biểu đồ tổng học sinh vs học sinh bất thường theo lớp")
        total_per_class = df_filtered.groupby('Lop').size().reset_index(name='Tổng học sinh')
        anomalies_per_class = df_anomalies.groupby('Lop').size().reset_index(name='Số bất thường')
        class_summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left').fillna(0)

        fig_bar = px.bar(
            class_summary,
            x='Lop',
            y=['Tổng học sinh', 'Số bất thường'],
            barmode='group',
            color_discrete_map={'Tổng học sinh':'#4CAF50','Số bất thường':'#FF5252'},
            title="Tổng học sinh và học sinh bất thường theo lớp",
            labels={'value':'Số học sinh', 'Lop':'Lớp'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================
    # Scatter & Histogram theo môn
    # ==========================
    st.subheader("📊 Scatter & Histogram theo môn")
    for subj in selected_subjects:
        st.markdown(f"### Môn: {subj}")
        df_filtered['Color'] = df_filtered[f"Z_{subj}"].apply(lambda x: x if abs(x)>z_threshold else 0)
        fig_scatter = px.scatter(
            df_filtered,
            x='MaHS',
            y=subj,
            size=df_filtered[f"Z_{subj}"].abs(),
            color=df_filtered[f"Z_{subj}"],
            color_continuous_scale='RdYlGn_r',
            title=f"Scatter {subj} (size/màu theo Z-score)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        fig_hist = px.histogram(
            df_filtered,
            x=subj,
            color=df_filtered[f"Z_{subj}"].apply(lambda x: 'Bất thường' if abs(x)>z_threshold else 'Bình thường'),
            color_discrete_map={'Bất thường':'#FF5252','Bình thường':'#4CAF50'},
            nbins=20,
            title=f"Histogram {subj} (Bất thường vs Bình thường)"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("📂 Vui lòng upload file CSV để bắt đầu phân tích.")

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
