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
# CSS tùy chỉnh
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

st.markdown("""
Ứng dụng này phân tích điểm số bất thường của học sinh dựa trên z-score.  
- **Yêu cầu file CSV**: Có header (ví dụ: "MaHS", "Lop", "Toan", "Ly", "Hoa").  
- **Z-Score**: Điểm bất thường nếu |z-score| > ngưỡng (mặc định 2).  
- **Hỗ trợ tiếng Việt**: File CSV nên lưu ở định dạng UTF-8.
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài Đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
    st.markdown("---")
    st.info("File CSV cần có cột số cho điểm (ví dụ: Toan, Ly, Hoa) và mã hóa UTF-8.")

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

    # Chuẩn hóa tên cột
    df.columns = [c.strip() for c in df.columns]
    df.columns = [c.capitalize() for c in df.columns]

    # Chọn các cột điểm
    subject_cols = [c for c in df.columns if c not in ['MaHS','Lop','Stt']]

    # Sidebar multi-select môn + lớp
    with st.sidebar:
        selected_subjects = st.multiselect("Chọn môn để phân tích", subject_cols, default=subject_cols)
        unique_classes = sorted(df['Lop'].unique())
        selected_classes = st.multiselect("Chọn lớp để hiển thị", unique_classes, default=unique_classes)

    # Filter lớp
    df_filtered = df[df['Lop'].isin(selected_classes)].copy()

    # Tính Z-score từng môn
    for subj in selected_subjects:
        df_filtered[f'Z_{subj}'] = stats.zscore(df_filtered[subj].fillna(0))
        df_filtered[f'Highlight_{subj}'] = np.where(abs(df_filtered[f'Z_{subj}']) >= z_threshold,
                                                    'Extremely Abnormal', 'Normal')
        # Size scatter (absolute Z)
        df_filtered[f'Size_{subj}'] = np.abs(df_filtered[f'Z_{subj}'])*5 + 5

    # ==========================
    # Hiển thị tổng số học sinh bất thường
    # ==========================
    st.subheader("📊 Thống kê học sinh bất thường")
    anomalies_count = ((df_filtered[[f'Z_{s}' for s in selected_subjects]].abs() > z_threshold).any(axis=1)).sum()
    st.markdown(f"- Tổng số học sinh trong lớp đã chọn: **{len(df_filtered)}**")
    st.markdown(f"- Số học sinh bất thường: **{anomalies_count}**")

    # ==========================
    # Hiển thị 2 bảng dữ liệu
    # ==========================
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 Bảng học sinh gốc")
        st.dataframe(df_filtered, use_container_width=True)
        csv_buffer = io.StringIO()
        df_filtered.to_csv(csv_buffer, index=False, encoding='utf-8')
        st.download_button("📥 Xuất CSV học sinh gốc", data=csv_buffer.getvalue(),
                           file_name="Students_All.csv", mime="text/csv")

    with col2:
        st.subheader("⚠️ Học sinh bất thường")
        anomalies_df = df_filtered[(df_filtered[[f'Z_{s}' for s in selected_subjects]].abs() > z_threshold).any(axis=1)]
        st.dataframe(anomalies_df, use_container_width=True)
        csv_buffer2 = io.StringIO()
        anomalies_df.to_csv(csv_buffer2, index=False, encoding='utf-8')
        st.download_button("📥 Xuất CSV học sinh bất thường", data=csv_buffer2.getvalue(),
                           file_name="Students_Anomalies.csv", mime="text/csv")

    # ==========================
    # Biểu đồ cột: tổng học sinh & học sinh bất thường
    # ==========================
    st.subheader("📈 Biểu đồ cột: tổng học sinh vs học sinh bất thường theo lớp")
    summary_total = df_filtered.groupby('Lop').size().reset_index(name='Tổng học sinh')
    summary_anom = anomalies_df.groupby('Lop').size().reset_index(name='Học sinh bất thường')
    summary = pd.merge(summary_total, summary_anom, on='Lop', how='left')
    summary['Học sinh bất thường'] = summary['Học sinh bất thường'].fillna(0)

    fig_bar = px.bar(summary, x='Lop', y=['Tổng học sinh', 'Học sinh bất thường'],
                     barmode='group',
                     color_discrete_map={'Tổng học sinh':'#4CAF50', 'Học sinh bất thường':'#FF5252'},
                     title="Số học sinh và học sinh bất thường theo lớp")
    st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================
    # Scatter + Histogram theo từng môn
    # ==========================
    st.subheader("📊 Scatter & Histogram theo môn")
    for subj in selected_subjects:
        st.markdown(f"### Môn: {subj}")

        # Scatter
        fig_scat = px.scatter(
            df_filtered,
            x='MaHS',
            y=subj,
            color=f'Highlight_{subj}',
            size=f'Size_{subj}',
            color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
            title=f"Scatter {subj} (Z-score gradient + highlight cực bất thường)",
            hover_data={'MaHS':True, subj:True, f'Z_{subj}':True, 'Lop':df_filtered['Lop']}
        )
        st.plotly_chart(fig_scat, use_container_width=True)

        # Histogram
        fig_hist = px.histogram(df_filtered, x=f'Z_{subj}', nbins=20,
                                color=f'Highlight_{subj}',
                                color_discrete_map={'Normal':'lightblue','Extremely Abnormal':'red'},
                                title=f"Histogram Z-score {subj}")
        st.plotly_chart(fig_hist, use_container_width=True)

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
