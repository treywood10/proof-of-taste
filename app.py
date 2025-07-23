import hashlib

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

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

# Save JSON function
def save_json(subject_id, new_entry):

    # Make path
    filepath = Path("data") / f"{subject_id}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Add review_id to new_entry
    new_entry["review_id"] = make_review_id(new_entry)

    # If exists, load
    if filepath.exists():
        with open(filepath, "r") as f:
            data = json.load(f)
    else:
        data = []

    # Check if review_id exists
    existing_ids = [r.get("review_id") for r in data if "review_id" in r]
    if new_entry["review_id"] in existing_ids:
        # Update existing review
        data = [new_entry if r['review_id'] == new_entry['review_id'] else r for r in data]
        is_new = False
    else:
        # Append
        data.append(new_entry)
        is_new = True

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

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
                is_new = save_json(subject_id, entry)
                if is_new:
                    st.success("Thank you for submitting!")
                else:
                    st.warning("This review already exists.")

    # Display previous, if there
    filepath = Path("data") / f"{subject_id}.json"
    if filepath.exists():
        st.header("Your Bourbon Tasting Log")
        with open(filepath, "r") as f:
            past_entries = json.load(f)
        for i, e in enumerate(past_entries[::-1], 1):
            st.write(f"**{i}. {e['date']} - {e['bourbon_name']}**")
            st.write(e["notes"])
            st.write("---")