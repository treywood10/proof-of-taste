import hashlib
import streamlit as st
from datetime import datetime, UTC
from supabase_client import supabase
from postgrest.exceptions import APIError

# ---------------------- Constants ----------------------
CURATOR_ID = "curator"

# ---------------------- Title ----------------------
st.title("Proof of Taste")
st.subheader("Your Bourbon Tasting Log")

# ---------------------- Utility Functions ----------------------

def make_review_id(entry):
    """Creates a unique review_id based on tasting fields."""
    concat_str = (
        entry["date"] +
        entry["distillery"].strip().lower() +
        entry["bourbon_name"].strip().lower() +
        str(entry["proof"]) +
        entry["notes"].strip().lower()
    )
    return hashlib.sha256(concat_str.encode("utf-8")).hexdigest()

def user_exists(subject_id):
    """Checks if a user exists in the 'subjects' table."""
    response = supabase.table("subjects").select("subject_id").eq("subject_id", subject_id).execute()
    return bool(response.data)

def create_user(subject_id):
    """Creates a new user with a created_at timestamp."""
    supabase.table("subjects").insert({
        "subject_id": subject_id,
        "created_at": datetime.now(UTC).isoformat()
    }).execute()

def save_to_supabase(subject_id, new_entry):
    """Saves or updates a tasting entry in Supabase."""
    new_entry["review_id"] = make_review_id(new_entry)
    new_entry["subject_id"] = subject_id

    existing = supabase.table("tastings").select("review_id").eq("review_id", new_entry["review_id"]).execute()

    if existing.data:
        supabase.table("tastings").update(new_entry).eq("review_id", new_entry["review_id"]).execute()
        return False  # not new
    else:
        supabase.table("tastings").insert(new_entry).execute()
        return True  # new entry

def make_curated_id(entry):
    """Creates a unique ID for curated review using bourbon, notes, and source URL."""
    concat_str = (
        entry["bourbon_name"].strip().lower() +
        entry["distillery"].strip().lower() +
        str(entry["proof"]) +
        entry["review_text"].strip().lower() +
        entry["url"].strip().lower()
    )
    return hashlib.sha256(concat_str.encode("utf-8")).hexdigest()

def save_curated_review(entry):
    try:
        entry["curated_id"] = make_curated_id(entry)

        existing = (
            supabase.table("curated_reviews")
            .select("curated_id")
            .eq("curated_id", entry["curated_id"])
            .execute()
        )

        if existing.data:
            print("Curated review already exists.")
            return False

        result = supabase.table("curated_reviews").insert(entry).execute()
        print("Insert success:", result.data)
        return True

    except APIError as e:
        print("Supabase API error:", e.message)
        print("Error code:", e.code)
        print("Details:", e.details)
        print("Hint:", e.hint)
        return False
    except Exception as e:
        print("Unexpected error:", str(e))
        return False

# ---------------------- Login ----------------------

subject_id = None
curator_mode = False

subject_id_input = st.text_input("Enter your username (case-insensitive)")

if subject_id_input:
    normalized_id = subject_id_input.strip().lower()
    if normalized_id == CURATOR_ID:
        password_input = st.text_input("Enter curator password", type="password")
        if password_input:
            if password_input == st.secrets["CURATOR_PASSWORD"]:
                subject_id = CURATOR_ID
                curator_mode = True
                st.success("Curator login successful!")
            else:
                st.error("Incorrect curator password. Please try again or enter a different username.")
    else:
        if user_exists(normalized_id):
            subject_id = normalized_id
            st.success(f"Welcome back, **{subject_id}**!")
        else:
            confirm = st.checkbox("Create new account with this username?")
            if confirm:
                create_user(normalized_id)
                subject_id = normalized_id
                st.success(f"Account created. Welcome, **{subject_id}**!")
            else:
                st.info("Username not found. Check spelling or confirm to create new account.")

# ---------------------- Curator Mode ----------------------

