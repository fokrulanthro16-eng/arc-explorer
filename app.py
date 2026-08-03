"""ARC Explorer Streamlit Web Application Dashboard."""

import os
import streamlit as st
from arc_explorer.agent import ExplorerAgent
from arc_explorer.scenarios import create_scenario_1, create_scenario_2, create_scenario_3
from arc_explorer.replay import ReplayLogger
from arc_explorer.arc_task import ARCTask, create_arc_task_environment
from arc_explorer.ui_helpers import (
    render_grid_html,
    run_benchmark_evaluation,
    list_available_replays,
    list_available_arc_tasks,
    load_and_verify_replay,
    COLOR_HEX_MAP,
)


def init_session_state():
    """Initializes Streamlit session state variables."""
    if "current_result" not in st.session_state:
        st.session_state.current_result = None
    if "current_step_idx" not in st.session_state:
        st.session_state.current_step_idx = 0
    if "benchmark_data" not in st.session_state:
        st.session_state.benchmark_data = None
    if "loaded_replay" not in st.session_state:
        st.session_state.loaded_replay = None
    if "replay_step_idx" not in st.session_state:
        st.session_state.replay_step_idx = 0


def reset_ui_state():
    """Resets session state to default clean state."""
    st.session_state.current_result = None
    st.session_state.current_step_idx = 0
    st.session_state.benchmark_data = None
    st.session_state.loaded_replay = None
    st.session_state.replay_step_idx = 0


