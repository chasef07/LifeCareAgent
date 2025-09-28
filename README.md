# Life Care Planning Research Assistant

A professional AI-powered tool for life care planning research that enables doctors to review, edit, and approve medical equipment and medication recommendations with interactive tables and structured reporting.

## 🌟 Features

- **AI Research**: Automated research of medical equipment, medications, and costs using OpenAI agents
- **Doctor Review Interface**: Interactive editable tables for medical professional oversight
- **Approval Workflow**: Simple approve/reject/needs review system for each researched item
- **Cost Editing**: Direct inline editing of costs and medical details
- **Professional Reports**: Structured export functionality for final documentation
- **Real-time Updates**: Live summary statistics and progress tracking

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd LifeCareAgent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   # Create .env file with your OpenAI API key
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

5. Open your browser to `http://localhost:8501`

## 📋 How to Use

### 1. Research Phase
- Enter medical items to research (one per line or comma-separated)
- Examples: `walker, wheelchair, oxygen concentrator, physical therapy`
- Click "Start Research" to begin AI analysis

### 2. Doctor Review Phase
- Review AI-generated research in the interactive table
- Edit costs directly in the table cells
- Select approval status for each item:
  - **Pending**: Not yet reviewed
  - **Approved**: Accepted for final plan
  - **Rejected**: Not suitable for patient
  - **Needs Review**: Requires additional consideration
- Add doctor notes for clinical context

### 3. Export Phase
- View real-time summary statistics
- Export final report with approved items only
- Download formatted text report with all decisions

## 🏥 Doctor Demo Features

- **Editable Tables**: Click-to-edit costs, frequencies, and notes
- **Approval Controls**: Dropdown selection for each item status
- **Summary Metrics**: Real-time counts of approved/rejected/pending items
- **Professional Export**: Formatted reports ready for documentation
- **Cost Calculations**: Automatic totaling of approved annual costs

## 🔧 Configuration

### AI Agent Settings
The AI research agent can be configured in `lifecareagent.py`:
- **Data Sources**: Currently uses medmartonline.com for equipment, goodrx.com for medications
- **Output Format**: Structured JSON with cost ranges, CPT codes, and source citations
- **Research Quality**: Focuses on 50th percentile (median) costs when available

### Streamlit Settings
- **Layout**: Wide layout optimized for table viewing
- **Theme**: Professional medical interface styling
- **Session Management**: Maintains data between interactions

## 📁 Project Structure

```
LifeCareAgent/
├── app.py                    # Main Streamlit application
├── lifecareagent.py          # AI research agent configuration
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── README.md                 # This file
├── ARCHITECTURE.md           # Detailed system architecture
└── LifeCareAgent_Research.md # Research documentation
```

## 🔒 Security & Privacy

- **Environment Variables**: API keys stored securely in .env file
- **Session State**: Data only persists during browser session
- **No Data Storage**: No patient information is permanently stored
- **Local Processing**: All data processing happens locally or via secure APIs

## 🚀 Deployment Options

### Local Development
```bash
streamlit run app.py
```

### Streamlit Community Cloud
1. Push code to GitHub repository
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Deploy with one click

### Production Deployment
For production use with real patient data:
- Use secure cloud platforms (AWS, GCP, Azure)
- Implement proper authentication
- Ensure HIPAA compliance measures
- Use encrypted data transmission

## 📊 Sample Usage

### Input Example:
```
walker
power wheelchair
gabapentin 300mg
physical therapy sessions
hospital bed with rails
```

### Expected AI Output:
- Structured research data with costs, CPT codes, and sources
- Interactive table for doctor review
- Approval workflow for each item
- Professional formatted export

## 🛠️ Development

### Adding New Features
- **New Data Sources**: Modify agent instructions in `lifecareagent.py`
- **UI Components**: Add functions to `app.py`
- **Export Formats**: Extend `generate_report()` function

### Testing
```bash
# Test AI agent directly
python lifecareagent.py

# Test Streamlit app
streamlit run app.py
```

## 📞 Support

For issues or questions:
1. Check the documentation in `ARCHITECTURE.md`
2. Review the research methodology in `LifeCareAgent_Research.md`
3. Create an issue in the GitHub repository

## 📄 License

This project is designed for professional medical use. Ensure compliance with local healthcare regulations and privacy laws when deploying.

---

**Note**: This tool is designed to assist medical professionals in life care planning research. All AI-generated recommendations should be reviewed and approved by qualified medical personnel before use in patient care planning.