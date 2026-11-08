# CFG to Pushdown Automaton (PDA) Construction & Simulation

Interactive Streamlit application for **Theory of Computation / Formal Languages and Automata Theory**.

## 📁 Project Structure

```
CFG_to_PDA/
├── app.py              # Streamlit interface: CFG input, PDA construction, and simulation output
├── pda.py              # CFG parsing, PDA construction, transition generation, and PDA simulation
└── requirements.txt    # Minimal dependencies (streamlit>=1.30.0)
```

---

## 🚀 Quickstart (Using Virtual Environment)

All dependencies and execution are isolated in the local virtual environment (`venv`).

### Launch the Streamlit Application

From the project root:
```powershell
.\venv\Scripts\streamlit.exe run CFG_to_PDA/app.py
```

Or activate the virtual environment first:
```powershell
.\venv\Scripts\Activate.ps1
streamlit run CFG_to_PDA/app.py
```

The application will launch in your default web browser at `http://localhost:8501`.

---

## 📐 Theoretical Model & Features

### 1. Context-Free Grammar (CFG) Input & Dynamic Parsing
- Automatically parses multi-line grammar rules using `->`, `::=`, or `=>`.
- Handles multiple alternatives (`|`), recursive productions, and $\epsilon$-productions (`ε`, `epsilon`, or empty alternatives).
- Automatically discovers:
  - **Non-terminals / Variables ($V$)**: Extracted from LHS of rules.
  - **Terminals ($\Sigma$)**: Extracted from RHS symbols.
  - **Start Symbol ($S$)**: First defined non-terminal.

### 2. Standard Single-State CFG-to-PDA Construction
Constructs the formal 7-tuple:
$$P = \{(q), (\Sigma), (\Gamma), \delta, q, z_0, q\}$$
- **State ($Q$)**: $\{q\}$ (Single working state)
- **Input Alphabet ($\Sigma$)**: Terminals of the CFG
- **Stack Alphabet ($\Gamma$)**: $V \cup \Sigma \cup \{z_0\}$
- **Start State**: $q$
- **Start Stack Symbol**: $z_0$
- **Accept State**: $q$ (Acceptance by empty stack / final state)

### 3. Transition Functions ($\delta$)
- **Production Expansions**:
  - $R_1$: Recursive rules $\delta(q, \epsilon, A) = \{(q, \alpha)\}$
  - $R_2$: Base/grouped rules $\delta(q, \epsilon, A) = \{(q, \alpha_1) \mid (q, \alpha_2) \mid \dots\}$
- **Terminal Matching Rules**:
  - For each terminal $a \in \Sigma$: $\delta(q, a, a) = \{(q, \epsilon)\}$
- **Stack Clearing Rule**:
  - Bottom marker pop: $\delta(q, \epsilon, z_0) = \{(q, \epsilon)\}$

### 4. Stack Orientation
- **Leftmost symbol is defined as the TOP of the stack**.
- For instance, if the stack string is `a S b z0`, `a` is at the top of the stack.

### 5. Non-Deterministic Simulation & Loop Prevention
- Uses **Breadth-First Search (BFS)** to explore non-deterministic branches level-by-level, ensuring the shortest accepting trace is found.
- Eliminates infinite loops through:
  1. **Visited Configuration Tracking**: `(state, input_idx, stack_tuple)` prunes duplicate or cyclic configurations.
  2. **Terminal Prefix Compatibility**: Prunes branches where leading stack terminals mismatch remaining input.
  3. **Terminal Count Bound**: Prunes branches where the count of terminals on the stack exceeds remaining input length.
  4. **Epsilon Loop Guard**: Limits consecutive $\epsilon$-steps without terminal consumption.

### 6. Standard Textbook Solution Output Format
Outputs clean turnstile notation (`⊢`) matching standard university exams and textbooks:

```text
Solution:

The PDA can be given as:

    1.  P = {(q), (a, b), (S, a, b, z0), δ, q, z0, q}

The mapping function δ will be:

R1: δ(q, ε, S) = {(q, aSb)}
R2: δ(q, ε, S) = {(q, a) | (q, b) | (q, ε)}
R3: δ(q, a, a) = {(q, ε)}
R4: δ(q, b, b) = {(q, ε)}
R5: δ(q, ε, z0) = {(q, ε)}

Simulation: Consider the string aaabb

1.  δ(q, εaaabb, S) ⊢ δ(q, aaabb, aSb)         R1
2.                  ⊢ δ(q, εaabb, Sb)          R3
3.                  ⊢ δ(q, aabb, aSbb)         R1
4.                  ⊢ δ(q, εabb, Sbb)          R3
5.                  ⊢ δ(q, abb, abb)           R2
6.                  ⊢ δ(q, bb, bb)             R3
7.                  ⊢ δ(q, b, b)               R4
8.                  ⊢ δ(q, ε, z0)              R4
9.                  ⊢ δ(q, ε)                  R5
10.                 ACCEPT
```
