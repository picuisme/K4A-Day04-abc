import streamlit as st
from pathlib import Path
import json

from chat import run_model_tool_loop, trim_history, safe_slug
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import build_artifact_version
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)

st.set_page_config(page_title="IT Helpdesk Agent", page_icon="🤖", layout="wide")
st.title("IT Helpdesk Agent (Live Chat & Analytics)")

# ----------------- UI Sidebar Configuration -----------------
with st.sidebar:
    st.header("Cấu hình Agent")
    provider_choice = st.selectbox("Provider", ["openai", "anthropic", "gemini", "openrouter"], index=0)
    version_label = st.text_input("Artifact Version", value="v14")

    # Tính toán Artifact Version & Hash
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)

    st.markdown("---")
    st.markdown("### Thông tin Session")
    st.markdown(f"**Artifact Hash:** `{artifact_version.artifact_version}`")

    # Khởi tạo Transcript Path
    if "transcript_path" not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        t_id = f"ui_{safe_slug(version_label)}_{timestamp}"
        st.session_state.transcript_path = str(ROOT / "transcripts" / f"{t_id}.transcript.json")

    st.markdown(f"**Transcript Path:** `{st.session_state.transcript_path}`")

    st.markdown("---")
    if st.button("Reset Chat"):
        st.session_state.history = []
        st.session_state.display_messages = []
        st.rerun()

# ----------------- Tabs Setup -----------------
tab_chat, tab_compare = st.tabs(["💬 Live Chat Demo", "📊 So sánh Phiên bản (Eval Runs)"])

# ----------------- Initialization -----------------
if "history" not in st.session_state:
    st.session_state.history = []
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

def init_agent(provider_name: str, model_name: str | None = None):
    system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)
    selected_model = model_name if model_name else getattr(provider, "default_model", None)
    return system_prompt, openai_tools, provider, selected_model

# ----------------- Chat Display -----------------
with tab_chat:

    for msg in st.session_state.display_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant":
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "tool_events":
            with st.expander(f"🛠️ Agent gọi {len(msg['events'])} tool(s)"):
                for event in msg["events"]:
                    st.markdown(f"**Tool:** `{event['tool']}`")
                    st.json(event["args"], expanded=False)
                    st.markdown("**Kết quả:**")
                    st.json(event["result"], expanded=False)

    # ----------------- Chat Input & Process -----------------
    if prompt := st.chat_input("Nhập câu hỏi hoặc yêu cầu..."):
        # Display user input
        st.chat_message("user").write(prompt)
        st.session_state.display_messages.append({"role": "user", "content": prompt})

        with st.spinner("Agent đang suy nghĩ..."):
            try:
                # Initialize provider and tools
                system_prompt, openai_tools, provider, selected_model = init_agent(provider_choice, None)

                # Prepare messages
                working_messages = [
                    {"role": "system", "content": system_prompt},
                    *trim_history(st.session_state.history, 5),
                    {"role": "user", "content": prompt},
                ]

                # Run the agent tool loop (reusing from chat.py)
                result = run_model_tool_loop(
                    provider=provider,
                    messages=working_messages,
                    tools=openai_tools,
                    model=selected_model,
                    max_tool_rounds=4
                )

                tool_events = result.get("tool_events", [])
                assistant_text = result.get("assistant_text", "")

                # Record to history (for agent context)
                st.session_state.history.append({"role": "user", "content": prompt})
                st.session_state.history.append({"role": "assistant", "content": assistant_text})

                # Record for display
                if tool_events:
                    st.session_state.display_messages.append({"role": "tool_events", "events": tool_events})

                st.session_state.display_messages.append({"role": "assistant", "content": assistant_text})

                # Lưu Transcript ra file
                t_path = Path(st.session_state.transcript_path)
                t_path.parent.mkdir(parents=True, exist_ok=True)
                t_path.write_text(json.dumps(st.session_state.display_messages, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

                st.rerun()

            except Exception as e:
                st.error(f"Đã xảy ra lỗi: {e}")

with tab_compare:
    st.header("Thống kê Evaluation Runs")
    runs_dir = ROOT / "runs"

    if not runs_dir.exists() or not list(runs_dir.glob("*.json")):
        st.info("Chưa có dữ liệu. Vui lòng chạy lệnh `python run_eval.py ...` để tạo file log chấm điểm.")
    else:
        run_data = []
        for run_file in runs_dir.glob("*.json"):
            try:
                data = json.loads(run_file.read_text(encoding="utf-8"))
                summary = data.get("summary", data)
                run_data.append({
                    "Timestamp": data.get("generated_at") or data.get("created_at", ""),
                    "Version": data.get("version", ""),
                    "Suite": data.get("suite", ""),
                    "Provider": data.get("provider", ""),
                    "Model": data.get("model", ""),
                    "Total": summary.get("total_cases", 0),
                    "Passed": summary.get("passed_cases", 0),
                    "Accuracy": summary.get("case_accuracy", 0.0)
                })
            except Exception:
                pass

        if run_data:
            df = pd.DataFrame(run_data)
            df = df.sort_values(by="Timestamp", ascending=False).reset_index(drop=True)

            st.markdown("### Lịch sử Chấm điểm")
            st.dataframe(df, width="stretch")

            st.markdown("### Biểu đồ Độ chính xác (Accuracy)")
            # Create a label for x-axis
            df["Run Label"] = df["Version"] + " (" + df["Provider"] + " - " + df["Suite"] + ")"

            st.bar_chart(data=df, x="Run Label", y="Accuracy", width="stretch")
