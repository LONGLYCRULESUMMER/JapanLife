# JapanLife Plan 2 — 多智能体 + API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Plan 1 的混合检索之上，用 LangChain + LangGraph 搭一个 supervisor 路由 + 三专家（tax/visa/ward_office）+ 一处 handoff 的多智能体，DeepSeek 作 LLM，SQLite checkpointer 持久化对话，并用 FastAPI 暴露 `/chat`、`/chat/stream`、`/health`。

**Architecture:** `tools/`（领域计算工具 + 知识检索工具，包 LangChain `@tool`）→ `agents/`（state / supervisor / specialists(create_react_agent) / handoffs / graph）→ `app/`（FastAPI）。所有单测用**桩/假 LLM**，不需要真实 DeepSeek key；另有一个 `@pytest.mark.integration` 的真实端到端测试，无 key 时自动跳过。

**Tech Stack（已安装，版本已验证）:** langgraph 1.2.x, langchain 1.3.x, langchain-deepseek 1.1.x, langgraph-checkpoint-sqlite 3.1.x, fastapi 0.136.x, uvicorn, sse-starlette, httpx, pytest-asyncio。

参考规格：`docs/superpowers/specs/2026-06-09-japanlife-langgraph-refactor-design.md`（第 5、7、8、9、10 节）。

## 已验证的关键 API（实现时按这些写，勿臆测）
- `from langgraph.prebuilt import create_react_agent` —— 签名含 `model, tools, prompt, state_schema, checkpointer, name`。返回已编译图，可作父图节点。
- `from langgraph.graph import START, END, StateGraph`；`from langgraph.graph.message import add_messages`。
- `from langgraph.types import Command` —— `Command(goto=..., update=..., graph=Command.PARENT)`；`Command.PARENT == "__parent__"`。
- `from langgraph.checkpoint.sqlite import SqliteSaver` —— `SqliteSaver(conn)`，需 `saver.setup()`。
- `from langchain_deepseek import ChatDeepSeek` —— `ChatDeepSeek(model=..., api_key=..., temperature=...)`；属性 `model_name`；有 `with_structured_output`、`bind_tools`。
- `from langchain_core.tools import tool, StructuredTool, InjectedToolCallId`。
- handoff 工具返回 `Command`；`tool.invoke({"name":..,"args":{},"id":"tc1","type":"tool_call"})` 可在测试中触发并拿回 `Command`。
- 图编排已用桩验证：`START→supervisor→specialist→supervisor→END` 与 `ward_office→visa` handoff 均工作；SqliteSaver 持久化 `get_state(config).values` 可读。

---

## File Structure (Plan 2 范围)

| 文件 | 职责 |
|---|---|
| `core/llm.py` | ChatDeepSeek 工厂（一处切换 LLM 提供商） |
| `tools/tax_tools.py` | 税务计算（移植）+ `TAX_TOOLS` |
| `tools/visa_tools.py` | 在留资格/续签工具 + `VISA_TOOLS` |
| `tools/ward_office_tools.py` | 区役所流程工具 + `WARD_OFFICE_TOOLS` |
| `tools/knowledge_tool.py` | `make_knowledge_search_tool(domain)` 包 `search_knowledge_base` |
| `agents/state.py` | `GraphState` (TypedDict) |
| `agents/prompts.py` | supervisor + 三专家系统提示 |
| `agents/supervisor.py` | `Route` 模型 + `make_supervisor(llm)` 路由节点 |
| `agents/handoffs.py` | `make_handoff_tool(target)` |
| `agents/specialists/{tax,visa,ward_office}.py` | `*_tools()` + `build_*_agent(llm)` |
| `agents/graph.py` | `build_graph(llm, checkpointer, specialists?, supervisor?)` |
| `agents/output.py` | `extract_reply` / `extract_citations` |
| `app/schemas.py` | `ChatRequest` / `ChatResponse` |
| `app/routes.py` | `/chat` `/chat/stream` `/health` + `get_graph` 依赖 |
| `app/main.py` | FastAPI app + lifespan（建图 + checkpointer） |
| `tests/**` | 单测（桩/假 LLM）+ 1 个集成测试（无 key 跳过） |

---

## Task 1: 脚手架 + LLM 工厂

**Files:** Modify `pyproject.toml`/`poetry.lock`(已由 `poetry add` 改动，需提交); Create `tools/__init__.py`, `agents/__init__.py`, `agents/specialists/__init__.py`, `app/__init__.py`, `core/llm.py`, `tests/test_llm.py`

- [ ] **Step 1: 创建包目录**
```bash
cd /Users/javagod/VsCodeProjects/JapanLife
mkdir -p tools agents/specialists app
touch tools/__init__.py agents/__init__.py agents/specialists/__init__.py app/__init__.py
```

- [ ] **Step 2: 失败测试 `tests/test_llm.py`**
```python
def test_get_llm_uses_configured_model(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    from core.llm import get_llm
    llm = get_llm()
    name = getattr(llm, "model_name", None) or getattr(llm, "model", "")
    assert "deepseek" in name.lower()


def test_get_llm_override(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    from core.llm import get_llm
    llm = get_llm(model="deepseek-reasoner")
    name = getattr(llm, "model_name", None) or getattr(llm, "model", "")
    assert name == "deepseek-reasoner"
```

- [ ] **Step 3: 运行，确认 FAIL** — `poetry run pytest tests/test_llm.py -v`

- [ ] **Step 4: 实现 `core/llm.py`**
```python
from __future__ import annotations

from langchain_deepseek import ChatDeepSeek

from core.config import settings


def get_llm(model: str | None = None, temperature: float = 0.0) -> ChatDeepSeek:
    """Build the DeepSeek chat model. Swap the provider here to change the whole app's LLM."""
    return ChatDeepSeek(
        model=model or settings.llm_model,
        api_key=settings.deepseek_api_key,
        temperature=temperature,
    )
```

