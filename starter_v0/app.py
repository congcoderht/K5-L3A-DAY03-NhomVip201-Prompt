from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import run_model_tool_loop, trim_history, write_transcript
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
TRANSCRIPTS_DIR = ROOT / "transcripts"
PROVIDER_NAME = "openrouter"
load_lab_env(ROOT)

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")
st.title("🔎 Research Agent")


def current_artifact_version():
    return build_artifact_version("latest", PROMPT_PATH, TOOLS_PATH)


def start_new_conversation(artifact_version: Any) -> None:
    transcript_id = f"latest_openrouter_{datetime.now().strftime('%Y%m%dT%H%M%S%f')}"
    st.session_state.active_artifact_version = artifact_version.artifact_version
    st.session_state.messages = []
    st.session_state.history = []
    st.session_state.transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": PROVIDER_NAME,
        "model": None,
        "system_prompt": str(PROMPT_PATH),
        "tools": str(TOOLS_PATH),
        "turns": [],
    }


artifact_version = current_artifact_version()
if st.session_state.get("active_artifact_version") != artifact_version.artifact_version:
    start_new_conversation(artifact_version)

if st.button("Bắt đầu hội thoại mới"):
    start_new_conversation(artifact_version)
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tool_events"):
            with st.expander("Chi tiết tool đã gọi"):
                st.json(message["tool_events"])

prompt = st.chat_input("Bạn muốn tìm hiểu điều gì?")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Read live artifacts for every request so edits and newly registered
        # tools are picked up without a separate version selector.
        artifact_version = current_artifact_version()
        if st.session_state.active_artifact_version != artifact_version.artifact_version:
            start_new_conversation(artifact_version)
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.info("Cấu hình agent vừa thay đổi; đã bắt đầu hội thoại mới bằng cấu hình mới nhất.")

        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        declarations = load_tool_declarations(TOOLS_PATH)
        # Keep the external Telegram action disabled until the UI has an
        # explicit confirmation step. Other declared tools load automatically.
        declarations = [tool for tool in declarations if tool.get("name") != "send"]
        openai_tools = to_openai_tools(declarations)
        provider = make_provider(PROVIDER_NAME)
        run = run_model_tool_loop(
            provider=provider,
            messages=[
                {"role": "system", "content": system_prompt},
                *trim_history(st.session_state.history, 5),
                {"role": "user", "content": prompt},
            ],
            tools=openai_tools,
            model=None,
            max_tool_rounds=4,
        )
        answer = run["assistant_text"] or "Mình chưa có câu trả lời cho yêu cầu này."
        st.session_state.history.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ])
        entry = {
            "turn_index": len(st.session_state.transcript["turns"]) + 1,
            "user": prompt,
            **run,
        }
        st.session_state.transcript["turns"].append(entry)
        write_transcript(st.session_state.transcript_path, st.session_state.transcript)
        rendered = {"role": "assistant", "content": answer, "tool_events": run.get("tool_events", [])}
        st.session_state.messages.append(rendered)
        with st.chat_message("assistant"):
            st.markdown(answer)
            if rendered["tool_events"]:
                with st.expander("Chi tiết tool đã gọi"):
                    st.json(rendered["tool_events"])
    except Exception as exc:
        error = f"Có lỗi khi chạy agent: {type(exc).__name__}: {exc}"
        st.session_state.messages.append({"role": "assistant", "content": error})
        with st.chat_message("assistant"):
            st.error(error)

