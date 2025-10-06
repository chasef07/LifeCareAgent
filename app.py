import streamlit as st
import asyncio
import json
import urllib.request
import urllib.error
import pandas as pd
from dotenv import load_dotenv
from lifecareagent import Life_Care_Agent, Runner

# Load environment variables from .env file
load_dotenv()

# Initialize session state
if 'research_data' not in st.session_state:
    st.session_state.research_data = None
if 'location_input' not in st.session_state:
    st.session_state.location_input = ""
if 'pending_location_value' not in st.session_state:
    st.session_state.pending_location_value = None

def main():
    # Header - Simple title and description
    st.title("Life Care Planning Research Assistant")
    st.subheader("Professional Medical Equipment & Cost Research")

    # Input section - Large text area for easy typing
    items_input = st.text_area(
        "Enter medical items to research:",
        placeholder="walker\nwheelchair\noxygen concentrator\nhospital bed",
        height=150,
        help="Enter one item per line or separate with commas"
    )

    # If there is a staged detected location, apply it BEFORE rendering the input
    if st.session_state.pending_location_value is not None:
        st.session_state.location_input = st.session_state.pending_location_value
        st.session_state.pending_location_value = None

    # Location input and detection button
    st.markdown("#### Location")
    loc_col1, loc_col2 = st.columns([3, 1])
    with loc_col1:
        st.text_input(
            "Patient location (city, state or ZIP)",
            key="location_input",
            placeholder="e.g., Austin, TX or 78701"
        )
    with loc_col2:
        if st.button("Use My Current Location"):
            try:
                # Use a short timeout to avoid freezing the UI on slow networks
                with urllib.request.urlopen("https://ipapi.co/json/", timeout=4) as response:
                    data = json.loads(response.read().decode("utf-8"))
                city = (data.get("city") or "").strip()
                region = (data.get("region") or data.get("region_code") or "").strip()
                postal = (data.get("postal") or "").strip()
                country = (data.get("country_name") or data.get("country") or "").strip()

                # Prefer City, Region; fall back to ZIP; then Country
                detected = ", ".join([p for p in [city, region] if p]) or postal or country
                if detected:
                    st.session_state.pending_location_value = detected
                    st.success(f"Detected location: {detected}")
                    st.rerun()
                else:
                    st.info("Could not detect a precise location. Please enter it manually.")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
                st.warning("Location detection failed. Please enter your location manually.")

    # Research button - Large and prominent
    if st.button("Start Research", type="primary", use_container_width=True):
        if items_input.strip():
            # Show progress while researching
            with st.spinner("AI is researching your items... Please wait."):
                try:
                    user_location = (st.session_state.get("location_input") or "").strip()
                    result = asyncio.run(research_items(items_input, user_location))
                    # Try to parse JSON
                    research_data = json.loads(result)
                    st.session_state.research_data = research_data
                    st.success("✅ Research completed!")
                except json.JSONDecodeError:
                    # Fallback to text display if not JSON
                    st.success("✅ Research completed!")
                    st.markdown("### Research Results")
                    st.write(result)
                    st.download_button(
                        "Download Results as Text",
                        result,
                        "medical_research_results.txt"
                    )
                except Exception as e:
                    st.error(f"Research failed: {str(e)}")
        else:
            # Simple error message
            st.warning("⚠️ Please enter at least one medical item to research.")

    # Doctor review section
    if st.session_state.research_data:
        render_doctor_review()

def render_doctor_review():
    """Render the doctor review interface with editable table"""
    st.markdown("---")
    st.subheader("👨‍⚕️ Doctor Review & Approval")

    items = st.session_state.research_data.get('research_items', [])

    if not items:
        st.warning("No research items found.")
        return

    # Convert to DataFrame for editing
    df_data = []
    for item in items:
        sources = item.get('sources', [])
        # Display plain URLs on separate lines, no brackets or parentheses
        source_links = '\n'.join([str(s) for s in sources])
        df_data.append({
            'Item/Service': item.get('item_service', ''),
            'Cost ($)': item.get('cost_per_unit', 0.0),
            'Frequency': item.get('frequency', ''),
            'CPT Code': item.get('cpt_code', ''),
            'Comment': item.get('comment', ''),
            'Sources': source_links,
            'Doctor Approval': 'Pending',
            'Doctor Notes': ''
        })

    df = pd.DataFrame(df_data)


    # Display item count
    st.write(f"**{len(items)} items found for review**")

    # Editable table
    edited_df = st.data_editor(
        df,
        column_config={
            "Cost ($)": st.column_config.NumberColumn(
                "Cost ($)",
                min_value=0,
                format="$%.2f"
            ),
            "Doctor Approval": st.column_config.SelectboxColumn(
                "Doctor Approval",
                options=["Pending", "Approved", "Rejected", "Needs Review"]
            ),
            "Doctor Notes": st.column_config.TextColumn(
                "Doctor Notes",
                width="medium"
            )
        },
        use_container_width=True,
        num_rows="dynamic"
    )

    # Summary stats
    col1, col2, col3 = st.columns(3)
    approved_count = len(edited_df[edited_df['Doctor Approval'] == 'Approved'])
    rejected_count = len(edited_df[edited_df['Doctor Approval'] == 'Rejected'])
    pending_count = len(edited_df[edited_df['Doctor Approval'] == 'Pending'])

    col1.metric("✅ Approved", approved_count)
    col2.metric("❌ Rejected", rejected_count)
    col3.metric("⏳ Pending", pending_count)

    # Export removed

async def research_items(items_text, location):
    """Send the user's list directly to the agent"""
    location_clause = (
        f" The patient's location is: {location}. Prioritize pricing, availability, and codes relevant to this location when possible."
        if location else ""
    )
    prompt = (
        "Research the following medical items and provide costs, codes, and details: "
        f"{items_text}." + location_clause
    )
    result = await Runner.run(Life_Care_Agent, prompt)
    return result.final_output

# Basic styling for readability
st.markdown("""
<style>
    .main {
        font-size: 18px;
    }
    .stButton > button {
        font-size: 20px;
        padding: 15px;
    }
    .stTextArea > div > div > textarea {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()