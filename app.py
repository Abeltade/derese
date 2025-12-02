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

    # Initialize session state for editing
    if 'edit_woreda_id' not in st.session_state:
        st.session_state.edit_woreda_id = None
    if 'edit_kebele_id' not in st.session_state:
        st.session_state.edit_kebele_id = None

    # --- ADD WOREDA / KEBELE SECTION ---
    with st.expander("➕ Add New Woreda or Kebele", expanded=False):
        col1_add, col2_add = st.columns(2)
        with col1_add:
            st.subheader("Add New Woreda")
            new_woreda_name_input = st.text_input("New Woreda Name", key="new_woreda_name_input")
            if st.button("Save New Woreda"):
                if new_woreda_name_input:
                    db.add(Woreda(name=new_woreda_name_input))
                    db.commit()
                    st.success(f"Woreda '{new_woreda_name_input}' saved")
                    st.rerun()
                else:
                    st.warning("Woreda name cannot be empty.")

        with col2_add:
            st.subheader("Add Kebeles to Woreda")
            woredas_for_add = db.query(Woreda).all()
            if woredas_for_add:
                woreda_select_add = st.selectbox("Select Woreda to add Kebeles", [w.name for w in woredas_for_add], key="woreda_select_add")
                kebele_names = st.text_area("Add New Kebeles (one per line)", key="add_kebeles_text_area")
                if st.button("Save New Kebeles"):
                    w = db.query(Woreda).filter(Woreda.name == woreda_select_add).first()
                    if kebele_names and w:
                        for kebele_name in kebele_names.split('\n'):
                            if kebele_name.strip():
                                db.add(Kebele(name=kebele_name.strip(), woreda_id=w.id))
                        db.commit()
                        st.success("Kebeles saved")
                        st.rerun()
                    else:
                        st.warning("Kebele names cannot be empty or Woreda not selected.")
            else:
                st.warning("No Woredas found. Please add a Woreda first.")
    
    st.divider()

    # --- EDIT FORMS (only one can be open at a time) ---
    if st.session_state.edit_woreda_id:
        woreda_to_edit = db.query(Woreda).filter(Woreda.id == st.session_state.edit_woreda_id).first()
        if woreda_to_edit:
            with st.form(key=f"edit_woreda_form_{woreda_to_edit.id}"):
                st.subheader(f"Edit Woreda: {woreda_to_edit.name}")
                new_woreda_name_edit = st.text_input("Woreda Name", value=woreda_to_edit.name)
                save_woreda, cancel_woreda = st.columns(2)
                if save_woreda.form_submit_button("Save Changes"):
                    woreda_to_edit.name = new_woreda_name_edit
                    db.commit()
                    st.success("Woreda updated!")
                    st.session_state.edit_woreda_id = None
                    st.rerun()
                if cancel_woreda.form_submit_button("Cancel"):
                    st.session_state.edit_woreda_id = None
                    st.rerun()
    elif st.session_state.edit_kebele_id:
        kebele_to_edit = db.query(Kebele).filter(Kebele.id == st.session_state.edit_kebele_id).first()
        if kebele_to_edit:
            with st.form(key=f"edit_kebele_form_{kebele_to_edit.id}"):
                st.subheader(f"Edit Kebele: {kebele_to_edit.name}")
                new_kebele_name_edit = st.text_input("Kebele Name", value=kebele_to_edit.name)
                all_woredas = db.query(Woreda).all()
                all_woreda_names = [w.name for w in all_woredas]
                current_woreda_index = all_woreda_names.index(kebele_to_edit.woreda.name)
                selected_new_woreda_name = st.selectbox("Assign to Woreda", all_woreda_names, index=current_woreda_index)
                save_kebele, cancel_kebele = st.columns(2)
                if save_kebele.form_submit_button("Save Changes"):
                    kebele_to_edit.name = new_kebele_name_edit
                    new_parent_woreda = db.query(Woreda).filter(Woreda.name == selected_new_woreda_name).first()
                    kebele_to_edit.woreda_id = new_parent_woreda.id
                    db.commit()
                    st.success("Kebele updated!")
                    st.session_state.edit_kebele_id = None
                    st.rerun()
                if cancel_kebele.form_submit_button("Cancel"):
                    st.session_state.edit_kebele_id = None
                    st.rerun()

    # --- TABLE DISPLAY ---
    st.header("Existing Woredas and Kebeles")
    header_cols = st.columns([4, 2, 1, 1])
    header_cols[0].markdown("**Name**")
    header_cols[1].markdown("**Type**")
    header_cols[2].markdown("**Edit**")
    header_cols[3].markdown("**Delete**")
    st.divider()

    woredas_list = db.query(Woreda).order_by(Woreda.name).all()
    if not woredas_list:
        st.info("No Woredas or Kebeles found. Use the 'Add' section above to create them.")

    for woreda in woredas_list:
        # Woreda Row
        woreda_cols = st.columns([4, 2, 1, 1])
        woreda_cols[0].markdown(f"**{woreda.name}**")
        woreda_cols[1].markdown("*Woreda*")
        if woreda_cols[2].button("✏️", key=f"edit_woreda_{woreda.id}"):
            st.session_state.edit_woreda_id = woreda.id
            st.session_state.edit_kebele_id = None
            st.rerun()
        if woreda_cols[3].button("🗑️", key=f"delete_woreda_{woreda.id}"):
            # Add confirmation later
            for kebele in woreda.kebeles:
                db.delete(kebele)
            db.delete(woreda)
            db.commit()
            st.rerun()

        # Kebele Rows
        for kebele in sorted(woreda.kebeles, key=lambda k: k.name):
            kebele_cols = st.columns([4, 2, 1, 1])
            kebele_cols[0].markdown(f"&nbsp;&nbsp;&nbsp;- {kebele.name}")
            kebele_cols[1].markdown("*Kebele*")
            if kebele_cols[2].button("✏️", key=f"edit_kebele_{kebele.id}"):
                st.session_state.edit_kebele_id = kebele.id
                st.session_state.edit_woreda_id = None
                st.rerun()
            if kebele_cols[3].button("🗑️", key=f"delete_kebele_{kebele.id}"):
                db.delete(kebele)
                db.commit()
                st.rerun()
        st.divider()

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

    # Initialize session state for editing
    if 'edit_farmer_id' not in st.session_state:
        st.session_state.edit_farmer_id = None

    # --- FILTERING ---
    st.sidebar.header("Filter Farmers")
    woredas = db.query(Woreda).all()
    woreda_names = ["All"] + [w.name for w in woredas]
    selected_woreda = st.sidebar.selectbox("Filter by Woreda", woreda_names)

    farmers_query = db.query(Farmer)
    if selected_woreda != "All":
        farmers_query = farmers_query.filter(Farmer.woreda == selected_woreda)

    farmers = farmers_query.order_by(Farmer.timestamp.desc()).all()

    # --- DISPLAY FARMERS ---
    if not farmers:
        st.info("No farmers registered yet or match the current filter.")
        return

    # --- EDIT FORM ---
    if st.session_state.edit_farmer_id:
        farmer_to_edit = db.query(Farmer).filter(Farmer.id == st.session_state.edit_farmer_id).first()
        if farmer_to_edit:
            with st.form(key=f"edit_form_{farmer_to_edit.id}"):
                st.subheader(f"Editing Farmer: {farmer_to_edit.name}")
                new_name = st.text_input("Name", value=farmer_to_edit.name)
                new_phone = st.text_input("Phone", value=farmer_to_edit.phone)
                
                # Woreda and Kebele dropdowns
                woredas_list = db.query(Woreda).all()
                woreda_names_list = [w.name for w in woredas_list]
                selected_woreda_index = woreda_names_list.index(farmer_to_edit.woreda) if farmer_to_edit.woreda in woreda_names_list else 0
                new_woreda_name = st.selectbox("Woreda", woreda_names_list, index=selected_woreda_index)

                kebeles_list = db.query(Kebele).join(Woreda).filter(Woreda.name == new_woreda_name).all()
                kebele_names_list = [k.name for k in kebeles_list]
                selected_kebele_index = kebele_names_list.index(farmer_to_edit.kebele) if farmer_to_edit.kebele in kebele_names_list else 0
                new_kebele_name = st.selectbox("Kebele", kebele_names_list, index=selected_kebele_index)

                submitted = st.form_submit_button("Save Changes")
                if submitted:
                    farmer_to_edit.name = new_name
                    farmer_to_edit.phone = new_phone
                    farmer_to_edit.woreda = new_woreda_name
                    farmer_to_edit.kebele = new_kebele_name
                    db.commit()
                    st.success("Farmer details updated!")
                    st.session_state.edit_farmer_id = None
                    st.rerun()
            if st.button("Cancel Edit"):
                st.session_state.edit_farmer_id = None
                st.rerun()
            st.divider()


    # --- FARMER LIST ---
    st.subheader("All Registered Farmers")

    # Header
    header_cols = st.columns([1, 2, 2, 2, 2, 2, 1, 1])
    headers = ["ID", "Name", "Phone", "Woreda", "Kebele", "Registered By", "Edit", "Delete"]
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")
    
    st.divider()

    for farmer in farmers:
        row_cols = st.columns([1, 2, 2, 2, 2, 2, 1, 1])
        row_cols[0].write(farmer.id)
        row_cols[1].write(farmer.name)
        row_cols[2].write(farmer.phone)
        row_cols[3].write(farmer.woreda)
        row_cols[4].write(farmer.kebele)
        row_cols[5].write(farmer.registered_by)
        
        with row_cols[6]:
            if st.button("✏️", key=f"edit_{farmer.id}"):
                st.session_state.edit_farmer_id = farmer.id
                st.rerun()

        with row_cols[7]:
            if st.button("🗑️", key=f"delete_{farmer.id}"):
                db.delete(farmer)
                db.commit()
                st.rerun()
        st.divider()
    
    # --- DOWNLOAD BUTTON ---
    if farmers:
        data = [{
            "Name": f.name, "Phone": f.phone, "Woreda": f.woreda, "Kebele": f.kebele,
            "Registered By": f.registered_by, "Registration Date": f.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for f in farmers]
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="Download as CSV",
            data=csv,
            file_name='farmer_registrations.csv',
            mime='text/csv',
        )

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