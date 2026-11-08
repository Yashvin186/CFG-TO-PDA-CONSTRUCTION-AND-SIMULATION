"""
CFG to PDA Core Engine.
Produces standard academic / university textbook solutions:
  P = {(q), (terminals), (stack_alphabet), δ, q, S, q}
Mapping functions (grouped per non-terminal on the same line):
  R1: δ(q, ε, S) = {(q, 0BB)}
  R2: δ(q, ε, B) = {(q, 0S) | (q, 1S) | (q, 0)}
  R3: δ(q, 0, 0) = {(q, ε)}
  R4: δ(q, 1, 1) = {(q, ε)}
Simulation trace (clean inputs, no artificial epsilon prefixes):
  1. δ(q, 010000, S) ⊢ δ(q, 010000, 0BB)        R1
  2.                 ⊢ δ(q, 10000, BB)          R3
  ...
  12.                ⊢ δ(q, ε, ε)               R3
  13.                ACCEPT
"""

from typing import List, Tuple, Set, Optional, Dict, Any
from collections import deque
import re

STANDALONE_EPSILON = {'ε', 'epsilon', 'lambda', 'λ', '^', 'e', '""', "''"}


# =====================================================================
# 1. CFG Representation and Parser
# =====================================================================

class Production:
    def __init__(self, lhs: str, rhs: List[str]):
        self.lhs = lhs
        self.rhs = list(rhs)  # empty list represents epsilon

    @property
    def is_epsilon(self) -> bool:
        return len(self.rhs) == 0

    def rhs_str(self) -> str:
        return "".join(self.rhs) if self.rhs else "ε"

    def rhs_spaced(self) -> str:
        return " ".join(self.rhs) if self.rhs else "ε"

    def __repr__(self) -> str:
        return f"{self.lhs} -> {self.rhs_spaced()}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Production):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __hash__(self) -> int:
        return hash((self.lhs, tuple(self.rhs)))


class CFG:
    def __init__(self, variables: List[str], terminals: List[str], start_symbol: str, productions: List[Production]):
        self.variables: List[str] = list(dict.fromkeys(variables))
        self.terminals: List[str] = list(dict.fromkeys(terminals))
        self.start_symbol: str = start_symbol
        self.productions: List[Production] = productions

    def get_productions_for(self, var: str) -> List[Production]:
        return [p for p in self.productions if p.lhs == var]


