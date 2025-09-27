# Life Care Planning Agent - User Interface Design

## Overview
Simple, intuitive web interface for 60-year-old doctors to input medical items and receive professional research results.

## Design Principles
- **Simplicity**: Minimal clicks, clear workflow
- **Accessibility**: Large fonts, high contrast, keyboard-friendly
- **Professional**: Medical industry appearance and standards
- **Efficiency**: Fast input → instant research → clear results

## Interface Layout

### 1. Header Section
```
🏥 Life Care Planning Research Assistant
Professional Medical Equipment & Cost Research
```
- Large, clear title
- Professional medical icon
- Subtitle explaining purpose

### 2. Input Section
```
┌─────────────────────────────────────────────┐
│ Enter medical items to research:            │
│ ┌─────────────────────────────────────────┐ │
│ │ walker                                  │ │
│ │ wheelchair                              │ │
│ │ oxygen concentrator                     │ │
│ │ hospital bed                            │ │
│ │ CPAP machine                            │ │
│ │                                         │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│     [🔍 Start Research]                     │
└─────────────────────────────────────────────┘
```

**Features:**
- Large text area (150px height)
- Placeholder examples showing format
- Help text: "Enter one item per line or separate with commas"
- Large, prominent research button (full width)

### 3. Processing Section
```
🔄 Researching your items...
Please wait while we gather professional cost data and specifications.

[████████████████████████████████] 100%
Currently researching: Hospital bed
```

**Features:**
- Progress indicator
- Current item being researched
- Professional loading message

### 4. Results Display

#### Summary Metrics
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Items Researched│ │ Total Est. Cost │ │   Status        │
│       5         │ │    $12,450      │ │  5/5 Found      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

#### Results Table
```
| Item/Service    | Cost per Unit | Comment           | Source(s)              |
|-----------------|---------------|-------------------|------------------------|
| Standard Walker | $75-$125      | Adjustable height | medmartonline.com      |
| Wheelchair      | $200-$450     | Manual, standard  | Medicare fee schedule  |
| Oxygen Conc.    | $300-$800     | 5L/min capacity   | medmartonline.com      |
```

**Features:**
- Clean, professional table styling
- Alternating row colors for readability
- Sortable columns
- Links in source column

### 5. Export Options
```
[📊 Download CSV]  [📄 Download PDF]  [🖨️ Print View]
```

**Features:**
- Three export formats
- Large, clear buttons
- Professional report formatting

### 6. Session Management
```
Recent Searches:
[Select previous research...        ▼]

[💾 Save This Research]
```

**Features:**
- Dropdown of recent searches
- Save current research session
- Load previous work

## Technical Implementation

### App.py Structure
```python
import streamlit as st
import asyncio
from agent import Life_Care_Agent, Runner

def main():
    # Header
    st.title("🏥 Life Care Planning Research Assistant")
    st.subheader("Professional Medical Equipment & Cost Research")

    # Input
    items_input = st.text_area(
        "Enter medical items to research:",
        placeholder="walker\nwheelchair\noxygen concentrator",
        height=150,
        help="Enter one item per line or separate with commas"
    )

    # Process
    if st.button("🔍 Start Research", type="primary", use_container_width=True):
        if items_input.strip():
            with st.spinner("Researching your items..."):
                result = asyncio.run(research_items(items_input))
                display_results(result)
        else:
            st.warning("Please enter at least one medical item to research.")

async def research_items(items_text):
    prompt = f"Research the following medical items and provide costs, codes, and details: {items_text}"
    result = await Runner.run(Life_Care_Agent, prompt)
    return result.final_output

def display_results(result_text):
    st.success("Research completed!")
    st.markdown("### Research Results")
    st.write(result_text)

    # Export options
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📊 Download CSV", result_text, "research.csv")
    with col2:
        st.download_button("📄 Download PDF", result_text, "research.pdf")
    with col3:
        if st.button("🖨️ Print View"):
            st.write("Print functionality here")

if __name__ == "__main__":
    main()
```

### Styling
```python
# Custom CSS for professional medical appearance
st.markdown("""
<style>
    .main {
        font-family: 'Arial', sans-serif;
        font-size: 18px;
    }
    .stButton > button {
        font-size: 20px;
        padding: 15px 30px;
        border-radius: 5px;
    }
    .stTextArea > div > div > textarea {
        font-size: 16px;
        line-height: 1.4;
    }
    .metric-container {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    h1 {
        color: #2c5aa0;
        margin-bottom: 10px;
    }
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)
```

## User Workflow
1. **Enter Items**: Doctor types or pastes list of medical items
2. **Click Research**: Single button press starts the process
3. **Wait**: Progress indicator shows research in progress
4. **Review Results**: Professional table with all requested information
5. **Export**: Download or print results in preferred format

## Accessibility Features
- **Large Fonts**: 18px base, 20px+ for buttons
- **High Contrast**: Dark text on light backgrounds
- **Keyboard Navigation**: Tab through all interactive elements
- **Screen Reader**: Proper labels and descriptions
- **Mobile Friendly**: Responsive design for tablets

## Error Handling
- Clear messages when items cannot be found
- Suggestions for alternative searches
- Graceful handling of API failures
- Retry options for failed requests

This design prioritizes ease of use for medical professionals while maintaining the robust research capabilities of your existing agent.