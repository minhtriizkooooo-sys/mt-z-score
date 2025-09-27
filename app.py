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
- **Hỗ trợ tiếng Việt**: File CSV nên lưu ở định dạng UTF-8.
""")

# ==========================
# Sidebar
# ==========================
with st.sidebar:
    st.header("🛠 Cài Đặt")
    z_threshold = st.slider("Ngưỡng Z-Score", 1.0, 5.0, 2.0, 0.1, help="Chọn ngưỡng để xác định điểm bất thường")
    st.markdown("---")
    st.info("File CSV cần có cột số cho điểm (ví dụ: Toán, Lý, Hóa) và mã hóa UTF-8.")

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
        st.error(f"Lỗi khi xử lý file: {str(e)}. Vui lòng kiểm tra định dạng file CSV.")
        st.stop()

    # Layout 2 cột
    col1, col2 = st.columns([2,1])

    # Chọn các cột số
    numeric_cols = df.select_dtypes(include=np.number).columns
    if len(numeric_cols) == 0:
        st.error("Không tìm thấy cột số trong file. Vui lòng kiểm tra (các cột điểm phải là số).")
        st.stop()

    # Tính điểm trung bình và z-score
    df["DiemTB"] = df[numeric_cols].mean(axis=1)
    df["Zscore"] = stats.zscore(df["DiemTB"].fillna(0))

    # Cột hiển thị
    display_cols = ["MaHS", "DiemTB", "Zscore"]
    if 'Lop' in df.columns:
        display_cols.insert(1, "Lop")

    # Hiển thị bảng điểm trung bình & Z-score
    with col1:
        st.subheader("📋 Bảng điểm trung bình và Z-Score")
        st.dataframe(df[display_cols].style.format({"DiemTB": "{:.2f}", "Zscore": "{:.2f}"}), use_container_width=True)

    # Lọc học sinh bất thường
    anomalies = df[abs(df["Zscore"]) > z_threshold]

    with col1:
        if anomalies.empty:
            st.success(f"Không tìm thấy học sinh bất thường (|z-score| > {z_threshold}).")
        else:
            st.warning(f"Tìm thấy {len(anomalies)} học sinh bất thường (|z-score| > {z_threshold}).")
            st.subheader("Danh sách học sinh bất thường")
            st.dataframe(
                anomalies[display_cols].style.apply(
                    lambda row: ['background-color: #FF5252' if abs(row["Zscore"]) > z_threshold else '' for _ in row],
                    axis=1
                ).format({"DiemTB": "{:.2f}", "Zscore": "{:.2f}"}), use_container_width=True
            )
            # Xuất CSV
            csv_buffer = io.StringIO()
            anomalies.to_csv(csv_buffer, index=False, encoding='utf-8')
            st.download_button(
                label="📥 Xuất file CSV học sinh bất thường",
                data=csv_buffer.getvalue(),
                file_name="Studentscore_BatThuong.csv",
                mime="text/csv"
            )

    # Bộ lọc theo lớp
    if 'Lop' in df.columns:
        with col2:
            st.subheader("🔎 Lọc Theo Lớp")
            unique_classes = sorted(df['Lop'].unique())
            selected_class = st.selectbox("Chọn lớp để lọc báo cáo", ["Tất cả"] + list(unique_classes))

            if selected_class != "Tất cả":
                filtered_df = df[df['Lop'] == selected_class]
                filtered_anomalies = anomalies[anomalies['Lop'] == selected_class]
            else:
                filtered_df = df
                filtered_anomalies = anomalies

            st.markdown(f"**Báo cáo thống kê cho lớp {selected_class}**")
            st.markdown(f"- Tổng số học sinh: **{len(filtered_df)}**")
            st.markdown(f"- Số học sinh bất thường: **{len(filtered_anomalies)}**")
            st.markdown(f"- Điểm trung bình: **{filtered_df['DiemTB'].mean():.2f}**")

            if not filtered_anomalies.empty:
                st.subheader("Danh sách học sinh bất thường trong lớp")
                st.dataframe(
                    filtered_anomalies[display_cols].style.apply(
                        lambda row: ['background-color: #00A86B' if abs(row["Zscore"]) > z_threshold else '' for _ in row],
                        axis=1
                    ).format({"DiemTB": "{:.2f}", "Zscore": "{:.2f}"}), use_container_width=True
                )

    # ==========================
    # Biểu đồ cột theo lớp
    # ==========================
    if 'Lop' in df.columns:
        st.subheader("📈 Biểu Đồ Tổng Học Sinh và Học Sinh Bất Thường Theo Lớp")
        total_per_class = df.groupby('Lop').size().reset_index(name='Tổng học sinh')
        anomalies_per_class = anomalies.groupby('Lop').size().reset_index(name='Số bất thường')
        class_summary = pd.merge(total_per_class, anomalies_per_class, on='Lop', how='left')
        class_summary['Số bất thường'] = class_summary['Số bất thường'].fillna(0).astype(int)

        fig = px.bar(
            class_summary,
            x='Lop',
            y=['Tổng học sinh', 'Số bất thường'],
            barmode='group',
            title="Tổng số học sinh và học sinh bất thường theo lớp",
            labels={'value':'Số học sinh','Lop':'Lớp'},
            color_discrete_map={'Tổng học sinh':'#4CAF50','Số bất thường':'#FF5252'}
        )
        fig.update_layout(xaxis_tickangle=-45, legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Vui lòng upload file CSV (khuyến nghị mã hóa UTF-8) để bắt đầu phân tích.")

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
