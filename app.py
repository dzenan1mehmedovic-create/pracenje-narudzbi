import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(page_title="Praćenje narudžbi", page_icon="📦", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
TABLE = "narudzbe"

STATUS_OPTIONS = ["Čeka odgovor", "Naručeno", "U dolasku", "Problem", "Stiglo", "Otkazano"]
ODGOVOR_OPTIONS = ["Da", "Ne", "Djelimično"]

def public_headers():
    return {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}

def auth_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {st.session_state.access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def sign_up(email, password):
    return requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers=public_headers(),
        json={"email": email, "password": password},
        timeout=20,
    )

def sign_in(email, password):
    return requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=public_headers(),
        json={"email": email, "password": password},
        timeout=20,
    )

def db_url():
    return f"{SUPABASE_URL}/rest/v1/{TABLE}"

def load_orders():
    r = requests.get(
        db_url(),
        headers=auth_headers(),
        params={"select": "*", "order": "id.desc"},
        timeout=20,
    )
    if r.status_code != 200:
        st.error("Ne mogu učitati narudžbe.")
        st.code(r.text)
        return pd.DataFrame()
    return pd.DataFrame(r.json())

def insert_order(order):
    order["user_id"] = st.session_state.user_id
    r = requests.post(db_url(), headers=auth_headers(), json=order, timeout=20)
    if r.status_code not in (200, 201):
        st.error("Greška pri spremanju narudžbe.")
        st.code(r.text)
        return False
    return True

def update_order(order_id, values):
    r = requests.patch(
        f"{db_url()}?id=eq.{order_id}",
        headers=auth_headers(),
        json=values,
        timeout=20,
    )
    if r.status_code not in (200, 204):
        st.error("Greška pri izmjeni narudžbe.")
        st.code(r.text)
        return False
    return True

def delete_order(order_id):
    r = requests.delete(
        f"{db_url()}?id=eq.{order_id}",
        headers=auth_headers(),
        timeout=20,
    )
    if r.status_code not in (200, 204):
        st.error("Greška pri brisanju.")
        st.code(r.text)
        return False
    return True

