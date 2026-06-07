import streamlit as st
import os
from components.tab_vault import render_vault

BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8000")
render_vault(BACKEND)
