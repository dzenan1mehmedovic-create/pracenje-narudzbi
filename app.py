import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(
    page_title="Praćenje narudžbi",
    page_icon="📦",
    layout="wide"
)

# Podatke upisuješ u .streamlit/secrets.toml lokalno,
# a kasnije u Streamlit Cloud -> App settings -> Secrets.
SUPABASE_URL = st.secrets["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = st.secrets["SUPABASE_SECRET_KEY"]
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

TABLE_NAME = "narudzbe"

STATUS_OPTIONS = [
    "Čeka odgovor",
    "Naručeno",
    "U dolasku",
    "Stiglo",
    "Problem",
    "Otkazano"
]

ODGOVOR_OPTIONS = [
    "Da",
    "Ne",
    "Djelimično"
]


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def api_url():
    return f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"


def load_data():
    params = {
        "select": "*",
        "order": "id.desc"
    }

    response = requests.get(
        api_url(),
        headers=supabase_headers(),
        params=params,
        timeout=20
    )

    if response.status_code != 200:
        st.error("Greška pri učitavanju podataka iz Supabase baze.")
        st.code(response.text)
        return pd.DataFrame()

    data = response.json()
    return pd.DataFrame(data)


def insert_order(order):
    response = requests.post(
        api_url(),
        headers=supabase_headers(),
        json=order,
        timeout=20
    )

    if response.status_code not in [200, 201]:
        st.error("Greška pri spremanju narudžbe.")
        st.code(response.text)
        return False

    return True


def update_order(order_id, updated_order):
    url = f"{api_url()}?id=eq.{order_id}"

    response = requests.patch(
        url,
        headers=supabase_headers(),
        json=updated_order,
        timeout=20
    )

    if response.status_code not in [200, 204]:
        st.error("Greška pri uređivanju narudžbe.")
        st.code(response.text)
        return False

    return True


def delete_order(order_id):
    url = f"{api_url()}?id=eq.{order_id}"

    response = requests.delete(
        url,
        headers=supabase_headers(),
        timeout=20
    )

    if response.status_code not in [200, 204]:
        st.error("Greška pri brisanju narudžbe.")
        st.code(response.text)
        return False

    return True


def check_late(row):
    if row.get("status", "") in ["Stiglo", "Otkazano"]:
        return "Ne"

    value = row.get("kada_dolazi", "")

    if value in ["", None]:
        return "Ne"

    try:
        arrival_date = pd.to_datetime(value).date()
        if arrival_date < date.today():
            return "Da"
    except Exception:
        return "Ne"

    return "Ne"


def login():
    if APP_PASSWORD == "":
        return True

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return True

    st.title("🔐 Praćenje narudžbi")
    password = st.text_input("Unesi šifru za ulaz", type="password")

    if st.button("Uđi"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Pogrešna šifra.")

    return False


if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "saved_message" not in st.session_state:
    st.session_state.saved_message = False


if not login():
    st.stop()


df = load_data()

st.title("📦 Praćenje narudžbi")
st.caption("Online mini aplikacija za praćenje narudžbi. Podaci se čuvaju u Supabase bazi.")

if st.session_state.saved_message:
    st.success("Narudžba je sačuvana i forma je očišćena.")
    st.session_state.saved_message = False

st.markdown("---")

# Statistika
if len(df) == 0:
    total_orders = 0
    waiting_orders = 0
    arriving_orders = 0
    problem_orders = 0
else:
    total_orders = len(df)
    waiting_orders = len(df[df["status"] == "Čeka odgovor"])
    arriving_orders = len(df[df["status"] == "U dolasku"])
    problem_orders = len(df[df["status"] == "Problem"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ukupno narudžbi", total_orders)
col2.metric("Čeka odgovor", waiting_orders)
col3.metric("U dolasku", arriving_orders)
col4.metric("Problem", problem_orders)

st.markdown("---")

# Dodavanje nove narudžbe
with st.expander("➕ Dodaj novu narudžbu", expanded=True):
    form_key = f"add_order_form_{st.session_state.form_version}"

    with st.form(form_key, clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            dobavljac = st.text_input(
                "Dobavljač",
                placeholder="npr. Goran, CNC Centar, AM Pneumatik",
                key=f"dobavljac_{st.session_state.form_version}"
            )
            masina = st.text_input(
                "Za koju mašinu je naručeno",
                placeholder="npr. Pakerica 1, CNC mašina, transporter",
                key=f"masina_{st.session_state.form_version}"
            )
            sta_je_naruceno = st.text_area(
                "Šta je naručeno",
                placeholder="npr. cilindar, regulator, remen, motor...",
                key=f"naruceno_{st.session_state.form_version}"
            )

        with c2:
            datum_narudzbe = st.date_input(
                "Kad je naručeno",
                value=date.today(),
                key=f"datum_{st.session_state.form_version}"
            )
            kada_dolazi = st.date_input(
                "Kada dolazi",
                value=date.today(),
                key=f"dolazi_{st.session_state.form_version}"
            )
            status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                key=f"status_{st.session_state.form_version}"
            )
            odgovorio = st.selectbox(
                "Da li je odgovorio",
                ODGOVOR_OPTIONS,
                key=f"odgovorio_{st.session_state.form_version}"
            )

        sta_nemaju = st.text_area(
            "Šta nemaju od onog što nam treba",
            placeholder="npr. nemaju regulator 1/4, nude zamjenu...",
            key=f"nemaju_{st.session_state.form_version}"
        )
        napomena = st.text_area(
            "Napomena",
            placeholder="npr. nazvati ponovo, čekamo ponudu, provjeriti cijenu dostave...",
            key=f"napomena_{st.session_state.form_version}"
        )

        submitted = st.form_submit_button("Sačuvaj narudžbu")

        if submitted:
            if dobavljac.strip() == "" or sta_je_naruceno.strip() == "":
                st.error("Moraš unijeti barem dobavljača i šta je naručeno.")
            else:
                new_order = {
                    "dobavljac": dobavljac.strip(),
                    "masina": masina.strip(),
                    "sta_je_naruceno": sta_je_naruceno.strip(),
                    "datum_narudzbe": datum_narudzbe.strftime("%Y-%m-%d"),
                    "kada_dolazi": kada_dolazi.strftime("%Y-%m-%d"),
                    "status": status,
                    "odgovorio": odgovorio,
                    "sta_nemaju": sta_nemaju.strip(),
                    "napomena": napomena.strip()
                }

                if insert_order(new_order):
                    st.session_state.form_version += 1
                    st.session_state.saved_message = True
                    st.rerun()

st.markdown("---")

# Filteri
st.subheader("🔎 Pregled i filteri")

if len(df) == 0:
    st.info("Još nema narudžbi.")
else:
    f1, f2, f3 = st.columns(3)

    with f1:
        dobavljaci = ["Svi"] + sorted([x for x in df["dobavljac"].fillna("").unique().tolist() if x != ""])
        selected_dobavljac = st.selectbox("Filter po dobavljaču", dobavljaci)

    with f2:
        masine = ["Sve"] + sorted([x for x in df["masina"].fillna("").unique().tolist() if x != ""])
        selected_masina = st.selectbox("Filter po mašini", masine)

    with f3:
        statusi = ["Svi"] + STATUS_OPTIONS
        selected_status = st.selectbox("Filter po statusu", statusi)

    search_text = st.text_input("Pretraga", placeholder="Upiši npr. motor, pakerica, Goran, reduktor...")

    filtered_df = df.copy()

    if selected_dobavljac != "Svi":
        filtered_df = filtered_df[filtered_df["dobavljac"] == selected_dobavljac]

    if selected_masina != "Sve":
        filtered_df = filtered_df[filtered_df["masina"] == selected_masina]

    if selected_status != "Svi":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    if search_text.strip() != "":
        search_lower = search_text.lower()
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_lower in " ".join(row.astype(str)).lower(),
                axis=1
            )
        ]

    if len(filtered_df) > 0:
        display_df = filtered_df.copy()
        display_df["Kasni"] = display_df.apply(check_late, axis=1)

        display_df = display_df.rename(columns={
            "id": "ID",
            "created_at": "Kreirano",
            "dobavljac": "Dobavljač",
            "masina": "Mašina",
            "sta_je_naruceno": "Šta je naručeno",
            "datum_narudzbe": "Datum narudžbe",
            "kada_dolazi": "Kada dolazi",
            "status": "Status",
            "odgovorio": "Odgovorio",
            "sta_nemaju": "Šta nemaju",
            "napomena": "Napomena"
        })

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nema rezultata za odabrane filtere.")

st.markdown("---")

# Uređivanje jedne narudžbe
with st.expander("✏️ Uredi narudžbu"):
    if len(df) == 0:
        st.info("Trenutno nema narudžbi za uređivanje.")
    else:
        edit_options = []
        id_lookup = {}

        for _, row in df.iterrows():
            text = f"{row['id']}. {row['dobavljac']} | {row.get('masina', '')} | {row['sta_je_naruceno']}"
            edit_options.append(text)
            id_lookup[text] = row["id"]

        selected_edit = st.selectbox("Odaberi narudžbu za uređivanje", edit_options)
        selected_id = id_lookup[selected_edit]
        selected_row = df[df["id"] == selected_id].iloc[0]

        with st.form("edit_order_form"):
            ec1, ec2 = st.columns(2)

            with ec1:
                edit_dobavljac = st.text_input("Dobavljač", value=str(selected_row.get("dobavljac", "")))
                edit_masina = st.text_input("Mašina", value=str(selected_row.get("masina", "")))
                edit_naruceno = st.text_area("Šta je naručeno", value=str(selected_row.get("sta_je_naruceno", "")))

            with ec2:
                edit_datum = st.date_input(
                    "Datum narudžbe",
                    value=pd.to_datetime(selected_row.get("datum_narudzbe", date.today())).date()
                )
                edit_dolazi = st.date_input(
                    "Kada dolazi",
                    value=pd.to_datetime(selected_row.get("kada_dolazi", date.today())).date()
                )
                current_status = selected_row.get("status", STATUS_OPTIONS[0])
                current_status_index = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                edit_status = st.selectbox("Status", STATUS_OPTIONS, index=current_status_index)

                current_odgovor = selected_row.get("odgovorio", ODGOVOR_OPTIONS[0])
                current_odgovor_index = ODGOVOR_OPTIONS.index(current_odgovor) if current_odgovor in ODGOVOR_OPTIONS else 0
                edit_odgovorio = st.selectbox("Odgovorio", ODGOVOR_OPTIONS, index=current_odgovor_index)

            edit_nemaju = st.text_area("Šta nemaju", value=str(selected_row.get("sta_nemaju", "")))
            edit_napomena = st.text_area("Napomena", value=str(selected_row.get("napomena", "")))

            edit_submitted = st.form_submit_button("Sačuvaj izmjene")

            if edit_submitted:
                updated_order = {
                    "dobavljac": edit_dobavljac.strip(),
                    "masina": edit_masina.strip(),
                    "sta_je_naruceno": edit_naruceno.strip(),
                    "datum_narudzbe": edit_datum.strftime("%Y-%m-%d"),
                    "kada_dolazi": edit_dolazi.strftime("%Y-%m-%d"),
                    "status": edit_status,
                    "odgovorio": edit_odgovorio,
                    "sta_nemaju": edit_nemaju.strip(),
                    "napomena": edit_napomena.strip()
                }

                if update_order(selected_id, updated_order):
                    st.success("Izmjene su sačuvane.")
                    st.rerun()

# Brisanje narudžbe
with st.expander("🗑️ Obriši narudžbu"):
    if len(df) == 0:
        st.info("Trenutno nema narudžbi za brisanje.")
    else:
        delete_options = []
        delete_lookup = {}

        for _, row in df.iterrows():
            text = f"{row['id']}. {row['dobavljac']} | {row.get('masina', '')} | {row['sta_je_naruceno']}"
            delete_options.append(text)
            delete_lookup[text] = row["id"]

        selected_delete = st.selectbox("Odaberi narudžbu za brisanje", delete_options)

        confirm_delete = st.checkbox("Potvrđujem da želim obrisati ovu narudžbu")

        if st.button("Obriši odabranu narudžbu"):
            if not confirm_delete:
                st.warning("Prvo označi potvrdu za brisanje.")
            else:
                selected_id = delete_lookup[selected_delete]
                if delete_order(selected_id):
                    st.success("Narudžba je obrisana.")
                    st.rerun()

st.markdown("---")

# Export Excel
st.subheader("📥 Export")

if len(df) > 0:
    export_df = df.rename(columns={
        "id": "ID",
        "created_at": "Kreirano",
        "dobavljac": "Dobavljač",
        "masina": "Mašina",
        "sta_je_naruceno": "Šta je naručeno",
        "datum_narudzbe": "Datum narudžbe",
        "kada_dolazi": "Kada dolazi",
        "status": "Status",
        "odgovorio": "Odgovorio",
        "sta_nemaju": "Šta nemaju",
        "napomena": "Napomena"
    })

    excel_file = "narudzbe_export.xlsx"
    export_df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as file:
        st.download_button(
            label="Preuzmi Excel fajl",
            data=file,
            file_name="narudzbe_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Nema podataka za export.")
