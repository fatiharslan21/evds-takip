import streamlit as st
import evds
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="EVDS Market Monitörü",
    page_icon="✨",
    layout="wide"
)

# --- 2. ÖZEL CSS (ESTETİK DOKUNUŞLAR) ---
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #f8f9fa;
    }

    /* Başlık Alanı */
    .header-container {
        padding: 20px;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Filtre Kartı (Beyaz Kutu) */
    .filter-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }

    /* Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #eee;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }

    /* Buton Stili */
    div.stButton > button {
        background: #2563eb;
        color: white;
        border-radius: 10px;
        height: 50px;
        font-weight: bold;
        border: none;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
</style>
""", unsafe_allow_html=True)


# --- 3. FONKSİYONLAR ---
@st.cache_resource
def get_evds_client(key):
    return evds.evdsAPI(key)


@st.cache_data
def get_main_categories(_client):
    try:
        df = _client.main_categories
        return dict(zip(df['TOPIC_TITLE_TR'], df['CATEGORY_ID']))
    except:
        return {}


@st.cache_data
def get_sub_categories(_client, cat_id):
    try:
        df = _client.get_sub_categories(cat_id)
        return dict(zip(df['DATAGROUP_NAME'], df['DATAGROUP_CODE']))
    except:
        return {}


@st.cache_data
def get_series(_client, group_code):
    try:
        df = _client.get_series(group_code)
        # İsimleri temizle
        return dict(zip(df['SERIE_NAME'], df['SERIE_CODE']))
    except:
        return {}


# --- 4. BAŞLIK ALANI ---
st.markdown("""
    <div class="header-container">
        <h1 style='margin:0; font-size: 2.2rem;'>📈 PİYASA VE VERİ MONİTÖRÜ</h1>
        <p style='margin:0; opacity: 0.8;'>TCMB EVDS Altyapısı ile Güçlendirilmiştir</p>
    </div>
""", unsafe_allow_html=True)

# --- 5. API KONTROL ---
if 'EVDS_KEY' in st.secrets:
    api_key = st.secrets['EVDS_KEY']
else:
    # Şık bir expander içine gizleyelim ki görüntü bozulmasın
    with st.expander("🔑 API Ayarları (Sadece Local Kullanım İçin)"):
        api_key = st.text_input("EVDS API Anahtarı", type="password")

if not api_key:
    st.warning("Lütfen API anahtarınızı giriniz.")
    st.stop()

evds_client = get_evds_client(api_key)

# --- 6. FİLTRE PANELİ (KART GÖRÜNÜMÜ) ---
# Streamlit container ile filtreleri bir kutuya alıyoruz
with st.container():
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    # --- A. VERİ SEÇİMİ (KASKAD YAPI) ---
    col_cat, col_sub, col_ser = st.columns(3)

    with col_cat:
        cats = get_main_categories(evds_client)
        selected_cat = st.selectbox("📂 1. Kategori", options=cats.keys())
        cat_id = cats.get(selected_cat)

    with col_sub:
        subs = {}
        if cat_id: subs = get_sub_categories(evds_client, cat_id)
        selected_sub = st.selectbox("📂 2. Alt Grup", options=subs.keys())
        sub_code = subs.get(selected_sub)

    with col_ser:
        series = {}
        if sub_code: series = get_series(evds_client, sub_code)
        selected_series_name = st.selectbox("📊 3. Veri Serisi", options=series.keys())
        selected_series_code = series.get(selected_series_name)

    st.markdown("<hr style='margin: 15px 0; border-color: #eee;'>", unsafe_allow_html=True)

    # --- B. PARAMETRELER VE BUTON ---
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.2])  # Son kolon (buton) biraz daha geniş

    with c1:
        start_date = st.date_input("Başlangıç", value=datetime.now() - timedelta(days=365))
    with c2:
        end_date = st.date_input("Bitiş", value=datetime.now())
    with c3:
        freq_map = {'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8}
        freq = st.selectbox("Frekans", freq_map.keys(), index=2)
    with c4:
        calc_map = {'Düzey': 0, 'Aylık %': 1, 'Yıllık %': 3}
        calc = st.selectbox("Hesaplama", calc_map.keys(), index=0)
    with c5:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)  # Butonu aşağı hizalamak için boşluk
        run_btn = st.button("ANALİZ ET 🚀", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Kart kapanışı

# --- 7. SONUÇ EKRANI ---
if run_btn and selected_series_code:
    try:
        with st.spinner("Veriler analiz ediliyor..."):
            # Veri Çekme
            df = evds_client.get_data(
                [selected_series_code],
                startdate=start_date.strftime('%d-%m-%Y'),
                enddate=end_date.strftime('%d-%m-%Y'),
                frequency=freq_map[freq],
                formulas=[calc_map[calc]]
            )

            if df is not None and not df.empty:
                # Temizleme
                if 'Tarih' in df.columns: df.rename(columns={'Tarih': 'Date'}, inplace=True)
                cols = [c for c in df.columns if c != 'Date' and c != 'UNIXTIME']

                if cols:
                    df.rename(columns={cols[0]: 'Deger'}, inplace=True)
                    df = df.dropna()
                    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

                    # --- KPI KARTLARI ---
                    latest = df['Deger'].iloc[-1]
                    prev = df['Deger'].iloc[-2] if len(df) > 1 else latest
                    diff = latest - prev
                    pct = (diff / prev * 100) if prev != 0 else 0

                    st.markdown("### 📌 Piyasa Özeti")
                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

                    kpi1.metric("Son Değer", f"{latest:,.2f}", delta=f"{diff:,.2f}")
                    kpi2.metric("Değişim (%)", f"%{pct:.2f}", delta_color="normal")
                    kpi3.metric("Dönem Başı", f"{df['Deger'].iloc[0]:,.2f}")
                    kpi4.metric("Ortalama", f"{df['Deger'].mean():,.2f}")

                    # --- GRAFİK ALANI (PLOTLY) ---
                    st.markdown("### 📈 Grafik Analizi")

                    fig = px.area(df, x='Date', y='Deger', title=selected_series_name)

                    # Grafik Güzelleştirme
                    fig.update_layout(
                        paper_bgcolor='white',
                        plot_bgcolor='white',
                        font=dict(color='#333'),
                        hovermode="x unified",
                        height=500,
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor='#eee')
                    )
                    # Çizgi Rengi (Lacivert ve Altına Dolgu)
                    fig.update_traces(line=dict(color='#2563eb', width=3), fillcolor='rgba(37, 99, 235, 0.1)')

                    st.plotly_chart(fig, use_container_width=True)

                    # --- TABLO VE İNDİRME ---
                    with st.expander("📋 Detaylı Veri Tablosunu Göster"):
                        st.dataframe(df.style.format({"Deger": "{:.2f}"}), use_container_width=True)

                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Excel Olarak İndir", csv, "veri.csv", "text/csv")

                else:
                    st.error("Veri formatı uygun değil.")
            else:
                st.info("Bu tarih aralığında veri bulunamadı.")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")

elif not run_btn:
    # Sayfa ilk açıldığında boş kalmasın diye hoş bir karşılama
    st.info("👆 Analiz yapmak için yukarıdan veri setini seçip **ANALİZ ET** butonuna basınız.")