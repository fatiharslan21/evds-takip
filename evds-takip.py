import streamlit as st
import evds
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="EVDS Analiz Paneli", page_icon="🚀", layout="wide")

# --- 2. CSS (Makyaj) ---
st.markdown("""
<style>
    .stApp {background-color: #f8f9fa;}
    .header-container {
        padding: 20px; background: linear-gradient(90deg, #1e1b4b 0%, #312e81 100%);
        border-radius: 12px; color: white; text-align: center; margin-bottom: 20px;
    }
    .filter-card {
        background-color: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
    }
    .metric-card {
        background-color: #fff; border-left: 5px solid #4F46E5;
        padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    div.stButton > button {
        background: #4F46E5; color: white; border-radius: 8px; height: 50px; font-weight: bold; border: none;
    }
    div.stButton > button:hover {background: #4338ca;}
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


# --- 4. YARDIMCI FONKSİYON: İSTATİSTİK KARTI ---
def istatistik_goster(df, col_name, label_name):
    """Verilen sütun için Son Değer ve En Büyük Artışı hesaplar"""
    if len(df) < 2:
        st.warning("İstatistik için yeterli veri yok.")
        return

    # 1. Son Değer
    son_deger = df[col_name].iloc[-1]

    # 2. En Büyük Artış Hesabı (Fark)
    df['Fark'] = df[col_name].diff()  # Bir önceki satıra göre fark
    max_artis = df['Fark'].max()

    # Artışın olduğu satırın indexi
    if pd.isna(max_artis):
        max_artis_str = "Veri Yok"
        tarih_str = "-"
    else:
        idx_max = df['Fark'].idxmax()
        tarih_bitis = df.loc[idx_max, 'Date']
        # Bir önceki tarih (artışın başladığı yer)
        # İndex'ten bir önceki satırı buluyoruz
        row_loc = df.index.get_loc(idx_max)
        tarih_baslangic = df.iloc[row_loc - 1]['Date']

        t1 = tarih_baslangic.strftime('%d.%m.%Y')
        t2 = tarih_bitis.strftime('%d.%m.%Y')

        max_artis_str = f"+{max_artis:,.2f} Artış"
        tarih_str = f"({t1} ➡ {t2} arası)"

    # Ekrana Basma (HTML ile özel tasarım)
    st.markdown(f"""
    <div class="metric-card">
        <h4 style="margin:0; color:#6b7280; font-size:0.9rem;">{label_name}</h4>
        <h2 style="margin:0; color:#111827; font-size:1.8rem;">{son_deger:,.2f}</h2>
        <hr style="margin:10px 0; border-color:#f3f4f6;">
        <p style="margin:0; color:#059669; font-weight:bold;">🚀 Rekor Yükseliş: {max_artis_str}</p>
        <p style="margin:0; color:#9ca3af; font-size:0.8rem;">📅 {tarih_str}</p>
    </div>
    """, unsafe_allow_html=True)


# --- 5. BAŞLIK VE GİRİŞ ---
st.markdown("""
    <div class="header-container">
        <h1 style='margin:0;'>📊 EVDS Analiz Paneli</h1>
        <p style='opacity:0.8;'>Detaylı Piyasa Analizi</p>
    </div>
""", unsafe_allow_html=True)

if 'EVDS_KEY' in st.secrets:
    api_key = st.secrets['EVDS_KEY']
else:
    with st.expander("🔑 API Anahtarı Girişi"):
        api_key = st.text_input("Anahtar:", type="password")

if not api_key: st.stop()
evds_client = get_evds_client(api_key)

# --- 6. FİLTRE PANELİ ---
with st.container():
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)

    col_sw, col_sp = st.columns([2, 5])
    karsilastirma = col_sw.toggle("🔄 Karşılaştırma Modu", value=False)

    # -- 1. VERİ SETİ --
    st.caption("BİRİNCİ VERİ SETİ (SOL EKSEN)")
    c1, c2, c3 = st.columns(3)
    cats = get_main_categories(evds_client)
    sel_cat1 = c1.selectbox("Kategori", cats.keys(), key="c1")
    cat_id1 = cats.get(sel_cat1)

    subs1 = {} if not cat_id1 else get_sub_categories(evds_client, cat_id1)
    sel_sub1 = c2.selectbox("Alt Grup", subs1.keys(), key="s1")
    sub_code1 = subs1.get(sel_sub1)

    ser1 = {} if not sub_code1 else get_series(evds_client, sub_code1)
    sel_ser_name1 = c3.selectbox("Seri", ser1.keys(), key="sr1")
    sel_ser_code1 = ser1.get(sel_ser_name1)

    # -- 2. VERİ SETİ (OPSİYONEL) --
    sel_ser_code2 = None
    if karsilastirma:
        st.markdown("---")
        st.caption("İKİNCİ VERİ SETİ (SAĞ EKSEN)")
        k1, k2, k3 = st.columns(3)
        sel_cat2 = k1.selectbox("Kategori (2)", cats.keys(), key="c2", index=1)
        cat_id2 = cats.get(sel_cat2)
        subs2 = {} if not cat_id2 else get_sub_categories(evds_client, cat_id2)
        sel_sub2 = k2.selectbox("Alt Grup (2)", subs2.keys(), key="s2")
        sub_code2 = subs2.get(sel_sub2)
        ser2 = {} if not sub_code2 else get_series(evds_client, sub_code2)
        sel_ser_name2 = k3.selectbox("Seri (2)", ser2.keys(), key="sr2")
        sel_ser_code2 = ser2.get(sel_ser_name2)

    st.markdown("---")

    # -- PARAMETRELER --
    p1, p2, p3, p4 = st.columns([1, 1, 1, 1.5])
    start = p1.date_input("Başlangıç", datetime.now() - timedelta(days=365 * 2))
    end = p2.date_input("Bitiş", datetime.now())
    freq = p3.selectbox("Frekans", ['Günlük', 'Haftalık', 'Aylık', 'Yıllık'], index=2)
    freq_map = {'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8}

    btn = p4.button("ANALİZİ BAŞLAT 🚀", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. ANALİZ MOTORU ---
if btn and sel_ser_code1:
    try:
        with st.spinner("Veriler işleniyor ve analiz ediliyor..."):
            codes = [sel_ser_code1]
            if karsilastirma and sel_ser_code2: codes.append(sel_ser_code2)

            df = evds_client.get_data(codes, startdate=start.strftime('%d-%m-%Y'), enddate=end.strftime('%d-%m-%Y'),
                                      frequency=freq_map[freq])

            if df is not None and not df.empty:
                # TEMİZLİK
                if 'Tarih' in df.columns: df.rename(columns={'Tarih': 'Date'}, inplace=True)
                if 'UNIXTIME' in df.columns: df.drop(columns=['UNIXTIME'], inplace=True)

                cols = [c for c in df.columns if c != 'Date']
                if cols: df.rename(columns={cols[0]: 'Deger1'}, inplace=True)
                if len(cols) > 1 and karsilastirma: df.rename(columns={cols[1]: 'Deger2'}, inplace=True)

                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
                df = df.dropna()

                # --- A. İSTATİSTİK KARTLARI (YENİ ÖZELLİK) ---
                st.markdown("### 📌 Kritik İstatistikler")

                if karsilastirma and 'Deger2' in df.columns:
                    col_stat1, col_stat2 = st.columns(2)
                    with col_stat1:
                        istatistik_goster(df.copy(), 'Deger1', sel_ser_name1)
                    with col_stat2:
                        istatistik_goster(df.copy(), 'Deger2', sel_ser_name2)
                else:
                    # Tekli modda tek kart ve belki ek bilgiler
                    col_center, _ = st.columns([1, 2])
                    with col_center:
                        istatistik_goster(df.copy(), 'Deger1', sel_ser_name1)

                st.markdown("---")

                # --- B. GRAFİK (DUAL AXIS) ---
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Çizgi 1
                fig.add_trace(go.Scatter(x=df['Date'], y=df['Deger1'], name=sel_ser_name1,
                                         line=dict(color='#4F46E5', width=3)), secondary_y=False)

                # Çizgi 2
                if karsilastirma and 'Deger2' in df.columns:
                    fig.add_trace(go.Scatter(x=df['Date'], y=df['Deger2'], name=sel_ser_name2,
                                             line=dict(color='#EF4444', width=3, dash='dot')), secondary_y=True)

                    # Korelasyon Notu
                    corr = df['Deger1'].corr(df['Deger2'])
                    relation_type = "Pozitif" if corr > 0 else "Negatif"
                    strength = "Güçlü" if abs(corr) > 0.7 else "Zayıf"
                    st.info(
                        f"💡 **İlişki Analizi:** İki veri arasında **%{corr * 100:.1f}** oranında **{strength} {relation_type}** ilişki var.")

                fig.update_layout(title="Zaman Serisi Analizi", template="plotly_white", height=500,
                                  hovermode="x unified", legend=dict(orientation="h", y=1.1))
                fig.update_yaxes(title_text=sel_ser_name1, secondary_y=False, showgrid=True, gridcolor='#f3f4f6')
                if karsilastirma: fig.update_yaxes(title_text=sel_ser_name2, secondary_y=True, showgrid=False)

                st.plotly_chart(fig, use_container_width=True)

                # --- C. TABLO VE İNDİRME ---
                with st.expander("📄 Veri Tablosunu İncele"):
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Excel/CSV İndir", csv, "evds_analiz.csv", "text/csv")
            else:
                st.error("Veri çekilemedi veya boş geldi.")
    except Exception as e:
        st.error(f"Hata: {e}")