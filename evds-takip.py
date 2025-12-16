import streamlit as st
import evds
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="EVDS Pro Analiz", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #f8f9fa;}
    .header-container {
        padding: 20px; background: linear-gradient(90deg, #111827 0%, #374151 100%);
        border-radius: 12px; color: white; text-align: center; margin-bottom: 20px;
    }
    .filter-card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
    }
    div.stButton > button {
        background: #2563EB; color: white; border-radius: 8px; height: 48px; font-weight: bold; border: none;
    }
    div.stButton > button:hover {background: #1D4ED8;}
</style>
""", unsafe_allow_html=True)


# --- 2. FONKSİYONLAR ---
@st.cache_resource
def get_evds_client(key): return evds.evdsAPI(key)


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
        return dict(zip(df['SERIE_NAME'], df['SERIE_CODE']))
    except:
        return {}


# --- 3. BAŞLIK ---
st.markdown("""
    <div class="header-container">
        <h1 style='margin:0; font-size: 2rem;'>⚡ EVDS KORELASYON ANALİZİ</h1>
    </div>
""", unsafe_allow_html=True)

# --- 4. API GİRİŞİ ---
if 'EVDS_KEY' in st.secrets:
    api_key = st.secrets['EVDS_KEY']
else:
    with st.expander("🔑 API Ayarları"):
        api_key = st.text_input("EVDS API Anahtarı", type="password")

if not api_key: st.stop()
evds_client = get_evds_client(api_key)

# --- 5. KONTROL PANELİ ---
with st.container():
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    col_mode, col_space = st.columns([1.5, 5])
    karsilastirma = col_mode.toggle("🔄 Karşılaştırma Modu Aç/Kapat", value=False)

    st.markdown("#### 1. Ana Veri Seti (Sol Eksen)")
    c1, c2, c3 = st.columns(3)

    # KATEGORİ 1
    cats = get_main_categories(evds_client)
    sel_cat1 = c1.selectbox("Kategori", options=cats.keys(), key="cat1")
    cat_id1 = cats.get(sel_cat1)

    subs1 = {}
    if cat_id1: subs1 = get_sub_categories(evds_client, cat_id1)
    sel_sub1 = c2.selectbox("Alt Grup", options=subs1.keys(), key="sub1")
    sub_code1 = subs1.get(sel_sub1)

    series1 = {}
    if sub_code1: series1 = get_series(evds_client, sub_code1)
    sel_ser_name1 = c3.selectbox("Veri Serisi", options=series1.keys(), key="ser1")
    sel_ser_code1 = series1.get(sel_ser_name1)

    # KATEGORİ 2 (OPSİYONEL)
    sel_ser_code2 = None
    sel_ser_name2 = None

    if karsilastirma:
        st.markdown("---")
        st.markdown("#### 2. Karşılaştırılacak Veri (Sağ Eksen)")
        k1, k2, k3 = st.columns(3)

        sel_cat2 = k1.selectbox("Kategori (2)", options=cats.keys(), key="cat2", index=0)
        cat_id2 = cats.get(sel_cat2)

        subs2 = {}
        if cat_id2: subs2 = get_sub_categories(evds_client, cat_id2)
        sel_sub2 = k2.selectbox("Alt Grup (2)", options=subs2.keys(), key="sub2")
        sub_code2 = subs2.get(sel_sub2)

        series2 = {}
        if sub_code2: series2 = get_series(evds_client, sub_code2)
        sel_ser_name2 = k3.selectbox("Veri Serisi (2)", options=series2.keys(), key="ser2")
        sel_ser_code2 = series2.get(sel_ser_name2)

    st.markdown("---")

    p1, p2, p3, p4 = st.columns([1, 1, 1, 1.5])
    start = p1.date_input("Başlangıç", value=datetime.now() - timedelta(days=365))
    end = p2.date_input("Bitiş", value=datetime.now())
    freq = p3.selectbox("Frekans", ['Günlük', 'Haftalık', 'Aylık', 'Yıllık'], index=2)
    freq_map = {'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8}

    btn = p4.button("ANALİZ ET 🚀", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. HESAPLAMA VE ÇİZİM (HATA DÜZELTİLMİŞ KISIM) ---
if btn and sel_ser_code1:
    try:
        with st.spinner("Veriler analiz ediliyor..."):
            # Kod listesi hazırla
            codes = [sel_ser_code1]
            if karsilastirma and sel_ser_code2:
                codes.append(sel_ser_code2)

            # Veriyi çek
            df = evds_client.get_data(
                codes,
                startdate=start.strftime('%d-%m-%Y'),
                enddate=end.strftime('%d-%m-%Y'),
                frequency=freq_map[freq]
            )

            if df is not None and not df.empty:
                # 1. TARİH DÜZELTME
                if 'Tarih' in df.columns:
                    df.rename(columns={'Tarih': 'Date'}, inplace=True)

                # 2. UNIXTIME SİLME (Varsa)
                if 'UNIXTIME' in df.columns:
                    df.drop(columns=['UNIXTIME'], inplace=True)

                # 3. İSİMLENDİRME (KONUM BAZLI - GARANTİ YÖNTEM)
                # Date dışındaki kolonları al
                veri_kolonlari = [c for c in df.columns if c != 'Date']

                # İlk kolon -> Deger1
                if len(veri_kolonlari) > 0:
                    df.rename(columns={veri_kolonlari[0]: 'Deger1'}, inplace=True)

                # İkinci kolon -> Deger2 (Varsa)
                if len(veri_kolonlari) > 1 and karsilastirma:
                    df.rename(columns={veri_kolonlari[1]: 'Deger2'}, inplace=True)

                # Tarih formatı ve boşluk temizliği
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
                df = df.dropna()

                # --- GRAFİK ---
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # 1. Çizgi
                fig.add_trace(
                    go.Scatter(x=df['Date'], y=df['Deger1'], name=sel_ser_name1, line=dict(color='#2563EB', width=3)),
                    secondary_y=False
                )

                # 2. Çizgi (Eğer varsa)
                if karsilastirma and 'Deger2' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['Date'], y=df['Deger2'], name=sel_ser_name2,
                                   line=dict(color='#DC2626', width=3, dash='dot')),
                        secondary_y=True
                    )

                    # Korelasyon Bilgisi
                    corr = df['Deger1'].corr(df['Deger2'])
                    st.info(f"💡 **Korelasyon Katsayısı:** %{corr * 100:.2f}")

                # Grafik Ayarları
                fig.update_layout(
                    title="Analiz Grafiği", template="plotly_white", height=550, hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )
                fig.update_yaxes(title_text=sel_ser_name1, secondary_y=False, showgrid=True, gridcolor='#eee')
                if karsilastirma:
                    fig.update_yaxes(title_text=sel_ser_name2, secondary_y=True, showgrid=False)

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Detaylı Veri Tablosu"):
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 İndir", csv, "analiz.csv", "text/csv")

            else:
                st.error("Veri bulunamadı veya API hatası.")

    except Exception as e:
        st.error(f"Hata oluştu: {e}")