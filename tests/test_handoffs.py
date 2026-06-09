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
