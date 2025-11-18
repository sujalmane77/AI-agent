"""
Streamlit dashboard for student engagement insights with advanced filters,
data entry helpers, and lightweight predictive analytics.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

st.set_page_config(page_title="Smart Campus Insights", layout="wide")

DATA_DIR = Path(__file__).parent
ATTENDANCE_FILE = DATA_DIR / "attendance_logs.csv"
EVENTS_FILE = DATA_DIR / "event_participation.csv"
LMS_FILE = DATA_DIR / "lms_usage.csv"


@st.cache_data
def load_attendance(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@st.cache_data
def load_events(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@st.cache_data
def load_lms(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def append_row(file_path: Path, row: dict) -> None:
    df = pd.DataFrame([row])
    header = not file_path.exists() or file_path.stat().st_size == 0
    df.to_csv(file_path, mode="a", index=False, header=header)


def invalidate_caches() -> None:
    load_attendance.clear()
    load_events.clear()
    load_lms.clear()


attendance_df = load_attendance(ATTENDANCE_FILE)
events_df = load_events(EVENTS_FILE)
lms_df = load_lms(LMS_FILE)

all_students = sorted(
    set(attendance_df["StudentID"]).union(events_df["StudentID"]).union(lms_df["StudentID"])
)
attendance_statuses = sorted(attendance_df["Status"].unique())
event_names = sorted(events_df["EventName"].unique())

st.sidebar.header("🔍 Advanced Filters")
selected_students = st.sidebar.multiselect(
    "Student IDs",
    options=all_students,
    default=all_students,
    help="Start typing to jump to any student quickly.",
)

min_att_date, max_att_date = attendance_df["Date"].min(), attendance_df["Date"].max()
date_range = st.sidebar.date_input(
    "Attendance window",
    value=(min_att_date.date(), max_att_date.date()),
    min_value=min_att_date.date(),
    max_value=max_att_date.date(),
)

selected_statuses = st.sidebar.multiselect(
    "Attendance Status",
    options=attendance_statuses,
    default=attendance_statuses,
)

selected_events = st.sidebar.multiselect(
    "Event Types",
    options=event_names,
    default=event_names,
)

session_min, session_max = float(lms_df["SessionDuration"].min()), float(lms_df["SessionDuration"].max())
session_range = st.sidebar.slider(
    "Session duration (minutes)",
    min_value=0.0,
    max_value=max(120.0, session_max),
    value=(0.0, max(60.0, session_min + 60)),
)

min_pages, max_pages = int(lms_df["PagesViewed"].min()), int(lms_df["PagesViewed"].max())
pages_range = st.sidebar.slider(
    "Pages viewed",
    min_value=0,
    max_value=max(20, max_pages),
    value=(0, max(10, min_pages + 10)),
)


def filter_frames():
    att = attendance_df[
        attendance_df["StudentID"].isin(selected_students)
        & attendance_df["Status"].isin(selected_statuses)
        & attendance_df["Date"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
    ]

    ev = events_df[
        events_df["StudentID"].isin(selected_students) & events_df["EventName"].isin(selected_events)
    ]

    lms = lms_df[
        lms_df["StudentID"].isin(selected_students)
        & lms_df["SessionDuration"].between(session_range[0], session_range[1])
        & lms_df["PagesViewed"].between(pages_range[0], pages_range[1])
    ]

    return att, ev, lms


filtered_attendance, filtered_events, filtered_lms = filter_frames()

st.title("📊 Smart Campus Insights")
st.caption(
    "Slice and dice students across attendance, events, and LMS usage. The filters update every chart instantly."
)

overview_tab, attendance_tab, events_tab, lms_tab, model_tab, entry_tab = st.tabs(
    ["Overview", "Attendance", "Events", "LMS", "Engagement Risk", "Quick Data Entry"]
)

with overview_tab:
    st.subheader("Key Engagement Pulse")

    absent_rate = (
        (filtered_attendance["Status"].str.lower() == "absent").mean()
        if not filtered_attendance.empty
        else 0
    )
    avg_sessions = filtered_lms["SessionDuration"].mean() if not filtered_lms.empty else 0
    participation = filtered_events.groupby("StudentID").size().mean() if not filtered_events.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Attendance (Present%)", f"{(1 - absent_rate):.0%}")
    col2.metric("Avg Session Duration", f"{avg_sessions:,.1f} min")
    col3.metric("Avg Events/Student", f"{participation:,.1f}")

    st.divider()

    merged = filtered_attendance.merge(
        filtered_lms.groupby("StudentID")[["SessionDuration", "PagesViewed"]].mean().reset_index(),
        on="StudentID",
        how="left",
    ).merge(
        filtered_events.groupby("StudentID").size().reset_index(name="EventsAttended"),
        on="StudentID",
        how="left",
    )
    st.dataframe(
        merged.fillna({"SessionDuration": 0, "PagesViewed": 0, "EventsAttended": 0}).sort_values(
            ["StudentID", "Date"]
        ),
        use_container_width=True,
    )

with attendance_tab:
    st.subheader("Attendance Trends")
    if filtered_attendance.empty:
        st.info("No attendance data matches the selected filters.")
    else:
        attendance_summary = (
            filtered_attendance.groupby(["Date", "Status"]).size().reset_index(name="Count")
        )
        att_chart = px.area(
            attendance_summary,
            x="Date",
            y="Count",
            color="Status",
            title="Daily Attendance Status",
        )
        st.plotly_chart(att_chart, use_container_width=True)

        st.write("Detailed Log")
        st.dataframe(filtered_attendance.sort_values("Date"), use_container_width=True)

with events_tab:
    st.subheader("Event Participation")
    if filtered_events.empty:
        st.info("No event data matches the selected filters.")
    else:
        event_counts = filtered_events.groupby(["EventName"]).size().reset_index(name="Attendance")
        event_chart = px.bar(
            event_counts,
            x="EventName",
            y="Attendance",
            color="EventName",
            title="Events Attended",
        )
        st.plotly_chart(event_chart, use_container_width=True)

        timeline = filtered_events.groupby(["Date", "EventName"]).size().reset_index(name="Count")
        timeline_chart = px.scatter(
            timeline,
            x="Date",
            y="Count",
            color="EventName",
            size="Count",
            title="Event Timeline",
        )
        st.plotly_chart(timeline_chart, use_container_width=True)

        st.write("Raw Participation Data")
        st.dataframe(filtered_events.sort_values("Date", ascending=False), use_container_width=True)

with lms_tab:
    st.subheader("Learning Management Usage")
    if filtered_lms.empty:
        st.info("No LMS data matches the selected filters.")
    else:
        lms_summary = (
            filtered_lms.groupby("StudentID")[["SessionDuration", "PagesViewed"]]
            .mean()
            .reset_index()
        )
        lms_chart = px.scatter(
            lms_summary,
            x="SessionDuration",
            y="PagesViewed",
            hover_name="StudentID",
            size="PagesViewed",
            title="Avg Session Duration vs. Pages Viewed",
        )
        st.plotly_chart(lms_chart, use_container_width=True)

        st.write("Session Details")
        st.dataframe(filtered_lms.sort_values("Date", ascending=False), use_container_width=True)

with model_tab:
    st.subheader("Engagement Risk Predictor")
    ml_data = pd.merge(
        attendance_df.groupby("StudentID")["Status"]
        .apply(lambda x: (x.str.lower() == "absent").mean())
        .reset_index(name="AbsenceRate"),
        lms_df.groupby("StudentID")[["SessionDuration", "PagesViewed"]].mean().reset_index(),
        on="StudentID",
    )
    ml_data["Engagement"] = (ml_data["AbsenceRate"] < 0.2).astype(int)

    X = ml_data[["AbsenceRate", "SessionDuration", "PagesViewed"]]
    y = ml_data["Engagement"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, stratify=y)

    model = DecisionTreeClassifier(max_depth=4, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    st.write("Model performance")
    st.text(classification_report(y_test, y_pred))

    st.write("Feature importance")
    importances = pd.DataFrame(
        {"Feature": X.columns, "Importance": model.feature_importances_}
    ).sort_values("Importance", ascending=False)
    st.bar_chart(importances.set_index("Feature"))

    st.write("Predict new student")
    col_a, col_b, col_c = st.columns(3)
    absence_rate = col_a.number_input("Absence Rate (0-1)", min_value=0.0, max_value=1.0, value=0.1)
    session_duration = col_b.number_input(
        "Avg Session Duration (min)", min_value=0.0, max_value=300.0, value=45.0
    )
    pages_viewed = col_c.number_input("Avg Pages Viewed", min_value=0.0, max_value=100.0, value=12.0)

    if st.button("Predict Engagement", type="primary"):
        prediction = model.predict([[absence_rate, session_duration, pages_viewed]])[0]
        label = "Engaged" if prediction == 1 else "At Risk"
        st.success(f"Predicted Engagement Status: {label}")

with entry_tab:
    st.subheader("One-click data entry")
    st.write(
        "Append fresh attendance, event, or LMS records directly from here. "
        "The dashboard refreshes with your changes instantly."
    )

    att_col, event_col, lms_col = st.columns(3)

    with att_col:
        st.markdown("**Attendance**")
        with st.form("attendance_form", clear_on_submit=True):
            att_student = st.text_input("Student ID", placeholder="e.g. S021")
            att_date = st.date_input("Date")
            att_status = st.selectbox("Status", attendance_statuses)
            att_submit = st.form_submit_button("Save attendance")
            if att_submit:
                if not att_student:
                    st.warning("Student ID is required.")
                else:
                    append_row(
                        ATTENDANCE_FILE,
                        {"StudentID": att_student, "Date": att_date.isoformat(), "Status": att_status},
                    )
                    invalidate_caches()
                    st.success("Attendance record saved.")
                    st.experimental_rerun()

    with event_col:
        st.markdown("**Event participation**")
        with st.form("event_form", clear_on_submit=True):
            event_student = st.text_input("Student ID", key="event_student", placeholder="e.g. S021")
            event_name = st.selectbox("Event", event_names)
            event_date = st.date_input("Event date")
            event_submit = st.form_submit_button("Save event")
            if event_submit:
                if not event_student:
                    st.warning("Student ID is required.")
                else:
                    append_row(
                        EVENTS_FILE,
                        {"StudentID": event_student, "EventName": event_name, "Date": event_date.isoformat()},
                    )
                    invalidate_caches()
                    st.success("Event participation recorded.")
                    st.experimental_rerun()

    with lms_col:
        st.markdown("**LMS usage**")
        with st.form("lms_form", clear_on_submit=True):
            lms_student = st.text_input("Student ID", key="lms_student", placeholder="e.g. S021")
            lms_date = st.date_input("Session date")
            lms_duration = st.number_input("Session duration (min)", min_value=0.0, value=30.0)
            lms_pages = st.number_input("Pages viewed", min_value=0, value=5)
            lms_submit = st.form_submit_button("Save session")
            if lms_submit:
                if not lms_student:
                    st.warning("Student ID is required.")
                else:
                    append_row(
                        LMS_FILE,
                        {
                            "StudentID": lms_student,
                            "Date": lms_date.isoformat(),
                            "SessionDuration": lms_duration,
                            "PagesViewed": lms_pages,
                        },
                    )
                    invalidate_caches()
                    st.success("LMS session stored.")
                    st.experimental_rerun()

    st.info(
        textwrap.dedent(
            """
            💡 Tip: preload IDs for incoming batches using the forms, then leverage the filters
            to validate the new entries right away.
            """
        )
    )

