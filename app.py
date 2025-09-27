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
# CSS Header + Footer
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

# ==========================
# Upload file
# ==========================
uploaded_file = st.file_uploader("📂 Upload bảng điểm (CSV)", type="csv", help="Chọn file CSV chứa bảng điểm")
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

    # ==========================
    # Sidebar: multi lớp, chọn môn, slider Z-score
    # ==========================
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    if len(numeric_cols) == 0:
        st.error("Không tìm thấy cột số trong file CSV.")
        st.stop()

    with st.sidebar:
        st.header("🛠 Cài Đặt Phân Tích")
        selected_subjects = st.multiselect("Chọn môn để phân tích", numeric_cols, default=numeric_cols)
        z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
        if 'Lop' in df.columns:
            classes = sorted(df['Lop'].unique())
            selected_classes = st.multiselect("Chọn lớp để hiển thị", classes, default=classes)
        else:
            selected_classes = None

    # Filter theo lớp
    if selected_classes is not None:
        df_filtered = df[df['Lop'].isin(selected_classes)].copy()
    else:
        df_filtered = df.copy()

    # ==========================
    # Tính Z-score theo môn
    # ==========================
    for subj in selected_subjects:
        df_filtered[f'Z_{subj}'] = stats.zscore(df_filtered[subj].fillna(0))
        # Highlight cực bất thường
        df_filtered[f'Highlight_{subj}'] = np.where(df_filtered[f'Z_{subj}'].abs() > z_threshold, 'Extremely Abnormal', 'Normal')
        # Size scatter
        df_filtered[f'Size_{subj}'] = np.maximum(np.abs(df_filtered[f'Z_{subj}'])*5, 5)  # size >=5

    # ==========================
    # Bảng học sinh
    # ==========================
    st.subheader("📋 Bảng gốc")
    st.dataframe(df_filtered.style.format({col: "{:.2f}" for col in selected_subjects}), use_container_width=True)

    # Bảng học sinh bất thường
    st.subheader("⚠️ Danh sách học sinh bất thường")
    mask_anomaly = np.zeros(len(df_filtered), dtype=bool)
    for subj in selected_subjects:
        mask_anomaly |= df_filtered[f'Z_{subj}'].abs() > z_threshold
    anomalies = df_filtered[mask_anomaly]

    st.dataframe(anomalies.style.format({col: "{:.2f}" for col in selected_subjects}), use_container_width=True)
    # Download CSV
    csv_buffer = io.StringIO()
    anomalies.to_csv(csv_buffer, index=False)
    st.download_button("📥 Xuất CSV học sinh bất thường", data=csv_buffer.getvalue(), file_name="Students_Abnormal.csv", mime="text/csv")

    # ==========================
    # Biểu đồ cột tổng học sinh vs bất thường theo lớp
    # ==========================
    if 'Lop' in df_filtered.columns:
        st.subheader("📈 Biểu đồ cột: Tổng học sinh vs Học sinh bất thường")
        total_per_class = df_filtered.groupby('Lop').size().reset_index(name='Tổng học sinh')
        anomalies_per_class = anomalies.groupby('Lop').size().reset_index(name='Học sinh bất thường')
        class_summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left')
        class_summary['Học sinh bất thường'] = class_summary['Học sinh bất thường'].fillna(0)

        fig_bar = px.bar(
            class_summary,
            x='Lop',
            y=['Tổng học sinh', 'Học sinh bất thường'],
            barmode='group',
            color_discrete_map={'Tổng học sinh': '#4CAF50', 'Học sinh bất thường': '#FF5252'},
            title="Tổng học sinh vs Học sinh bất thường theo lớp",
            labels={'value': 'Số học sinh', 'Lop':'Lớp'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================
    # Scatter & histogram theo môn
    # ==========================
    for subj in selected_subjects:
        st.subheader(f"📊 Scatter & Histogram: {subj}")
        fig_scat = px.scatter(
            df_filtered,
            x='MaHS',
            y=subj,
            color=f'Highlight_{subj}',
            size=f'Size_{subj}',
            color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
            title=f"Scatter {subj} (Z-score gradient + highlight cực bất thường)",
            hover_data=[subj, f'Z_{subj}', 'Lop']
        )
        st.plotly_chart(fig_scat, use_container_width=True)

        # Histogram Z-score
        fig_hist = px.histogram(
            df_filtered,
            x=f'Z_{subj}',
            nbins=20,
            color=f'Highlight_{subj}',
            color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
            title=f"Histogram Z-score môn {subj}"
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
