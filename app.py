import streamlit as st
import asyncio
import json
import urllib.request
import urllib.error
from typing import Any, Dict
import pandas as pd
from dotenv import load_dotenv
from test import WorkflowInput, run_workflow, stream_workflow

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

    # Input section - large text area for clinical context
    patient_summary = st.text_area(
        "Enter patient medical summary and injury details:",
        placeholder=(
            "Example:\n"
            "Patient: 62-year-old male with C5 spinal cord injury after MVA.\n"
            "Medical history: hypertension, Type II diabetes.\n"
            "Needs: long-term mobility support, home respiratory therapy, daily wound care.\n"
            "Goals: independent transfers, prevent pressure ulcers, maintain respiratory function."
        ),
        height=200,
        help="Provide relevant diagnoses, functional limitations, and ongoing care needs."
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
        if patient_summary.strip():
            user_location = (st.session_state.get("location_input") or "").strip()

            progress_placeholder = st.progress(0)
            status_placeholder = st.empty()
            log_placeholder = st.empty()

            stage_order = ["planner", "cost_research"]
            stage_display = {
                "planner": "Planning Recommendations",
                "cost_research": "Cost & Sourcing",
                "fallback": "Fallback Execution",
                "final": "Finalization",
                "streaming": "Streaming"
            }
            stage_sequence: list[str] = []
            stage_logs: dict[str, dict[str, Any]] = {}

            progress_placeholder.progress(0)
            status_placeholder.markdown("Preparing agent workflow…")
            log_placeholder.markdown("_Awaiting agent updates..._")

            def render_log() -> None:
                if not stage_sequence:
                    log_placeholder.markdown("_Awaiting agent updates..._")
                    return

                sections: list[str] = []
                for stage in stage_sequence:
                    stage_data = stage_logs.get(stage)
                    if not stage_data:
                        continue

                    lines: list[str] = []
                    reasoning_text = stage_data.get("reasoning", "").strip()
                    if reasoning_text:
                        quoted = "> " + reasoning_text.replace("\n", "\n> ")
                        lines.append(quoted)

                    for note in stage_data.get("notes", []):
                        note_text = note.strip()
                        if note_text:
                            lines.append(f"- {note_text}")

                    if not lines:
                        lines.append("_No updates yet_")

                    heading = stage_display.get(stage, stage.replace("_", " ").title())
                    sections.append(f"**{heading}**\n" + "\n".join(lines))

                log_placeholder.markdown("\n\n".join(sections))

            def handle_event(event: Dict[str, Any]) -> None:
                stage = event.get("stage")
                if not stage:
                    return

                kind = event.get("type")
                content = str(event.get("content", "") or "")

                entry = stage_logs.setdefault(stage, {"reasoning": "", "notes": [], "output": ""})
                if stage in stage_display and stage not in stage_sequence:
                    stage_sequence.append(stage)

                if kind == "stage_start":
                    if stage in stage_order:
                        idx = stage_order.index(stage)
                        progress_placeholder.progress(int((idx / max(len(stage_order), 1)) * 100))
                    status_placeholder.markdown(f"**{stage_display.get(stage, stage.replace('_', ' ').title())}** started…")
                elif kind == "reasoning_delta":
                    entry["reasoning"] += content
                elif kind == "tool_call":
                    entry["notes"].append(f"Tool call: {content}")
                elif kind == "tool_output":
                    entry["notes"].append(f"Tool output: {content}")
                elif kind == "message":
                    entry["notes"].append(content)
                elif kind == "agent_updated":
                    entry["notes"].append(f"Switching to agent: {content}")
                elif kind == "stage_complete":
                    if stage in stage_order:
                        idx = stage_order.index(stage)
                        progress_placeholder.progress(int(((idx + 1) / max(len(stage_order), 1)) * 100))
                    else:
                        progress_placeholder.progress(100)
                    status_placeholder.markdown(f"**{stage_display.get(stage, stage.replace('_', ' ').title())}** complete.")
                elif kind == "stage_output":
                    entry["output"] = content
                elif kind == "stage_error":
                    entry["notes"].append(f"⚠️ {content}")
                    status_placeholder.error(content)
                # output_delta and other event types are ignored in the live log

                render_log()

            try:
                result = asyncio.run(research_items(patient_summary, user_location, on_event=handle_event))
                progress_placeholder.progress(100)
                status_placeholder.markdown("✅ Workflow complete.")

                st.session_state.raw_agent_response = result
                with st.expander("Raw agent response", expanded=False):
                    st.code(result or "No response returned.", language="json")

                # Try to parse JSON
                research_data = json.loads(result)
                st.session_state.research_data = research_data
                st.session_state.doctor_reviews = {}
                st.success("✅ Research completed!")
            except json.JSONDecodeError:
                # Fallback to text display if not JSON
                st.session_state.research_data = None
                st.session_state.doctor_reviews = {}
                status_placeholder.warning("Agent returned non-JSON output. Showing raw text.")
                st.success("✅ Research completed!")
                st.markdown("### Research Results")
                st.write(result)
                st.download_button(
                    "Download Results as Text",
                    result,
                    "medical_research_results.txt"
                )
            except Exception as e:
                st.session_state.research_data = None
                st.session_state.doctor_reviews = {}
                status_placeholder.error("Research workflow failed.")
                st.error(f"Research failed: {str(e)}")
        else:
            # Simple error message
            st.warning("⚠️ Please enter the patient's medical summary before starting research.")

    # Doctor review section
    if st.session_state.research_data:
        render_doctor_review()

def render_doctor_review():
    """Render the doctor review interface with editable table"""
    st.markdown("---")
    st.subheader("👨‍⚕️ Doctor Review & Approval")

    research_payload = st.session_state.research_data or {}
    if not isinstance(research_payload, dict):
        st.warning("No structured research items found.")
        return

    category_data = {
        key: value for key, value in research_payload.items()
        if isinstance(value, list)
    }

    if not category_data:
        st.warning("No research items found.")
        return

    doctor_state = st.session_state.setdefault("doctor_reviews", {})

    label_map = {
        "research_items": "Recommendations",
        "durable_medical_equipment": "Durable Medical Equipment",
        "home_modifications": "Home Modifications",
        "medications": "Medications",
        "therapeutic_modalities": "Therapeutic Modalities",
    }

    for category_key, items in category_data.items():
        if not items:
            continue

        display_label = label_map.get(
            category_key,
            category_key.replace("_", " ").title()
        )
        st.markdown(f"### {display_label}")

        normalized_rows = []
        for item in items:
            sources = item.get('sources', [])
            if isinstance(sources, (list, tuple)):
                source_links = '\n'.join([str(s) for s in sources])
            else:
                source_links = str(sources) if sources else ''

            cost_value = item.get('cost_per_unit', item.get('price', 0.0))
            try:
                cost_value = float(cost_value)
            except (TypeError, ValueError):
                cost_value = 0.0

            normalized_rows.append({
                'Item/Service': (
                    item.get('item_service')
                    or item.get('item_name')
                    or item.get('name')
                    or ''
                ),
                'Cost ($)': cost_value,
                'Frequency': (
                    item.get('frequency')
                    or item.get('replacement_frequency')
                    or ''
                ),
                'CPT Code': item.get('cpt_code', ''),
                'Comment': item.get('comment', ''),
                'Sources': source_links,
                'Doctor Approval': 'Pending',
                'Doctor Notes': ''
            })

        if not normalized_rows:
            st.info("No items found in this category.")
            continue

        if category_key not in doctor_state or not doctor_state[category_key]:
            doctor_state[category_key] = normalized_rows

        df = pd.DataFrame(doctor_state[category_key])

        editor_key = f"editor_{category_key}".replace(" ", "_")

        edited_df = st.data_editor(
            df,
            key=editor_key,
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

        doctor_state[category_key] = edited_df.to_dict('records')

        approved_count = len(edited_df[edited_df['Doctor Approval'] == 'Approved'])
        rejected_count = len(edited_df[edited_df['Doctor Approval'] == 'Rejected'])
        pending_count = len(edited_df[edited_df['Doctor Approval'] == 'Pending'])

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Approved", approved_count)
        col2.metric("❌ Rejected", rejected_count)
        col3.metric("⏳ Pending", pending_count)

async def research_items(patient_summary_text, location, on_event=None):
    """Send the patient's summary directly to the agent, streaming progress when possible."""
    location_clause = (
        f" The patient's location is: {location}. Prioritize pricing, availability, and codes relevant to this location when possible."
        if location else ""
    )
    prompt = (
        "Review the following patient medical summary and determine the medically necessary items, services, and equipment. "
        "Provide detailed research including costs, frequencies, CPT codes (if applicable), and concise comments for each recommendation. "
        f"Patient medical summary: {patient_summary_text}." + location_clause
    )
    workflow_input = WorkflowInput(input_as_text=prompt)
    try:
        return await stream_workflow(workflow_input, callback=on_event)
    except Exception as exc:
        if on_event:
            on_event({
                "stage": "streaming",
                "type": "stage_error",
                "content": f"Streaming failed: {str(exc)}"
            })
            on_event({
                "stage": "fallback",
                "type": "stage_start",
                "content": "Falling back to non-streaming workflow."
            })
        fallback_result = await run_workflow(workflow_input)
        if on_event:
            on_event({
                "stage": "fallback",
                "type": "stage_complete",
                "content": "Fallback run finished."
            })
            on_event({
                "stage": "final",
                "type": "stage_complete",
                "content": "Workflow finished"
            })
        return fallback_result

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
