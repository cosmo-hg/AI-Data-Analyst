"""
Streamlit UI for AI Data Analyst
Chat-style interface for natural language data analysis.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st
import pandas as pd
from orchestrator.core import DataAnalystOrchestrator
from data.data_loader import load_uploaded_file
from config import AVAILABLE_MODELS, DEFAULT_MODEL, get_all_models, get_model_by_name, has_gemini_api_key

# Page configuration
st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 10px;
    }
    .sql-box {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .upload-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        color: #155724;
    }
    .model-info {
        font-size: 0.85rem;
        color: #666;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)


def get_orchestrator():
    """Get or create orchestrator based on current session state."""
    # Check if we need to reinitialize (model or data changed)
    current_model = st.session_state.get("selected_model", DEFAULT_MODEL)
    current_db = st.session_state.get("uploaded_db_path")
    current_schema = st.session_state.get("uploaded_schema")
    
    cached_key = f"orchestrator_{current_model}_{current_db}"
    
    if cached_key not in st.session_state:
        # Clear any old orchestrators
        for key in list(st.session_state.keys()):
            if key.startswith("orchestrator_"):
                del st.session_state[key]
        
        # Create new orchestrator
        st.session_state[cached_key] = DataAnalystOrchestrator(
            model_name=current_model,
            db_path=current_db,
            custom_schema=current_schema
        )
    
    return st.session_state[cached_key]


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_sql" not in st.session_state:
        st.session_state.show_sql = False
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL
    if "uploaded_db_path" not in st.session_state:
        st.session_state.uploaded_db_path = None
    if "uploaded_schema" not in st.session_state:
        st.session_state.uploaded_schema = None
    if "uploaded_schema_dict" not in st.session_state:
        st.session_state.uploaded_schema_dict = None
    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None


def render_model_selector():
    """Render the model selector in sidebar."""
    st.markdown("## 🤖 Model Selection")
    
    # Get all available models (Gemini only)
    all_models = get_all_models()
    model_options = [m.name for m in all_models]
    model_display = {m.name: m.display_name for m in all_models}
    
    # Find current index
    current_model = st.session_state.selected_model
    current_index = 0
    for i, m in enumerate(all_models):
        if m.name == current_model:
            current_index = i
            break
    
    # Model dropdown
    selected = st.selectbox(
        "Choose a model",
        options=model_options,
        index=current_index,
        format_func=lambda x: model_display.get(x, x),
        key="model_selector"
    )
    
    # Show model info
    selected_config = get_model_by_name(selected)
    if selected_config:
        st.markdown(f"<p class='model-info'>{selected_config.description}</p>", unsafe_allow_html=True)
        
        # Check for API key
        if not has_gemini_api_key():
            st.warning("⚠️ Add your GEMINI_API_KEY to the .env file")
    
    # Update session state if model changed
    if selected != st.session_state.selected_model:
        st.session_state.selected_model = selected
        # Clear messages when switching models
        st.session_state.messages = []
        st.rerun()


def render_file_uploader():
    """Render the file upload section."""
    st.markdown("## 📁 Upload Data")
    
    uploaded_file = st.file_uploader(
        "Drop a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Upload your own dataset to analyze",
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        # Check if this is a new file
        if st.session_state.uploaded_filename != uploaded_file.name:
            with st.spinner("Processing file..."):
                try:
                    # Load the file
                    db_path, schema_desc, schema_dict = load_uploaded_file(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        table_name="data"
                    )
                    
                    # Store in session
                    st.session_state.uploaded_db_path = db_path
                    st.session_state.uploaded_schema = schema_desc
                    st.session_state.uploaded_schema_dict = schema_dict
                    st.session_state.uploaded_filename = uploaded_file.name
                    
                    # Clear old messages and orchestrator cache
                    st.session_state.messages = []
                    for key in list(st.session_state.keys()):
                        if key.startswith("orchestrator_"):
                            del st.session_state[key]
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to load file: {str(e)}")
                    return
        
        # Show success message
        st.success(f"✅ Loaded: **{uploaded_file.name}**")
    
    # Button to clear uploaded data and start fresh
    if st.session_state.uploaded_db_path is not None:
        if st.button("🗑️ Clear Data & Start Fresh", use_container_width=True):
            st.session_state.uploaded_db_path = None
            st.session_state.uploaded_schema = None
            st.session_state.uploaded_schema_dict = None
            st.session_state.uploaded_filename = None
            st.session_state.messages = []
            # Clear orchestrator cache
            for key in list(st.session_state.keys()):
                if key.startswith("orchestrator_"):
                    del st.session_state[key]
            st.rerun()


def render_schema_info():
    """Render schema information based on current data source."""
    st.markdown("## 📋 Available Data")
    
    if st.session_state.uploaded_schema_dict:
        # Dynamic schema from uploaded file
        schema = st.session_state.uploaded_schema_dict
        st.markdown(f"**Table:** `{schema['table_name']}`")
        st.markdown(f"**Rows:** {schema['row_count']:,}")
        st.markdown("**Columns:**")
        
        for col_name, col_info in schema['columns'].items():
            st.markdown(f"- `{col_name}`: {col_info['type']}")
    else:
        # No data uploaded - show prompt
        st.info("""
        📁 **No data loaded**
        
        Upload a CSV or Excel file using the uploader above to get started.
        
        Once uploaded, you can ask questions like:
        - "Show me the first 5 rows"
        - "How many records are there?"
        - "What are the unique values in column X?"
        """)


def render_sidebar():
    """Render the sidebar with options and info."""
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        
        # Show SQL toggle
        st.session_state.show_sql = st.toggle(
            "Show SQL Queries",
            value=st.session_state.show_sql,
            help="Display the generated SQL for each answer"
        )
        
        st.divider()
        
        # Model selector
        render_model_selector()
        
        st.divider()
        
        # File uploader
        render_file_uploader()
        
        st.divider()
        
        # Schema info
        render_schema_info()
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            try:
                orchestrator = get_orchestrator()
                orchestrator.clear_memory()
            except:
                pass
            st.rerun()
        
        st.divider()
        
        # Example questions (dynamic based on data source)
        st.markdown("## 💡 Example Questions")
        
        if st.session_state.uploaded_schema_dict:
            # Dynamic examples for uploaded data
            schema = st.session_state.uploaded_schema_dict
            columns = list(schema['columns'].keys())
            
            example_questions = [
                f"How many rows are in the data?",
                f"Show me 5 sample records",
                f"What are the unique values in {columns[0]}?" if columns else "Show all data",
            ]
            
            if len(columns) >= 2:
                example_questions.append(f"Count by {columns[0]}")
        else:
            example_questions = [
                "What is the total revenue?",
                "Top 10 products by quantity sold",
                "Which country has the most orders?",
                "How many unique customers?",
                "Average order value by country",
                "Monthly sales trend"
            ]
        
        for q in example_questions:
            if st.button(q, key=f"example_{q}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()


def render_message(role: str, content: str, sql: str = None, 
                   columns: list = None, rows: list = None, has_table: bool = False):
    """Render a chat message with optional SQL and table."""
    with st.chat_message(role):
        st.markdown(content)
        
        # Show SQL if enabled and available
        if sql and st.session_state.show_sql and role == "assistant":
            with st.expander("🔍 View SQL Query"):
                st.code(sql, language="sql")
        
        # Show results table if applicable
        if has_table and columns and rows and role == "assistant":
            with st.expander("📊 View Data Table", expanded=len(rows) <= 10):
                df = pd.DataFrame(rows, columns=columns)
                st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    
    # Main header
    st.markdown('<p class="main-header">📊 AI Data Analyst</p>', unsafe_allow_html=True)
    
    # Dynamic subheader
    if st.session_state.uploaded_filename:
        subtitle = f"Analyzing: **{st.session_state.uploaded_filename}**"
    else:
        subtitle = "Upload a CSV or Excel file to start analyzing your data"
    st.markdown(f'<p class="sub-header">{subtitle}</p>', unsafe_allow_html=True)
    
    # Check if data is loaded
    if not st.session_state.uploaded_db_path:
        st.info("""
        👋 **Welcome to AI Data Analyst!**
        
        Upload a CSV or Excel file using the sidebar to get started.
        Then ask questions about your data in natural language!
        """)
    
    # Get orchestrator
    try:
        orchestrator = get_orchestrator()
    except Exception as e:
        st.error(f"""
        ⚠️ **Failed to initialize AI model!**
        
        Make sure you have set up your Gemini API key:
        1. Get your API key from https://aistudio.google.com/apikey
        2. Add it to the `.env` file: `GEMINI_API_KEY=your-key-here`
        
        Error: {str(e)}
        """)
        st.stop()
    
    # Display chat history
    for msg in st.session_state.messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            sql=msg.get("sql"),
            columns=msg.get("columns"),
            rows=msg.get("rows"),
            has_table=msg.get("has_table", False)
        )
    
    # Check for pending question from sidebar
    if "pending_question" in st.session_state:
        question = st.session_state.pending_question
        del st.session_state.pending_question
    else:
        question = None
    
    # Chat input
    if prompt := (question or st.chat_input("Ask a question about the data...")):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                result = orchestrator.process_query(prompt)
            
            # Display answer
            st.markdown(result["answer"])
            
            # Show SQL if enabled
            if result["sql"] and st.session_state.show_sql:
                with st.expander("🔍 View SQL Query"):
                    st.code(result["sql"], language="sql")
            
            # Show table if applicable
            if result["has_table"] and result["columns"] and result["rows"]:
                with st.expander("📊 View Data Table", expanded=len(result["rows"]) <= 10):
                    df = pd.DataFrame(result["rows"], columns=result["columns"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Show error if any
            if result["error"]:
                st.error(f"Error details: {result['error']}")
        
        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sql": result["sql"],
            "columns": result["columns"],
            "rows": result["rows"],
            "has_table": result["has_table"]
        })


if __name__ == "__main__":
    main()