- [ ] **Step 5: 运行，确认 PASS（2 passed）**

- [ ] **Step 6: 提交**
```bash
git add pyproject.toml poetry.lock tools agents app core/llm.py tests/test_llm.py
git commit -m "feat(agents): add LangGraph/LangChain/FastAPI deps + DeepSeek LLM factory

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: 税务工具 `tools/tax_tools.py`（移植）

**Files:** Create `tools/tax_tools.py`, `tests/test_tax_tools.py`

- [ ] **Step 1: 失败测试 `tests/test_tax_tools.py`**
```python
from tools.tax_tools import (
    TAX_TOOLS,
    calculate_furusato_nozei_limit,
    estimate_income_tax,
    get_tax_deadlines,
)


def test_estimate_income_tax_known_value():
    r = estimate_income_tax(5_000_000, employment_type="employee")
    assert r["taxable_income"] == 2_330_000
    assert r["total_tax"] == 138_345
    assert r["tax_bracket"] == "10%"


def test_estimate_income_tax_zero_income():
    r = estimate_income_tax(0)
    assert r["taxable_income"] == 0
    assert r["total_tax"] == 0


def test_furusato_limit_scales_with_income():
    low = calculate_furusato_nozei_limit(3_000_000)["estimated_limit"]
    high = calculate_furusato_nozei_limit(8_000_000)["estimated_limit"]
    assert high > low > 0


def test_tax_deadlines_structure():
    d = get_tax_deadlines()
    assert "deadlines" in d and isinstance(d["deadlines"], list)
    assert all("days_remaining" in x for x in d["deadlines"])


def test_tax_tools_exported_as_langchain_tools():
    names = {t.name for t in TAX_TOOLS}
    assert names == {"estimate_income_tax", "calculate_furusato_nozei_limit", "get_tax_deadlines"}
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `tools/tax_tools.py`**
```python
from __future__ import annotations

from datetime import date

from langchain_core.tools import tool


def estimate_income_tax(
    annual_income: int, employment_type: str = "employee", deductions: str = ""
) -> dict:
    """Estimate Japanese income tax for a foreign resident (reference only, not professional advice).

    Args:
        annual_income: Annual gross income in JPY.
        employment_type: "employee" or "self_employed".
        deductions: Comma-separated extra deductions, e.g. "medical,life_insurance,spouse".

    Returns:
        dict with taxable_income, income_tax, reconstruction_tax, total_tax,
        effective_rate, and tax_bracket.
    """
    if employment_type == "employee":
        if annual_income <= 1_625_000:
            employment_deduction = 550_000
        elif annual_income <= 1_800_000:
            employment_deduction = int(annual_income * 0.4) - 100_000
        elif annual_income <= 3_600_000:
            employment_deduction = int(annual_income * 0.3) + 80_000
        elif annual_income <= 6_600_000:
            employment_deduction = int(annual_income * 0.2) + 440_000
        elif annual_income <= 8_500_000:
            employment_deduction = int(annual_income * 0.1) + 1_100_000
        else:
            employment_deduction = 1_950_000
    else:
        employment_deduction = 0

    basic_deduction = 480_000
    social_insurance = int(annual_income * 0.15) if employment_type == "employee" else 0

    extra = 0
    for d in (x.strip().lower() for x in deductions.split(",") if x.strip()):
        extra += {
            "medical": 100_000,
            "life_insurance": 120_000,
            "earthquake_insurance": 50_000,
            "spouse": 380_000,
            "dependent": 380_000,
        }.get(d, 0)

    taxable_income = max(
        annual_income - employment_deduction - basic_deduction - social_insurance - extra, 0
    )

    brackets = [
        (1_950_000, 0.05, 0),
        (3_300_000, 0.10, 97_500),
        (6_950_000, 0.20, 427_500),
        (9_000_000, 0.23, 636_000),
        (18_000_000, 0.33, 1_536_000),
        (40_000_000, 0.40, 2_796_000),
        (float("inf"), 0.45, 4_796_000),
    ]
    income_tax = 0
    bracket = "0%"
    for upper, rate, ded in brackets:
        if taxable_income <= upper:
            income_tax = int(taxable_income * rate - ded)
            bracket = f"{int(rate * 100)}%"
            break
    income_tax = max(income_tax, 0)
    reconstruction_tax = int(income_tax * 0.021)
    total_tax = income_tax + reconstruction_tax
    effective_rate = round(total_tax / annual_income * 100, 1) if annual_income > 0 else 0.0

    return {
        "annual_income": annual_income,
        "taxable_income": taxable_income,
        "income_tax": income_tax,
        "reconstruction_tax": reconstruction_tax,
        "total_tax": total_tax,
        "effective_rate": effective_rate,
        "tax_bracket": bracket,
        "note": "Estimate only. Consult a tax professional (税理士) for accuracy.",
    }


def calculate_furusato_nozei_limit(
    annual_income: int, family_status: str = "single", dependents: int = 0
) -> dict:
    """Estimate the Furusato Nozei (hometown tax) donation limit in JPY.

    Args:
        annual_income: Annual gross income in JPY.
        family_status: "single", "married", or "married_with_children".
        dependents: Number of tax dependents.

    Returns:
        dict with estimated_limit, self_payment (always 2000), and explanation.
    """
    if annual_income <= 0:
        return {"estimated_limit": 0, "self_payment": 2000, "explanation": "No income reported."}

    resident_tax = annual_income * 0.10
    special_portion = resident_tax * 0.20

    factor = 1.0
    if family_status == "married":
        factor -= 0.05
    elif family_status == "married_with_children":
        factor -= 0.10
    factor -= dependents * 0.03

    estimated_limit = max(int(special_portion * factor), 0)
    return {
        "estimated_limit": estimated_limit,
        "self_payment": 2000,
        "explanation": (
            f"Based on annual income ¥{annual_income:,}, the estimated Furusato Nozei limit "
            f"is about ¥{estimated_limit:,}. You pay ¥2,000 out of pocket; the rest is "
            f"deducted from your taxes. This is an estimate only."
        ),
    }


def get_tax_deadlines() -> dict:
    """Return upcoming Japanese tax deadlines relative to today.

    Returns:
        dict with current_date, tax_year, and a sorted list of deadlines
        (each with deadline, description, days_remaining, urgent).
    """
    today = date.today()
    year = today.year
    filing_start = date(year, 2, 16)
    filing_end = date(year, 3, 15)
    if today > filing_end:
        filing_start = date(year + 1, 2, 16)
        filing_end = date(year + 1, 3, 15)
        tax_year = year
    else:
        tax_year = year - 1

    raw = [
        (filing_end, f"Income tax filing deadline for {tax_year} (確定申告期限)"),
        (filing_start, f"Tax filing period opens for {tax_year}"),
        (date(year, 6, 30), f"First resident tax (住民税) installment for {year}"),
        (date(year, 12, 31), f"Furusato Nozei donation deadline for {year}"),
    ]
    deadlines = []
    for d, desc in raw:
        days = (d - today).days
        if days >= 0:
            deadlines.append(
                {"deadline": str(d), "description": desc, "days_remaining": days, "urgent": days <= 30}
            )
    deadlines.sort(key=lambda x: x["days_remaining"])
    return {"current_date": str(today), "tax_year": tax_year, "deadlines": deadlines}


TAX_TOOLS = [
    tool(estimate_income_tax),
    tool(calculate_furusato_nozei_limit),
    tool(get_tax_deadlines),
]
```