if curator_mode:
    st.header("Curated Reviews Admin Panel")

    # Initialize reset flag
    if "reset_curator_form" not in st.session_state:
        st.session_state["reset_curator_form"] = False

    # Reset form fields before rendering widgets if flag is set
    if st.session_state["reset_curator_form"]:
        st.session_state.update({
            "curator_bourbon_name": "",
            "curator_distillery": "",
            "curator_proof": 0.0,
            "curator_single_barrel": False,
            "curator_review_text": "",
            "curator_url": "",
            "reset_curator_form": False,
        })

    with st.form(key="curated_form"):
        distillery = st.text_input("Distillery", key="curator_distillery")
        bourbon_name = st.text_input("Bourbon Name", key="curator_bourbon_name")
        proof = st.number_input("Proof (0 - 200)", min_value=0.0, max_value=200.0, step=0.1, key="curator_proof")
        single_barrel = st.checkbox("Is this a single barrel release?", key="curator_single_barrel")
        review_text = st.text_area("Review Notes", key="curator_review_text")
        url = st.text_input("URL of the review (required)", key="curator_url")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit Curated Review")
        with col2:
            clear_form = st.form_submit_button("Clear")

    if clear_form:
        st.session_state["reset_curator_form"] = True
        st.rerun()

    if submitted:
        if not distillery.strip():
            st.error("Please enter the distillery")
        elif not bourbon_name.strip():
            st.error("Please enter the bourbon name")
        elif not review_text.strip():
            st.error("Please enter the review notes")
        elif not url.strip():
            st.error("Please include the source URL for tracking purposes")
        else:
            curated_entry = {
                "bourbon_name": bourbon_name,
                "distillery": distillery,
                "proof": proof,
                "review_text": review_text,
                "url": url,
                "single_barrel": single_barrel,
            }
            if save_curated_review(curated_entry):
                st.success("Curated review added!")
                st.session_state["reset_curator_form"] = True
                st.rerun()
            else:
                st.warning("This curated review already exists.")

# ---------------------- Regular User Mode ----------------------

elif subject_id and not curator_mode:
    st.header("Log a New Tasting")

    # Initialize reset flag
    if "reset_tasting_form" not in st.session_state:
        st.session_state["reset_tasting_form"] = False

    # Reset form fields before rendering widgets if flag is set
    if st.session_state["reset_tasting_form"]:
        st.session_state.update({
            "tasting_date": datetime.today(),
            "tasting_distillery": "",
            "tasting_bourbon_name": "",
            "tasting_proof": 0.0,
            "tasting_single_barrel": False,
            "tasting_notes": "",
            "reset_tasting_form": False,
        })

    with st.form(key="tasting_form"):
        date = st.date_input("Date of Tasting", value=st.session_state["tasting_date"], key="tasting_date")
        distillery = st.text_input("Distillery", key="tasting_distillery")
        bourbon_name = st.text_input("Bourbon Name", key="tasting_bourbon_name")
        proof = st.number_input("Proof (0 - 200)", min_value=0.0, max_value=200.0, step=0.1, key="tasting_proof")
        single_barrel = st.checkbox("Is this a single barrel?", key="tasting_single_barrel")
        notes = st.text_area("Tasting Notes", key="tasting_notes")

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit")
        with col2:
            clear_form = st.form_submit_button("Clear")

    if clear_form:
        st.session_state["reset_tasting_form"] = True
        st.rerun()

    if submitted:
        if not distillery.strip():
            st.error("Please enter the distillery")
        elif not bourbon_name.strip():
            st.error("Please enter the bourbon name")
        elif not notes.strip():
            st.error("Please enter tasting notes")
        else:
            entry = {
                "date": date.isoformat(),
                "distillery": distillery,
                "bourbon_name": bourbon_name,
                "proof": proof,
                "notes": notes,
                "single_barrel": single_barrel,
            }

            is_new = save_to_supabase(subject_id, entry)

            if is_new:
                st.success("Thank you for submitting!")
            else:
                st.warning("This review already exists and has been updated.")

            st.session_state["reset_tasting_form"] = True
            st.rerun()

    # Show past tastings
    entries = (
        supabase.table("tastings")
        .select("*")
        .eq("subject_id", subject_id)
        .order("date", desc=True)
        .execute()
        .data
    )

    if entries:
        st.header(f"{subject_id}'s Bourbon Tasting Log")
        for i, e in enumerate(entries, 1):
            st.markdown(f"**{i}. {e['date']} - {e['bourbon_name']}**")
            st.write(f"_Distillery:_ {e['distillery']}")
            st.write(f"_Bourbon Name:_ {e['bourbon_name']}")
            st.write(f"_Proof:_ {e['proof']}")
            st.write(f"_Single Barrel:_ {'Yes' if e.get('single_barrel') else 'No'}")
            st.write(f"_Notes:_ {e['notes']}")
            st.write("---")