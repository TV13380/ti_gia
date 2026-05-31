import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# TPBank API endpoint
API_URL = "https://tpb.vn/CMCWPCoreAPI/api/public-service/get-currency-rate-core"
TOKEN = "Uacgq6WsEchmCnWQJNB_S5o"

CURRENCIES = ["USD", "JPY", "AUD", "SGD"]

def get_exchange_rate(ccy, from_date, to_date):
    payload = {
        "type": "1",
        "FROM_DATE": from_date,
        "TO_DATE": to_date,
        "CCY": ccy,
        "token": TOKEN
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        st.error(f"Loi khi lay du lieu {ccy}: {e}")
        return None

def parse_rates(data, ccy):
    rows = []
    if not data:
        return rows
    items = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(items, dict):
        items = items.get("listCurrencyRate", items.get("rates", []))
    if not isinstance(items, list):
        return rows
    for item in items:
        date_val = item.get("CREATED_DATE", item.get("date", ""))
        buy = item.get("MUA_CK", item.get("buyCK", item.get("buy", "")))
        sell = item.get("BAN_CK", item.get("sellCK", item.get("sell", "")))
        rows.append({"Ngay": date_val, "Loai tien": ccy, "Mua CK": buy, "Ban CK": sell})
    return rows

st.set_page_config(page_title="Ti gia TPBank", page_icon="💱", layout="wide")
st.title("💱🔄 Ti gia ngoai te TPBank")
st.caption("Lay ti gia mua/ban chuyen khoan: USD · JPY · AUD · SGD")

col1, col2 = st.columns(2)
default_from = datetime.today() - timedelta(days=90)
default_to = datetime.today()

with col1:
    from_date = st.date_input("Tu ngay", value=default_from, format="YYYY/MM/DD")
with col2:
    to_date = st.date_input("Den ngay", value=default_to, format="YYYY/MM/DD")

if st.button("Lay ti gia", type="primary"):
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")
    all_rows = []
    progress = st.progress(0, text="Dang lay du lieu...")
    for i, ccy in enumerate(CURRENCIES):
        progress.progress((i + 1) / len(CURRENCIES), text=f"Dang lay {ccy}...")
        data = get_exchange_rate(ccy, from_str, to_str)
        rows = parse_rates(data, ccy)
        all_rows.extend(rows)
    progress.empty()
    if all_rows:
        df = pd.DataFrame(all_rows)
        st.success(f"Tim thay {len(df)} ban ghi")
        for ccy in CURRENCIES:
            df_ccy = df[df["Loai tien"] == ccy].copy()
            if not df_ccy.empty:
                st.subheader(f"Ti gia {ccy}")
                st.dataframe(df_ccy.reset_index(drop=True), use_container_width=True)
        st.download_button(
            label="Tai xuong Excel",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"ti_gia_tpbank_{from_str}_{to_str}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Khong co du lieu trong khoang thoi gian nay. Thu chon khoang khac.")