def main():
    st.set_page_config(
        page_title="ARC Explorer Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    # App Header
    st.title("🤖 ARC Explorer Dashboard")
    st.caption(
        "A CPU-only active hypothesis learning baseline for ARC-style grid environments. "
        "Observes states, plans safe informative experiments, tracks rule hypotheses, and records reasoning replays."
    )
    st.markdown("---")

    # Sidebar Controls
    st.sidebar.header("🕹️ Controls & Navigation")

    scenario_option = st.sidebar.selectbox(
        "Select Scenario",
        options=["Scenario 1", "Scenario 2", "Scenario 3", "All Scenarios"],
        help="Choose a hidden-rule scenario or run all sequentially.",
    )

    max_steps = st.sidebar.slider(
        "Maximum Exploration Steps",
        min_value=5,
        max_value=50,
        value=30,
        step=5,
    )

    col_btn1, col_btn2 = st.sidebar.columns(2)
    with col_btn1:
        run_exp_btn = st.button("🚀 Run Exploration", use_container_width=True)
    with col_btn2:
        run_bench_btn = st.button("📊 Run Benchmark", use_container_width=True)

    col_btn3, col_btn4 = st.sidebar.columns(2)
    with col_btn3:
        load_replay_btn = st.button("📂 Load Replay", use_container_width=True)
    with col_btn4:
        reset_btn = st.button("🔄 Reset UI", use_container_width=True)

    if reset_btn:
        reset_ui_state()
        st.rerun()

    # Action Handlers
    if run_exp_btn:
        scenario_map = {
            "Scenario 1": (1, "Scenario 1: Color Propagation & Reflection", create_scenario_1),
            "Scenario 2": (2, "Scenario 2: Color Door Key Sequence", create_scenario_2),
            "Scenario 3": (3, "Scenario 3: Symmetric Pattern Completion", create_scenario_3),
        }

        if scenario_option == "All Scenarios":
            # Run benchmark dynamically across all scenarios
            st.session_state.benchmark_data = run_benchmark_evaluation()
            st.success("Completed benchmark evaluation across all scenarios! Check the 📈 **Benchmark View** tab.")
        else:
            sc_num, name, creator_fn = scenario_map[scenario_option]
            env = creator_fn()
            agent = ExplorerAgent()
            result = agent.run_exploration(env, max_steps=max_steps)

            # Auto save replay trace
            os.makedirs("replays", exist_ok=True)
            replay_path = f"replays/ui_{scenario_option.lower().replace(' ', '_')}.json"
            ReplayLogger.save_replay(replay_path, result, memory=agent.memory, scenario_name=name)

            st.session_state.current_result = {
                "scenario_name": name,
                "env_initial_grid": env.initial_grid,
                "env_initial_pos": env.initial_pos,
                "result": result,
                "memory_transitions": agent.memory.to_list(),
            }
            st.session_state.current_step_idx = 0
            st.success(f"Exploration completed for {name}! Replay saved to `{replay_path}`. See 🔬 **Exploration View** tab.")

    if run_bench_btn:
        st.session_state.benchmark_data = run_benchmark_evaluation()
        st.success("Benchmark evaluation completed! Check the 📈 **Benchmark View** tab.")

    # Main Tabs
    tab_exp, tab_bench, tab_replay, tab_arc = st.tabs([
        "🔬 Exploration View",
        "📈 Benchmark View",
        "📜 Replay View",
        "🧩 ARC Tasks View",
    ])


    # --- TAB 1: EXPLORATION VIEW ---
    with tab_exp:
        if st.session_state.current_result is None:
            st.info("👈 Select a specific scenario and click **🚀 Run Exploration** to inspect step-by-step exploration.")
        else:
            exp_data = st.session_state.current_result
            res = exp_data["result"]
            trace_logs = res["trace_logs"]
            transitions = exp_data["memory_transitions"]

            st.subheader(f"Exploration Trace: {exp_data['scenario_name']}")

            # Summary Metrics Bar
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Rule Discovered", "YES ✅" if res["rule_discovered"] else "NO ❌")
            m2.metric("Total Steps", res["total_steps"])
            m3.metric("Hazards Hit", res["hazard_count"])
            m4.metric("Rule Score", f"{res['rule_score']:.2f} / 1.00")
            m5.metric("Discovery Score", f"{res['discovery_score']:.1f} / 100.0")

            st.info(f"**Inferred Rule**: {res['inferred_rule_name']} (`{res['inferred_rule_id']}`)")

            # Step Navigation Slider / Controls
            num_steps = len(trace_logs)
            c_prev, c_slider, c_next = st.columns([1, 6, 1])

            if num_steps <= 1:
                st.session_state.current_step_idx = 0
                with c_prev:
                    st.button("◀ Prev", disabled=True, key="exp_prev_dis")
                with c_slider:
                    msg = "Step 1 of 1" if num_steps == 1 else "No steps recorded"
                    st.info(f"📌 {msg}")
                with c_next:
                    st.button("Next ▶", disabled=True, key="exp_next_dis")
            else:
                st.session_state.current_step_idx = max(0, min(st.session_state.current_step_idx, num_steps - 1))
                with c_prev:
                    if st.button("◀ Prev", disabled=st.session_state.current_step_idx <= 0, key="exp_prev"):
                        st.session_state.current_step_idx -= 1
                        st.rerun()

                with c_slider:
                    st.session_state.current_step_idx = st.slider(
                        "Step Navigation",
                        min_value=0,
                        max_value=num_steps - 1,
                        value=st.session_state.current_step_idx,
                        key="exp_slider",
                    )

                with c_next:
                    if st.button("Next ▶", disabled=st.session_state.current_step_idx >= num_steps - 1, key="exp_next"):
                        st.session_state.current_step_idx += 1
                        st.rerun()

            # Render selected step
            curr_idx = st.session_state.current_step_idx
            if 0 <= curr_idx < len(transitions):
                trans = transitions[curr_idx]
                log = trace_logs[curr_idx]

                col_grid, col_details = st.columns([1, 1])

                with col_grid:
                    st.markdown(f"#### Grid State (Step {curr_idx + 1} / {max(1, num_steps)})")
                    # Display grid after action
                    grid_after = trans["obs_after"]["grid"]
                    agent_pos = tuple(trans["obs_after"]["agent_pos"])
                    st.components.v1.html(render_grid_html(grid_after, agent_pos), height=380)

                with col_details:
                    st.markdown("#### Step Details & Active Hypotheses")
                    st.write(f"**Action Executed**: `{log['action']}`")
                    st.write(f"**Agent Position**: `{log['pos']}`")
                    hazard_badge = "🚨 **YES (PENALTY)**" if log["hazard_alert"] else "🟢 **NO (SAFE)**"
                    st.write(f"**Hazard Alert**: {hazard_badge}")
                    st.write(f"**Active Top Hypothesis**: {log['top_hypothesis']}")
                    st.write(f"**Hypothesis Confidence**: `{log['top_score']:.4f}`")

                    # Cell changes delta
                    delta_changes = trans["delta"]["changes"]
                    if delta_changes:
                        st.write("**Grid Cell Modifications**:")
                        for ch in delta_changes:
                            from_c = COLOR_HEX_MAP.get(ch['from_color'], {}).get('name', 'Unknown')
                            to_c = COLOR_HEX_MAP.get(ch['to_color'], {}).get('name', 'Unknown')
                            st.caption(f"- Cell {ch['pos']}: `{from_c}` ➔ `{to_c}`")
                    else:
                        st.caption("No grid cells modified in this step.")

    # --- TAB 2: BENCHMARK VIEW ---
    with tab_bench:
        st.subheader("📊 Dynamic Benchmark Evaluation Report")

        if st.session_state.benchmark_data is None:
            st.info("👈 Click **📊 Run Benchmark** in the sidebar to evaluate all scenarios.")
        else:
            bench = st.session_state.benchmark_data

            # Prominent Overall Score Card
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Overall Benchmark Score", f"{bench['overall_score']:.2f} / 100.0")
            b2.metric("Scenarios Passed", f"{bench['total_passed']} / {bench['total_scenarios']}")
            b3.metric("Pass Rate", f"{(bench['total_passed']/bench['total_scenarios'])*100:.0f}%")
            b4.metric("Total Hazards Hit", sum(sc['hazards'] for sc in bench['scenario_results']))

            st.markdown("---")
            st.markdown("#### Benchmark Summary Table")

            # Dedicated Summary Table
            table_rows = []
            for sc in bench["scenario_results"]:
                table_rows.append({
                    "Scenario": sc["name"],
                    "Pass/Fail": "✅ PASSED" if sc["passed"] else "❌ FAILED",
                    "Steps": sc["steps"],
                    "Hazards": sc["hazards"],
                    "Rule Score": f"{sc.get('rule_score', 0.97):.2f}",
                    "Discovery Score": f"{sc['score']:.1f} / 100",
                })

            st.dataframe(table_rows, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### Scenario Inferred Rules")
            for sc in bench["scenario_results"]:
                with st.expander(f"Rule Details: {sc['name']}", expanded=False):
                    st.write(f"**Inferred Rule**: {sc['inferred_rule_name']}")
                    st.write(f"**Hypothesis ID**: `{sc['inferred_rule_id']}`")
                    st.write(f"**Final Status**: {sc['status']}")


    # --- TAB 3: REPLAY VIEW ---
    with tab_replay:
        st.subheader("📜 Saved Reasoning Trace Replay Viewer")

        replays = list_available_replays("replays")
        if not replays:
            st.warning("No saved replay JSON files found in `replays/` directory.")
        else:
            selected_replay_file = st.selectbox(
                "Select Replay File",
                options=replays,
                help="Choose a saved JSON trace file to replay step-by-step reasoning.",
            )

            if st.button("📂 Load Selected Replay") or load_replay_btn:
                success, data, err = load_and_verify_replay(selected_replay_file)
                if not success:
                    st.error(f"Failed to load replay file: {err}")
                else:
                    st.session_state.loaded_replay = data
                    st.session_state.replay_step_idx = 0
                    st.success(f"Loaded replay trace: {selected_replay_file}")

            if st.session_state.loaded_replay:
                rep_data = st.session_state.loaded_replay
                rep_summary = rep_data.get("summary", {})
                rep_logs = rep_data.get("trace_logs", [])
                rep_mem = rep_data.get("memory_transitions", [])

                st.markdown(f"### Replay Trace: {rep_data.get('scenario', 'ARC Explorer')}")

                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Inferred Rule", rep_summary.get("inferred_rule_id", "N/A"))
                r2.metric("Total Steps", rep_summary.get("total_steps", 0))
                r3.metric("Hazards Hit", rep_summary.get("hazard_count", 0))
                r4.metric("Discovery Score", f"{rep_summary.get('discovery_score', 0):.1f} / 100")

                # Step Navigation for Replay View
                num_rep_steps = len(rep_logs)
                c_r_prev, c_r_slider, c_r_next = st.columns([1, 6, 1])

                if num_rep_steps <= 0:
                    st.info("No trace steps recorded in this replay.")
                elif num_rep_steps == 1:
                    st.session_state.replay_step_idx = 0
                    with c_r_prev:
                        st.button("◀ Prev Replay", disabled=True, key="rep_prev_dis")
                    with c_r_slider:
                        st.info("📌 Step 1 of 1")
                    with c_r_next:
                        st.button("Next Replay ▶", disabled=True, key="rep_next_dis")
                else:
                    st.session_state.replay_step_idx = max(0, min(st.session_state.replay_step_idx, num_rep_steps - 1))
                    with c_r_prev:
                        if st.button("◀ Prev Replay", disabled=st.session_state.replay_step_idx <= 0, key="rep_prev"):
                            st.session_state.replay_step_idx -= 1
                            st.rerun()

                    with c_r_slider:
                        st.session_state.replay_step_idx = st.slider(
                            "Replay Step Scrub",
                            min_value=0,
                            max_value=num_rep_steps - 1,
                            value=st.session_state.replay_step_idx,
                            key="rep_slider",
                        )

                    with c_r_next:
                        if st.button("Next Replay ▶", disabled=st.session_state.replay_step_idx >= num_rep_steps - 1, key="rep_next"):
                            st.session_state.replay_step_idx += 1
                            st.rerun()

                r_idx = st.session_state.replay_step_idx
                if 0 <= r_idx < num_rep_steps:
                    r_log = rep_logs[r_idx]

                    col_r_grid, col_r_info = st.columns([1, 1])

                    with col_r_grid:
                        st.markdown(f"#### Grid State (Step {r_idx + 1} / {max(1, num_rep_steps)})")
                        if r_idx < len(rep_mem):
                            grid_arr = rep_mem[r_idx]["obs_after"]["grid"]
                            pos_arr = tuple(rep_mem[r_idx]["obs_after"]["agent_pos"])
                            st.components.v1.html(render_grid_html(grid_arr, pos_arr), height=380)

                    with col_r_info:
                        st.markdown("#### Reasoning Log")
                        st.write(f"**Step**: `{r_log.get('step')}`")
                        st.write(f"**Action**: `{r_log.get('action')}`")
                        st.write(f"**Position**: `{r_log.get('pos')}`")
                        st.write(f"**Hazard Alert**: `{r_log.get('hazard_alert')}`")
                        st.write(f"**Top Hypothesis**: `{r_log.get('top_hypothesis')}`")
                        st.write(f"**Score**: `{r_log.get('top_score')}`")

    # --- TAB 4: ARC TASKS VIEW ---
    with tab_arc:
        st.subheader("🧩 Official ARC Task Loader & Visualizer")
        st.caption(
            "Load and inspect official ARC-AGI task JSON files, view input/output grids, "
            "and convert tasks into interactive GridWorld environments."
        )

        arc_task_files = list_available_arc_tasks("samples")

        col_file_sel, col_file_up = st.columns([1, 1])
        with col_file_sel:
            selected_arc_file = st.selectbox(
                "Select Sample ARC Task JSON",
                options=arc_task_files,
                help="Choose from pre-packaged ARC sample tasks in samples/ directory.",
            )
        with col_file_up:
            uploaded_arc_file = st.file_uploader(
                "Or Upload Custom ARC Task JSON",
                type=["json"],
                help="Upload any official ARC task JSON file.",
            )

        arc_task = None
        if uploaded_arc_file is not None:
            try:
                import json
                task_dict = json.load(uploaded_arc_file)
                arc_task = ARCTask.load_from_dict(task_dict, task_id=uploaded_arc_file.name)
                st.success(f"Successfully loaded uploaded task: `{uploaded_arc_file.name}`")
            except Exception as e:
                st.error(f"Error parsing uploaded ARC JSON task: {e}")
        elif selected_arc_file:
            try:
                arc_task = ARCTask.load_from_file(selected_arc_file)
                st.info(f"Loaded task: `{arc_task.task_id}`")
            except Exception as e:
                st.error(f"Error loading ARC JSON task file: {e}")

        if arc_task:
            st.markdown(f"### ARC Task: `{arc_task.task_id}`")
            st.write(f"**Training Pairs**: `{len(arc_task.train_pairs)}` | **Test Pairs**: `{len(arc_task.test_pairs)}`")

            # Display Train Pairs
            st.markdown("#### Training Examples (Input ➔ Target Output Grids)")
            for idx, pair in enumerate(arc_task.train_pairs):
                st.markdown(f"**Train Pair #{idx + 1}**")
                col_in, col_out = st.columns(2)
                with col_in:
                    st.caption("Input Grid")
                    st.components.v1.html(render_grid_html(pair.input_grid, (0, 0)), height=320)
                with col_out:
                    st.caption("Target Output Grid")
                    if pair.output_grid:
                        st.components.v1.html(render_grid_html(pair.output_grid, (0, 0)), height=320)
                    else:
                        st.caption("No target output provided.")

            # Convert to GridWorld & Explore button
            if st.button(f"🚀 Convert & Explore Task ({arc_task.task_id})", use_container_width=True):
                try:
                    env = create_arc_task_environment(arc_task, pair_type="train", index=0, max_steps=max_steps)
                    agent = ExplorerAgent()
                    result = agent.run_exploration(env, max_steps=max_steps)

                    os.makedirs("replays", exist_ok=True)
                    replay_path = f"replays/ui_arc_task_{arc_task.task_id}.json"
                    ReplayLogger.save_replay(replay_path, result, memory=agent.memory, scenario_name=f"ARC Task: {arc_task.task_id}")

                    st.session_state.current_result = {
                        "scenario_name": f"ARC Task: {arc_task.task_id}",
                        "env_initial_grid": env.initial_grid,
                        "env_initial_pos": env.initial_pos,
                        "result": result,
                        "memory_transitions": agent.memory.to_list(),
                    }
                    st.session_state.current_step_idx = 0
                    st.success(
                        f"Exploration completed for ARC Task `{arc_task.task_id}`! "
                        f"Results available in 🔬 **Exploration View** tab."
                    )
                except Exception as e:
                    st.error(f"Error executing exploration on ARC task: {e}")


if __name__ == "__main__":
    main()