for key, default in {
    "access_token": None,
    "user_id": None,
    "user_email": None,
    "edit_id": None,
    "form_version": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def logout():
    st.session_state.access_token = None
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.edit_id = None
    st.rerun()

def show_login():
    st.title("📦 Praćenje narudžbi")
    st.caption("Svaki korisnik vidi samo svoje narudžbe.")

    login_tab, register_tab = st.tabs(["🔐 Prijava", "➕ Registracija"])

    with login_tab:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Lozinka", type="password", key="login_password")

        if st.button("Prijavi se", use_container_width=True):
            if not email or not password:
                st.warning("Unesi email i lozinku.")
            else:
                r = sign_in(email.strip(), password)
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.access_token = data["access_token"]
                    st.session_state.user_id = data["user"]["id"]
                    st.session_state.user_email = data["user"]["email"]
                    st.rerun()
                else:
                    st.error("Prijava nije uspjela.")
                    st.code(r.text)

    with register_tab:
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input("Lozinka", type="password", key="register_password")
        repeat_password = st.text_input("Ponovi lozinku", type="password", key="register_repeat")

        if st.button("Napravi nalog", use_container_width=True):
            if not new_email or not new_password:
                st.warning("Unesi email i lozinku.")
            elif len(new_password) < 6:
                st.warning("Lozinka mora imati najmanje 6 karaktera.")
            elif new_password != repeat_password:
                st.warning("Lozinke se ne podudaraju.")
            else:
                r = sign_up(new_email.strip(), new_password)
                if r.status_code in (200, 201):
                    data = r.json()
                    if data.get("access_token") and data.get("user"):
                        st.session_state.access_token = data["access_token"]
                        st.session_state.user_id = data["user"]["id"]
                        st.session_state.user_email = data["user"]["email"]
                        st.rerun()
                    else:
                        st.success("Nalog je napravljen. Provjeri email i potvrdi registraciju, pa se onda prijavi.")
                else:
                    st.error("Registracija nije uspjela.")
                    st.code(r.text)

if not st.session_state.access_token:
    show_login()
    st.stop()

top1, top2 = st.columns([5, 1])
with top1:
    st.title("📦 Moje narudžbe")
    st.caption(f"Prijavljen: {st.session_state.user_email}")
with top2:
    st.write("")
    st.write("")
    if st.button("Odjavi se"):
        logout()

df = load_orders()

if df.empty:
    df = pd.DataFrame(columns=[
        "id","dobavljac","masina","sta_je_naruceno","datum_narudzbe",
        "kada_dolazi","status","odgovorio","sta_nemaju","napomena"
    ])

for col in ["dobavljac","masina","sta_je_naruceno","datum_narudzbe","kada_dolazi","status","odgovorio","sta_nemaju","napomena"]:
    if col in df.columns:
        df[col] = df[col].fillna("")

active_df = df[~df["status"].isin(["Stiglo", "Otkazano"])].copy()
arrived_df = df[df["status"] == "Stiglo"].copy()
canceled_df = df[df["status"] == "Otkazano"].copy()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Aktivne", len(active_df))
m2.metric("Stiglo", len(arrived_df))
m3.metric("Otkazano", len(canceled_df))
m4.metric("Ukupno", len(df))

st.markdown("---")

with st.expander("➕ Dodaj novu narudžbu", expanded=True):
    form_key = f"add_order_{st.session_state.form_version}"
    with st.form(form_key, clear_on_submit=True):
        left, right = st.columns(2)
        with left:
            dobavljac = st.text_input("Dobavljač")
            masina = st.text_input("Za koju mašinu je naručeno")
            naruceno = st.text_area("Šta je naručeno")
        with right:
            datum_narudzbe = st.date_input("Kad je naručeno", value=date.today())
            kada_dolazi = st.date_input("Kada dolazi", value=date.today())
            status = st.selectbox("Status", STATUS_OPTIONS)
            odgovorio = st.selectbox("Da li je odgovorio", ODGOVOR_OPTIONS)
        sta_nemaju = st.text_area("Šta nemaju od onog što nam treba")
        napomena = st.text_area("Napomena")

        if st.form_submit_button("Sačuvaj narudžbu"):
            if not dobavljac.strip():
                st.warning("Unesi dobavljača.")
            elif not naruceno.strip():
                st.warning("Unesi šta je naručeno.")
            else:
                order = {
                    "dobavljac": dobavljac.strip(),
                    "masina": masina.strip(),
                    "sta_je_naruceno": naruceno.strip(),
                    "datum_narudzbe": datum_narudzbe.strftime("%Y-%m-%d"),
                    "kada_dolazi": kada_dolazi.strftime("%Y-%m-%d"),
                    "status": status,
                    "odgovorio": odgovorio,
                    "sta_nemaju": sta_nemaju.strip(),
                    "napomena": napomena.strip(),
                }
                if insert_order(order):
                    st.session_state.form_version += 1
                    st.rerun()

st.markdown("---")
st.subheader("📌 Aktivne narudžbe")

if active_df.empty:
    st.info("Nema aktivnih narudžbi.")
else:
    for _, row in active_df.iterrows():
        order_id = int(row["id"])
        with st.container(border=True):
            st.write(f"### {row['dobavljac']}")
            st.write(f"**Mašina:** {row['masina']}")
            st.write(f"**Naručeno:** {row['sta_je_naruceno']}")
            st.write(f"**Status:** {row['status']}")
            st.write(f"**Kada dolazi:** {row['kada_dolazi']}")

            b1, b2, b3, _ = st.columns([1, 1, 1, 5])
            if b1.button("✏️ Edit", key=f"edit_{order_id}"):
                st.session_state.edit_id = order_id
                st.rerun()
            if b2.button("✅ Stiglo", key=f"arrived_{order_id}"):
                if update_order(order_id, {"status": "Stiglo"}):
                    st.rerun()
            if b3.button("🚫 Otkaži", key=f"cancel_{order_id}"):
                if update_order(order_id, {"status": "Otkazano"}):
                    st.rerun()

st.markdown("---")
st.subheader("✅ Roba koja je stigla")

if arrived_df.empty:
    st.info("Još nema robe označene kao stigla.")
else:
    for _, row in arrived_df.iterrows():
        order_id = int(row["id"])
        with st.container(border=True):
            st.write(f"### ✅ {row['dobavljac']}")
            st.write(f"**Mašina:** {row['masina']}")
            st.write(f"**Stiglo:** {row['sta_je_naruceno']}")
            b1, b2, _ = st.columns([1, 1, 6])
            if b1.button("✏️ Edit", key=f"edit_arrived_{order_id}"):
                st.session_state.edit_id = order_id
                st.rerun()
            if b2.button("↩️ Vrati", key=f"return_{order_id}"):
                if update_order(order_id, {"status": "Naručeno"}):
                    st.rerun()

with st.expander("🚫 Otkazano"):
    if canceled_df.empty:
        st.info("Nema otkazanih narudžbi.")
    else:
        for _, row in canceled_df.iterrows():
            st.write(f"**{row['dobavljac']}** — {row['sta_je_naruceno']} ({row['masina']})")

if st.session_state.edit_id is not None:
    selected = df[df["id"] == st.session_state.edit_id]
    if not selected.empty:
        row = selected.iloc[0]
        st.markdown("---")
        st.subheader("✏️ Uredi narudžbu")

        with st.form("edit_order_form"):
            left, right = st.columns(2)
            with left:
                edit_dobavljac = st.text_input("Dobavljač", value=str(row["dobavljac"]))
                edit_masina = st.text_input("Mašina", value=str(row["masina"]))
                edit_naruceno = st.text_area("Šta je naručeno", value=str(row["sta_je_naruceno"]))
            with right:
                edit_datum = st.date_input(
                    "Datum narudžbe",
                    value=pd.to_datetime(row["datum_narudzbe"]).date() if row["datum_narudzbe"] else date.today(),
                )
                edit_dolazi = st.date_input(
                    "Kada dolazi",
                    value=pd.to_datetime(row["kada_dolazi"]).date() if row["kada_dolazi"] else date.today(),
                )
                current_status = row["status"] if row["status"] in STATUS_OPTIONS else "Naručeno"
                edit_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))
                current_odgovor = row["odgovorio"] if row["odgovorio"] in ODGOVOR_OPTIONS else "Da"
                edit_odgovorio = st.selectbox("Odgovorio", ODGOVOR_OPTIONS, index=ODGOVOR_OPTIONS.index(current_odgovor))

            edit_nemaju = st.text_area("Šta nemaju", value=str(row["sta_nemaju"]))
            edit_napomena = st.text_area("Napomena", value=str(row["napomena"]))

            save_col, close_col = st.columns([1, 5])
            save = save_col.form_submit_button("Sačuvaj izmjene")
            close = close_col.form_submit_button("Zatvori")

            if close:
                st.session_state.edit_id = None
                st.rerun()

            if save:
                updated = {
                    "dobavljac": edit_dobavljac.strip(),
                    "masina": edit_masina.strip(),
                    "sta_je_naruceno": edit_naruceno.strip(),
                    "datum_narudzbe": edit_datum.strftime("%Y-%m-%d"),
                    "kada_dolazi": edit_dolazi.strftime("%Y-%m-%d"),
                    "status": edit_status,
                    "odgovorio": edit_odgovorio,
                    "sta_nemaju": edit_nemaju.strip(),
                    "napomena": edit_napomena.strip(),
                }
                if update_order(st.session_state.edit_id, updated):
                    st.session_state.edit_id = None
                    st.rerun()

st.markdown("---")
with st.expander("🗑️ Obriši narudžbu"):
    if df.empty:
        st.info("Nema narudžbi.")
    else:
        options = {}
        for _, row in df.iterrows():
            label = f"{row['id']} | {row['dobavljac']} | {row['sta_je_naruceno']}"
            options[label] = int(row["id"])

        selected_label = st.selectbox("Odaberi narudžbu", list(options.keys()))
        confirm = st.checkbox("Potvrđujem brisanje")

        if st.button("Obriši narudžbu"):
            if not confirm:
                st.warning("Označi potvrdu za brisanje.")
            elif delete_order(options[selected_label]):
                st.rerun()
