import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io

from database import SessionLocal
from models import Farmer, Woreda, Kebele, create_tables, User
from auth import register_user, login_user

st.set_page_config(
    page_title="Farmer Registration System",
    page_icon="🌾",
    layout="wide"
)

# Create DB tables
create_tables()

def login_page():
    st.title("👤 Login / Register")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.header("Login")
        username_login = st.text_input("Username", key="login_username")
        password_login = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if login_user(username_login, password_login):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username_login
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

        with st.expander("Don't have an account? Register here"):
            st.header("Register")
            username_reg = st.text_input("Username", key="reg_username")
            password_reg = st.text_input("Password", type="password", key="reg_password")
            if st.button("Register"):
                register_user(username_reg, password_reg)
                st.success("User registered! You can now login.")

def manage_woreda_kebele_page():
    db = SessionLocal()
    st.title("🗂️ Manage Woredas & Kebeles")

    col1, col2 = st.columns(2)

    with col1:
        st.header("Add New Woreda")
        woreda_name = st.text_input("Woreda Name")
        if st.button("Save Woreda"):
            if woreda_name:
                db.add(Woreda(name=woreda_name))
                db.commit()
                st.success(f"Woreda '{woreda_name}' saved")
                st.rerun()
            else:
                st.warning("Woreda name cannot be empty.")

    with col2:
        st.header("Add Kebeles to Woreda")
        woredas = db.query(Woreda).all()
        if woredas:
            woreda_select = st.selectbox("Select Woreda", [w.name for w in woredas])

            if woreda_select:
                selected_woreda = db.query(Woreda).filter(Woreda.name == woreda_select).first()
                with st.expander(f"View existing Kebeles in {woreda_select}"):
                    kebeles = selected_woreda.kebeles
                    if kebeles:
                        for kebele in kebeles:
                            st.write(f"- {kebele.name}")
                    else:
                        st.info("No Kebeles found for this Woreda.")

                kebele_names = st.text_area("Add New Kebeles (one per line)")
                if st.button("Save Kebeles"):
                    w = db.query(Woreda).filter(Woreda.name == woreda_select).first()
                    if kebele_names:
                        for kebele_name in kebele_names.split('\n'):
                            if kebele_name.strip():
                                db.add(Kebele(name=kebele_name.strip(), woreda_id=w.id))
                        db.commit()
                        st.success("Kebeles saved")
                        st.rerun()
                    else:
                        st.warning("Kebele names cannot be empty.")
        else:
            st.warning("No Woredas found. Please add a Woreda first.")

def register_farmer_page():
    db = SessionLocal()
    st.title("🌾 Farmer Registration")

    col1, col2 = st.columns(2)

    with col1:
        # SELECT WOREDA
        woredas = db.query(Woreda).all()
        if not woredas:
            st.warning("No Woredas found. Please add a Woreda first in the 'Manage Woreda/Kebele' page.")
            st.stop()
        woreda_choice = st.selectbox("Select Woreda", [w.name for w in woredas])

        # INPUTS
        name = st.text_input("Farmer Name")

    with col2:
        # SELECT KEBELE (filtered)
        if woreda_choice:
            selected_woreda = db.query(Woreda).filter(Woreda.name == woreda_choice).first()
            if selected_woreda:
                kebeles = db.query(Kebele).filter(Kebele.woreda_id == selected_woreda.id).all()
                kebele_choice = st.selectbox("Select Kebele", [k.name for k in kebeles])
            else:
                kebele_choice = None
        else:
            kebele_choice = None
        
        phone = st.text_input("Phone Number")

    # SUBMIT
    if st.button("Register Farmer"):
        if name and phone and woreda_choice and kebele_choice:
            farmer = Farmer(
                name=name,
                woreda=woreda_choice,
                kebele=kebele_choice,
                phone=phone,
                registered_by=st.session_state["username"],
                timestamp=datetime.now(),
            )
            db.add(farmer)
            db.commit()

            # EXPORT TO EXCEL
            file = "exports/farmer_registrations.xlsx"
            data = {
                "Name": [name],
                "Woreda": [woreda_choice],
                "Kebele": [kebele_choice],
                "Phone": [phone],
                "Date/Time": [datetime.now()],
                "Registered By": [st.session_state["username"]],
            }

            df = pd.DataFrame(data)

            if os.path.exists(file):
                old = pd.read_excel(file)
                df = pd.concat([old, df], ignore_index=True)

            df.to_excel(file, index=False)

            st.success(f"Farmer '{name}' registered successfully!")
            st.balloons()
        else:
            st.error("Please fill in all the fields.")

