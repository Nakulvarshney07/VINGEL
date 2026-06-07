import streamlit as st
from components.tab_vault import render_vault

BACKEND = "http://localhost:8000"
render_vault(BACKEND)
