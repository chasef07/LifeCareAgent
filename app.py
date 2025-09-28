import streamlit as st
import asyncio
import os
import json
import pandas as pd
from dotenv import load_dotenv
from lifecareagent import Life_Care_Agent, Runner

# Load environment variables from .env file
load_dotenv()

# Initialize session state
if 'research_data' not in st.session_state:
    st.session_state.research_data = None

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

    # Research button - Large and prominent
    if st.button("Start Research", type="primary", use_container_width=True):
        if items_input.strip():
            # Show progress while researching
            with st.spinner("AI is researching your items... Please wait."):
                try:
                    result = asyncio.run(research_items(items_input))
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
        df_data.append({
            'Item/Service': item.get('item_service', ''),
            'Cost ($)': item.get('cost_per_unit', 0.0),
            'Frequency': item.get('frequency', ''),
            'CPT Code': item.get('cpt_code', ''),
            'Comment': item.get('comment', ''),
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

    # Export button
    if st.button("📄 Export Report", type="primary", use_container_width=True):
        export_text = generate_report(edited_df)
        st.download_button(
            "📥 Download Life Care Report",
            export_text,
            file_name=f"life_care_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )

def generate_report(df):
    """Generate a formatted report from the reviewed data"""
    report = "LIFE CARE PLANNING REPORT\n"
    report += "=" * 50 + "\n\n"
    report += f"Generated: {pd.Timestamp.now().strftime('%B %d, %Y at %I:%M %p')}\n\n"

    # Summary
    approved_count = len(df[df['Doctor Approval'] == 'Approved'])
    total_approved_cost = df[df['Doctor Approval'] == 'Approved']['Cost ($)'].sum()

    report += "SUMMARY\n"
    report += "-" * 20 + "\n"
    report += f"Total Items Reviewed: {len(df)}\n"
    report += f"Items Approved: {approved_count}\n"
    report += f"Total Approved Annual Cost: ${total_approved_cost:,.2f}\n\n"

    # Approved items
    approved_items = df[df['Doctor Approval'] == 'Approved']
    if len(approved_items) > 0:
        report += "APPROVED ITEMS\n"
        report += "-" * 20 + "\n"
        for _, row in approved_items.iterrows():
            report += f"Item: {row['Item/Service']}\n"
            report += f"Cost: ${row['Cost ($)']:,.2f}\n"
            report += f"Frequency: {row['Frequency']}\n"
            if row['CPT Code']:
                report += f"CPT Code: {row['CPT Code']}\n"
            if row['Doctor Notes']:
                report += f"Doctor Notes: {row['Doctor Notes']}\n"
            report += "\n"

    # Rejected items
    rejected_items = df[df['Doctor Approval'] == 'Rejected']
    if len(rejected_items) > 0:
        report += "REJECTED ITEMS\n"
        report += "-" * 20 + "\n"
        for _, row in rejected_items.iterrows():
            report += f"Item: {row['Item/Service']}\n"
            report += f"Reason: {row['Doctor Notes'] if row['Doctor Notes'] else 'No reason provided'}\n\n"

    return report

async def research_items(items_text):
    """Send the user's list directly to the agent"""
    prompt = f"Research the following medical items and provide costs, codes, and details: {items_text}"
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