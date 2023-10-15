import os
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from get_prompt import load_prompt, load_prompt_with_questions
import streamlit as st
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from PIL import Image
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set environment variables
ALLOWED_USERS = os.environ.get('ALLOWED_USERS', [])
AUTHORIZE_URL = os.environ.get('AUTHORIZE_URL')
TOKEN_URL = os.environ.get('TOKEN_URL')
REFRESH_TOKEN_URL = os.environ.get('REFRESH_TOKEN_URL')
REVOKE_TOKEN_URL = os.environ.get('REVOKE_TOKEN_URL')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')
SCOPE = os.environ.get('SCOPE')

# Create OAuth2Component instance
oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)

st.set_page_config(page_title="Learn with AI", page_icon=Image.open("artifacts/favicon.ico"), layout="wide")
st.title("Learn with AI")


import re

def convert_newlines(markdown_text: str) -> str:
    # Identify code blocks using regex
    code_blocks = re.findall(r'```.*?```', markdown_text, re.DOTALL)
    
    # Replace each code block with a unique placeholder
    placeholders = []
    for idx, block in enumerate(code_blocks):
        placeholder = f"CODEBLOCK{idx}PLACEHOLDER"
        placeholders.append(placeholder)
        markdown_text = markdown_text.replace(block, placeholder)
    
    # Convert single newlines to double newlines
    markdown_text = re.sub(r'(?<!\n)\n(?! *\n)', '\n\n', markdown_text)
    
    # Restore code blocks
    for placeholder, block in zip(placeholders, code_blocks):
        markdown_text = markdown_text.replace(placeholder, block)
    
    return markdown_text.strip()



class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

# Lesson selection dictionary
lesson_guides = {
    "Lesson 0: Multiplication": {
        "file": "lc_guides/multiplication_guide.txt",
        "description": "This lesson covers the basics of multiplication."
    },
    "Lesson 1: Getting Started with LangChain": {
        "file": "lc_guides/getting_started_guide.txt",
        "description": "This lesson covers the basics of getting started with LangChain."
    },
    "Lesson 2: Prompts": {
        "file": "lc_guides/prompt_guide.txt",
        "description": "This lesson focuses on prompts and their usage."
    },
    "Lesson 3: Language Models": {
        "file": "lc_guides/models_guide.txt",
        "description": "This lesson provides an overview of language models."
    },
    "Lesson 4: Memory": {
        "file": "lc_guides/memory_guide.txt",
        "description": "This lesson is about Memory."
    },
    "Lesson 5: Chains": {
        "file": "lc_guides/chains_guide.txt",
        "description": "This lesson provides information on Chains in LangChain, their types, and usage."
    },
    "Lesson 6: Retrieval": {
        "file": "lc_guides/retrieval_guide.txt",
        "description": "This lesson provides information on indexing and retrieving information using LangChain."
    },
    "Lesson 7: Agents": {
        "file": "lc_guides/agents_guide.txt",
        "description": "This lesson provides information on agents, tools, and toolkits."
    },
    "Lesson 8: Intro to ChatGPT": {
        "file": "lc_guides/chatgpt_guide.txt",
        "description": "This lesson provides an introduction to ChatGPT."
    },
    "Lesson 9: ChatGPT for Instructional Designers": {
        "file": "lc_guides/chatgpt_id_guide.txt",
        "description": "This lesson provides information on using ChatGPT for instructional designers."
    },
}


st.sidebar.image("artifacts/learn_with_ai_logo.png")

# Check if token exists in session state
if 'profile' not in st.session_state:
    # If not, show authorize button
    st.session_state.result = oauth2.authorize_button("Login with Google", REDIRECT_URI, SCOPE)
    if st.session_state.result and 'token' in st.session_state.result:
        # If authorization successful, save token in session state
        token = st.session_state.result.get('token')

        # Initialize Google People API
        credentials = Credentials(token['access_token'], id_token=token['id_token'])
        people_service = build('people', 'v1', credentials=credentials)
        st.session_state["profile"] = people_service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses,photos'
        ).execute()
        st.rerun()
else:
    # If user is not in allowed users, show error message and stop execution
    if 0 < len(ALLOWED_USERS) and st.session_state['profile']['emailAddresses'][0]['value'] not in ALLOWED_USERS:
        st.error("You are not authorized to access this application.")
        st.stop()

    if 'profile_photo_url' not in st.session_state and 'photos' in st.session_state['profile'] and \
            0 < len(st.session_state['profile']['photos']):
        st.session_state['profile_photo_url'] = st.session_state['profile']['photos'][0]['url']

    # Lesson selection sidebar
    lesson_selection = st.sidebar.selectbox("Select Lesson", list(lesson_guides.keys()))

    # Display lesson content and description based on selection
    lesson_info = lesson_guides[lesson_selection]
    lesson_content = open(lesson_info["file"], "r").read()
    lesson_description = lesson_info["description"]

    # Clear chat session if dropdown option or radio button changes
    if st.session_state.get("current_lesson") != lesson_selection:
        user_name = st.session_state['profile']['names'][0]['givenName']
        st.session_state["current_lesson"] = lesson_selection
        st.session_state["messages"] = [
            SystemMessage(content="You are a teacher named Dr. Tensai. Your goal is to guide the student through this lesson. "
                                  "You should keep the student on topic by steering them back to the lesson content. Pay special "
                                  "attention to the formatting of the lesson content including spacing and indentation. Never admit "
                                  "you are an AI or reveal any personal details about yourself. The student cannot see the "
                                  "lesson content, so you need to transcribe it to them in a digestible way."),
            AIMessage(
                content=f"Welcome, {user_name}! Are you ready to jump into this lesson?"
            )
        ]

    # Display lesson name and description
    st.markdown(f"**{lesson_selection}**")
    st.write(f"_{lesson_description}_")

    for msg in st.session_state["messages"][1:]:
        if isinstance(msg, HumanMessage):
            st.chat_message("user", avatar=st.session_state['profile_photo_url']).write(convert_newlines(msg.content))
        else:
            st.chat_message("assistant", avatar='artifacts/favicon_large.png').write(msg.content)

    if prompt := st.chat_input():
        prompt = prompt.strip()
        st.chat_message("user", avatar=st.session_state['profile_photo_url']).write(convert_newlines(prompt))

        with st.chat_message("assistant", avatar='artifacts/favicon_large.png'):
            stream_handler = StreamHandler(st.empty())
            with st.spinner("Thinking..."):
                model = ChatOpenAI(
                    streaming=True,
                    callbacks=[stream_handler],
                    model="gpt-3.5-turbo", # "gpt-3.5-turbo-16k"
                )

            prompt_template = load_prompt(content=lesson_content)

            chain = LLMChain(prompt=prompt_template, llm=model)

            response = chain(
                {"input": prompt, "chat_history": st.session_state.messages[-20:]},
                include_run_info=True,
                tags=[lesson_selection]
            )
            st.session_state.messages.append(HumanMessage(content=prompt))
            st.session_state.messages.append(AIMessage(content=response[chain.output_key]))
            run_id = response["__run"].run_id

            col_blank, col_text, col1, col2 = st.columns([10, 2, 1, 1])

