import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# TPBank API endpoint
API_URL = "https://tpb.vn/CMCWPCoreAPI/api/public-service/get-currency-rate-core"
SOURCE_URL = "https://tpb.vn/cong-cu-tinh-toan/ty-gia-ngoai-te"
TOKEN = "Uacgq6WsEchmCnWQJNB_S5o"

CURRENCIES = ["USD", "JPY", "AUD", "SGD"]

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://tpb.vn",
    "referer": SOURCE_URL,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def to_api_date(d):
    """Convert date to DDMMYYYY format required by TPBank API"""
    return d.strftime("%d%m%Y")

def get_exchange_rate(ccy, from_date, to_date):
    payload = {
        "type": "1",
        "FROM_DATE": to_api_date(from_date),
        "TO_DATE": to_api_date(to_date),
        "CCY": ccy,
        "token": TOKEN
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Loi khi lay du lieu {ccy}: {e}")
        return None

def find_list_in_response(data):
    """Recursively search for the first list in a nested dict/list structure"""
    if isinstance(data, list) and len(data) > 0:
        return data
    if isinstance(data, dict):
        for key in ["data", "Data", "result", "Result", "items", "Items",
                    "listCurrencyRate", "currencyRates", "rates", "Rates",
                    "listData", "ListData"]:
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                return val
        # Search all values recursively
        for v in data.values():
            found = find_list_in_response(v)
            if found:
                return found
    return []

def parse_rates(data, ccy):
    rows = []
    if not data:
        return rows
    items = find_list_in_response(data)
    for item in items:
        if not isinstance(item, dict):
            continue
        date_val = (item.get("CREATED_DATE") or item.get("DATE") or
                    item.get("date") or item.get("Date") or
                    item.get("ngay") or "")
        buy = (item.get("MUA_CK") or item.get("BUY_CK") or
               item.get("buyCK") or item.get("buy") or
               item.get("muaCK") or "")
        sell = (item.get("BAN_CK") or item.get("SELL_CK") or
                item.get("sellCK") or item.get("sell") or
                item.get("banCK") or "")
        rows.append({"Ngay": date_val, "Loai tien": ccy, "Mua CK": buy, "Ban CK": sell})
    return rows

st.set_page_config(page_title="Ti gia TPBank", page_icon="\U0001f4b1", layout="wide")
st.title("\U0001f4b1\U0001f504 Ti gia ngoai te TPBank")
st.caption("Lay ti gia mua/ban chuyen khoan: USD · JPY · AUD · SGD")

col1, col2 = st.columns(2)
default_from = datetime.today() - timedelta(days=90)
default_to = datetime.today()

with col1:
    from_date = st.date_input("Tu ngay", value=default_from, format="YYYY/MM/DD")
with col2:
    to_date = st.date_input("Den ngay", value=default_to, format="YYYY/MM/DD")

debug_mode = st.checkbox("Hien thi du lieu goc (debug)")

if st.button("Lay ti gia", type="primary"):
    all_rows = []
    progress = st.progress(0, text="Dang lay du lieu...")
    for i, ccy in enumerate(CURRENCIES):
        progress.progress((i + 1) / len(CURRENCIES), text=f"Dang lay {ccy}...")
        data = get_exchange_rate(ccy, from_date, to_date)
        if debug_mode and i == 0 and data:
            with st.expander(f"Raw API response ({ccy})"):
                st.json(data)
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
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        st.download_button(
            label="Tai xuong CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"ti_gia_tpbank_{from_str}_{to_str}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Khong co du lieu trong khoang thoi gian nay.")
        if not debug_mode:
            st.info("Bat checkbox 'Hien thi du lieu goc (debug)' de xem response tu API.")
