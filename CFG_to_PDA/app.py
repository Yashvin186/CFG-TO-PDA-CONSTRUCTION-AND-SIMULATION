"""
Streamlit Web Interface for CFG to PDA Construction and Simulation.
Formats solution in the exact academic / university textbook format:
  P = {(q), (terminals), (stack_alphabet), δ, q, S, q}
  Mapping functions: Grouped per non-terminal on the SAME line
  Simulation turnstile steps: 1. δ(q, 010000, S) ⊢ δ(q, 010000, 0BB)  R1
Includes a prominent 'Start' button to run the simulation.
"""

import streamlit as st
import pandas as pd
from pda import parse_cfg, convert_cfg_to_pda, simulate_pda, CFG, PDA

# Page configuration
st.set_page_config(
    page_title="CFG to PDA Converter & Simulator",
    page_icon="⚙️",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1e1b4b;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.25rem;
    }
    .solution-box {
        background-color: #ffffff;
        border: 1.5px solid #cbd5e1;
        border-radius: 8px;
        padding: 1.25rem 1.5rem;
        font-family: 'Fira Code', Consolas, Monaco, monospace;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #0f172a;
        white-space: pre-wrap;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚙️ CFG to PDA Converter & Simulator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Theory of Computation • Pushdown Automaton Construction & Step-by-Step Simulation</div>', unsafe_allow_html=True)

# Preset Grammars (with textbook example as default)
PRESETS = {
    "Example 1 (From Image): S -> 0BB, B -> 0S | 1S | 0": {
        "grammar": "S -> 0 B B\nB -> 0 S | 1 S | 0",
        "samples": ["010000", "00", "0100", "01000000", "1", "0"]
    },
    "Example 2: S -> aSb | a | b | ε": {
        "grammar": "S -> a S b | a | b | ε",
        "samples": ["aaabb", "ab", "a", "b", "aabb", "ε", "abb"]
    },
    "a^n b^n (n ≥ 0)": {
        "grammar": "S -> a S b | ε",
        "samples": ["aabb", "ab", "aaabbb", "ε", "aab", "ba"]
    },
    "Palindromes (Even & Odd length)": {
        "grammar": "S -> a S a | b S b | a | b | ε",
        "samples": ["abba", "aba", "aa", "bb", "ε", "ab"]
    },
    "Balanced Parentheses": {
        "grammar": "S -> ( S ) | S S | ε",
        "samples": ["(())", "()", "()()", "(()())", "ε", "("]
    },
    "Arithmetic Expressions": {
        "grammar": "E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id",
        "samples": ["id + id * id", "id", "id + id", "( id + id ) * id", "+ id"]
    },
    "Equal 'a's and 'b's": {
        "grammar": "S -> a S b | b S a | S S | ε",
        "samples": ["aabb", "ab", "ba", "baba", "ε", "aab"]
    }
}

# Sidebar
st.sidebar.header("Grammar Presets")
selected_preset_name = st.sidebar.selectbox("Load Example Grammar:", list(PRESETS.keys()))
default_grammar = PRESETS[selected_preset_name]["grammar"]
preset_samples = PRESETS[selected_preset_name]["samples"]

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Format Specification:**
- 7-Tuple: $P = \\{(q), (\\Sigma), (\\Gamma), \\delta, q, S, q\\}$
- Single working state $q$
- Leftmost symbol = **TOP** of stack
- Mapping functions grouped on the **same line** per variable
- Clean input string (no stray $\\varepsilon$'s)
""")

# =====================================================================
# Section 1 & 2: Grammar Input & Analysis
# =====================================================================
col_input, col_analysis = st.columns([1.2, 0.8])

with col_input:
    st.subheader("1. CFG Production Rules")
    grammar_text = st.text_area(
        "Enter productions (one rule per line):",
        value=default_grammar,
        height=140,
        help="Example: S -> 0 B B\nB -> 0 S | 1 S | 0"
    )

cfg = None
pda = None
parse_error = None

try:
    cfg = parse_cfg(grammar_text)
    pda = convert_cfg_to_pda(cfg)
except Exception as e:
    parse_error = str(e)

with col_analysis:
    st.subheader("2. Grammar Analysis")
    if parse_error:
        st.error(f"Error parsing grammar: {parse_error}")
    elif cfg:
        st.markdown(f"**Non-Terminals ($V$):** `{' , '.join(cfg.variables)}`")
        term_str = ' , '.join(cfg.terminals) if cfg.terminals else "ε (none)"
        st.markdown(f"**Terminals ($\Sigma$):** `{term_str}`")
        st.markdown(f"**Start Symbol ($S$):** `{cfg.start_symbol}`")
        with st.expander("View Parsed Productions", expanded=True):
            for prod in cfg.productions:
                st.code(str(prod), language="text")

if cfg and pda:
    st.markdown("---")

    # =====================================================================
    # Section 3: String Testing & Simulation with Start Button
    # =====================================================================
    st.subheader("3. String Testing & Simulation")

    st.markdown("**Sample Test Strings:**")
    sample_cols = st.columns(len(preset_samples) + 1)

    if "test_str_val" not in st.session_state:
        st.session_state.test_str_val = preset_samples[0]
    if "sim_started" not in st.session_state:
        st.session_state.sim_started = True

    for i, sample in enumerate(preset_samples):
        display_name = "ε (empty)" if sample == "" else sample
        if sample_cols[i].button(display_name, key=f"sample_{i}"):
            st.session_state.test_str_val = sample
            st.session_state.sim_started = True

    col_str_input, col_btn = st.columns([3.5, 1])
    with col_str_input:
        test_input = st.text_input(
            "Input string to test (enter 'ε' or leave blank for empty string):",
            value=st.session_state.test_str_val,
            key="main_test_input"
        )
    with col_btn:
        st.write("")
        st.write("")
        start_button = st.button("▶ Start", type="primary", use_container_width=True)

    if start_button:
        st.session_state.sim_started = True

    if st.session_state.get("sim_started", True):
        sim_res = simulate_pda(pda, test_input)

        # Result Badge
        disp_input = test_input if test_input else "ε"
        if sim_res.accepted:
            st.success(f"### ✅ ACCEPTED: String `{disp_input}` is accepted by the PDA.")
        else:
            st.error(f"### ❌ REJECTED: String `{disp_input}` cannot be accepted by the PDA.")

        # =====================================================================
        # Section 4: Academic Textbook Solution Format (As in Image)
        # =====================================================================
        st.markdown("---")
        st.subheader("4. Solution (Academic Output)")
        st.caption("Standard format matching university exams and classroom textbooks:")

        st.code(sim_res.solution_text, language="text")

        st.download_button(
            label="📥 Download Solution (.txt)",
            data=sim_res.solution_text,
            file_name=f"pda_solution_{disp_input}.txt",
            mime="text/plain"
        )

        # =====================================================================
        # Section 5: Interactive Step-by-Step Visualizer
        # =====================================================================
        if sim_res.accepted and sim_res.turnstile_steps:
            st.markdown("---")
            st.subheader("5. Interactive Step-by-Step Inspector")

            total_steps = len(sim_res.turnstile_steps)
            step_idx = st.slider("Step through computation:", 1, total_steps, 1) - 1
            curr_step = sim_res.turnstile_steps[step_idx]

            v1, v2, v3, v4 = st.columns([1, 1.2, 1.5, 1])
            with v1:
                st.metric("Step #", f"{curr_step.step_number} of {total_steps}")
            with v2:
                st.metric("Input Before", curr_step.current_input)
                st.metric("Input After", curr_step.next_input)
            with v3:
                st.metric("Stack Before", curr_step.current_stack)
                st.metric("Stack After", curr_step.next_stack)
            with v4:
                st.metric("Applied Rule", curr_step.applied_rule_id)

            # Tabular View
            with st.expander("View Full Trace Data Table", expanded=False):
                table_rows = []
                for s in sim_res.turnstile_steps:
                    table_rows.append({
                        "Step": s.step_number,
                        "Current Input": s.current_input,
                        "Current Stack": s.current_stack,
                        "Next Input": s.next_input,
                        "Next Stack": s.next_stack,
                        "Applied Rule": s.applied_rule_id
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
