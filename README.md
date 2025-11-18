# Students-Insights-Model-2

Streamlit dashboard that unifies attendance, event participation, and LMS usage to surface actionable insights about student engagement.

## Getting started

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the Streamlit app:
   ```bash
   streamlit run script.py
   ```

## Features

- Rich sidebar filters: slice by student, date range, status, event type, session duration, and pages viewed.
- Overview metrics plus detailed tabs for attendance, events, LMS usage, and ML-based risk prediction.
- Quick data-entry forms that append to the CSV data sources without leaving the dashboard.