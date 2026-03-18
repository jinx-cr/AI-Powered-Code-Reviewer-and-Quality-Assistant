# AI-Powered-Code-Reviewer-and-Quality-Assistant

# 🧠 AI Code Reviewer 

An AI-powered Python code quality analyser built with Streamlit. Analyses your Python projects for docstring coverage, PEP 257 compliance, and cyclomatic complexity — with a Groq-powered AI Fix feature.

---

## 🚀 Run
```bash
pip install -r requirements.txt
streamlit run main_app.py
```

## ✨ Features

- 📊 Dashboard with test results, filters, search and export
- 📈 Cyclomatic complexity and Maintainability Index scoring
- 📝 Docstring coverage tracking per file
- ✅ PEP 257 compliance checker (D100–D400 rules)
- ⚡ AI auto-fix violations using Groq LLM
- 🧪 Built-in test suite with 90+ tests

## 🛠️ Tech Stack

Python · Streamlit · Groq API · Radon · Plotly · Pytest

## ⚙️ Setup

1. Clone the repo
2. Run `pip install -r requirements.txt`
3. Run `streamlit run main_app.py`

## 🧪 Run Tests
```bash
pytest tests/ -v
```
