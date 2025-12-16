import streamlit as st
import evds
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. SAYFA KONFİGÜRASYONU (Geniş Ekran & Başlık) ---
st.set_page_config(
    page_title="EVDS Pro Monitör",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS İLE MAKYAJ (Çirkinliği Giderme) ---
st.markdown("""
    <style>
    /* Ana başlık stili */
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A; /* Lacivert */
        text-align: center;
        font-weight: 800;
        padding-bottom: 20px;
    }
    /* Metrik kutularının stili */
    div[data-testid="stMetric"] {
        background-color: #F0F2F6;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #D1D5DB;
    }
    /* Gereksiz boşlukları silme */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


# --- 3. FONKSİYONLAR (Cache ile Hızlandırma) ---
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
        # İsim temizliği
        names = df['SERIE_NAME'] + " (" + df['SERIE_CODE'] + ")"
        return dict(zip(names, df['SERIE_CODE']))
    except:
        return {}


# --- 4. SIDEBAR (Tüm Ayarlar Burada) ---
with st.sidebar:
    st.image("https://www.tcmb.gov.tr/wps/wcm/connect/tr/resources/img/tcmb-logo.png", width=50)
    st.title("⚙️ Kontrol Paneli")

    # API KEY YÖNETİMİ
    if 'EVDS_KEY' in st.secrets:
        api_key = st.secrets['EVDS_KEY']
    else:
        api_key = st.text_input("🔑 API Anahtarı", type="password")
        if not api_key:
            st.warning("Lütfen API anahtarı giriniz.")
            st.stop()

    evds_client = get_evds_client(api_key)

    st.divider()

    # KASKAD SEÇİM (Burada sayfa yenilenmesi normaldir ama sadece sidebar etkilenir)
    st.subheader("1. Veri Seçimi")

    cats = get_main_categories(evds_client)
    selected_cat = st.selectbox("Kategori", options=cats.keys())
    cat_id = cats.get(selected_cat)

    subs = {}
    if cat_id: subs = get_sub_categories(evds_client, cat_id)
    selected_sub = st.selectbox("Alt Grup", options=subs.keys())
    sub_code = subs.get(selected_sub)

    series = {}
    if sub_code: series = get_series(evds_client, sub_code)
    selected_series_name = st.selectbox("Veri Serisi", options=series.keys())
    selected_series_code = series.get(selected_series_name)

    st.divider()

    # FORM YAPISI (Asıl hızlandırıcı bu! Butona basana kadar grafiği yenilemez)
    with st.form("analiz_formu"):
        st.subheader("2. Parametreler")
        col1, col2 = st.columns(2)
        start_date = col1.date_input("Başlangıç", value=datetime.now() - timedelta(days=365))
        end_date = col2.date_input("Bitiş", value=datetime.now())

        freq_map = {'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8}
        freq = st.selectbox("Frekans", freq_map.keys(), index=2)  # Default Aylık

        calc_map = {'Düzey': 0, 'Yıllık % Değişim': 3, 'Aylık % Değişim': 1}
        calc = st.selectbox("Hesaplama", calc_map.keys(), index=0)

        submitted = st.form_submit_button("🚀 Analizi Başlat", type="primary", use_container_width=True)

# --- 5. ANA EKRAN (Dashboard) ---
st.markdown('<div class="main-header">TCMB Veri Analiz Monitörü</div>', unsafe_allow_html=True)

if submitted and selected_series_code:
    try:
        with st.spinner("Veriler işleniyor..."):
            # Veri Çekme
            df = evds_client.get_data(
                [selected_series_code],
                startdate=start_date.strftime('%d-%m-%Y'),
                enddate=end_date.strftime('%d-%m-%Y'),
                frequency=freq_map[freq],
                formulas=[calc_map[calc]]
            )

            if df is not None and not df.empty:
                # Veri Temizliği
                if 'Tarih' in df.columns: df.rename(columns={'Tarih': 'Date'}, inplace=True)
                cols = [c for c in df.columns if c != 'Date' and c != 'UNIXTIME']

                if cols:
                    val_col = cols[0]
                    df.rename(columns={val_col: 'Deger'}, inplace=True)
                    df = df.dropna()
                    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

                    # --- METRİKLER (KPI) ---
                    latest_val = df['Deger'].iloc[-1]
                    prev_val = df['Deger'].iloc[-2] if len(df) > 1 else latest_val
                    delta = latest_val - prev_val
                    delta_pct = (delta / prev_val) * 100 if prev_val != 0 else 0

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Son Değer", f"{latest_val:,.2f}", f"{delta:,.2f}")
                    m2.metric("Değişim (%)", f"%{delta_pct:.2f}", delta_color="normal")
                    m3.metric("En Yüksek", f"{df['Deger'].max():,.2f}")
                    m4.metric("Ortalama", f"{df['Deger'].mean():,.2f}")

                    st.markdown("---")

                    # --- PRO GRAFİK (PLOTLY) ---
                    fig = px.line(df, x='Date', y='Deger', title=f"{selected_series_name}")

                    # Grafik Makyajı
                    fig.update_layout(
                        xaxis_title="",
                        yaxis_title="Değer",
                        hovermode="x unified",
                        template="plotly_white",  # Temiz beyaz tema
                        height=500,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    # Çizgi rengi ve kalınlığı
                    fig.update_traces(line=dict(color='#1E3A8A', width=3))

                    st.plotly_chart(fig, use_container_width=True)

                    # --- TABLO VE İNDİRME ---
                    with st.expander("📋 Veri Tablosunu İncele"):
                        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)

                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "💾 Excel/CSV İndir",
                            data=csv,
                            file_name="evds_data.csv",
                            mime="text/csv"
                        )
                else:
                    st.error("Veri sütunu okunamadı.")
            else:
                st.info("Seçilen tarih aralığında veri yok.")

    except Exception as e:
        st.error(f"Hata: {e}")

elif not submitted:
    st.info("👈 Lütfen sol menüden veri setini seçip 'Analizi Başlat' butonuna basın.")