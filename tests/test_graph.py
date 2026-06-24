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
