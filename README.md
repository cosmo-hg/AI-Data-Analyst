# 📊 AI Data Analyst

An intelligent data analysis assistant powered by **Google Gemini**. Ask natural language questions about your CSV or Excel datasets and get instant answers, SQL queries, and interactive data visualizations.

## 🚀 Features

- **Natural Language to SQL**: Transform plain English questions into optimized SQL queries.
- **Automated Insights**: Get summaries and key metrics from your data instantly.
- **Interactive UI**: Built with Streamlit for a seamless, chat-like experience.
- **Smart Schema Detection**: Automatically understands your data structure upon upload.
- **Multi-format Support**: Works with CSV, XLSX, and XLS files.
- **Safe & Secure**: Local database processing (SQLite) ensure your data remains under your control.

## 🛠️ Tech Stack

- **Large Language Model**: Google Gemini (via `langchain-google-genai`)
- **Framework**: LangChain & Streamlit
- **Data Processing**: Pandas & SQLAlchemy
- **Database**: SQLite (In-memory/Local)

## 🏗️ Getting Started

### Prerequisites

- Python 3.9 or higher
- A Google Gemini API Key (get it from [Google AI Studio](https://aistudio.google.com/apikey))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/cosmo-hg/AI-Data-Analyst.git
   cd AI-Data-Analyst
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory and add your API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Running the App

Start the application using the provided entry point:
```bash
python main.py
```
The app will be available at `http://localhost:8501`.

## 📂 Project Structure

- `ui/`: Streamlit interface components.
- `orchestrator/`: Core logic for query processing and model interaction.
- `chains/`: LangChain implementations for SQL generation and answer synthesis.
- `prompts/`: Optimized system prompts for the Gemini model.
- `data/`: Data loading and schema description utilities.
- `evaluation/`: Scripts and datasets for testing performance.

## 🤝 Contributing

Feel free to fork this project and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
