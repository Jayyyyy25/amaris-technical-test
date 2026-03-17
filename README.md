# Starbucks Nutrition Analysis Tool

An LLM-powered nutrition analysis tool for the Starbucks menu. Built with Streamlit, pandas, Plotly, and the Groq LLM API (Llama 3).

## Features

- **Data loading & cleaning** — Handles two Starbucks CSVs (drinks and food) with automatic encoding detection, missing-value handling, and deduplication
- **Descriptive statistics** — Per-dataset and cross-dataset nutritional summaries
- **Interactive visualizations** — Bar charts, pie charts, scatter plots, and histograms (Plotly)
- **AI-generated insights** — Groq/Llama 3 produces natural language nutritional summaries
- **Natural language Q&A** — Ask free-form questions about the menu; the LLM answers using context injection

## Requirements

- Python 3.12+
- A Groq API key

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd amaris-technical-test
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your Groq API key**
   ```bash
   # Edit .env and replace the placeholder with your actual key
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. **Run the app**
   ```bash
   streamlit run app/main.py
   ```
   The app opens at `http://localhost:8501`.

## Project Structure

```
amaris-technical-test/
├── data/                        # Starbucks CSV datasets
│   ├── starbucks-menu-nutrition-drinks.csv
│   └── starbucks-menu-nutrition-food.csv
├── src/                         # Business logic (no Streamlit dependency)
│   ├── data_loader.py           # CSV ingestion and encoding detection
│   ├── data_processor.py        # Cleaning pipeline, statistics, filtering
│   ├── visualizer.py            # Plotly chart factories
│   ├── llm_client.py            # Groq API wrapper
│   └── summarizer.py            # Prompt engineering and NL query engine
├── app/                         # Streamlit UI layer
│   ├── main.py                  # Entry point, sidebar, session state
│   └── pages/
│       ├── overview.py          # Dataset stats and data quality report
│       ├── visualizations.py    # Interactive charts
│       ├── llm_summary.py       # AI-generated nutritional insights
│       └── nl_query.py          # Natural language Q&A
├── requirements.txt
├── .env.example
└── README.md
```

## Usage

- **Upload your own CSVs** via the sidebar file uploaders, or use the bundled datasets in `data/`
- **Filter the data** with the sidebar sliders (max calories, max fat, etc.)
- **Generate insights** on the "LLM Insights" page (requires Groq API key)
- **Ask questions** like "What is the highest calorie food item?" on the "Ask a Question" page

## Data Notes

- Approximately 40% of drink entries have no nutritional data in the source CSV; these rows are automatically removed during cleaning
- Caffeine content is **not available** in the source datasets
- The food CSV uses UTF-16 encoding, which is handled automatically

## Design Decisions

| Decision | Rationale |
|---|---|
| Streamlit over Flask | Better suited for data apps; built-in widgets, no HTML/CSS needed |
| Context injection over RAG | Datasets are small and structured — injecting computed stats is more accurate than retrieval |
| `src/` isolated from `app/` | Business logic is independently testable without Streamlit |
| `chardet` + hardcoded UTF-16 fallback | Reliable encoding detection with a safety net for the known food CSV encoding |
| `pd.to_numeric(errors='coerce')` | Silently converts any bad values to NaN instead of crashing |
