# gui.py
import streamlit as st
import pandas as pd
from app_logic import authenticate_user, get_user_info, get_student_assignments, get_teacher_analytics, create_classroom, process_ocr_upload, SPHERE_DATA
from ai_tutor import create_tutor_session, send_message
from data_analyzer import fit_curve, propagate_error, get_dataset_summary
import time # For cool transitions/animations

# --- Configuration & State Initialization ---
st.set_page_config(
    page_title="SPHERE AI Learning Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.current_page = 'Login'
    st.session_state.chat_session = None

# --- UI Components and Helpers ---

def cool_button(label, key, role_color="blue"):
    """Creates an attractive button with CSS styling."""
    st.markdown(f"""
    <style>
    .stButton > button[key="{key}"] {{
        background-color: {'#4CAF50' if role_color == 'green' else '#2196F3' if role_color == 'blue' else '#FF9800'};
        color: white;
        padding: 10px 24px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 12px;
        transition-duration: 0.4s;
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
    }}
    .stButton > button[key="{key}"]:hover {{
        background-color: #f44336; /* Hover effect */
    }}
    </style>
    """, unsafe_allow_html=True)
    return st.button(label, key=key)

def navbar():
    """Displays the sidebar navigation based on user role."""
    st.sidebar.title("SPHERE Platform 🎓")
    st.sidebar.header(f"Welcome, {st.session_state.user_info['name']}!")
    
    pages = {
        "student": ["Dashboard", "AI Tutor", "Data Analysis", "OCR/Upload"],
        "teacher": ["Dashboard", "Classrooms", "Test Generator", "Analytics"],
        "admin": ["Dashboard", "User Management", "RAG Admin", "System Health"],
    }
    
    role = st.session_state.user_info['role']
    st.session_state.current_page = st.sidebar.radio("Navigation", pages[role], index=0)

    if cool_button("Logout 👋", "logout_btn", "red"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.current_page = 'Login'
        st.session_state.chat_session = None
        st.experimental_rerun()

# --- Page Implementations ---

def login_page():
    """Handles user login."""
    st.title("Login to SPHERE AI Platform")
    
    with st.form("login_form"):
        email = st.text_input("Email (e.g., student@ai.com)")
        password = st.text_input("Password (any text for demo)", type="password")
        submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            user = authenticate_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_info = user
                st.session_state.current_page = 'Dashboard'
                st.success(f"Login successful! Redirecting to {user['role']} dashboard...")
                time.sleep(1) # Cool transition effect
                st.experimental_rerun()
            else:
                st.error("Invalid email or password.")

def dashboard_page():
    """Generic dashboard view."""
    role = st.session_state.user_info['role']
    st.title(f"{role.upper()} Dashboard 📊")
    st.write("---")

    if role == 'student':
        st.header("My Classrooms & Assignments")
        
        assignments = get_student_assignments(st.session_state.user_info['email'])
        if assignments:
            st.dataframe(pd.DataFrame(assignments), hide_index=True)
        else:
            st.info("No active assignments found.")

    elif role == 'teacher':
        st.header("Classroom Overview")
        st.metric(label="Total Classrooms", value=len(app_logic.CLASSROOMS))
        st.metric(label="Student Roster Size", value=len(app_logic.USERS) - 2) # Exclude admin/teacher

        # Placeholder for creating a classroom
        with st.expander("➕ Create New Classroom"):
            with st.form("new_class_form"):
                class_name = st.text_input("Classroom Name", "New Physics 202")
                if st.form_submit_button("Create"):
                    new_id = create_classroom(st.session_state.user_info['email'], class_name)
                    st.success(f"Classroom '{class_name}' created with code: {app_logic.CLASSROOMS[new_id]['code']}")
        
        st.header("Quick Analytics")
        analytics = get_teacher_analytics(None) # Placeholder
        st.dataframe(pd.Series(analytics).rename("Value").to_frame(), use_container_width=True)


def ai_tutor_page():
    """AI Tutor Workspace using Gemini 2.5 Flash."""
    st.title("AI Workspace 🧠")
    st.info("Context-aware AI Tutor (Gemini 2.5 Flash) is ready to help with Physics and STEM questions.")

    # Initialize chat session if not present
    if st.session_state.chat_session is None:
        st.session_state.chat_session = create_tutor_session(st.session_state.user_info['role'])
        if st.session_state.chat_session:
            st.session_state.messages = []
            st.session_state.messages.append({"role": "AI", "content": "Hello! I'm your AI Tutor. What can I help you learn today?"})
        else:
            st.error("Could not initialize AI Tutor. Check API Key.")
            return

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask your tutor..."):
        st.session_state.messages.append({"role": "User", "content": prompt})
        with st.chat_message("User"):
            st.markdown(prompt)

        # Send message to Gemini
        with st.spinner("AI Tutor is thinking..."):
            response = send_message(st.session_state.chat_session, prompt)
            st.session_state.messages.append({"role": "AI", "content": response})
            with st.chat_message("AI"):
                st.markdown(response)
        
        # Save Session (Feature Stub)
        # st.session_state.saved_sessions.append({'user': prompt, 'ai': response})


def data_analysis_page():
    """Data Analysis and Error Propagation Tools."""
    st.title("Experimental Data Analyzer 🔬")
    st.write("---")
    
    st.header("Merged Dataset Summary (SPHERE CSV)")
    summary = get_dataset_summary()
    st.dataframe(pd.Series(summary).rename("Value").to_frame(), use_container_width=True)
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.header("1. Curve Fitting")
        st.markdown("**Example Data:** $x = [1, 2, 3, 4, 5]$, $y = [1.2, 3.8, 9.5, 15.1, 25.5]$")
        
        # Simple data input for demo
        x_str = st.text_input("X Data (comma-separated)", "1, 2, 3, 4, 5")
        y_str = st.text_input("Y Data (comma-separated)", "1.2, 3.8, 9.5, 15.1, 25.5")
        fit_type = st.selectbox("Select Curve Type", ['linear', 'poly2'])
        
        if st.button("Run Curve Fit", type="primary"):
            try:
                x_data = [float(i.strip()) for i in x_str.split(',')]
                y_data = [float(i.strip()) for i in y_str.split(',')]
                
                if len(x_data) != len(y_data):
                    st.error("X and Y data must have the same number of points.")
                else:
                    fit_eq, y_fit = fit_curve(x_data, y_data, fit_type)
                    st.success(f"Result: {fit_eq}")
                    
                    # Visualization-ready output
                    if y_fit is not None:
                        plot_df = pd.DataFrame({'X': x_data, 'Y (Observed)': y_data, 'Y (Fitted)': y_fit})
                        st.line_chart(plot_df.set_index('X'))

            except ValueError:
                st.error("Please enter valid numerical data.")


    with col2:
        st.header("2. Error Propagation")
        st.markdown("**Formula:** $F = m \cdot a$")
        
        st.subheader("Values:")
        m = st.number_input("Mass (m)", value=10.0)
        a = st.number_input("Acceleration (a)", value=2.0)
        
        st.subheader("Uncertainties ($\Delta$):")
        dm = st.number_input("Error in m ($\Delta m$)", value=0.1)
        da = st.number_input("Error in a ($\Delta a$)", value=0.1)

        if st.button("Calculate Error", type="secondary"):
            values = {'m': m, 'a': a}
            errors = {'m': dm, 'a': da}
            result = propagate_error("F=ma", values, errors)
            st.success(result)

def ocr_upload_page():
    """OCR Image-to-Text/Data Extraction."""
    st.title("OCR Parser & Media Upload 🖼️")
    st.info("Upload an image of an experiment, a handwritten solution, or data table.")

    uploaded_file = st.file_uploader("Upload Image File", type=['jpg', 'jpeg', 'png'])

    if uploaded_file is not None:
        st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)
        
        if cool_button("Extract Text & Data", "ocr_run_btn", "green"):
            with st.spinner("Parsing image with Tesseract/OCR integration..."):
                # In a real app, this would read the file's bytes and pass to the backend OCR logic
                # For now, use the logic stub:
                extracted_data = process_ocr_upload(uploaded_file.read())
                
                st.subheader("Extracted Results:")
                st.code(extracted_data)
                
                # Feature Stub: Save to DB
                st.success("Extracted text/data stored for project reference.")

# --- Main App Execution ---

if __name__ == "__main__":
    import app_logic # Need to import the logic file to access constants

    if st.session_state.logged_in:
        # User is logged in, show the sidebar and current page
        navbar()
        
        # Route to the correct page based on session state
        if st.session_state.current_page == 'Dashboard':
            dashboard_page()
        elif st.session_state.current_page == 'AI Tutor':
            ai_tutor_page()
        elif st.session_state.current_page == 'Data Analysis':
            if st.session_state.user_info['role'] == 'student':
                data_analysis_page()
            else:
                st.error("Access Denied: Only students can use the direct Data Analysis tool.")
        elif st.session_state.current_page == 'OCR/Upload':
            if st.session_state.user_info['role'] == 'student':
                ocr_upload_page()
            else:
                st.error("Access Denied: Only students can use the OCR tool.")
        # Add stubs for Teacher/Admin pages here
        elif st.session_state.current_page in ['Classrooms', 'Test Generator', 'Analytics', 'User Management', 'RAG Admin', 'System Health']:
            st.title(st.session_state.current_page)
            st.info("This feature is architected in `app_logic.py` and is a placeholder for a full implementation.")
            st.dataframe(app_logic.SPHERE_DATA.head()) # Example display of merged data
            

    else:
        # User is not logged in, show the login page
        login_page()