def parse_cfg(text: str) -> CFG:
    """
    Parses CFG productions. Automatically detects variables, terminals, and start symbol.
    Supports both spaced tokens and unspaced single characters dynamically.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip() and not line.strip().startswith('#')]
    if not lines:
        raise ValueError("Grammar input is empty. Please enter at least one production rule.")

    raw_rules: List[Tuple[str, str]] = []
    lhs_order: List[str] = []
    arrow_regex = re.compile(r'\s*(?:->|-->|::=|=>)\s*')

    for line_num, line in enumerate(lines, 1):
        parts = arrow_regex.split(line, maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Line {line_num}: Invalid syntax '{line}'. Expected 'LHS -> RHS'.")
        lhs, rhs = parts[0].strip(), parts[1].strip()
        if not lhs:
            raise ValueError(f"Line {line_num}: Missing Left-Hand Side.")
        if not rhs:
            raise ValueError(f"Line {line_num}: Missing Right-Hand Side.")
        raw_rules.append((lhs, rhs))
        if lhs not in lhs_order:
            lhs_order.append(lhs)

    start_symbol = lhs_order[0]
    variables_set = set(lhs_order)

    # Check if the grammar uses spaced tokens
    has_spaces = any(
        len(alt.split()) > 1
        for _, rhs_str in raw_rules
        for alt in rhs_str.split('|')
        if alt.strip() and alt.strip() not in STANDALONE_EPSILON
    )

    def tokenize_alternative(alt: str) -> List[str]:
        alt = alt.strip()
        if not alt or alt in STANDALONE_EPSILON:
            return []
        toks = alt.split()
        if len(toks) > 1 or has_spaces:
            res = []
            for t in toks:
                if t not in STANDALONE_EPSILON:
                    res.append(t)
            return res

        single = toks[0]
        if single in STANDALONE_EPSILON:
            return []
        if single in variables_set:
            return [single]

        # Single string without spaces, e.g. '0BB' or 'aSb'
        res = []
        i = 0
        sorted_vars = sorted(list(variables_set), key=lambda x: -len(x))
        while i < len(single):
            matched = None
            for v in sorted_vars:
                if v and single.startswith(v, i):
                    matched = v
                    break
            if matched:
                res.append(matched)
                i += len(matched)
            else:
                res.append(single[i])
                i += 1
        return res

    productions: List[Production] = []
    terminals_set: Set[str] = set()

    for lhs, rhs_str in raw_rules:
        for alt in [a.strip() for a in rhs_str.split('|')]:
            symbols = tokenize_alternative(alt)
            productions.append(Production(lhs, symbols))
            for sym in symbols:
                if sym not in variables_set:
                    terminals_set.add(sym)

    intersection = variables_set.intersection(terminals_set)
    if intersection:
        raise ValueError(f"Symbol conflict: {intersection} detected as both variable and terminal.")

    return CFG(
        variables=lhs_order,
        terminals=sorted(list(terminals_set)),
        start_symbol=start_symbol,
        productions=productions
    )


# =====================================================================
# 2. PDA Representation & CFG-to-PDA Conversion
# =====================================================================

class PDATransition:
    def __init__(
        self,
        rule_id: str,
        group_id: str,
        from_state: str,
        input_symbol: str,    # 'ε' or terminal
        pop_symbol: str,      # top of stack symbol
        to_state: str,
        push_symbols: List[str],  # leftmost is TOP of stack. [] means ε (pop)
        category: str,        # 'production', 'terminal_match'
        description: str,
        associated_production: Optional[Production] = None
    ):
        self.rule_id = rule_id
        self.group_id = group_id
        self.from_state = from_state
        self.input_symbol = input_symbol
        self.pop_symbol = pop_symbol
        self.to_state = to_state
        self.push_symbols = list(push_symbols)
        self.category = category
        self.description = description
        self.associated_production = associated_production

    @property
    def push_str(self) -> str:
        return "".join(self.push_symbols) if self.push_symbols else "ε"

    def formal_notation(self) -> str:
        return f"δ({self.from_state}, {self.input_symbol}, {self.pop_symbol}) = {{({self.to_state}, {self.push_str})}}"

    def __repr__(self) -> str:
        return f"[{self.group_id}] {self.formal_notation()}"


class PDA:
    def __init__(
        self,
        states: List[str],
        input_alphabet: List[str],
        stack_alphabet: List[str],
        start_state: str,
        start_stack_symbol: str,
        accept_states: List[str],
        transitions: List[PDATransition],
        source_cfg: CFG,
        mapping_rules_text: List[str]
    ):
        self.states = states
        self.input_alphabet = input_alphabet
        self.stack_alphabet = stack_alphabet
        self.start_state = start_state
        self.start_stack_symbol = start_stack_symbol
        self.accept_states = accept_states
        self.transitions = transitions
        self.source_cfg = source_cfg
        self.mapping_rules_text = mapping_rules_text

        self._trans_index: Dict[Tuple[str, str, str], List[PDATransition]] = {}
        for t in self.transitions:
            key = (t.from_state, t.input_symbol, t.pop_symbol)
            self._trans_index.setdefault(key, []).append(t)

    def get_applicable_transitions(self, state: str, input_symbol: Optional[str], top_of_stack: str) -> List[PDATransition]:
        applicable = []
        eps_key = (state, 'ε', top_of_stack)
        if eps_key in self._trans_index:
            applicable.extend(self._trans_index[eps_key])

        if input_symbol is not None and input_symbol != 'ε':
            term_key = (state, input_symbol, top_of_stack)
            if term_key in self._trans_index:
                applicable.extend(self._trans_index[term_key])

        return applicable

    def get_7tuple_str(self) -> str:
        q_str = f"({', '.join(self.states)})"
        sigma_str = f"({', '.join(self.input_alphabet)})"
        gamma_str = f"({', '.join(self.stack_alphabet)})"
        f_str = f"{self.accept_states[0]}" if len(self.accept_states) == 1 else f"({', '.join(self.accept_states)})"
        return f"P = {{{q_str}, {sigma_str}, {gamma_str}, δ, {self.start_state}, {self.start_stack_symbol}, {f_str}}}"


def convert_cfg_to_pda(cfg: CFG) -> PDA:
    """
    Standard Single-State CFG-to-PDA conversion matching university textbook format:
      P = {(q), (terminals), (variables, terminals), δ, q, S, q}
      All alternatives for the same non-terminal are written on the SAME line:
        R1: δ(q, ε, S) = {(q, 0BB)}
        R2: δ(q, ε, B) = {(q, 0S) | (q, 1S) | (q, 0)}
        R3: δ(q, 0, 0) = {(q, ε)}
        R4: δ(q, 1, 1) = {(q, ε)}
    """
    states = ["q"]
    input_alphabet = list(cfg.terminals)
    start_stack_symbol = cfg.start_symbol
    stack_alphabet = list(dict.fromkeys(cfg.variables + cfg.terminals))
    start_state = "q"
    accept_states = ["q"]

    transitions: List[PDATransition] = []
    mapping_rules_text: List[str] = []
    rule_num = 1

    # 1. Production Transitions grouped per non-terminal on the SAME line
    for var in cfg.variables:
        prods = cfg.get_productions_for(var)
        r_id = f"R{rule_num}"
        targets = " | ".join(f"(q, {p.rhs_str()})" for p in prods)
        mapping_rules_text.append(f"{r_id}: δ(q, ε, {var}) = {{{targets}}}")

        for sub_idx, p in enumerate(prods, 1):
            t = PDATransition(
                rule_id=f"{r_id}_{sub_idx}",
                group_id=r_id,
                from_state="q",
                input_symbol="ε",
                pop_symbol=var,
                to_state="q",
                push_symbols=list(p.rhs),
                category="production",
                description=f"Production Expansion: Replace top '{var}' with '{p.rhs_str()}'.",
                associated_production=p
            )
            transitions.append(t)
        rule_num += 1

    # 2. Terminal matching transitions
    for term in cfg.terminals:
        r_id = f"R{rule_num}"
        t = PDATransition(
            rule_id=r_id,
            group_id=r_id,
            from_state="q",
            input_symbol=term,
            pop_symbol=term,
            to_state="q",
            push_symbols=[],
            category="terminal_match",
            description=f"Terminal Match: Match and consume terminal '{term}' from input and pop '{term}' from stack."
        )
        transitions.append(t)
        mapping_rules_text.append(f"{r_id}: δ(q, {term}, {term}) = {{(q, ε)}}")
        rule_num += 1

    return PDA(
        states=states,
        input_alphabet=input_alphabet,
        stack_alphabet=stack_alphabet,
        start_state=start_state,
        start_stack_symbol=start_stack_symbol,
        accept_states=accept_states,
        transitions=transitions,
        source_cfg=cfg,
        mapping_rules_text=mapping_rules_text
    )


# =====================================================================
# 3. PDA Simulation Engine
# =====================================================================

class TurnstileStep:
    def __init__(
        self,
        step_number: int,
        current_input: str,
        current_stack: str,
        next_input: str,
        next_stack: str,
        applied_rule_id: str,
        is_first: bool = False
    ):
        self.step_number = step_number
        self.current_input = current_input
        self.current_stack = current_stack
        self.next_input = next_input
        self.next_stack = next_stack
        self.applied_rule_id = applied_rule_id
        self.is_first = is_first

    def format_line(self) -> str:
        num_str = f"{self.step_number}."
        if self.is_first:
            left_part = f"{num_str:<4}δ(q, {self.current_input}, {self.current_stack}) ⊢ δ(q, {self.next_input}, {self.next_stack})"
        else:
            left_part = f"{num_str:<4}                ⊢ δ(q, {self.next_input}, {self.next_stack})"

        return f"{left_part:<46} {self.applied_rule_id}"


class SimulationResult:
    def __init__(
        self,
        accepted: bool,
        input_string: str,
        input_tokens: List[str],
        turnstile_steps: List[TurnstileStep],
        total_explored: int,
        message: str,
        solution_text: str
    ):
        self.accepted = accepted
        self.input_string = input_string
        self.input_tokens = input_tokens
        self.turnstile_steps = turnstile_steps
        self.total_explored = total_explored
        self.message = message
        self.solution_text = solution_text


def tokenize_input_string(input_str: str, terminals: List[str]) -> List[str]:
    s = input_str.strip()
    if not s or s in STANDALONE_EPSILON:
        return []

    tokens = s.split()
    if len(tokens) > 1:
        return [t for t in tokens if t not in STANDALONE_EPSILON]

    single_token = tokens[0]
    if single_token in terminals:
        return [single_token]

    terminals_sorted = sorted(terminals, key=lambda x: -len(x))
    res = []
    i = 0
    while i < len(single_token):
        matched = None
        for term in terminals_sorted:
            if term and single_token.startswith(term, i):
                matched = term
                break
        if matched:
            res.append(matched)
            i += len(matched)
        else:
            res.append(single_token[i])
            i += 1
    return res


def simulate_pda(pda: PDA, raw_input_string: str, max_explored_limit: int = 35000) -> SimulationResult:
    """
    Simulates the PDA using BFS to discover the shortest accepting computation trace.
    Generates exact academic turnstile format without artificial epsilon prefixes:
      1. δ(q, 010000, S) ⊢ δ(q, 010000, 0BB)        R1
      2.                 ⊢ δ(q, 10000, BB)          R3
      ...
    """
    input_tokens = tokenize_input_string(raw_input_string, pda.input_alphabet)
    n = len(input_tokens)

    # Validate input symbols against Σ
    for token in input_tokens:
        if token not in pda.input_alphabet:
            lines = []
            lines.append("Solution:\n")
            lines.append("The PDA can be given as:\n")
            lines.append(f"    1.  {pda.get_7tuple_str()}\n")
            lines.append("The mapping function δ will be:\n")
            for r in pda.mapping_rules_text:
                lines.append(f"{r}")
            lines.append(f"\nTesting {raw_input_string if raw_input_string else 'ε'} against PDA:\n")
            lines.append(f"    REJECT: Input symbol '{token}' is not in the PDA alphabet Σ = {{{', '.join(pda.input_alphabet)}}}.")
            return SimulationResult(
                accepted=False,
                input_string=raw_input_string,
                input_tokens=input_tokens,
                turnstile_steps=[],
                total_explored=0,
                message=f"Rejected: Input symbol '{token}' is not in the PDA alphabet Σ = {{{', '.join(pda.input_alphabet)}}}.",
                solution_text="\n".join(lines)
            )

    def get_remaining_str(idx: int) -> str:
        return "".join(input_tokens[idx:]) if idx < n else "ε"

    def stack_disp(stk: Tuple[str, ...]) -> str:
        return "".join(stk) if stk else "ε"

    # Initial stack: Start symbol S directly
    initial_stack = (pda.source_cfg.start_symbol,)
    queue = deque()
    # (state, input_idx, stack_tuple, path, consecutive_eps_count)
    queue.append((pda.start_state, 0, initial_stack, [], 0))

    visited: Set[Tuple[str, int, Tuple[str, ...]]] = set()
    visited.add((pda.start_state, 0, initial_stack))

    terminals_set = set(pda.input_alphabet)
    variables_set = set(pda.source_cfg.variables)
    max_consecutive_eps = max(40, len(variables_set) * 6)
    total_explored = 0

    while queue:
        state, input_idx, stack, path, eps_count = queue.popleft()
        total_explored += 1

        # Check acceptance condition: input consumed, stack is empty
        if input_idx == n and len(stack) == 0:
            turnstile_steps: List[TurnstileStep] = []

            for idx, (c_before, trans, c_after) in enumerate(path):
                b_state, b_idx, b_stack = c_before
                a_state, a_idx, a_stack = c_after
                step_no = idx + 1

                rem_b = get_remaining_str(b_idx)
                rem_a = get_remaining_str(a_idx)

                stk_b = stack_disp(b_stack)
                stk_a = stack_disp(a_stack)

                is_first = (idx == 0)
                turnstile_steps.append(
                    TurnstileStep(
                        step_number=step_no,
                        current_input=rem_b,
                        current_stack=stk_b,
                        next_input=rem_a,
                        next_stack=stk_a,
                        applied_rule_id=trans.group_id,
                        is_first=is_first
                    )
                )

            # Generate solution text
            lines = []
            lines.append("Solution:\n")
            lines.append("The PDA can be given as:\n")
            lines.append(f"    1.  {pda.get_7tuple_str()}\n")
            lines.append("The mapping function δ will be:\n")
            for r in pda.mapping_rules_text:
                lines.append(f"{r}")
            lines.append(f"\nTesting {raw_input_string if raw_input_string else 'ε'} against PDA:\n")

            for t_step in turnstile_steps:
                lines.append(t_step.format_line())

            accept_num_str = f"{len(turnstile_steps) + 1}."
            lines.append(f"{accept_num_str:<4}                ACCEPT")
            solution_text = "\n".join(lines)

            return SimulationResult(
                accepted=True,
                input_string=raw_input_string,
                input_tokens=input_tokens,
                turnstile_steps=turnstile_steps,
                total_explored=total_explored,
                message=f"String ACCEPTED in {len(turnstile_steps)} steps.",
                solution_text=solution_text
            )

        if total_explored >= max_explored_limit or not stack:
            continue

        top_symbol = stack[0]
        stack_tail = stack[1:]
        next_input_token = input_tokens[input_idx] if input_idx < n else None

        # PRUNING 1: Leading terminal prefix compatibility
        prefix_mismatch = False
        leading_terms = []
        for s in stack:
            if s in terminals_set:
                leading_terms.append(s)
            else:
                break
        for k, term in enumerate(leading_terms):
            if input_idx + k >= n or input_tokens[input_idx + k] != term:
                prefix_mismatch = True
                break
        if prefix_mismatch:
            continue

        # PRUNING 2: Terminal count bound
        term_count = sum(1 for s in stack if s in terminals_set)
        if term_count > (n - input_idx):
            continue

        # Find applicable transitions
        applicable = pda.get_applicable_transitions(state, next_input_token, top_symbol)

        for trans in applicable:
            if trans.input_symbol == 'ε':
                new_input_idx = input_idx
                new_eps_count = eps_count + 1
            else:
                new_input_idx = input_idx + 1
                new_eps_count = 0

            if new_eps_count > max_consecutive_eps:
                continue

            new_stack = tuple(trans.push_symbols) + stack_tail
            new_state = trans.to_state

            new_config_key = (new_state, new_input_idx, new_stack)
            if new_config_key in visited:
                continue
            visited.add(new_config_key)

            current_config = (state, input_idx, stack)
            next_config = (new_state, new_input_idx, new_stack)
            new_path = path + [(current_config, trans, next_config)]

            queue.append((new_state, new_input_idx, new_stack, new_path, new_eps_count))

    # Rejection text
    lines = []
    lines.append("Solution:\n")
    lines.append("The PDA can be given as:\n")
    lines.append(f"    1.  {pda.get_7tuple_str()}\n")
    lines.append("The mapping function δ will be:\n")
    for r in pda.mapping_rules_text:
        lines.append(f"{r}")
    lines.append(f"\nTesting {raw_input_string if raw_input_string else 'ε'} against PDA:\n")
    lines.append("    REJECT: String cannot be derived by the PDA.")
    solution_text = "\n".join(lines)

    return SimulationResult(
        accepted=False,
        input_string=raw_input_string,
        input_tokens=input_tokens,
        turnstile_steps=[],
        total_explored=total_explored,
        message=f"String REJECTED after exploring {total_explored} configurations.",
        solution_text=solution_text
    )
