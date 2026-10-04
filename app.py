import json

import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client as TwilioClient

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    ANALYSIS_PROMPT,
    STUDY_PROMPT,
    EXPENSE_PROMPT,
    DEADLINE_PROMPT,
    SUMMARY_REQUEST_PROMPT,
    QUIZ_PROMPT,
    STUDY_PLAN_PROMPT,
    RECOMMENDATION_PROMPT,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SnapWise AI",
    page_icon="🧠",
    layout="wide",
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "gemini-3.5-flash"


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]

TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]

TWILIO_WHATSAPP_FROM = st.secrets["TWILIO_WHATSAPP_FROM"]

TWILIO_CONTENT_SID = st.secrets["TWILIO_CONTENT_SID"]


# ============================================================
# CACHED CLIENTS
# ============================================================

@st.cache_resource
def get_gemini_client():
    return genai.Client(
        api_key=GEMINI_API_KEY
    )


@st.cache_resource
def get_twilio_client():
    return TwilioClient(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )


gemini_client = get_gemini_client()

twilio_client = get_twilio_client()


# ============================================================
# SESSION STATE
# ============================================================

if "name" not in st.session_state:
    st.session_state.name = ""

if "whatsapp_number" not in st.session_state:
    st.session_state.whatsapp_number = ""

if "onboarded" not in st.session_state:
    st.session_state.onboarded = False

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_image" not in st.session_state:
    st.session_state.last_image = None

if "last_image_type" not in st.session_state:
    st.session_state.last_image_type = "image/jpeg"

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = ""

if "analysis_type" not in st.session_state:
    st.session_state.analysis_type = "GENERAL"


# ============================================================
# MESSAGE FUNCTIONS
# ============================================================

def add_message(role, kind, content):
    st.session_state.messages.append(
        {
            "role": role,
            "kind": kind,
            "content": content,
        }
    )


def render_message(message):

    with st.chat_message(message["role"]):

        if message["kind"] == "text":

            st.markdown(message["content"])

        elif message["kind"] == "image":

            st.image(
                message["content"],
                caption="Uploaded image",
                use_container_width=True,
            )


def render_all_messages():

    for message in st.session_state.messages:

        render_message(message)


# ============================================================
# GEMINI FUNCTION
# ============================================================

def ask_gemini(prompt, image_bytes=None, mime_type=None):

    try:

        contents = []

        if image_bytes is not None:

            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type or "image/jpeg",
            )

            contents.append(image_part)

        contents.append(prompt)

        response = gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2500,
            ),
        )

        if response.text:

            return response.text

        return "Sorry, I couldn't generate a response."

    except Exception as error:

        return f"Sorry, something went wrong: {error}"


# ============================================================
# WHATSAPP TEXT CLEANER
# ============================================================

def clean_whatsapp_text(text):

    if not text:

        return "No summary available."

    # Remove excessive whitespace/new lines
    text = " ".join(text.split())

    # Keep the message reasonably short
    if len(text) > 1500:

        return text[:1500] + "..."

    return text


# ============================================================
# SEND WHATSAPP
# ============================================================

def send_whatsapp(to_number, user_name, summary):

    try:

        clean_summary = clean_whatsapp_text(
            summary
        )

        # Template variables:
        # {{1}} = user's name
        # {{2}} = summary

        content_variables = json.dumps(
            {
                "1": user_name,
                "2": clean_summary,
            },
            ensure_ascii=False,
        )

        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to_number}",
            content_sid=TWILIO_CONTENT_SID,
            content_variables=content_variables,
        )

        return True, message.sid

    except Exception as error:

        return False, str(error)


# ============================================================
# RESET SESSION
# ============================================================

def reset_session():

    st.session_state.name = ""

    st.session_state.whatsapp_number = ""

    st.session_state.onboarded = False

    st.session_state.messages = []

    st.session_state.last_image = None

    st.session_state.last_image_type = "image/jpeg"

    st.session_state.last_analysis = ""

    st.session_state.analysis_type = "GENERAL"


# ============================================================
# ONBOARDING
# ============================================================

