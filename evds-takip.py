import streamlit as st
import evds
import pandas as pd
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="EVDS Analiz Monitörü",
    page_icon="📈",
    layout="wide"
)

# --- API ANAHTARI YÖNETİMİ (Güvenli Mod) ---
# Önce Streamlit Secrets'a bakar (Sunucu için), yoksa Sidebar'dan ister (Local için)
api_key = None

if 'EVDS_KEY' in st.secrets:
    api_key = st.secrets['EVDS_KEY']
else:
    with st.sidebar:
        st.warning("⚠️ API Anahtarı Bulunamadı")
        api_key = st.text_input("EVDS API Anahtarınızı Girin:", type="password")
        st.info("Not: Streamlit Cloud'a yüklerken 'Secrets' kısmına eklemeyi unutmayın.")


# --- ÖNBELLEKLİ FONKSİYONLAR (Hız için) ---
@st.cache_resource
def get_evds_client(key):
    return evds.evdsAPI(key)


@st.cache_data
def get_main_categories(_client):
    try:
        df = _client.main_categories
        return dict(zip(df['TOPIC_TITLE_TR'], df['CATEGORY_ID']))
    except Exception:
        return {}


@st.cache_data
def get_sub_categories(_client, cat_id):
    try:
        df = _client.get_sub_categories(cat_id)
        return dict(zip(df['DATAGROUP_NAME'], df['DATAGROUP_CODE']))
    except Exception:
        return {}


@st.cache_data
def get_series(_client, group_code):
    try:
        df = _client.get_series(group_code)
        # Seri adını ve kodunu birleştirip gösterelim
        return dict(zip(df['SERIE_NAME'] + " (" + df['SERIE_CODE'] + ")", df['SERIE_CODE']))
    except Exception:
        return {}


# --- UYGULAMA BAŞLIĞI ---
st.title("📈 TCMB - EVDS Veri Analiz Portalı")
st.markdown("""
Bu uygulama **TCMB Elektronik Veri Dağıtım Sistemi (EVDS)** üzerinden anlık veri çeker.
Veri setini seçin, frekansı ayarlayın ve grafikleri inceleyin.
""")
st.divider()

# --- ANA AKIŞ ---
if api_key:
    try:
        evds_client = get_evds_client(api_key)

        # 1. KATEGORİ VE SERİ SEÇİMİ (3 Kolonlu Yapı)
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("1. Kategori")
            ana_kategoriler = get_main_categories(evds_client)
            if not ana_kategoriler:
                st.error("Kategoriler yüklenemedi. API Anahtarınızı kontrol edin.")
                st.stop()
            secilen_kategori_isim = st.selectbox("Konu Başlığı", options=ana_kategoriler.keys())
            secilen_kategori_id = ana_kategoriler.get(secilen_kategori_isim)

        with col2:
            st.subheader("2. Veri Grubu")
            alt_gruplar = {}
            if secilen_kategori_id:
                alt_gruplar = get_sub_categories(evds_client, secilen_kategori_id)
            secilen_alt_isim = st.selectbox("Alt Grup", options=alt_gruplar.keys())
            secilen_alt_kod = alt_gruplar.get(secilen_alt_isim)

        with col3:
            st.subheader("3. Veri Serisi")
            seriler = {}
            if secilen_alt_kod:
                seriler = get_series(evds_client, secilen_alt_kod)
            secilen_seri_isim = st.selectbox("İlgili Seri", options=seriler.keys())
            secilen_seri_kod = seriler.get(secilen_seri_isim)

        st.markdown("---")

        # 2. PARAMETRELER VE TARİH
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            baslangic = st.date_input("Başlangıç Tarihi", value=pd.to_datetime("2024-01-01"))
        with c2:
            bitis = st.date_input("Bitiş Tarihi", value=datetime.now())
        with c3:
            # EVDS Frekans Kodları
            frekans_map = {
                'Orjinal': None, 'Günlük': 1, 'Haftalık': 3, 'Aylık': 5, 'Yıllık': 8
            }
            secilen_frekans_isim = st.selectbox("Frekans", frekans_map.keys(), index=0)
            secilen_frekans = frekans_map[secilen_frekans_isim]
        with c4:
            # EVDS Formül Kodları
            formul_map = {
                'Düzey (Orjinal)': 0, 'Yüzde Değişim': 1, 'Yıllık % Değişim': 3, 'Fark': 2
            }
            secilen_formul_isim = st.selectbox("Hesaplama Yöntemi", formul_map.keys(), index=0)
            secilen_formul = formul_map[secilen_formul_isim]

        # 3. VERİYİ GETİR BUTONU
        if st.button("Verileri Getir ve Analiz Et", type="primary", use_container_width=True):
            if not secilen_seri_kod:
                st.warning("Lütfen bir veri serisi seçiniz.")
            else:
                with st.spinner('EVDS Sunucularına Bağlanılıyor...'):
                    try:
                        # API İSTEĞİ
                        df = evds_client.get_data(
                            [secilen_seri_kod],
                            startdate=baslangic.strftime('%d-%m-%Y'),
                            enddate=bitis.strftime('%d-%m-%Y'),
                            frequency=secilen_frekans,
                            formulas=[secilen_formul]
                        )

                        # VERİ TEMİZLEME VE DÜZENLEME
                        if df is not None and not df.empty:
                            # Tarih sütunu standardizasyonu
                            if 'Tarih' in df.columns:
                                df.rename(columns={'Tarih': 'Date'}, inplace=True)

                            # Tarih dışındaki veri sütununu bulma (Dinamik isim düzeltme)
                            veri_kolonlari = [c for c in df.columns if c != 'Date' and c != 'UNIXTIME']

                            if veri_kolonlari:
                                # İlk veri kolonunun ismini 'Deger' yapalım ki grafik çizerken kolay olsun
                                orjinal_kolon_adi = veri_kolonlari[0]
                                df.rename(columns={orjinal_kolon_adi: 'Deger'}, inplace=True)

                                # Sadece Date ve Deger al, NaN satırları at
                                df = df[['Date', 'Deger']].dropna()

                                # Tarihi datetime formatına çevirelim (Grafik için önemli)
                                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)

                                # --- SONUÇLARI GÖSTERME ---
                                st.success(f"✅ İşlem Başarılı! Toplam {len(df)} kayıt çekildi.")

                                tab_grafik, tab_veri = st.tabs(["📊 Grafik Analizi", "📋 Veri Tablosu"])

                                with tab_grafik:
                                    # İnteraktif Alan Grafik
                                    st.line_chart(df, x='Date', y='Deger', color="#FF4B4B")

                                with tab_veri:
                                    st.dataframe(df, use_container_width=True)

                                # İNDİRME BUTONU (CSV)
                                csv = df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 Veriyi Excel/CSV Olarak İndir",
                                    data=csv,
                                    file_name=f'evds_veri_{secilen_seri_kod}.csv',
                                    mime='text/csv',
                                    use_container_width=True
                                )
                            else:
                                st.error("Gelen veride uygun sütun bulunamadı.")
                        else:
                            st.warning("Seçilen tarih aralığında veri bulunamadı.")

                    except Exception as e:
                        st.error(f"Veri çekilirken hata oluştu: {e}")

    except Exception as e:
        st.error("API bağlantısı kurulamadı. Lütfen anahtarınızı kontrol edin.")
else:
    st.info("👈 Lütfen başlamak için API Anahtarınızı girin.")