- [ ] **Step 4: 运行，确认 PASS（5 passed）**
- [ ] **Step 5: 提交**
```bash
git add tools/tax_tools.py tests/test_tax_tools.py
git commit -m "feat(tools): tax calculators ported as LangChain tools

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: 在留工具 `tools/visa_tools.py`

**Files:** Create `tools/visa_tools.py`, `tests/test_visa_tools.py`

- [ ] **Step 1: 失败测试 `tests/test_visa_tools.py`**
```python
from tools.visa_tools import (
    VISA_TOOLS,
    check_permanent_residency_eligibility,
    visa_renewal_checklist,
)


def test_pr_eligible_after_10_years():
    r = check_permanent_residency_eligibility(years_in_japan=10, years_on_work_visa=6)
    assert r["eligible"] is True


def test_pr_not_eligible_too_few_years():
    r = check_permanent_residency_eligibility(years_in_japan=3, years_on_work_visa=2)
    assert r["eligible"] is False
    assert r["years_short"] == 7


def test_pr_highly_skilled_fast_track():
    r = check_permanent_residency_eligibility(
        years_in_japan=2, years_on_work_visa=2, highly_skilled=True
    )
    assert r["eligible"] is True


def test_renewal_checklist_has_documents():
    r = visa_renewal_checklist()
    assert isinstance(r["documents"], list) and r["documents"]
    assert r["apply_window_months_before_expiry"] == 3


def test_visa_tools_exported():
    names = {t.name for t in VISA_TOOLS}
    assert names == {"check_permanent_residency_eligibility", "visa_renewal_checklist"}
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `tools/visa_tools.py`**
```python
from __future__ import annotations

from langchain_core.tools import tool


def check_permanent_residency_eligibility(
    years_in_japan: int, years_on_work_visa: int, highly_skilled: bool = False
) -> dict:
    """Roughly check eligibility for Japanese permanent residency (永住).

    General rule: 10 continuous years in Japan, at least 5 on a work visa.
    Highly Skilled Professionals may qualify after 1-3 years.

    Args:
        years_in_japan: Total continuous years residing in Japan.
        years_on_work_visa: Years held on a work visa.
        highly_skilled: Whether the applicant holds Highly Skilled Professional status.

    Returns:
        dict with eligible (bool), reason, and years_short (0 if eligible).
    """
    if highly_skilled and years_in_japan >= 3:
        return {"eligible": True, "reason": "Highly Skilled Professional fast track (1-3 years).", "years_short": 0}

    meets_total = years_in_japan >= 10
    meets_work = years_on_work_visa >= 5
    if meets_total and meets_work:
        return {"eligible": True, "reason": "Meets the standard 10-year requirement.", "years_short": 0}

    years_short = max(10 - years_in_japan, 0)
    reason = "Needs 10 continuous years (≥5 on a work visa)."
    if meets_total and not meets_work:
        reason = "Has 10 years total but fewer than 5 years on a work visa."
    return {"eligible": False, "reason": reason, "years_short": years_short}


def visa_renewal_checklist() -> dict:
    """Return the documents and timing for a residence-status renewal (在留期間更新).

    Returns:
        dict with documents (list), apply_window_months_before_expiry, and processing_time.
    """
    return {
        "documents": [
            "Application for extension of period of stay",
            "Passport and residence card (在留カード)",
            "ID photo (4cm x 3cm)",
            "Certificate of employment / enrollment",
            "Proof of tax payment (納税証明書)",
        ],
        "apply_window_months_before_expiry": 3,
        "processing_time": "2 weeks to 1 month",
        "note": "Apply at the Immigration Bureau (入管) before your current status expires.",
    }


VISA_TOOLS = [
    tool(check_permanent_residency_eligibility),
    tool(visa_renewal_checklist),
]
```

- [ ] **Step 4: 运行，确认 PASS（5 passed）**
- [ ] **Step 5: 提交**
```bash
git add tools/visa_tools.py tests/test_visa_tools.py
git commit -m "feat(tools): visa eligibility + renewal tools

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: 区役所工具 `tools/ward_office_tools.py`

**Files:** Create `tools/ward_office_tools.py`, `tests/test_ward_office_tools.py`

- [ ] **Step 1: 失败测试 `tests/test_ward_office_tools.py`**
```python
from tools.ward_office_tools import (
    WARD_OFFICE_TOOLS,
    days_until_move_in_deadline,
    moving_in_checklist,
)