if not st.session_state.onboarded:

    st.title("🧠 SnapWise AI")

    st.caption(
        "Snap it. Understand it. Take action."
    )

    st.write(
        "Your AI assistant for study material, "
        "expenses, deadlines and smart everyday analysis."
    )

    st.divider()

    with st.form("onboarding_form"):

        name = st.text_input(
            "Your name",
            placeholder="Enter your name",
        )

        whatsapp_number = st.text_input(
            "WhatsApp number",
            placeholder="+91XXXXXXXXXX",
            help="Enter the number that joined your Twilio WhatsApp Sandbox.",
        )

        submitted = st.form_submit_button(
            "Let's Get Started 🚀",
            use_container_width=True,
        )

        if submitted:

            if (
                not name.strip()
                or not whatsapp_number.strip()
            ):

                st.warning(
                    "Please enter both your name and WhatsApp number."
                )

            else:

                st.session_state.name = name.strip()

                st.session_state.whatsapp_number = (
                    whatsapp_number.strip()
                )

                st.session_state.messages = []

                st.session_state.onboarded = True

                st.rerun()

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🧠 SnapWise AI")

    st.write(
        f"Welcome, **{st.session_state.name}** 👋"
    )

    st.divider()

    st.subheader("What can I analyze?")

    st.write("📚 Study Material")
    st.write("🧾 Receipts & Expenses")
    st.write("📅 Deadlines & Timetables")
    st.write("📄 Documents")
    st.write("🖼️ Images")
    st.write("💬 Text Questions")

    st.divider()

    st.subheader("Smart Actions")

    st.write("📖 Explain")
    st.write("📝 Generate Quiz")
    st.write("📅 Create Study Plan")
    st.write("💰 Split Bill")
    st.write("🎯 Recommend Next Action")
    st.write("📱 Send to WhatsApp")

    st.divider()

    if st.button(
        "🔄 Start New Session",
        use_container_width=True,
    ):

        reset_session()

        st.rerun()


# ============================================================
# HEADER
# ============================================================

header_col, whatsapp_col = st.columns(
    [5, 2],
    vertical_alignment="center",
)


with header_col:

    st.title("🧠 SnapWise AI")

    st.caption(
        "Snap anything. Understand everything. Take action."
    )


# ============================================================
# WHATSAPP BUTTON
# ============================================================

with whatsapp_col:

    has_conversation = (
        len(st.session_state.messages) > 1
    )

    if st.button(
        "📱 Send to WhatsApp",
        disabled=not has_conversation,
        use_container_width=True,
    ):

        with st.spinner(
            "Preparing your WhatsApp summary..."
        ):

            summary = ask_gemini(
                SUMMARY_REQUEST_PROMPT
            )

        success, info = send_whatsapp(
            st.session_state.whatsapp_number,
            st.session_state.name,
            summary,
        )

        if success:

            st.success(
                "Sent! Check your WhatsApp 📲"
            )

        else:

            st.error(
                f"Couldn't send the message: {info}"
            )


st.caption(
    f"WhatsApp: {st.session_state.whatsapp_number}"
)


# ============================================================
# WELCOME MESSAGE
# ============================================================

if not st.session_state.messages:

    welcome = WELCOME_MESSAGE_TEMPLATE.format(
        name=st.session_state.name
    )

    add_message(
        "assistant",
        "text",
        welcome,
    )


# ============================================================
# CHAT HISTORY
# ============================================================

render_all_messages()


# ============================================================
# CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Ask something or attach an image...",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
    ],
)


# ============================================================
# PROCESS USER INPUT
# ============================================================

