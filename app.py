import hashlib
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from supabase_client import supabase

# Title info
st.title("Proof of Taste")
st.subheader("Your Bourbon Tasting Log")

# Subject ID
subject_id = st.text_input("Enter your Subject ID")

# Make review ID as a SHA256 hash
def make_review_id(entry):
    # Create a string from the key fields
    concat_str = (
            entry["date"] +
            entry["distillery"].strip().lower() +
            entry["bourbon_name"].strip().lower() +
            str(entry["proof"]) +
            entry["notes"].strip().lower()
    )
    # hash it
    return hashlib.sha256(concat_str.encode("utf-8")).hexdigest()

# Save to Supabase
def save_to_supabase(subject_id, new_entry):
    # First, ensure subject exists. If not, it violates foreign key constraint
    existing_subject = supabase.table("subjects").select("subject_id").eq("subject_id", subject_id).execute()
    if not existing_subject.data:
        supabase.table("subjects").insert({"subject_id": subject_id}).execute()

    # Add review_id and subject_id
    new_entry["review_id"] = make_review_id(new_entry)
    new_entry["subject_id"] = subject_id

    # Check if entry already exists
    existing = supabase.table("tastings").select('review_id').eq('review_id', new_entry["review_id"]).execute()
    if existing.data:
        # Update existing
        supabase.table("tastings").update(new_entry).eq("review_id", new_entry["review_id"]).execute()
        is_new = False
    else:
        # Insert new
        supabase.table("tastings").insert(new_entry).execute()
        is_new = True

    return is_new


# If subject found
if subject_id:
    st.success(f"Welcome, {subject_id}!")

    # Start form
    with st.form(key="tasting_form"):
        date = st.date_input("Date of Tasting", datetime.today())
        distillery = st.text_input("Distillery")
        bourbon_name = st.text_input("Bourbon Name")
        proof = st.number_input("Proof (0 - 200)", min_value=0.0, max_value=200.0, step=0.1)
        notes = st.text_area("Tasting Notes")
        submitted = st.form_submit_button("Submit")

        if submitted:

            # Validate fields
            if not distillery.strip():
                st.error("Please enter the distillery")
            elif not bourbon_name.strip():
                st.error("Please enter the bourbon name")
            elif not notes.strip():
                st.error("Please enter the notes")
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
                    st.warning("This review already exists.")

    # Display previous, if there
    entries = supabase.table("tastings").select("*").eq("subject_id", subject_id).order("date",
                                                                                        desc=True).execute().data
    if entries:
        st.header("Your Bourbon Tasting Log")
        for i, e in enumerate(entries, 1):
            st.write(f"**{i}. {e['date']} - {e['bourbon_name']}**")
            st.write(e["notes"])
            st.write("---")