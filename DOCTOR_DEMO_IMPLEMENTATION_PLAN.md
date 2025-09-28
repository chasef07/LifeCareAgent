# Doctor Demo Implementation Plan
## Interactive Life Care Planning Review System

### Executive Summary
This document outlines a step-by-step plan to transform the current Life Care Planning Research Assistant into an interactive system where doctors can review, edit, and approve AI-generated research findings through editable tables and approval workflows.

### Current State Analysis
- **Existing System**: Text-based input → AI research → Markdown table output
- **AI Agent**: Uses OpenAI SDK with web search capabilities
- **Output Format**: Structured tables with Item/Service, Cost per Unit, Comment, Source(s)
- **Interface**: Basic Streamlit app with text area input and text output

### Target Demo Goals
1. **Interactive Review**: Transform static tables into editable, reviewable data grids
2. **Approval Workflow**: 3-state approval system (Approved/Needs Review/Rejected)
3. **Doctor Oversight**: Allow inline editing of costs, comments, and recommendations
4. **Professional Output**: Generate final reports with doctor approval stamps
5. **Audit Trail**: Track all changes and doctor decisions

---

## Phase 1: Data Structure Enhancement (Week 1)

### Step 1.1: Define Research Data Models
Create structured data models to replace text-based outputs:

```python
# models.py
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"

class ResearchItem(BaseModel):
    id: str
    category: str
    item_service: str
    cost_per_unit: float
    cost_range_min: Optional[float]
    cost_range_max: Optional[float]
    frequency: str
    comment: str
    sources: List[str]
    cpt_code: Optional[str]
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    doctor_notes: str = ""
    confidence_score: float
    last_updated: datetime

class LifeCarePlan(BaseModel):
    patient_id: str
    research_items: List[ResearchItem]
    overall_status: str
    doctor_signature: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
```

### Step 1.2: Modify AI Agent Output
Update the agent to return structured data instead of markdown:

```python
# Enhanced lifecareagent.py
Life_Care_Agent = Agent(
    name="LifeCareAgent",
    instructions="""
... existing instructions ...

IMPORTANT: Return results as structured JSON data with the following format:
{
    "research_items": [
        {
            "category": "mobility_equipment",
            "item_service": "Standard Walker",
            "cost_per_unit": 125.00,
            "cost_range_min": 75.00,
            "cost_range_max": 175.00,
            "frequency": "Replace every 3-5 years",
            "comment": "Basic aluminum walker with wheels",
            "sources": ["medmartonline.com/walkers"],
            "cpt_code": "E0130",
            "confidence_score": 0.85
        }
    ]
}
""",
    response_format="json"
)
```

### Step 1.3: Create Database Schema
Set up SQLite database for storing research data:

```sql
-- database/schema.sql
CREATE TABLE life_care_plans (
    id TEXT PRIMARY KEY,
    patient_name TEXT,
    case_description TEXT,
    overall_status TEXT DEFAULT 'draft',
    doctor_signature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE research_items (
    id TEXT PRIMARY KEY,
    plan_id TEXT REFERENCES life_care_plans(id),
    category TEXT,
    item_service TEXT,
    cost_per_unit REAL,
    cost_range_min REAL,
    cost_range_max REAL,
    frequency TEXT,
    comment TEXT,
    sources TEXT, -- JSON array
    cpt_code TEXT,
    approval_status TEXT DEFAULT 'pending',
    doctor_notes TEXT DEFAULT '',
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Phase 2: Interactive Table System (Week 2)

### Step 2.1: Create Editable Data Components
Build Streamlit components for interactive tables:

```python
# components/interactive_table.py
import streamlit as st
import pandas as pd
from typing import List, Callable

