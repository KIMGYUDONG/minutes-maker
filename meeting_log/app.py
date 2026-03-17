"""Meeting Minutes Generator - Main Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Meeting Minutes Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1565C0;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📋 회의록 생성기</div>', unsafe_allow_html=True)
st.markdown("회의 녹음 파일을 업로드하면 AI가 자동으로 구조화된 회의록을 생성합니다.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📋 Bridge 회의록")
    st.markdown(
        "팀 내부 회의 녹음을 업로드하면 요약, 업데이트, "
        "논의사항, 할 일 목록이 포함된 회의록을 자동 생성하여 노션에 저장합니다."
    )

with col2:
    st.markdown("### 🤝 숨고 클라이언트")
    st.markdown(
        "영업 미팅 녹음을 업로드하면 고객 현황, 요구사항, "
        "제안 솔루션, 후속 액션이 포함된 미팅 노트를 자동 생성합니다."
    )

st.markdown("---")
st.markdown("#### 사용 흐름")
st.markdown(
    "1. 사이드바에서 모드를 선택\n"
    "2. 음성 파일(.m4a, .mp3, .wav) 또는 텍스트 파일(.txt) 업로드\n"
    "3. AI가 회의록을 생성하면 내용을 확인\n"
    "4. 노션에 저장하고 텔레그램으로 알림 전송"
)
