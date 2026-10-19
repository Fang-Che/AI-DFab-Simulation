import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent/'.env',override=False)
st.set_page_config(page_title='AI-DFab自動化模擬與建造代理',page_icon='◈',layout='wide',initial_sidebar_state='expanded')
from robotics.runtime_reload import refresh
refresh()
from robotics.ui import render_robotics
render_robotics()