def render_research_table(items: List[ResearchItem],
                         on_approve: Callable,
                         on_reject: Callable,
                         on_edit: Callable) -> None:
    """Render interactive research table with approval controls"""

    # Convert to DataFrame for display
    df = pd.DataFrame([{
        "Item/Service": item.item_service,
        "Cost": f"${item.cost_per_unit:,.2f}",
        "Range": f"${item.cost_range_min:,.0f}-${item.cost_range_max:,.0f}",
        "Frequency": item.frequency,
        "CPT Code": item.cpt_code or "N/A",
        "Sources": ", ".join(item.sources[:2]),  # Show first 2 sources
        "Status": item.approval_status.value,
        "Confidence": f"{item.confidence_score:.0%}"
    } for item in items])

    # Display editable dataframe
    edited_df = st.data_editor(
        df,
        column_config={
            "Cost": st.column_config.NumberColumn(
                "Cost per Unit",
                min_value=0,
                format="$%.2f"
            ),
            "Status": st.column_config.SelectboxColumn(
                "Approval Status",
                options=["pending", "approved", "needs_review", "rejected"]
            ),
            "Confidence": st.column_config.ProgressColumn(
                "AI Confidence",
                min_value=0,
                max_value=1
            )
        },
        disabled=["Confidence"],  # Don't allow editing confidence
        use_container_width=True
    )

    return edited_df

def render_approval_controls(item: ResearchItem) -> None:
    """Render approval controls for individual items"""
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Approve", key=f"approve_{item.id}"):
            return "approved"

    with col2:
        if st.button("⚠️ Needs Review", key=f"review_{item.id}"):
            return "needs_review"

    with col3:
        if st.button("❌ Reject", key=f"reject_{item.id}"):
            return "rejected"
```

### Step 2.2: Category-Based Navigation
Create multi-page navigation for the 18 life care categories:

```python
# components/category_navigation.py

LIFE_CARE_CATEGORIES = {
    "mobility_equipment": "Mobility Equipment",
    "medications": "Medications",
    "therapeutic_services": "Therapeutic Services",
    "medical_supplies": "Medical Supplies",
    "home_modifications": "Home Modifications",
    # ... all 18 categories
}

def render_category_sidebar(plan_data: LifeCarePlan) -> str:
    """Render category navigation with approval status indicators"""

    st.sidebar.title("Life Care Categories")

    selected_category = None

    for category_key, category_name in LIFE_CARE_CATEGORIES.items():
        # Count items in this category
        category_items = [item for item in plan_data.research_items
                         if item.category == category_key]

        # Calculate approval status
        approved_count = len([item for item in category_items
                            if item.approval_status == ApprovalStatus.APPROVED])
        total_count = len(category_items)

        # Status indicator
        if total_count == 0:
            status_icon = "⚪"  # No items
        elif approved_count == total_count:
            status_icon = "✅"  # All approved
        elif approved_count > 0:
            status_icon = "🔄"  # Partially approved
        else:
            status_icon = "⏳"  # Pending

        # Create button with status
        button_label = f"{status_icon} {category_name} ({approved_count}/{total_count})"

        if st.sidebar.button(button_label, key=f"nav_{category_key}"):
            selected_category = category_key

    return selected_category
```

### Step 2.3: Doctor Notes and Comments System
Add doctor annotation capabilities:

```python
# components/doctor_notes.py
def render_doctor_notes_section(item: ResearchItem) -> str:
    """Render doctor notes input for research items"""

    st.subheader(f"Doctor Notes: {item.item_service}")

    # Show AI reasoning
    with st.expander("AI Research Details"):
        st.write(f"**Confidence:** {item.confidence_score:.0%}")
        st.write(f"**Sources:** {', '.join(item.sources)}")
        st.write(f"**Original Comment:** {item.comment}")

    # Doctor notes input
    doctor_notes = st.text_area(
        "Doctor Notes & Modifications:",
        value=item.doctor_notes,
        placeholder="Add your clinical notes, modifications, or concerns...",
        key=f"notes_{item.id}"
    )

    # Reasoning for status changes
    if item.approval_status in [ApprovalStatus.NEEDS_REVIEW, ApprovalStatus.REJECTED]:
        st.text_area(
            "Reason for Review/Rejection:",
            placeholder="Required: Explain why this item needs review or was rejected",
            key=f"reason_{item.id}"
        )

    return doctor_notes
```

---

## Phase 3: Approval Workflow Engine (Week 3)

### Step 3.1: State Management System
Create workflow management for approval states:

```python
# services/approval_workflow.py
from enum import Enum
from typing import Dict, List
import logging

