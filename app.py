import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
import io

# ==========================
# Cấu hình trang
# ==========================
st.set_page_config(page_title="Phân Tích Điểm Bất Thường - Nâng Cao", layout="wide", page_icon="📊")

# ==========================
# CSS tùy chỉnh
# ==========================
st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 5px; }
    .stFileUploader>label { font-weight: bold; }
    h1 { color: #2c3e50; }
    h2 { color: #34495e; }
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
    st.title("📊 Phân Tích Điểm Số Bất Thường - Dashboard Nâng Cao")

st.markdown("""
Ứng dụng phân tích điểm số bất thường dựa trên z-score, hiển thị bảng và biểu đồ nâng cao.
- **Yêu cầu file CSV**: cột "MaHS", "Lop", các cột điểm số (Toán, Lý, Hóa,...)
- **Z-Score**: Điểm bất thường nếu |z-score| > ngưỡng
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài Đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1)
    st.markdown("---")
    st.info("File CSV cần có cột số cho điểm và cột MaHS, Lop.")

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
        st.warning("File không phải UTF-8, đã thử latin1.")

    numeric_cols = df.select_dtypes(include=np.number).columns
    if len(numeric_cols) == 0:
        st.error("Không tìm thấy cột số (điểm) trong CSV.")
        st.stop()

    # Tính Điểm TB và Z-score
    df["DiemTB"] = df[numeric_cols].mean(axis=1)
    df["Zscore"] = stats.zscore(df["DiemTB"].fillna(0))
    anomalies = df[abs(df["Zscore"]) > z_threshold]

    display_cols = ["MaHS", "DiemTB", "Zscore"]
    if 'Lop' in df.columns:
        display_cols.insert(1, "Lop")

    # ==========================
    # Bảng tổng hợp
    # ==========================
    st.subheader("📋 Bảng tổng hợp học sinh")
    st.dataframe(df[display_cols].style.format({"DiemTB": "{:.2f}", "Zscore": "{:.2f}"}), use_container_width=True)

    # ==========================
    # Lọc theo lớp
    # ==========================
    if 'Lop' in df.columns:
        st.subheader("🔎 Lọc theo lớp")
        classes = sorted(df['Lop'].unique())
        selected_class = st.selectbox("Chọn lớp", ["Tất cả"] + classes)

        if selected_class != "Tất cả":
            df_filtered = df[df['Lop'] == selected_class]
            anomalies_filtered = anomalies[anomalies['Lop'] == selected_class]
        else:
            df_filtered = df
            anomalies_filtered = anomalies

        st.markdown(f"- Tổng học sinh: **{len(df_filtered)}**")
        st.markdown(f"- Học sinh bất thường: **{len(anomalies_filtered)}**")
        st.markdown(f"- Điểm trung bình: **{df_filtered['DiemTB'].mean():.2f}**")

    # ==========================
    # Biểu đồ cột: Tổng học sinh vs bất thường
    # ==========================
    if 'Lop' in df.columns:
        st.subheader("📈 Biểu đồ cột Tổng học sinh vs Học sinh bất thường")
        anomalies_per_class = anomalies.groupby('Lop').size().reset_index(name='Số bất thường')
        total_per_class = df.groupby('Lop').size().reset_index(name='Tổng học sinh')
        summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left').fillna(0)
        summary['Ratio'] = summary['Số bất thường'] / summary['Tổng học sinh']

        # Gradient màu theo tỉ lệ bất thường
        colors = [px.colors.sequential.Reds[int(r*9)] for r in summary['Ratio']]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=summary['Lop'], y=summary['Tổng học sinh'], name='Tổng học sinh', marker_color='#4CAF50'))
        fig_bar.add_trace(go.Bar(x=summary['Lop'], y=summary['Số bất thường'], name='Bất thường', marker_color=colors))
        fig_bar.update_layout(barmode='group', xaxis_title='Lớp', yaxis_title='Số học sinh', title='Tổng học sinh vs Học sinh bất thường')
        st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================
    # Histogram Z-score
    # ==========================
    st.subheader("📊 Phân bố Z-score học sinh")
    fig_hist = px.histogram(df, x='Zscore', nbins=30, color=abs(df['Zscore'])>z_threshold,
                            color_discrete_map={True:'#FF5252', False:'#4CAF50'},
                            labels={'color':'Bất thường'}, title="Histogram Z-score (học sinh bất thường màu đỏ)")
    st.plotly_chart(fig_hist, use_container_width=True)

    # ==========================
    # Scatter plot DiemTB vs Z-score
    # ==========================
    st.subheader("📈 Scatter: Điểm TB vs Z-score")
    fig_scatter = px.scatter(df, x='DiemTB', y='Zscore', color=abs(df['Zscore'])>z_threshold,
                             color_discrete_map={True:'#FF5252', False:'#4CAF50'},
                             hover_data=display_cols, labels={'color':'Bất thường'}, title='Scatter DiemTB vs Z-score')
    st.plotly_chart(fig_scatter, use_container_width=True)

    # ==========================
    # Xuất CSV học sinh bất thường
    # ==========================
    if not anomalies.empty:
        csv_buffer = io.StringIO()
        anomalies.to_csv(csv_buffer, index=False, encoding='utf-8')
        st.download_button("📥 Xuất CSV học sinh bất thường", data=csv_buffer.getvalue(), file_name="Studentscore_BatThuong.csv", mime="text/csv")

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
