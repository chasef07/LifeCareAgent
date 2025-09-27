import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from lifecareagent import Life_Care_Agent, Runner

# Load environment variables from .env file
load_dotenv()

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
            with st.spinner("Researching your items... Please wait."):
                result = asyncio.run(research_items(items_input))

            # Display results
            st.success("✅ Research completed!")
            st.markdown("### Research Results")
            st.write(result)

            # Simple export option
            st.download_button(
                "Download Results as Text",
                result,
                "medical_research_results.txt"
            )
        else:
            # Simple error message
            st.warning("⚠️ Please enter at least one medical item to research.")

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