class WorkflowAction(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVIEW = "request_review"
    MODIFY = "modify"
    BULK_APPROVE = "bulk_approve"

class ApprovalWorkflow:
    def __init__(self, database_service):
        self.db = database_service
        self.logger = logging.getLogger(__name__)

    def process_approval(self, item_id: str, action: WorkflowAction,
                        doctor_id: str, notes: str = "") -> bool:
        """Process approval action with audit trail"""

        try:
            # Update item status
            self.db.update_research_item(
                item_id=item_id,
                approval_status=self._get_status_from_action(action),
                doctor_notes=notes,
                updated_by=doctor_id
            )

            # Log action for audit trail
            self._log_approval_action(item_id, action, doctor_id, notes)

            # Check if plan is complete
            self._check_plan_completion(item_id)

            return True

        except Exception as e:
            self.logger.error(f"Approval processing failed: {e}")
            return False

    def bulk_approve_category(self, plan_id: str, category: str,
                             doctor_id: str) -> int:
        """Approve all pending items in a category"""

        pending_items = self.db.get_pending_items_by_category(plan_id, category)
        approved_count = 0

        for item in pending_items:
            if item.confidence_score >= 0.8:  # Only auto-approve high confidence
                self.process_approval(item.id, WorkflowAction.APPROVE, doctor_id)
                approved_count += 1

        return approved_count

    def get_completion_status(self, plan_id: str) -> Dict:
        """Get overall plan completion status"""

        items = self.db.get_research_items(plan_id)

        status_counts = {
            "total": len(items),
            "approved": len([i for i in items if i.approval_status == ApprovalStatus.APPROVED]),
            "pending": len([i for i in items if i.approval_status == ApprovalStatus.PENDING]),
            "needs_review": len([i for i in items if i.approval_status == ApprovalStatus.NEEDS_REVIEW]),
            "rejected": len([i for i in items if i.approval_status == ApprovalStatus.REJECTED])
        }

        completion_percentage = (status_counts["approved"] / status_counts["total"]) * 100 if status_counts["total"] > 0 else 0

        return {
            "completion_percentage": completion_percentage,
            "status_counts": status_counts,
            "ready_for_finalization": status_counts["pending"] == 0
        }
```

### Step 3.2: Real-time Status Updates
Implement real-time status tracking:

```python
# components/status_dashboard.py
def render_approval_dashboard(plan_id: str, workflow: ApprovalWorkflow):
    """Render real-time approval status dashboard"""

    status = workflow.get_completion_status(plan_id)

    # Progress bar
    st.progress(status["completion_percentage"] / 100)
    st.write(f"**Plan Completion: {status['completion_percentage']:.1f}%**")

    # Status metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Items", status["status_counts"]["total"])

    with col2:
        st.metric("Approved", status["status_counts"]["approved"],
                 delta=status["status_counts"]["approved"])

    with col3:
        st.metric("Needs Review", status["status_counts"]["needs_review"])

    with col4:
        st.metric("Rejected", status["status_counts"]["rejected"])

    # Completion status
    if status["ready_for_finalization"]:
        st.success("✅ Plan ready for finalization!")
        if st.button("Finalize Plan & Generate Report"):
            return "finalize"
    else:
        remaining = status["status_counts"]["pending"] + status["status_counts"]["needs_review"]
        st.warning(f"⚠️ {remaining} items still need attention")
```

---

## Phase 4: Enhanced User Interface (Week 4)

### Step 4.1: Multi-Page Application Structure
Create professional multi-page Streamlit app:

```python
# doctor_demo_app.py
import streamlit as st
from components import interactive_table, category_navigation, doctor_notes
from services import approval_workflow, database_service

def main():
    st.set_page_config(
        page_title="Life Care Planning - Doctor Review",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize services
    if 'workflow' not in st.session_state:
        st.session_state.workflow = approval_workflow.ApprovalWorkflow(database_service)

    # Navigation
    pages = {
        "🏠 Dashboard": "dashboard",
        "🔍 Research Review": "review",
        "📊 Progress Tracking": "progress",
        "📋 Final Report": "report"
    }

    selected_page = st.sidebar.selectbox("Navigation", list(pages.keys()))
    page_key = pages[selected_page]

    # Route to appropriate page
    if page_key == "dashboard":
        render_dashboard_page()
    elif page_key == "review":
        render_review_page()
    elif page_key == "progress":
        render_progress_page()
    elif page_key == "report":
        render_report_page()

def render_dashboard_page():
    """Main dashboard with overview and quick actions"""

    st.title("🏥 Life Care Planning - Doctor Review")
    st.markdown("### Welcome, Dr. [Name]")

    # Quick stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Active Cases", 3)
    with col2:
        st.metric("Items Pending Review", 47)
    with col3:
        st.metric("Avg. Completion Time", "12 min")

    # Recent cases
    st.subheader("Recent Cases")

    cases_data = {
        "Patient": ["John Doe", "Jane Smith", "Mike Johnson"],
        "Status": ["In Review", "Completed", "Pending"],
        "Items": [15, 23, 9],
        "Progress": [67, 100, 0]
    }

    df = pd.DataFrame(cases_data)
    st.dataframe(df, use_container_width=True)

def render_review_page():
    """Main review interface with category navigation"""

    st.title("📋 Research Review & Approval")

    # Load current case
    case_id = st.selectbox("Select Case", ["case_001", "case_002"])
    plan_data = st.session_state.workflow.db.get_plan(case_id)

    # Category navigation
    selected_category = category_navigation.render_category_sidebar(plan_data)

    if selected_category:
        render_category_review(plan_data, selected_category)
    else:
        st.info("👈 Select a category from the sidebar to begin review")

def render_category_review(plan_data, category):
    """Render review interface for specific category"""

    st.subheader(f"Review: {LIFE_CARE_CATEGORIES[category]}")

    # Get items for this category
    category_items = [item for item in plan_data.research_items
                     if item.category == category]

    if not category_items:
        st.warning("No items found for this category")
        if st.button("Research Items for This Category"):
            # Trigger AI research for this category
            st.rerun()
        return

    # Bulk actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Approve All High Confidence"):
            approved = st.session_state.workflow.bulk_approve_category(
                plan_data.id, category, "doctor_demo"
            )
            st.success(f"Approved {approved} items")
            st.rerun()

    # Individual item review
    for item in category_items:
        render_item_review_card(item)

def render_item_review_card(item: ResearchItem):
    """Render individual item review card"""

    with st.container():
        # Header with status
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.subheader(item.item_service)

        with col2:
            status_color = {
                ApprovalStatus.APPROVED: "🟢",
                ApprovalStatus.PENDING: "🟡",
                ApprovalStatus.NEEDS_REVIEW: "🟠",
                ApprovalStatus.REJECTED: "🔴"
            }
            st.write(f"{status_color[item.approval_status]} {item.approval_status.value.title()}")

        with col3:
            st.write(f"Confidence: {item.confidence_score:.0%}")

        # Item details
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Cost:** ${item.cost_per_unit:,.2f}")
            st.write(f"**Range:** ${item.cost_range_min:,.0f} - ${item.cost_range_max:,.0f}")
            st.write(f"**Frequency:** {item.frequency}")
            if item.cpt_code:
                st.write(f"**CPT Code:** {item.cpt_code}")

        with col2:
            st.write(f"**Comment:** {item.comment}")
            st.write(f"**Sources:** {', '.join(item.sources[:2])}")

        # Approval actions
        approval_action = interactive_table.render_approval_controls(item)
        if approval_action:
            st.session_state.workflow.process_approval(
                item.id, approval_action, "doctor_demo"
            )
            st.rerun()

        # Doctor notes
        doctor_notes = doctor_notes.render_doctor_notes_section(item)

        st.divider()
```

### Step 4.2: Professional Styling
Add professional CSS styling:

```python
# styles/professional_theme.py
def apply_professional_styling():
    """Apply professional medical interface styling"""

    st.markdown("""
    <style>
    /* Main theme colors */
    :root {
        --primary-color: #1f4e79;
        --secondary-color: #2e8b57;
        --warning-color: #ff6b35;
        --success-color: #28a745;
        --background-color: #f8f9fa;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }

    /* Card styling for items */
    .review-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid var(--primary-color);
    }

    /* Status indicators */
    .status-approved { color: var(--success-color); font-weight: bold; }
    .status-pending { color: #ffc107; font-weight: bold; }
    .status-needs-review { color: var(--warning-color); font-weight: bold; }
    .status-rejected { color: #dc3545; font-weight: bold; }

    /* Approval buttons */
    .approve-btn {
        background-color: var(--success-color);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
    }

    /* Progress indicators */
    .progress-high { color: var(--success-color); }
    .progress-medium { color: var(--warning-color); }
    .progress-low { color: #dc3545; }

    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: var(--background-color);
    }

    /* Data editor enhancements */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## Phase 5: Report Generation & Export (Week 5)

### Step 5.1: Professional Report Templates
Create professional report generation:

```python
# services/report_generator.py
from jinja2 import Template
import pdfkit
from datetime import datetime

class LifeCareReportGenerator:
    def __init__(self):
        self.templates = self._load_templates()

    def generate_final_report(self, plan_data: LifeCarePlan,
                            doctor_signature: str) -> bytes:
        """Generate final PDF report with doctor approval"""

        # Organize data by category
        categorized_data = self._organize_by_category(plan_data.research_items)

        # Calculate totals
        cost_summary = self._calculate_cost_summary(plan_data.research_items)

        # Generate HTML report
        html_content = self._render_html_report(
            plan_data, categorized_data, cost_summary, doctor_signature
        )

        # Convert to PDF
        pdf_bytes = pdfkit.from_string(html_content, False, options={
            'page-size': 'Letter',
            'margin-top': '1in',
            'margin-right': '1in',
            'margin-bottom': '1in',
            'margin-left': '1in',
            'encoding': "UTF-8",
            'no-outline': None
        })

        return pdf_bytes

    def _render_html_report(self, plan_data, categorized_data,
                           cost_summary, doctor_signature):
        """Render HTML report using template"""

        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Life Care Plan - {{ plan_data.patient_name }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .header { text-align: center; border-bottom: 2px solid #1f4e79; padding-bottom: 20px; }
                .category { margin: 30px 0; }
                .category-title { background: #1f4e79; color: white; padding: 10px; }
                .item-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                .item-table th, .item-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .item-table th { background-color: #f4f4f4; }
                .approved { background-color: #d4edda; }
                .rejected { background-color: #f8d7da; }
                .signature { margin-top: 50px; text-align: right; }
                .summary { background: #f8f9fa; padding: 20px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Life Care Plan</h1>
                <h2>{{ plan_data.patient_name }}</h2>
                <p>Generated: {{ datetime.now().strftime('%B %d, %Y') }}</p>
                <p>Doctor Review Completed: {{ plan_data.completed_at.strftime('%B %d, %Y') if plan_data.completed_at else 'In Progress' }}</p>
            </div>

            <div class="summary">
                <h3>Cost Summary</h3>
                <table class="item-table">
                    <tr>
                        <th>Category</th>
                        <th>Items</th>
                        <th>Total Annual Cost</th>
                        <th>Present Value (20 years)</th>
                    </tr>
                    {% for category, summary in cost_summary.items() %}
                    <tr>
                        <td>{{ category.replace('_', ' ').title() }}</td>
                        <td>{{ summary.item_count }}</td>
                        <td>${{ "{:,.2f}".format(summary.annual_cost) }}</td>
                        <td>${{ "{:,.2f}".format(summary.present_value) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>

            {% for category, items in categorized_data.items() %}
            <div class="category">
                <div class="category-title">
                    <h3>{{ category.replace('_', ' ').title() }}</h3>
                </div>

                <table class="item-table">
                    <thead>
                        <tr>
                            <th>Item/Service</th>
                            <th>Cost per Unit</th>
                            <th>Frequency</th>
                            <th>CPT Code</th>
                            <th>Status</th>
                            <th>Doctor Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in items %}
                        <tr class="{{ 'approved' if item.approval_status.value == 'approved' else 'rejected' if item.approval_status.value == 'rejected' else '' }}">
                            <td>{{ item.item_service }}</td>
                            <td>${{ "{:,.2f}".format(item.cost_per_unit) }}</td>
                            <td>{{ item.frequency }}</td>
                            <td>{{ item.cpt_code or 'N/A' }}</td>
                            <td>{{ item.approval_status.value.replace('_', ' ').title() }}</td>
                            <td>{{ item.doctor_notes or 'No notes' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endfor %}

            <div class="signature">
                <p><strong>Doctor Signature:</strong></p>
                <p>{{ doctor_signature }}</p>
                <p>Date: {{ datetime.now().strftime('%B %d, %Y') }}</p>
            </div>
        </body>
        </html>
        """)

        return template.render(
            plan_data=plan_data,
            categorized_data=categorized_data,
            cost_summary=cost_summary,
            doctor_signature=doctor_signature,
            datetime=datetime
        )
```

### Step 5.2: Export Options
Add multiple export formats:

```python
# components/export_controls.py
def render_export_controls(plan_data: LifeCarePlan):
    """Render export options and controls"""

    st.subheader("📤 Export Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📄 Generate PDF Report"):
            pdf_bytes = generate_pdf_report(plan_data)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"life_care_plan_{plan_data.patient_name}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

    with col2:
        if st.button("📊 Export to Excel"):
            excel_bytes = generate_excel_export(plan_data)
            st.download_button(
                "Download Excel",
                data=excel_bytes,
                file_name=f"life_care_data_{plan_data.patient_name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col3:
        if st.button("📋 Copy Summary"):
            summary_text = generate_text_summary(plan_data)
            st.code(summary_text)
            st.success("Summary ready to copy!")

def generate_excel_export(plan_data: LifeCarePlan) -> bytes:
    """Generate Excel export with multiple sheets"""

    import pandas as pd
    from io import BytesIO

    # Create Excel writer
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        # Summary sheet
        summary_data = []
        for category in LIFE_CARE_CATEGORIES.keys():
            category_items = [item for item in plan_data.research_items
                            if item.category == category]
            if category_items:
                total_cost = sum(item.cost_per_unit for item in category_items)
                summary_data.append({
                    'Category': LIFE_CARE_CATEGORIES[category],
                    'Item Count': len(category_items),
                    'Total Annual Cost': total_cost,
                    'Approved Items': len([i for i in category_items if i.approval_status == ApprovalStatus.APPROVED])
                })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Detailed items sheet
        items_data = []
        for item in plan_data.research_items:
            items_data.append({
                'Category': LIFE_CARE_CATEGORIES.get(item.category, item.category),
                'Item/Service': item.item_service,
                'Cost per Unit': item.cost_per_unit,
                'Frequency': item.frequency,
                'CPT Code': item.cpt_code,
                'Approval Status': item.approval_status.value,
                'Doctor Notes': item.doctor_notes,
                'AI Confidence': item.confidence_score,
                'Sources': '; '.join(item.sources)
            })

        items_df = pd.DataFrame(items_data)
        items_df.to_excel(writer, sheet_name='Detailed Items', index=False)

    output.seek(0)
    return output.read()
```

---

## Phase 6: Testing & Deployment (Week 6)

### Step 6.1: Demo Data Setup
Create realistic demo data for presentation:

```python
# data/demo_data.py
def create_demo_life_care_plan() -> LifeCarePlan:
    """Create realistic demo data for doctor presentation"""

    demo_items = [
        # Mobility Equipment
        ResearchItem(
            id="item_001",
            category="mobility_equipment",
            item_service="Standard Walker with Wheels",
            cost_per_unit=125.00,
            cost_range_min=75.00,
            cost_range_max=175.00,
            frequency="Replace every 3-5 years",
            comment="Lightweight aluminum walker with front wheels and rear glides",
            sources=["medmartonline.com/walkers", "medicare.gov/dmepos"],
            cpt_code="E0130",
            approval_status=ApprovalStatus.PENDING,
            confidence_score=0.92
        ),
        ResearchItem(
            id="item_002",
            category="mobility_equipment",
            item_service="Power Wheelchair - Standard",
            cost_per_unit=15750.00,
            cost_range_min=12000.00,
            cost_range_max=25000.00,
            frequency="Replace every 5-7 years",
            comment="Standard power wheelchair with joystick control, suitable for indoor/outdoor use",
            sources=["medmartonline.com/power-wheelchairs", "cms.gov/medicare-coverage"],
            cpt_code="K0014",
            approval_status=ApprovalStatus.PENDING,
            confidence_score=0.88
        ),

        # Medications
        ResearchItem(
            id="item_003",
            category="medications",
            item_service="Gabapentin 300mg",
            cost_per_unit=45.00,
            cost_range_min=25.00,
            cost_range_max=85.00,
            frequency="Monthly prescription",
            comment="For neuropathic pain management, typical dose 300mg TID",
            sources=["goodrx.com/gabapentin", "fda.gov/orange-book"],
            cpt_code=None,
            approval_status=ApprovalStatus.PENDING,
            confidence_score=0.95
        ),

        # Therapeutic Services
        ResearchItem(
            id="item_004",
            category="therapeutic_services",
            item_service="Physical Therapy Session",
            cost_per_unit=150.00,
            cost_range_min=120.00,
            cost_range_max=200.00,
            frequency="2-3 sessions per week initially, then weekly maintenance",
            comment="Outpatient physical therapy for strength and mobility training",
            sources=["cms.gov/physician-fee-schedule", "fairhealth.org"],
            cpt_code="97110",
            approval_status=ApprovalStatus.PENDING,
            confidence_score=0.90
        ),

        # Medical Supplies
        ResearchItem(
            id="item_005",
            category="medical_supplies",
            item_service="Catheter Supplies (Monthly)",
            cost_per_unit=285.00,
            cost_range_min=200.00,
            cost_range_max=350.00,
            frequency="Monthly supply",
            comment="Intermittent catheter supplies including catheters, gloves, and cleaning supplies",
            sources=["medmartonline.com/catheters", "medicare.gov/dmepos"],
            cpt_code="A4351",
            approval_status=ApprovalStatus.NEEDS_REVIEW,
            doctor_notes="Patient may need different catheter type - verify with urology consult",
            confidence_score=0.82
        )
    ]

    return LifeCarePlan(
        patient_id="demo_patient_001",
        research_items=demo_items,
        overall_status="in_review",
        created_at=datetime.now()
    )
```

### Step 6.2: Integration Testing
Create comprehensive test suite:

```python
# tests/test_doctor_demo.py
import pytest
from services.approval_workflow import ApprovalWorkflow
from models import ResearchItem, ApprovalStatus

class TestDoctorDemo:

    def test_approval_workflow(self):
        """Test approval workflow functionality"""
        workflow = ApprovalWorkflow(mock_database())

        # Test item approval
        result = workflow.process_approval(
            item_id="test_001",
            action=WorkflowAction.APPROVE,
            doctor_id="demo_doctor",
            notes="Approved based on clinical needs"
        )

        assert result == True

        # Verify status change
        item = workflow.db.get_research_item("test_001")
        assert item.approval_status == ApprovalStatus.APPROVED

    def test_bulk_approval(self):
        """Test bulk approval of high-confidence items"""
        workflow = ApprovalWorkflow(mock_database())

        approved_count = workflow.bulk_approve_category(
            plan_id="test_plan",
            category="mobility_equipment",
            doctor_id="demo_doctor"
        )

        assert approved_count > 0

    def test_report_generation(self):
        """Test PDF report generation"""
        from services.report_generator import LifeCareReportGenerator

        generator = LifeCareReportGenerator()
        plan_data = create_demo_life_care_plan()

        pdf_bytes = generator.generate_final_report(
            plan_data=plan_data,
            doctor_signature="Dr. Demo Physician"
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b'%PDF')  # Valid PDF header
```

---

## Implementation Timeline Summary

| Week | Phase | Key Deliverables | Demo Features |
|------|-------|------------------|---------------|
| 1 | Data Structure | Pydantic models, JSON outputs, SQLite schema | Structured data display |
| 2 | Interactive Tables | Editable grids, approval controls, navigation | Click-to-edit tables |
| 3 | Approval Workflow | State management, bulk actions, audit trail | One-click approvals |
| 4 | UI Enhancement | Multi-page app, professional styling, dashboard | Polished interface |
| 5 | Report Generation | PDF export, Excel export, templates | Professional outputs |
| 6 | Testing & Demo | Demo data, integration tests, deployment | Ready for presentation |

## Success Metrics for Demo

**Functional Requirements:**
- ✅ Doctor can edit costs and comments inline
- ✅ One-click approval/rejection of items
- ✅ Bulk approval of high-confidence items
- ✅ Professional PDF report generation
- ✅ Real-time progress tracking

**User Experience:**
- ⏱️ <5 seconds to load and navigate between categories
- 🎯 <2 clicks to approve/reject items
- 📱 Responsive design works on tablets
- 🔄 Real-time updates without page refresh

**Professional Standards:**
- 📋 Maintains all 18 life care planning categories
- 📊 Proper cost calculations and formatting
- 🏥 Medical terminology and CPT code accuracy
- 📝 Audit trail for all doctor decisions

This implementation plan transforms your current text-based research assistant into a professional, interactive system that doctors can use to efficiently review and approve AI-generated life care planning research.