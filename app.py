import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, timedelta

# TPBank API endpoint
API_URL = "https://tpb.vn/CMCWPCoreAPI/api/public-service/get-currency-rate-core"
SOURCE_URL = "https://tpb.vn/cong-cu-tinh-toan/ty-gia-ngoai-te"
# Fallback token (may expire - app auto-fetches new token)
DEFAULT_TOKEN = "Uacgq6WsEchmCnWQJNB_S5o"

CURRENCIES = ["USD", "JPY", "AUD", "SGD"]

BASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://tpb.vn",
    "referer": SOURCE_URL,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@st.cache_data(ttl=3600)
def get_token():
    """Fetch a fresh token from TPBank website"""
    try:
        r = requests.get(SOURCE_URL, headers={"user-agent": BASE_HEADERS["user-agent"]}, timeout=15)
        if r.status_code == 200:
            # Try to find token in page source
            m = re.search(r'"token"\s*:\s*"([A-Za-z0-9_\-\.]{15,})"', r.text)
            if m:
                return m.group(1)
            # Try alternate pattern
            m2 = re.search(r"token['\"\s:=]+([A-Za-z0-9_\-\.]{15,})", r.text)
            if m2:
                return m2.group(1)
    except Exception:
        pass
    return DEFAULT_TOKEN

def to_api_date(d):
    """Convert date to DDMMYYYY format required by TPBank API"""
    return d.strftime("%d%m%Y")

def get_exchange_rate(ccy, from_date, to_date, token):
    payload = {
        "type": "1",
        "FROM_DATE": to_api_date(from_date),
        "TO_DATE": to_api_date(to_date),
        "CCY": ccy,
        "token": token
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=BASE_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Check for API error
        if isinstance(data, dict) and data.get("status") not in (None, "200", "0", 200, 0):
            st.warning(f"API tra ve loi cho {ccy}: {data.get('errMessage', data.get('errCode', 'Unknown'))}")
            return None
        return data
    except Exception as e:
        st.error(f"Loi khi lay du lieu {ccy}: {e}")
        return None

def find_list_in_response(data):
    """Recursively search for the first non-empty list in a nested structure"""
    if isinstance(data, list) and len(data) > 0:
        return data
    if isinstance(data, dict):
        for key in ["data", "Data", "result", "Result", "items", "Items",
                    "listCurrencyRate", "currencyRates", "rates", "Rates",
                    "listData", "ListData", "list", "List"]:
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                return val
        for v in data.values():
            if isinstance(v, (dict, list)):
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
                    item.get("date") or item.get("Date") or "")
        buy = (item.get("MUA_CK") or item.get("BUY_CK") or
               item.get("buyCK") or item.get("buy") or "")
        sell = (item.get("BAN_CK") or item.get("SELL_CK") or
                item.get("sellCK") or item.get("sell") or "")
        rows.append({"Ngay": date_val, "Loai tien": ccy, "Mua CK": buy, "Ban CK": sell})
    return rows

st.set_page_config(page_title="Ti gia TPBank", page_icon="\U0001f4b1", layout="wide")
st.title("\U0001f4b1\U0001f504 Ti gia ngoai te TPBank")
st.caption("Lay ti gia mua/ban chuyen khoan: USD · JPY · AUD · SGD")

col1, col2 = st.columns(2)
default_from = datetime.today() - timedelta(days=30)
default_to = datetime.today()

with col1:
    from_date = st.date_input("Tu ngay", value=default_from, format="YYYY/MM/DD")
with col2:
    to_date = st.date_input("Den ngay", value=default_to, format="YYYY/MM/DD")

debug_mode = st.checkbox("Hien thi du lieu goc (debug)")

if st.button("Lay ti gia", type="primary"):
    token = get_token()
    if debug_mode:
        st.info(f"Token dang dung: {token[:10]}...")
    all_rows = []
    progress = st.progress(0, text="Dang lay du lieu...")
    for i, ccy in enumerate(CURRENCIES):
        progress.progress((i + 1) / len(CURRENCIES), text=f"Dang lay {ccy}...")
        data = get_exchange_rate(ccy, from_date, to_date, token)
        if debug_mode and i == 0 and data is not None:
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
        st.warning("Khong co du lieu trong khoang thoi gian nay hoac API khong phan hoi.")
        if debug_mode:
            st.info("API tra ve status 998 = token het han. Thu refresh trang.")