if user_input:

    photo = (
        user_input.files[0]
        if user_input.files
        else None
    )

    text = user_input.text.strip()

    image_bytes = None

    mime_type = None


    # --------------------------------------------------------
    # IMAGE
    # --------------------------------------------------------

    if photo is not None:

        image_bytes = photo.getvalue()

        mime_type = photo.type

        st.session_state.last_image = image_bytes

        st.session_state.last_image_type = mime_type

        add_message(
            "user",
            "image",
            image_bytes,
        )


    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if text:

        add_message(
            "user",
            "text",
            text,
        )


    # --------------------------------------------------------
    # DEFAULT IMAGE QUESTION
    # --------------------------------------------------------

    if (
        not text
        and image_bytes is not None
    ):

        text = (
            "Analyze this image and explain "
            "what it contains."
        )


    # --------------------------------------------------------
    # AUTOMATIC CLASSIFICATION
    # --------------------------------------------------------

    with st.spinner(
        "🔍 Understanding your input..."
    ):

        analysis = ask_gemini(
            ANALYSIS_PROMPT
            + "\n\nUser input:\n"
            + text,
            image_bytes,
            mime_type,
        )


    st.session_state.last_analysis = analysis


    # --------------------------------------------------------
    # DETECT TYPE
    # --------------------------------------------------------

    upper_analysis = analysis.upper()


    if "STUDY" in upper_analysis:

        st.session_state.analysis_type = "STUDY"

    elif "EXPENSE" in upper_analysis:

        st.session_state.analysis_type = "EXPENSE"

    elif "DEADLINE" in upper_analysis:

        st.session_state.analysis_type = "DEADLINE"

    else:

        st.session_state.analysis_type = "GENERAL"


    # --------------------------------------------------------
    # SELECT RESPONSE PROMPT
    # --------------------------------------------------------

    if st.session_state.analysis_type == "STUDY":

        selected_prompt = STUDY_PROMPT

    elif st.session_state.analysis_type == "EXPENSE":

        selected_prompt = EXPENSE_PROMPT

    elif st.session_state.analysis_type == "DEADLINE":

        selected_prompt = DEADLINE_PROMPT

    else:

        selected_prompt = RECOMMENDATION_PROMPT


    # --------------------------------------------------------
    # GENERATE ANSWER
    # --------------------------------------------------------

    with st.spinner(
        "🧠 Creating your smart response..."
    ):

        answer = ask_gemini(
            selected_prompt
            + "\n\nInitial analysis:\n"
            + analysis,
            image_bytes,
            mime_type,
        )


    add_message(
        "assistant",
        "text",
        answer,
    )


    st.rerun()


# ============================================================
# SMART ACTIONS
# ============================================================