def test_checklist_from_within_japan_requires_transfer_cert():
    r = moving_in_checklist(from_within_japan=True)
    assert any("転出証明書" in d for d in r["documents"])
    assert r["deadline_days"] == 14


def test_checklist_from_abroad_no_transfer_cert():
    r = moving_in_checklist(from_within_japan=False)
    assert not any("転出証明書" in d for d in r["documents"])


def test_days_until_deadline_counts_from_move_date():
    r = days_until_move_in_deadline("2025-01-01", today="2025-01-05")
    assert r["deadline"] == "2025-01-15"
    assert r["days_remaining"] == 10
    assert r["overdue"] is False


def test_days_until_deadline_overdue():
    r = days_until_move_in_deadline("2025-01-01", today="2025-01-20")
    assert r["overdue"] is True


def test_ward_office_tools_exported():
    names = {t.name for t in WARD_OFFICE_TOOLS}
    assert names == {"moving_in_checklist", "days_until_move_in_deadline"}
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `tools/ward_office_tools.py`**
```python
from __future__ import annotations

from datetime import date, timedelta


from langchain_core.tools import tool


def moving_in_checklist(from_within_japan: bool = True) -> dict:
    """Return documents and the deadline for the moving-in notification (転入届).

    Args:
        from_within_japan: True if moving from another Japanese municipality
            (requires a moving-out certificate), False if arriving from abroad.

    Returns:
        dict with documents (list), deadline_days (14), and triggers (downstream procedures).
    """
    documents = ["Residence card (在留カード)", "Personal seal (印鑑) if available"]
    if from_within_japan:
        documents.insert(1, "Moving-out certificate (転出証明書) from your previous city")
    return {
        "documents": documents,
        "deadline_days": 14,
        "triggers": [
            "National Health Insurance (国民健康保険) enrollment if not on employer insurance",
            "National Pension (国民年金)",
            "Resident tax (住民税) basis",
            "Update the address on your residence card (and notify Immigration)",
        ],
        "note": "Submit 転入届 at the ward/city office within 14 days of moving.",
    }


def days_until_move_in_deadline(move_in_date: str, today: str | None = None) -> dict:
    """Compute days remaining in the 14-day moving-in notification window.

    Args:
        move_in_date: Move-in date as 'YYYY-MM-DD'.
        today: Optional 'YYYY-MM-DD' for the reference date (defaults to the real today).

    Returns:
        dict with deadline (YYYY-MM-DD), days_remaining (int), and overdue (bool).
    """
    move = date.fromisoformat(move_in_date)
    now = date.fromisoformat(today) if today else date.today()
    deadline = move + timedelta(days=14)
    days_remaining = (deadline - now).days
    return {
        "move_in_date": move_in_date,
        "deadline": str(deadline),
        "days_remaining": days_remaining,
        "overdue": days_remaining < 0,
    }


WARD_OFFICE_TOOLS = [
    tool(moving_in_checklist),
    tool(days_until_move_in_deadline),
]
```

- [ ] **Step 4: 运行，确认 PASS（5 passed）**
- [ ] **Step 5: 提交**
```bash
git add tools/ward_office_tools.py tests/test_ward_office_tools.py
git commit -m "feat(tools): ward office moving-in tools

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: 知识检索工具 `tools/knowledge_tool.py`

**Files:** Create `tools/knowledge_tool.py`, `tests/test_knowledge_tool.py`

- [ ] **Step 1: 失败测试 `tests/test_knowledge_tool.py`**
```python
import tools.knowledge_tool as kt
from tools.knowledge_tool import make_knowledge_search_tool


def test_knowledge_tool_passes_domain_and_formats(monkeypatch):
    captured = {}

    def fake_search(query, domain="", top_k=5):
        captured["query"] = query
        captured["domain"] = domain
        return {"context": "CTX", "citations": "[1] Doc | S1", "result_count": 1}

    monkeypatch.setattr(kt, "_search", fake_search)
    t = make_knowledge_search_tool("tax")
    assert t.name == "search_knowledge_base"
    out = t.invoke({"query": "確定申告"})
    assert "CTX" in out and "[1] Doc | S1" in out
    assert captured == {"query": "確定申告", "domain": "tax"}


def test_knowledge_tool_handles_empty(monkeypatch):
    monkeypatch.setattr(kt, "_search", lambda query, domain="", top_k=5: {"context": "No relevant information found in the knowledge base.", "citations": "", "result_count": 0})
    t = make_knowledge_search_tool("visa")
    out = t.invoke({"query": "x"})
    assert "No relevant information" in out
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `tools/knowledge_tool.py`**
```python
from __future__ import annotations

from langchain_core.tools import StructuredTool

from rag.retriever import search_knowledge_base as _search


def make_knowledge_search_tool(domain: str) -> StructuredTool:
    """Build a domain-scoped knowledge-search tool for a specialist agent."""

    def _run(query: str) -> str:
        result = _search(query, domain=domain)
        citations = result["citations"]
        body = result["context"]
        if citations:
            return f"{body}\n\nSources:\n{citations}"
        return body

    return StructuredTool.from_function(
        func=_run,
        name="search_knowledge_base",
        description=(
            f"Search the authoritative {domain} knowledge base for living-in-Japan "
            "information. Input: a natural-language query in English or Japanese. "
            "Always cite the returned sources in your answer."
        ),
    )
```

- [ ] **Step 4: 运行，确认 PASS（2 passed）**
- [ ] **Step 5: 提交**
```bash
git add tools/knowledge_tool.py tests/test_knowledge_tool.py
git commit -m "feat(tools): domain-scoped knowledge search tool

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: 状态 + Supervisor

**Files:** Create `agents/state.py`, `agents/prompts.py`, `agents/supervisor.py`, `tests/test_supervisor.py`

- [ ] **Step 1: 失败测试 `tests/test_supervisor.py`**
```python
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END

