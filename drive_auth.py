# drive_auth.py
import os
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CLIENT_SECRET_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def save_token(creds):
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

def load_token():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_token(creds)
        return creds
    return None

def login_google_drive():
    creds = load_token()
    if creds:
        return creds

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="https://taraa-capslock.streamlit.app/"
    )

    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        flow.fetch_token(code=code)
        creds = flow.credentials
        save_token(creds)
        st.success("✅ Login Google Drive berhasil!")
        st.rerun()

    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )
    st.markdown(f"[🔐 Login Google Drive]({auth_url})", unsafe_allow_html=True)
    st.stop()

def get_drive_service():
    creds = load_token()
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)