if st.session_state.last_analysis:

    st.divider()

    st.subheader("⚡ Smart Actions")

    st.caption(
        f"Detected type: **{st.session_state.analysis_type}**"
    )


    # ========================================================
    # STUDY
    # ========================================================

    if st.session_state.analysis_type == "STUDY":

        col1, col2, col3 = st.columns(3)


        with col1:

            if st.button(
                "📖 Explain Simply",
                use_container_width=True,
            ):

                with st.spinner(
                    "Explaining..."
                ):

                    result = ask_gemini(
                        STUDY_PROMPT,
                        st.session_state.last_image,
                        st.session_state.last_image_type,
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


        with col2:

            if st.button(
                "📝 Generate Quiz",
                use_container_width=True,
            ):

                with st.spinner(
                    "Creating quiz..."
                ):

                    result = ask_gemini(
                        QUIZ_PROMPT
                        + "\n\nTopic:\n"
                        + st.session_state.last_analysis
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


        with col3:

            if st.button(
                "📅 Study Plan",
                use_container_width=True,
            ):

                with st.spinner(
                    "Building study plan..."
                ):

                    result = ask_gemini(
                        STUDY_PLAN_PROMPT
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


    # ========================================================
    # EXPENSE
    # ========================================================

    elif st.session_state.analysis_type == "EXPENSE":

        col1, col2 = st.columns(2)


        with col1:

            if st.button(
                "🧾 Analyze Expense",
                use_container_width=True,
            ):

                with st.spinner(
                    "Analyzing expense..."
                ):

                    result = ask_gemini(
                        EXPENSE_PROMPT,
                        st.session_state.last_image,
                        st.session_state.last_image_type,
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


        with col2:

            people = st.number_input(
                "Number of people",
                min_value=1,
                max_value=50,
                value=2,
            )

            if st.button(
                "💰 Split Bill",
                use_container_width=True,
            ):

                split_prompt = f"""
Analyze the receipt or bill.

Split the total amount equally among
{people} people.

Give:

Total:
Number of people:
Amount per person:

Show the calculation clearly.

Do not invent missing values.
"""

                with st.spinner(
                    "Calculating..."
                ):

                    result = ask_gemini(
                        split_prompt,
                        st.session_state.last_image,
                        st.session_state.last_image_type,
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


    # ========================================================
    # DEADLINE
    # ========================================================

    elif st.session_state.analysis_type == "DEADLINE":

        col1, col2 = st.columns(2)


        with col1:

            if st.button(
                "📅 Extract Deadlines",
                use_container_width=True,
            ):

                with st.spinner(
                    "Finding deadlines..."
                ):

                    result = ask_gemini(
                        DEADLINE_PROMPT,
                        st.session_state.last_image,
                        st.session_state.last_image_type,
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


        with col2:

            if st.button(
                "🎯 Create Action Plan",
                use_container_width=True,
            ):

                with st.spinner(
                    "Creating action plan..."
                ):

                    result = ask_gemini(
                        STUDY_PLAN_PROMPT
                    )

                add_message(
                    "assistant",
                    "text",
                    result,
                )

                st.rerun()


    # ========================================================
    # GENERAL
    # ========================================================

    else:

        if st.button(
            "🎯 What Should I Do Next?",
            use_container_width=True,
        ):

            with st.spinner(
                "Thinking..."
            ):

                result = ask_gemini(
                    RECOMMENDATION_PROMPT
                )

            add_message(
                "assistant",
                "text",
                result,
            )

            st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🧠 SnapWise AI | Gemini Vision + Smart Actions + Twilio WhatsApp"
)







# import json

# import streamlit as st
# from google import genai
# from google.genai import types
# from twilio.rest import Client as TwilioClient

# from prompts import (
#     SUMMARY_REQUEST_PROMPT,
#     SYSTEM_PROMPT,
#     WELCOME_MESSAGE_TEMPLATE,
# )


# # --------------------------------------------------
# # CONFIGURATION
# # --------------------------------------------------

# MODEL_NAME = "gemini-3.5-flash"

# st.set_page_config(
#     page_title="Snap & Study",
#     page_icon="📚",
#     layout="centered",
# )


# # --------------------------------------------------
# # API KEYS
# # --------------------------------------------------

# GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
# TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
# TWILIO_WHATSAPP_FROM = st.secrets["TWILIO_WHATSAPP_FROM"]
# TWILIO_CONTENT_SID = st.secrets["TWILIO_CONTENT_SID"]


# # --------------------------------------------------
# # GEMINI CLIENT
# # --------------------------------------------------

# @st.cache_resource
# def get_gemini_client():
#     return genai.Client(api_key=GEMINI_API_KEY)


# # --------------------------------------------------
# # TWILIO CLIENT
# # --------------------------------------------------

# @st.cache_resource
# def get_twilio_client():
#     return TwilioClient(
#         TWILIO_ACCOUNT_SID,
#         TWILIO_AUTH_TOKEN
#     )


# gemini_client = get_gemini_client()
# twilio_client = get_twilio_client()


# # --------------------------------------------------
# # MESSAGE DISPLAY
# # --------------------------------------------------

# def render_message(message):

#     with st.chat_message(message["role"]):

#         if message["kind"] == "text":

#             st.write(message["content"])

#         elif message["kind"] == "image":

#             st.image(
#                 message["content"],
#                 use_container_width=True
#             )


# # --------------------------------------------------
# # ADD MESSAGE
# # --------------------------------------------------

# def add_message(role, kind, content):

#     st.session_state.messages.append(
#         {
#             "role": role,
#             "kind": kind,
#             "content": content
#         }
#     )

#     render_message(
#         st.session_state.messages[-1]
#     )


# # --------------------------------------------------
# # ASK GEMINI
# # --------------------------------------------------

# def ask_gemini(parts):

#     try:

#         response = st.session_state.chat.send_message(parts)

#         return response.text

#     except Exception as error:

#         return f"Sorry, something went wrong: {error}"


# # --------------------------------------------------
# # WHATSAPP TEXT CLEANER
# # --------------------------------------------------

# def clean_whatsapp_text(text):

#     if not text:

#         return "No study summary available."

#     text = " ".join(text.split())

#     return text[:1500] + "..." if len(text) > 1500 else text


# # --------------------------------------------------
# # SEND WHATSAPP
# # --------------------------------------------------

# def send_whatsapp(to_number, user_name, summary):

#     try:

#         content_variables = json.dumps(
#             {
#                 "1": user_name,
#                 "2": clean_whatsapp_text(summary)
#             },
#             ensure_ascii=False
#         )

#         message = twilio_client.messages.create(

#             from_=TWILIO_WHATSAPP_FROM,

#             to=f"whatsapp:{to_number}",

#             content_sid=TWILIO_CONTENT_SID,

#             content_variables=content_variables,
#         )

#         return True, message.sid

#     except Exception as error:

#         return False, str(error)


# # ==================================================
# # ONBOARDING
# # ==================================================

# if "onboarded" not in st.session_state:

#     st.title("📚 Snap & Study")

#     st.caption(
#         "Snap it. Understand it. Learn it."
#     )

#     st.write(
#         "Your AI study buddy for questions, "
#         "diagrams, notes, textbook pages and coding problems."
#     )

#     with st.form("onboarding_form"):

#         name = st.text_input(
#             "Your name"
#         )

#         whatsapp_number = st.text_input(
#             "WhatsApp number (with country code)",

#             placeholder="+91XXXXXXXXXX",

#             help="Your study summaries will be sent to this number."
#         )

#         submitted = st.form_submit_button(
#             "Start Learning 🚀"
#         )

#     if submitted:

#         if not name.strip() or not whatsapp_number.strip():

#             st.warning(
#                 "Please fill in both your name and WhatsApp number."
#             )

#         else:

#             st.session_state.name = name.strip()

#             st.session_state.whatsapp_number = (
#                 whatsapp_number.strip()
#             )

#             # Create Gemini conversation
#             st.session_state.chat = gemini_client.chats.create(

#                 model=MODEL_NAME,

#                 config=types.GenerateContentConfig(
#                     system_instruction=SYSTEM_PROMPT
#                 )
#             )

#             st.session_state.messages = []

#             st.session_state.onboarded = True

#             st.rerun()

#     st.stop()


# # ==================================================
# # HEADER
# # ==================================================

# header_col, button_col = st.columns(
#     [5, 2],
#     vertical_alignment="center"
# )


# with header_col:

#     st.title("📚 Snap & Study")


# with button_col:

#     send_disabled = (
#         len(st.session_state.messages) <= 2
#     )

#     if st.button(
#         "📤 Send to WhatsApp",
#         disabled=send_disabled,
#         use_container_width=True
#     ):

#         with st.spinner(
#             "Preparing your study summary..."
#         ):

#             summary = ask_gemini(
#                 [SUMMARY_REQUEST_PROMPT]
#             )

#         success, info = send_whatsapp(

#             st.session_state.whatsapp_number,

#             st.session_state.name,

#             summary
#         )

#         if success:

#             st.success(
#                 "Study summary sent to WhatsApp! 📲"
#             )

#         else:

#             st.error(
#                 f"Couldn't send the summary: {info}"
#             )


# # ==================================================
# # USER INFORMATION
# # ==================================================

# st.caption(
#     f"Student: {st.session_state.name}"
# )


# # ==================================================
# # EXPLANATION LEVEL
# # ==================================================

# st.subheader("🎯 Choose Explanation Level")


# explanation_level = st.radio(

#     "How should I explain things?",

#     [
#         "Beginner",
#         "Intermediate",
#         "Exam Preparation"
#     ],

#     horizontal=True,

#     label_visibility="collapsed"
# )


# # ==================================================
# # LEVEL INSTRUCTIONS
# # ==================================================

# level_instructions = {

#     "Beginner": """
# Explain this for a beginner.

# Use very simple language.
# Assume the student is learning the topic for the first time.
# Use a small example whenever useful.
# """,

#     "Intermediate": """
# Explain this at an intermediate level.

# Assume the student knows the basic concepts.
# Focus on understanding the logic and solving the problem.
# """,

#     "Exam Preparation": """
# Explain this for exam preparation.

# Keep it concise and exam-oriented.
# Highlight definitions, formulas, important steps,
# key points, and the final answer.
# """
# }


# # ==================================================
# # WELCOME MESSAGE
# # ==================================================

# if not st.session_state.messages:

#     add_message(

#         "assistant",

#         "text",

#         WELCOME_MESSAGE_TEMPLATE.format(
#             name=st.session_state.name
#         )
#     )

# else:

#     for message in st.session_state.messages:

#         render_message(message)


# # ==================================================
# # CHAT INPUT
# # ==================================================

# user_input = st.chat_input(

#     "Ask a question or upload a study image...",

#     accept_file=True,

#     file_type=[
#         "jpg",
#         "jpeg",
#         "png"
#     ]
# )


# # ==================================================
# # HANDLE USER INPUT
# # ==================================================

# if user_input:

#     photo = (
#         user_input.files[0]
#         if user_input.files
#         else None
#     )

#     text = user_input.text

#     parts = []


#     # ----------------------------------------------
#     # IMAGE
#     # ----------------------------------------------

#     if photo is not None:

#         photo_bytes = photo.getvalue()

#         add_message(
#             "user",
#             "image",
#             photo_bytes
#         )

#         parts.append(

#             types.Part.from_bytes(

#                 data=photo_bytes,

#                 mime_type=photo.type
#             )
#         )


#     # ----------------------------------------------
#     # TEXT
#     # ----------------------------------------------

#     if text:

#         add_message(
#             "user",
#             "text",
#             text
#         )

#         parts.append(text)


#     # ----------------------------------------------
#     # PHOTO WITHOUT TEXT
#     # ----------------------------------------------

#     elif photo is not None:

#         parts.append(
#             "Analyze this study material and explain it clearly."
#         )


#     # ----------------------------------------------
#     # EXPLANATION LEVEL
#     # ----------------------------------------------

#     parts.append(

#         level_instructions[
#             explanation_level
#         ]
#     )


#     # ----------------------------------------------
#     # ASK GEMINI
#     # ----------------------------------------------

#     with st.spinner(
#         "Studying your question... 📚"
#     ):

#         answer = ask_gemini(parts)


#     # ----------------------------------------------
#     # DISPLAY ANSWER
#     # ----------------------------------------------

#     add_message(

#         "assistant",

#         "text",

#         answer
#     )
# # import json
 
# # import streamlit as st
# # from google import genai
# # from google.genai import types
# # from twilio.rest import Client as TwilioClient
 
# # from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE
 
# # MODEL_NAME = "gemini-3.5-flash"
# # st.set_page_config(page_title="MacroSnap", page_icon="🥗")
 
# # GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
# # TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
# # TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
# # TWILIO_WHATSAPP_FROM = st.secrets["TWILIO_WHATSAPP_FROM"]
# # TWILIO_CONTENT_SID = st.secrets["TWILIO_CONTENT_SID"]
 
 
# # @st.cache_resource
# # def get_gemini_client():
# #     return genai.Client(api_key=GEMINI_API_KEY)
 
 
# # @st.cache_resource
# # def get_twilio_client():
# #     return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
 
 
# # gemini_client = get_gemini_client()
# # twilio_client = get_twilio_client()
 
 
# # def render_message(message):
# #     with st.chat_message(message["role"]):
# #         if message["kind"] == "text":
# #             st.write(message["content"])
# #         elif message["kind"] == "image":
# #             st.image(message["content"])
 
 
# # def add_message(role, kind, content):
# #     st.session_state.messages.append({"role": role, "kind": kind, "content": content})
# #     render_message(st.session_state.messages[-1])
 
 
# # def ask_gemini(parts):
# #     try:
# #         return st.session_state.chat.send_message(parts).text
# #     except Exception as error:
# #         return f"Sorry, something went wrong: {error}"
 
 
# # def clean_whatsapp_text(text):
# #     if not text:
# #         return "No nutrition summary available."
# #     text = " ".join(text.split())  # collapse whitespace/newlines
# #     return text[:1500] + "..." if len(text) > 1500 else text
 
 
# # def send_whatsapp(to_number, user_name, summary):
# #     # Content template expects {{1}} = name, {{2}} = summary.
# #     try:
# #         content_variables = json.dumps(
# #             {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
# #         )
# #         message = twilio_client.messages.create(
# #             from_=TWILIO_WHATSAPP_FROM,
# #             to=f"whatsapp:{to_number}",
# #             content_sid=TWILIO_CONTENT_SID,
# #             content_variables=content_variables,
# #         )
# #         return True, message.sid
# #     except Exception as error:
# #         return False, str(error)
 
 
# # # Step 1: onboarding
# # if "onboarded" not in st.session_state:
# #     st.title("🥗 MacroSnap")
# #     st.caption("Snap it. Track it. Text yourself the results.")
# #     with st.form("onboarding_form"):
# #         name = st.text_input("Your name")
# #         whatsapp_number = st.text_input(
# #             "WhatsApp number (with country code)",
# #             placeholder="+91XXXXXXXXXX",
# #             help="This is the number MacroSnap will text your summary to.",
# #         )
# #         submitted = st.form_submit_button("Let's go 🚀")
# #     if submitted:
# #         if not name.strip() or not whatsapp_number.strip():
# #             st.warning("Please fill in both your name and WhatsApp number.")
# #         else:
# #             st.session_state.name = name.strip()
# #             st.session_state.whatsapp_number = whatsapp_number.strip()
# #             st.session_state.chat = gemini_client.chats.create(
# #                 model=MODEL_NAME,
# #                 config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
# #             )
# #             st.session_state.messages = []
# #             st.session_state.onboarded = True
# #             st.rerun()
# #     st.stop()
 
# # # Step 2: chat interface
# # header_col, button_col = st.columns([5, 2], vertical_alignment="center")
 
# # with header_col:
# #     st.title("🥗 MacroSnap")
 
# # with button_col:
# #     send_disabled = len(st.session_state.messages) <= 2
# #     if st.button("📤 Send to WhatsApp", disabled=send_disabled, use_container_width=True):
# #         with st.spinner("Summarizing your day..."):
# #             summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
# #         success, info = send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
# #         if success:
# #             st.success("Sent! Check your WhatsApp 📲")
# #         else:
# #             st.error(f"Couldn't send that: {info}")
 
# # st.caption(f"Logged in as {st.session_state.name} - updates go to {st.session_state.whatsapp_number}")
 
# # if not st.session_state.messages:
# #     add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
# # else:
# #     for message in st.session_state.messages:
# #         render_message(message)
 
# # user_input = st.chat_input(
# #     "Ask a question, or attach a photo of your meal",
# #     accept_file=True,
# #     file_type=["jpg", "jpeg", "png"],
# # )
 
# # if user_input:
# #     photo = user_input.files[0] if user_input.files else None
# #     text = user_input.text
# #     parts = []
 
# #     if photo is not None:
# #         photo_bytes = photo.getvalue()
# #         add_message("user", "image", photo_bytes)
# #         parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
# #     if text:
# #         add_message("user", "text", text)
# #         parts.append(text)
# #     elif photo is not None:
# #         parts.append("What is this meal? Give me the calories and macros.")
 
# #     with st.spinner("Crunching the numbers..."):
# #         answer = ask_gemini(parts)
# #     add_message("assistant", "text", answer)
# # # import json
# # # from google import genai
# # # from google.genai import types
# # # import streamlit as st
# # # from twilio.rest import Client as TwilioClient

# # # from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT


# # # GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
# # # TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
# # # TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
# # # TWILIO_WHATSAPP_FROM = st.secrets["TWILIO_WHATSAPP_FROM"]
# # # TWILIO_CONTENT_SID = st.secrets["TWILIO_CONTENT_SID"]


# # # @st.cache_resource
# # # def get_gemini_client():
# # #     return genai.Client(api_key = GEMINI_API_KEY)

# # # @st.cache_resource
# # # def get_twilio_client():
# # #     return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# # # gemini_client = get_gemini_client()
# # # twilio_client = get_twilio_client()
# # # MODEL_NAME = "gemini-3.8-flash"

# # # def clean_whatsapp_text(text):
# # #     if not text:
# # #         return "No nutrition summary available."
# # #     text = " ".join(text.split())  # collapse whitespace/newlines
# # #     return text[:1500] + "..." if len(text) > 1500 else text


# # # def send_whatsapp(to_number, user_name, summary):
# # #     # Content template expects {{1}} = name, {{2}} = summary.
# # #     try:
# # #         content_variables = json.dumps(
# # #             {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
# # #         )
# # #         message = twilio_client.messages.create(
# # #             from_=TWILIO_WHATSAPP_FROM,
# # #             to=f"whatsapp:{to_number}",
# # #             content_sid=TWILIO_CONTENT_SID,
# # #             content_variables=content_variables,
# # #         )
# # #         return True, message.sid
# # #     except Exception as error:
# # #         return False, str(error)
 

# # # def render_message(message):
# # #     with st.chat_message(message["role"]):
# # #         if message["kind"] == "text":
# # #             st.write(message["content"])
# # #         elif message["kind"] == "image":
# # #             st.image(message["content"])

# # # def add_message(role, kind, content):
# # #     st.session_state.messages.append({"role": role, "kind": kind, "content": content})
# # #     render_message(st.session_state.messages[-1])

# # # def ask_gemini(parts):
# # #     try:
# # #         return st.session_state.chat.send_message(parts).text
# # #     except Exception as error:
# # #         return f"Sorry, something went wrong: {error}"

# # # #step 1: onborading (username and phone)

# # # if 'onboarded' not in st.session_state:
# # #     st.title("🥗 MacroSnap")
# # #     st.caption("Snap it. Track it. Text yourself the results.")

# # #     with st.form("onboarding_form"):
# # #         name = st.text_input("Your name") # sachtih
# # #         whatsapp_number = st.text_input(
# # #             "WhatsApp number (with country code)",
# # #             placeholder="+91XXXXXXXXXX",
# # #             help="This is the number MacroSnap will text your summary to.",
# # #         )

# # #         submitted = st.form_submit_button("Let's go 🚀")

# # #     if submitted:
# # #         if not name.strip() or not whatsapp_number.strip():
# # #             st.warning("Please fill in both your name and WhatsApp number.")

# # #         else:
# # #             st.session_state.name = name.strip()
# # #             st.session_state.whatsapp_number = whatsapp_number.strip()
# # #             #activate my ai
# # #             st.session_state.chat = gemini_client.chats.create(
# # #                 model=MODEL_NAME,
# # #                 config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
# # #             )
# # #             st.session_state.messages = []
# # #             st.session_state.onboarded = True
# # #             st.rerun()
# # #     st.stop()

# # # # create a chat interface

# # # header_col, button_col = st.columns([5, 2], vertical_alignment="center")

# # # with header_col:
# # #     st.title("🥗 MacroSnap")

# # # with button_col:
# # #     send_disabled = len(st.session_state.messages) <= 2
# # #     if st.button("📤 Send to WhatsApp", disabled=send_disabled, use_container_width=True):
# # #         with st.spinner("Summarizing your day..."):
# # #             summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
# # #         success, info = send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
# # #         if success:
# # #             st.success("Sent! Check your WhatsApp 📲")
# # #         else:
# # #             st.error(f"Couldn't send that: {info}")


# # # st.caption(f"Logged in as {st.session_state.name} - updates go to {st.session_state.whatsapp_number}")

# # # if not st.session_state.messages:
# # #     add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
# # # else:
# # #     for message in st.session_state.messages:
# # #         render_message(message)


# # # user_input = st.chat_input(
# # #     "Ask a question, or attach a photo of your meal",
# # #     accept_file=True,
# # #     file_type=["jpg", "jpeg", "png"],
# # # )

# # # if user_input:
# # #     photo = user_input.files[0] if user_input.files else None
# # #     text = user_input.text
# # #     parts = []

# # #     if photo is not None:
# # #         photo_bytes = photo.getvalue()
# # #         add_message("user", "image", photo_bytes)
# # #         parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
# # #     if text:
# # #         add_message("user", "text", text)
# # #         parts.append(text)
# # #     elif photo is not None:
# # #         parts.append("What is this meal? Give me the calories and macros.")

# # #     with st.spinner("Crunching the numbers..."):
# # #         answer = ask_gemini(parts)
# # #     add_message("assistant", "text", answer)