def upload_excel_page():
    st.title("📤 Upload Woreda–Kebele Excel")

    st.markdown("""
    Please upload an Excel file with two columns: `Woreda` and `Kebele`.
    - Each row should represent a single Kebele and its corresponding Woreda.
    - The Woreda for a Kebele will be created if it doesn't already exist.
    """)

    # Create a sample template for download
    template_df = pd.DataFrame({
        "Woreda": ["Sample Woreda 1", "Sample Woreda 1", "Sample Woreda 2"],
        "Kebele": ["Sample Kebele A", "Sample Kebele B", "Sample Kebele C"]
    })
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Sheet1')
    excel_data = output.getvalue()

    st.download_button(
        label="Download Template",
        data=excel_data,
        file_name="woreda_kebele_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    uploaded = st.file_uploader("Upload Excel", type=["xlsx"])

    if uploaded:
        df = pd.read_excel(uploaded)

        if "Woreda" not in df.columns or "Kebele" not in df.columns:
            st.error("The uploaded Excel file must contain 'Woreda' and 'Kebele' columns.")
            st.stop()
            
        db = SessionLocal()

        with st.spinner("Processing Excel file..."):
            for _, row in df.iterrows():
                w_name = row["Woreda"]
                k_name = row["Kebele"]

                if pd.isna(w_name) or pd.isna(k_name):
                    continue

                # Ensure Woreda exists
                woreda = db.query(Woreda).filter(Woreda.name == w_name).first()
                if not woreda:
                    woreda = Woreda(name=w_name)
                    db.add(woreda)
                    db.commit()
                    db.refresh(woreda)

                # Add kebele
                kebele = Kebele(name=k_name, woreda_id=woreda.id)
                db.add(kebele)

            db.commit()
        st.success("Excel imported successfully!")
        st.balloons()

def view_farmers_page():
    st.title("🧑‍🌾 Registered Farmers")

    db = SessionLocal()
    farmers_query = db.query(Farmer)

    st.sidebar.header("Filter Farmers")
    woredas = db.query(Woreda).all()
    woreda_names = ["All"] + [w.name for w in woredas]
    selected_woreda = st.sidebar.selectbox("Filter by Woreda", woreda_names)

    if selected_woreda != "All":
        farmers_query = farmers_query.filter(Farmer.woreda == selected_woreda)

    farmers = farmers_query.all()

    if farmers:
        data = []
        for farmer in farmers:
            data.append({
                "Name": farmer.name,
                "Phone": farmer.phone,
                "Woreda": farmer.woreda,
                "Kebele": farmer.kebele,
                "Registered By": farmer.registered_by,
                "Registration Date": farmer.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        df = pd.DataFrame(data)
        
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name='farmer_registrations.csv',
            mime='text/csv',
        )
    else:
        st.info("No farmers registered yet or match the current filter.")

def main():
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_page()
        return

    st.sidebar.title(f"Welcome {st.session_state['username']}")
    
    PAGES = {
        "🗂️ Manage Woreda/Kebele": manage_woreda_kebele_page,
        "🌾 Register Farmer": register_farmer_page,
        "📤 Upload Woreda/Kebele Excel": upload_excel_page,
        "🧑‍🌾 View Farmers": view_farmers_page
    }
    
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))
    
    page = PAGES[selection]
    page()

    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()

if __name__ == "__main__":
    main()