import streamlit as st
import evds
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="EVDS Pro Analiz", page_icon="⚡", layout="wide")

# --- 2. CSS ---
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
        background: #10B981; color: white; border-radius: 8px; height: 48px; font-weight: bold; border: none;
    }
    div.stButton > button:hover {background: #059669;}
</style>
""", unsafe_allow_html=True)


# --- 3. FONKSİYONLAR ---
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


# --- 4. BAŞLIK ---
st.markdown("""
    <div class="header-container">
        <h1 style='margin:0; font-size: 2rem;'>⚡ EVDS KORELASYON ANALİZİ</h1>
    </div>
""", unsafe_allow_html=True)

# --- 5. API ---
if 'EVDS_KEY' in st.secrets:
    api_key = st.secrets['EVDS_KEY']
else:
    with st.expander("🔑 API Ayarları"):
        api_key = st.text_input("EVDS API Anahtarı", type="password")

if not api_key: st.stop()
evds_client = get_evds_client(api_key)

# --- 6. KONTROL PANELİ ---
with st.container():
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    # MOD SEÇİMİ (TEKLİ Mİ ÇİFTLİ Mİ?)
    col_mode, col_space = st.columns([1, 5])
    karsilastirma = col_mode.toggle("🔄 Karşılaştırma Modu", value=False)

    st.markdown("#### 1. Ana Veri Seti (Sol Eksen)")
    c1, c2, c3 = st.columns(3)

    # 1. SERİ SEÇİMİ
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

    # 2. SERİ SEÇİMİ (SADECE KARŞILAŞTIRMA AÇIKSA GÖRÜNÜR)
    sel_ser_code2 = None
    sel_ser_name2 = None

    if karsilastirma:
        st.markdown("---")
        st.markdown("#### 2. Karşılaştırılacak Veri (Sağ Eksen)")
        k1, k2, k3 = st.columns(3)

        sel_cat2 = k1.selectbox("Kategori (2)", options=cats.keys(), key="cat2", index=1)  # Farklı başlasın
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

    # PARAMETRELER
    p1, p2, p3, p4 = st.columns([1, 1, 1, 1.5])
    start = p1.date_input("Başlangıç", value=datetime.now() - timedelta(days=365 * 2))
    end = p2.date_input("Bitiş", value=datetime.now())
    freq = p3.selectbox("Frekans", ['Günlük', 'Haftalık', 'Aylık', 'Yıllık'], index=2)
    freq_map = {'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8}

    btn = p4.button("VERİLERİ ÇEK VE ANALİZ ET 🚀", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. ANALİZ MOTORU ---
if btn and sel_ser_code1:
    try:
        with st.spinner("Analiz yapılıyor..."):
            # Kodları listeye at
            codes = [sel_ser_code1]
            if karsilastirma and sel_ser_code2:
                codes.append(sel_ser_code2)

            # Veriyi Tek Seferde Çek
            df = evds_client.get_data(codes, startdate=start.strftime('%d-%m-%Y'), enddate=end.strftime('%d-%m-%Y'),
                                      frequency=freq_map[freq])

            if df is not None and not df.empty:
                if 'Tarih' in df.columns: df.rename(columns={'Tarih': 'Date'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

                # Sütun isimlerini düzelt (EVDS karmaşık isimler dönebilir)
                # 1. Seri
                col1_real = [c for c in df.columns if sel_ser_code1 in c or c == sel_ser_code1]
                if col1_real: df.rename(columns={col1_real[0]: 'Deger1'}, inplace=True)

                # 2. Seri (Varsa)
                if karsilastirma and sel_ser_code2:
                    col2_real = [c for c in df.columns if sel_ser_code2 in c or c == sel_ser_code2]
                    if col2_real: df.rename(columns={col2_real[0]: 'Deger2'}, inplace=True)

                df = df.dropna()

                # --- GRAFİK OLUŞTURMA (DUAL AXIS) ---
                # Plotly'nin "make_subplots" özelliği ile çift eksen yaratıyoruz
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # 1. Çizgi (Sol Eksen)
                fig.add_trace(
                    go.Scatter(x=df['Date'], y=df['Deger1'], name=sel_ser_name1, line=dict(color='#1E3A8A', width=3)),
                    secondary_y=False
                )

                # 2. Çizgi (Sağ Eksen - Varsa)
                if karsilastirma and 'Deger2' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df['Date'], y=df['Deger2'], name=sel_ser_name2,
                                   line=dict(color='#DC2626', width=3, dash='dot')),
                        secondary_y=True
                    )

                    # Korelasyon Hesapla
                    corr = df['Deger1'].corr(df['Deger2'])
                    st.info(f"💡 **İstatistiksel İlişki (Korelasyon):** %{corr * 100:.2f}")
                    if corr > 0.7:
                        st.caption("👉 Güçlü Pozitif İlişki: Biri artarken diğeri de artıyor.")
                    elif corr < -0.7:
                        st.caption("👉 Güçlü Negatif İlişki: Biri artarken diğeri düşüyor.")

                # Grafik Makyajı
                fig.update_layout(
                    title="Karşılaştırmalı Analiz",
                    template="plotly_white",
                    height=550,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )
                fig.update_yaxes(title_text=sel_ser_name1, secondary_y=False, showgrid=True, gridcolor='#eee')
                if karsilastirma:
                    fig.update_yaxes(title_text=sel_ser_name2, secondary_y=True, showgrid=False)

                st.plotly_chart(fig, use_container_width=True)

                with st.expander("Veri Setini İncele"):
                    st.dataframe(df, use_container_width=True)

            else:
                st.error("Veri çekilemedi.")
    except Exception as e:
        st.error(f"Hata: {e}")