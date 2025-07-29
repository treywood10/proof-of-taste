import hashlib
import streamlit as st
from datetime import datetime, UTC
from supabase_client import supabase

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


# ---------------------- Login ----------------------

subject_id = None
subject_id_input = st.text_input("Enter your username (case-insensitive)")

if subject_id_input:
    normalized_id = subject_id_input.strip().lower()
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


# ---------------------- Tasting Form ----------------------

if subject_id:
    st.header("Log a New Tasting")

    with st.form(key="tasting_form"):
        date = st.date_input("Date of Tasting", datetime.today())
        distillery = st.text_input("Distillery")
        bourbon_name = st.text_input("Bourbon Name")
        proof = st.number_input("Proof (0 - 200)", min_value=0.0, max_value=200.0, step=0.1)
        notes = st.text_area("Tasting Notes")
        submitted = st.form_submit_button("Submit")

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
                    "notes": notes
                }

                is_new = save_to_supabase(subject_id, entry)

                if is_new:
                    st.success("Thank you for submitting!")
                else:
                    st.warning("This review already exists and has been updated.")


# ---------------------- Show Past Tastings ----------------------

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
            st.write(f"_Notes:_ {e["notes"]}")
            st.write("---")