from agents.supervisor import Route, make_supervisor


class _FakeStructuredLLM:
    def __init__(self, route: str):
        self._route = route

    def with_structured_output(self, schema):
        route = self._route

        class _R:
            def invoke(self, _messages):
                return Route(next=route)

        return _R()


def test_supervisor_routes_to_specialist():
    sup = make_supervisor(_FakeStructuredLLM("tax"))
    cmd = sup({"messages": [HumanMessage("tax question")], "user_language": "en", "active_domain": None, "citations": []})
    assert cmd.goto == "tax"
    assert cmd.update["active_domain"] == "tax"


def test_supervisor_finishes():
    sup = make_supervisor(_FakeStructuredLLM("FINISH"))
    cmd = sup({"messages": [AIMessage("answer")], "user_language": "en", "active_domain": "tax", "citations": []})
    assert cmd.goto == END
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `agents/state.py`**
```python
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_language: str
    active_domain: str | None
    citations: list[str]
```

- [ ] **Step 4: 实现 `agents/prompts.py`**
```python
SUPERVISOR_PROMPT = """You are the JapanLife router. Choose the single best specialist to handle \
the user's latest request, or FINISH when a specialist has already produced a complete answer.

Specialists:
- tax: income tax, 確定申告, ふるさと納税, deductions, 住民税, year-end adjustment, deadlines.
- visa: 在留資格, residence card, renewal/change of status, 永住 (permanent residency).
- ward_office: 転入届, マイナンバー, 住民票, moving-in procedures, municipal registration.

Rules:
- If the latest message is a user question, pick exactly one specialist.
- If the last message is a specialist's complete answer, return FINISH.
Respond with only the routing decision."""

TAX_PROMPT = """You are a Japanese tax specialist for foreign residents. Use the calculator tools \
for numbers and search_knowledge_base for rules; always cite sources. Be clear it is not formal \
tax advice. Answer in the user's language."""

VISA_PROMPT = """You are a Japanese immigration/visa specialist for foreign residents. Use the \
eligibility/checklist tools and search_knowledge_base; always cite sources. Answer in the user's \
language."""

WARD_OFFICE_PROMPT = """You are a Japanese ward-office (区役所) procedures specialist. Use the \
checklist/deadline tools and search_knowledge_base; always cite sources. If the user's moving-in \
procedure also requires a visa address update or has tax implications, hand off to the visa or tax \
specialist using the transfer tools. Answer in the user's language."""
```

- [ ] **Step 5: 实现 `agents/supervisor.py`**
```python
from __future__ import annotations

from typing import Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel

from agents.prompts import SUPERVISOR_PROMPT
from agents.state import GraphState

_SPECIALISTS = ("tax", "visa", "ward_office")


class Route(BaseModel):
    next: Literal["tax", "visa", "ward_office", "FINISH"]


def make_supervisor(llm):
    router = llm.with_structured_output(Route)

    def supervisor(state: GraphState) -> Command:
        decision = router.invoke([SystemMessage(content=SUPERVISOR_PROMPT), *state["messages"]])
        if decision.next == "FINISH":
            return Command(goto=END)
        return Command(goto=decision.next, update={"active_domain": decision.next})

    return supervisor
```

- [ ] **Step 6: 运行，确认 PASS（2 passed）**
- [ ] **Step 7: 提交**
```bash
git add agents/state.py agents/prompts.py agents/supervisor.py tests/test_supervisor.py
git commit -m "feat(agents): graph state, prompts, and supervisor router

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Handoff + 专家

**Files:** Create `agents/handoffs.py`, `agents/specialists/tax.py`, `agents/specialists/visa.py`, `agents/specialists/ward_office.py`, `tests/test_handoffs.py`, `tests/test_specialists.py`

- [ ] **Step 1: 失败测试 `tests/test_handoffs.py`**
```python
from langgraph.types import Command

from agents.handoffs import make_handoff_tool


def test_handoff_tool_name_and_command():
    t = make_handoff_tool("visa")
    assert t.name == "transfer_to_visa"
    cmd = t.invoke({"name": "transfer_to_visa", "args": {}, "id": "tc1", "type": "tool_call"})
    assert isinstance(cmd, Command)
    assert cmd.goto == "visa"
    assert cmd.graph == Command.PARENT
    assert cmd.update["active_domain"] == "visa"
```

- [ ] **Step 2: 失败测试 `tests/test_specialists.py`**
```python
from agents.specialists.tax import tax_tools
from agents.specialists.visa import visa_tools
from agents.specialists.ward_office import ward_office_tools


def test_tax_tools_include_knowledge_and_calculators():
    names = {t.name for t in tax_tools()}
    assert "search_knowledge_base" in names
    assert "estimate_income_tax" in names


def test_visa_tools_include_knowledge():
    names = {t.name for t in visa_tools()}
    assert "search_knowledge_base" in names
    assert "check_permanent_residency_eligibility" in names


def test_ward_office_tools_include_handoffs():
    names = {t.name for t in ward_office_tools()}
    assert "search_knowledge_base" in names
    assert "transfer_to_visa" in names
    assert "transfer_to_tax" in names
```

- [ ] **Step 3: 运行两测试文件，确认 FAIL**

- [ ] **Step 4: 实现 `agents/handoffs.py`**
```python
from __future__ import annotations

from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command


