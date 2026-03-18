# Starbucks Nutrition Analyzer

An LLM-powered nutrition analysis dashboard for the full Starbucks menu. Built with Streamlit, pandas, Plotly, and the Groq API (Llama 3).

---

## Features

- **Dashboard** — key metric cards, macro comparison chart, and top-item rankings across drinks and food
- **AI Summaries** — one-click nutritional narrative and full structured report
- **Drinks Analysis** — filterable inventory with Nutri-Grade scoring, macro composition, and insulin-spike scatter visualization
- **Food Analysis** — filterable inventory with satiety scoring, optimal-choice scatter, and macro distribution
- **Ask the Menu** — conversational NL query with session memory, grounded in computed dataset statistics

---

## Requirements

- Python 3.12+
- A Groq API key

---

## Setup

**1. Clone the repository**
```bash
git clone <repo-url>
cd amaris-technical-test
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Add your Groq API key**

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```
Get a free key at [console.groq.com](https://console.groq.com). The app runs without a key — AI features will be disabled until one is provided.

**5. Run the app**
```bash
streamlit run app/main.py
```
Opens at `http://localhost:8501`.

---

## Project Structure

```
amaris-technical-test/
├── data/
│   ├── starbucks-menu-nutrition-drinks.csv
│   └── starbucks-menu-nutrition-food.csv
│
├── src/                        # Business logic
│   ├── data/
│   │   ├── loader.py           # Load CSV ingestion, encoding detection
│   │   ├── cleaner.py          # Cleaning pipeline, category imputation
│   │   └── processor.py        # Statistics, filtering, Plotly chart factories
│   └── llm/
│       ├── client.py           # Groq API wrapper
│       └── summarizer.py       # Prompt engineering, context builder, NL query engine
│
├── app/                        # Streamlit UI layer
│   ├── main.py                 # Entry point, navigation, session state
│   ├── static/styles.css       # Global CSS
│   ├── pages/
│   │   ├── dashboard.py
│   │   ├── drinks.py
│   │   ├── food.py
│   │   ├── console.py
│   │   └── settings.py
│   ├── charts/                 # Visualization
│   │   ├── drinks.py
│   │   └── food.py
│   ├── components/
│   │   ├── cards.py
│   │   ├── tables.py
│   │   └── ui.py               # Layout and banner HTML helpers
│   └── utils/
│       ├── food_categories.py
│       └── nutri_grade.py
│
├── requirements.txt
├── .env                        # Add your own
└── README.md
```

---

## Data Notes

| Dataset | Rows | Encoding | Notes |
|---|---|---|---|
| Drinks | ~240 raw | UTF-8 / Latin-1 (auto-detected) | ~40% of rows have missing values; filled via category-median imputation |
| Food | ~80 rows | UTF-16 LE with BOM | All rows have complete data |

- **Caffeine** data is not available in either dataset.
- **Sugar** is not directly measured; net carbs (carbs − fiber) is used as a proxy.

---