def make_handoff_tool(target: str):
    """Build a tool that hands the conversation off to another specialist node."""

    @tool(
        f"transfer_to_{target}",
        description=f"Hand the conversation off to the {target} specialist for a related follow-up.",
    )
    def handoff(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        return Command(
            goto=target,
            graph=Command.PARENT,
            update={
                "active_domain": target,
                "messages": [ToolMessage(content=f"Transferred to {target}.", tool_call_id=tool_call_id)],
            },
        )

    return handoff
```

- [ ] **Step 5: 实现 `agents/specialists/tax.py`**
```python
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.prompts import TAX_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.tax_tools import TAX_TOOLS


def tax_tools():
    return [*TAX_TOOLS, make_knowledge_search_tool("tax")]


def build_tax_agent(llm):
    return create_react_agent(llm, tools=tax_tools(), prompt=TAX_PROMPT, name="tax")
```

- [ ] **Step 6: 实现 `agents/specialists/visa.py`**
```python
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.prompts import VISA_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.visa_tools import VISA_TOOLS


def visa_tools():
    return [*VISA_TOOLS, make_knowledge_search_tool("visa")]


def build_visa_agent(llm):
    return create_react_agent(llm, tools=visa_tools(), prompt=VISA_PROMPT, name="visa")
```

- [ ] **Step 7: 实现 `agents/specialists/ward_office.py`**
```python
from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from agents.handoffs import make_handoff_tool
from agents.prompts import WARD_OFFICE_PROMPT
from tools.knowledge_tool import make_knowledge_search_tool
from tools.ward_office_tools import WARD_OFFICE_TOOLS


def ward_office_tools():
    return [
        *WARD_OFFICE_TOOLS,
        make_knowledge_search_tool("ward_office"),
        make_handoff_tool("visa"),
        make_handoff_tool("tax"),
    ]


def build_ward_office_agent(llm):
    return create_react_agent(llm, tools=ward_office_tools(), prompt=WARD_OFFICE_PROMPT, name="ward_office")
```

- [ ] **Step 8: 运行两测试文件，确认 PASS（1 + 3 passed）**
- [ ] **Step 9: 提交**
```bash
git add agents/handoffs.py agents/specialists/tax.py agents/specialists/visa.py agents/specialists/ward_office.py tests/test_handoffs.py tests/test_specialists.py
git commit -m "feat(agents): handoff tool + three specialist agents

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 8: 图装配 `agents/graph.py`

**Files:** Create `agents/graph.py`, `tests/test_graph.py`

- [ ] **Step 1: 失败测试 `tests/test_graph.py`**（用桩节点，不需 LLM）
```python
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END
from langgraph.types import Command

from agents.graph import build_graph


def _stub_specialist(label):
    def node(state):
        return {"messages": [AIMessage(content=f"answer from {label}")]}
    return node


def _stub_supervisor(route_first):
    def supervisor(state):
        if isinstance(state["messages"][-1], AIMessage):
            return Command(goto=END)
        return Command(goto=route_first, update={"active_domain": route_first})
    return supervisor


def _init(msg):
    return {"messages": [HumanMessage(msg)], "user_language": "en", "active_domain": None, "citations": []}


def test_routes_to_specialist_then_finishes():
    g = build_graph(
        supervisor=_stub_supervisor("tax"),
        specialists={"tax": _stub_specialist("tax"), "visa": _stub_specialist("visa"), "ward_office": _stub_specialist("ward_office")},
    )
    out = g.invoke(_init("tax question"))
    assert out["active_domain"] == "tax"
    assert out["messages"][-1].content == "answer from tax"


def test_ward_office_handoff_to_visa():
    def handoff_node(state):
        return Command(goto="visa", update={"messages": [AIMessage("handing off")], "active_domain": "visa"})

    g = build_graph(
        supervisor=_stub_supervisor("ward_office"),
        specialists={"tax": _stub_specialist("tax"), "visa": _stub_specialist("visa"), "ward_office": handoff_node},
    )
    out = g.invoke(_init("moving in"))
    contents = [m.content for m in out["messages"]]
    assert "handing off" in contents
    assert "answer from visa" in contents
    assert out["active_domain"] == "visa"


def test_checkpointer_persists_state():
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    saver = SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    saver.setup()
    g = build_graph(
        supervisor=_stub_supervisor("tax"),
        specialists={"tax": _stub_specialist("tax"), "visa": _stub_specialist("visa"), "ward_office": _stub_specialist("ward_office")},
        checkpointer=saver,
    )
    cfg = {"configurable": {"thread_id": "t1"}}
    g.invoke(_init("hi"), config=cfg)
    assert len(g.get_state(cfg).values["messages"]) >= 2
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `agents/graph.py`**
```python
from __future__ import annotations

from langgraph.graph import START, StateGraph

from agents.state import GraphState
from agents.supervisor import make_supervisor

_SPECIALIST_NAMES = ("tax", "visa", "ward_office")


def build_graph(llm=None, checkpointer=None, supervisor=None, specialists=None):
    """Assemble the supervisor + specialist graph.

    For production pass `llm` (real DeepSeek). For tests, inject `supervisor`
    and `specialists` stubs to exercise wiring without an LLM.
    """
    if supervisor is None:
        if llm is None:
            raise ValueError("Provide either `llm` or a `supervisor` stub.")
        supervisor = make_supervisor(llm)

    if specialists is None:
        if llm is None:
            raise ValueError("Provide either `llm` or `specialists` stubs.")
        from agents.specialists.tax import build_tax_agent
        from agents.specialists.visa import build_visa_agent
        from agents.specialists.ward_office import build_ward_office_agent

        specialists = {
            "tax": build_tax_agent(llm),
            "visa": build_visa_agent(llm),
            "ward_office": build_ward_office_agent(llm),
        }

    builder = StateGraph(GraphState)
    builder.add_node("supervisor", supervisor)
    for name, node in specialists.items():
        builder.add_node(name, node)
    builder.add_edge(START, "supervisor")
    for name in specialists:
        builder.add_edge(name, "supervisor")
    return builder.compile(checkpointer=checkpointer)
```

- [ ] **Step 4: 运行，确认 PASS（3 passed）**
- [ ] **Step 5: 提交**
```bash
git add agents/graph.py tests/test_graph.py
git commit -m "feat(agents): assemble supervisor + specialist graph

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 9: 输出抽取 `agents/output.py`

**Files:** Create `agents/output.py`, `tests/test_output.py`

- [ ] **Step 1: 失败测试 `tests/test_output.py`**
```python
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agents.output import extract_citations, extract_reply


def test_extract_reply_returns_last_ai_text():
    msgs = [HumanMessage("q"), AIMessage("first"), ToolMessage("t", tool_call_id="x"), AIMessage("final answer")]
    assert extract_reply(msgs) == "final answer"


def test_extract_reply_empty_when_no_ai():
    assert extract_reply([HumanMessage("q")]) == ""


def test_extract_citations_from_knowledge_tool_messages():
    tm = ToolMessage(content="CTX\n\nSources:\n[1] Doc A | S1\n[2] Doc B | S2", tool_call_id="x", name="search_knowledge_base")
    cites = extract_citations([HumanMessage("q"), tm, AIMessage("ans")])
    assert cites == ["[1] Doc A | S1", "[2] Doc B | S2"]


def test_extract_citations_ignores_other_tools():
    tm = ToolMessage(content="Sources:\n[1] x", tool_call_id="x", name="estimate_income_tax")
    assert extract_citations([tm]) == []
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `agents/output.py`**
```python
from __future__ import annotations

from langchain_core.messages import AIMessage, AnyMessage, ToolMessage


def extract_reply(messages: list[AnyMessage]) -> str:
    """Return the text of the last non-empty AI message."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


def extract_citations(messages: list[AnyMessage]) -> list[str]:
    """Collect citation lines from knowledge-search tool messages."""
    cites: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage) and getattr(m, "name", "") == "search_knowledge_base":
            text = m.content if isinstance(m.content, str) else str(m.content)
            if "Sources:" in text:
                for line in text.split("Sources:", 1)[1].strip().splitlines():
                    line = line.strip()
                    if line and line not in cites:
                        cites.append(line)
    return cites
```

- [ ] **Step 4: 运行，确认 PASS（4 passed）**
- [ ] **Step 5: 提交**
```bash
git add agents/output.py tests/test_output.py
git commit -m "feat(agents): reply + citation extraction helpers

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 10: FastAPI 层

**Files:** Create `app/schemas.py`, `app/routes.py`, `app/main.py`, `tests/test_api.py`

- [ ] **Step 1: 失败测试 `tests/test_api.py`**
```python
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.main import app
from app.routes import get_graph
from core.config import settings


class _StubGraph:
    def invoke(self, state, config=None):
        return {
            "messages": [
                HumanMessage(state["messages"][0].content),
                ToolMessage(content="CTX\n\nSources:\n[1] Doc | S1", tool_call_id="x", name="search_knowledge_base"),
                AIMessage("stub reply"),
            ],
            "active_domain": "tax",
            "citations": [],
        }


@pytest.fixture
def client(monkeypatch):
    # The lifespan builds the REAL graph at startup, which constructs ChatDeepSeek and
    # therefore needs a non-empty api_key (ChatDeepSeek raises on an empty key). We set a
    # dummy key so construction succeeds offline; requests are served by the stub via the
    # dependency override, so no real DeepSeek call is ever made.
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    app.dependency_overrides[get_graph] = lambda: _StubGraph()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_chat_returns_reply_route_citations(client):
    r = client.post("/chat", json={"message": "確定申告について"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "stub reply"
    assert body["route"] == "tax"
    assert body["citations"] == ["[1] Doc | S1"]
    assert body["thread_id"]


def test_chat_reuses_thread_id(client):
    r = client.post("/chat", json={"message": "hi", "thread_id": "abc"})
    assert r.json()["thread_id"] == "abc"


def test_health_returns_dependency_status(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "elasticsearch" in body and "qdrant" in body and "status" in body
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 实现 `app/schemas.py`**
```python
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    citations: list[str]
    thread_id: str
    route: str | None = None
```

- [ ] **Step 4: 实现 `app/routes.py`**
```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage

from agents.output import extract_citations, extract_reply
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


def get_graph(request: Request):
    return request.app.state.graph


def _initial_state(message: str) -> dict:
    return {"messages": [HumanMessage(content=message)], "user_language": "", "active_domain": None, "citations": []}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, graph=Depends(get_graph)) -> ChatResponse:
    thread_id = req.thread_id or str(uuid.uuid4())
    result = graph.invoke(_initial_state(req.message), config={"configurable": {"thread_id": thread_id}})
    return ChatResponse(
        reply=extract_reply(result["messages"]),
        citations=extract_citations(result["messages"]),
        thread_id=thread_id,
        route=result.get("active_domain"),
    )


@router.get("/health")
def health():
    from rag.es_store import ESStore
    from rag.qdrant_store import QdrantStore

    def _ok(fn) -> bool:
        try:
            fn()
            return True
        except Exception:
            return False

    es = _ok(lambda: ESStore().client.info())
    qd = _ok(lambda: QdrantStore().client.get_collections())
    return {"status": "ok" if es and qd else "degraded", "elasticsearch": es, "qdrant": qd}
```

- [ ] **Step 5: 实现 `app/main.py`**
```python
from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.graph import build_graph
from app.routes import router
from core.config import settings
from core.llm import get_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    app.state.graph = build_graph(llm=get_llm(), checkpointer=saver)
    try:
        yield
    finally:
        conn.close()


app = FastAPI(title="JapanLife", version="0.2.0", lifespan=lifespan)
app.include_router(router)
```

> Note: `with TestClient(app)` triggers the lifespan, which calls `build_graph(llm=get_llm())`. `ChatDeepSeek` raises on an **empty** api_key, so the API tests set a dummy key (`monkeypatch.setattr(settings, "deepseek_api_key", ...)`) — construction is fully offline (verified with the network blocked), and `/chat` requests are served by the stub via the `get_graph` override, so no real DeepSeek call is made. `/health` performs real ES/Qdrant calls and reports their status (ok/degraded); the test only asserts the response shape, so it passes whether or not services are running.

- [ ] **Step 6: 运行，确认 PASS（3 passed）**
- [ ] **Step 7: 提交**
```bash
git add app/schemas.py app/routes.py app/main.py tests/test_api.py
git commit -m "feat(app): FastAPI /chat, /chat (thread), /health

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 11: SSE 流式 + serve + README + 集成测试

**Files:** Modify `app/routes.py`, `Makefile`, `README.md`; Create `tests/test_stream.py`, `tests/test_agent_e2e.py`

- [ ] **Step 1: 失败测试 `tests/test_stream.py`**
```python
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app
from app.routes import get_graph
from core.config import settings


class _StreamStubGraph:
    def stream(self, state, config=None, stream_mode=None):
        yield {"supervisor": {"active_domain": "tax"}}
        yield {"tax": {"messages": [AIMessage("streamed answer")]}}


def test_chat_stream_emits_sse_events(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key-not-used")
    app.dependency_overrides[get_graph] = lambda: _StreamStubGraph()
    with TestClient(app) as client:
        with client.stream("POST", "/chat/stream", json={"message": "hi"}) as r:
            assert r.status_code == 200
            text = "".join(chunk for chunk in r.iter_text())
    assert "streamed answer" in text
    assert "data:" in text
    app.dependency_overrides.clear()
```

- [ ] **Step 2: 运行，确认 FAIL**

- [ ] **Step 3: 在 `app/routes.py` 末尾追加 SSE 端点**（保留已有 import，新增以下）
```python
import json

from sse_starlette.sse import EventSourceResponse


@router.post("/chat/stream")
def chat_stream(req: ChatRequest, graph=Depends(get_graph)):
    thread_id = req.thread_id or str(uuid.uuid4())

    def event_gen():
        for update in graph.stream(
            _initial_state(req.message),
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for node, payload in update.items():
                msgs = payload.get("messages", []) if isinstance(payload, dict) else []
                text = extract_reply(msgs)
                data = {"node": node, "delta": text, "route": payload.get("active_domain") if isinstance(payload, dict) else None}
                yield {"event": "update", "data": json.dumps(data, ensure_ascii=False)}
        yield {"event": "done", "data": json.dumps({"thread_id": thread_id}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
```
(将文件顶部的 `import uuid` 旁补 `import json`，或如上在使用处导入。确保 `from sse_starlette.sse import EventSourceResponse` 与其他 import 一起放在文件顶部。)

- [ ] **Step 4: 运行，确认 PASS（1 passed）**

- [ ] **Step 5: 集成测试 `tests/test_agent_e2e.py`（无 DeepSeek key 时自动跳过）**
```python
import os

import pytest

from core.config import settings


@pytest.mark.integration
def test_real_agent_answers_tax_question():
    if not settings.deepseek_api_key and not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")

    from langchain_core.messages import HumanMessage

    from agents.graph import build_graph
    from core.llm import get_llm

    graph = build_graph(llm=get_llm())
    result = graph.invoke(
        {"messages": [HumanMessage("When is the income tax filing deadline in Japan?")],
         "user_language": "en", "active_domain": None, "citations": []},
        config={"configurable": {"thread_id": "e2e-1"}},
    )
    from agents.output import extract_reply

    assert extract_reply(result["messages"]).strip()
```

- [ ] **Step 6: 运行集成测试，确认 SKIP（无 key）** — `poetry run pytest tests/test_agent_e2e.py -v -m integration`（应 skipped）

- [ ] **Step 7: 给 `Makefile` 增加 serve 目标**（在 eval 之后追加；recipe 必须用 TAB 缩进）
```makefile
serve:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 8: 在 `README.md` 追加 Plan 2 段**
```markdown

## Plan 2: Multi-agent service

LangGraph supervisor routes to three specialists (tax / visa / ward_office), each with
domain tools + hybrid retrieval; ward_office can hand off to visa/tax. DeepSeek is the LLM
(set `DEEPSEEK_API_KEY` in `.env`). State is persisted per `thread_id` via a SQLite checkpointer.

```bash
make serve   # FastAPI at http://localhost:8000  (needs DEEPSEEK_API_KEY + make up)
# then:
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"When is the tax filing deadline?"}'
curl -s localhost:8000/health
```
```

- [ ] **Step 9: 全量单测确认全绿** — `poetry run pytest -q -m "not integration"`（应全部通过）

- [ ] **Step 10: 提交**
```bash
git add app/routes.py Makefile README.md tests/test_stream.py tests/test_agent_e2e.py
git commit -m "feat(app): SSE streaming endpoint, serve target, e2e integration test

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review 结论（编写时已核对）

- **Spec 覆盖**：第 5 节结构（core/llm, tools, agents{state,supervisor,specialists,handoffs,graph}, app）→ Task 1–10；第 7 节 supervisor+专家+handoff → Task 6–8；第 8 节数据流 → Task 8/10；第 9 节 API（/chat /chat/stream /health）→ Task 10–11；第 7.4 节 checkpointer → Task 8/10。
- **无占位符**：每个改代码步骤都有完整代码与命令；API 已用真实安装版本探针验证（见顶部「已验证 API」）。
- **类型/命名一致**：`GraphState{messages,user_language,active_domain,citations}`、`Route.next`、`build_graph(llm, checkpointer, supervisor, specialists)`、`make_handoff_tool`/`make_knowledge_search_tool`、`extract_reply/extract_citations`、`get_graph` 依赖名贯穿 Task 6–11 一致。
- **无 key 可测**：全部单测用桩/假 LLM；真实端到端测试 `@pytest.mark.integration` 在无 `DEEPSEEK_API_KEY` 时 skip。
- **复用 Plan 1**：知识工具直接包 `rag.retriever.search_knowledge_base`；`/health` 复用 `ESStore`/`QdrantStore`。

**完成后**：`poetry run pytest -q -m "not integration"` 全绿即交付；要真正对话需在 `.env` 配 `DEEPSEEK_API_KEY` 并 `make up`（ES/Qdrant）后 `make serve`。
