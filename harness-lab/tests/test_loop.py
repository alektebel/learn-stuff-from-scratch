"""The phase-1 core contract: the linear loop in `harness_lab.core.loop`.

LEARN mode. The loop is the learner's work, so every core test is an `xfail`
that expects `NotImplementedError` today: while the stub stands these report
as xfailed (not failed), and once the loop is implemented they must pass. A
wrong implementation makes them hard failures, which is the point.

The infrastructure test (registration of the `mini` adapter) passes today.
"""

import json

import pytest
from eval.agents import AGENT_NAMES, MiniAgent, make_agent
from eval.contract import Budget, TaskInput
from harness_lab.core.loop import LoopBudget, run_loop
from harness_lab.llm import Completion, Message, Price, ScriptedBackend, ToolCall, Usage

CORE = pytest.mark.xfail(
    raises=NotImplementedError,
    reason="phase-1 core: the learner implements run_loop (docs/phase1.md)",
)


class FakeExec:
    def __init__(self, stdout="", exit_code=0):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = ""
        self.timed_out = False


class FakeSandbox:
    """Structural stand-in for DockerSandbox: records commands, replays stdout."""

    def __init__(self, outputs=()):
        self.commands: list[str] = []
        self._outputs = list(outputs)

    def exec(self, command, timeout=120.0):
        self.commands.append(command)
        return FakeExec(self._outputs.pop(0) if self._outputs else "")


def bash_turn(command, *, call_id="c1", usage=None):
    call = ToolCall(id=call_id, name="bash", arguments=json.dumps({"command": command}))
    return Completion(
        message=Message(role="assistant", content="", tool_calls=(call,)),
        usage=usage or Usage(),
        stop_reason="tool_use",
    )


def final_turn(text="done", *, usage=None):
    return Completion(
        message=Message(role="assistant", content=text),
        usage=usage or Usage(),
    )


# --- adapter registration (infrastructure, passes today) ---------------------


def test_mini_agent_is_registered():
    assert "mini" in AGENT_NAMES
    assert make_agent("mini", None).name == "mini"
    assert MiniAgent().config()["model"]  # a value or "<unset>", never empty


# --- the loop contract -------------------------------------------------------


@CORE
def test_loop_completes_after_a_tool_call():
    model = ScriptedBackend([bash_turn("echo hi"), final_turn("done")])
    sandbox = FakeSandbox(outputs=["hi\n"])
    result = run_loop(model, "say hi", sandbox, LoopBudget(max_steps=10))
    assert result.stop_reason == "completed"
    assert result.turns == 2
    assert result.tool_calls == 1
    assert sandbox.commands == ["echo hi"]


@CORE
def test_loop_reports_token_totals():
    model = ScriptedBackend(
        [
            bash_turn("echo hi", usage=Usage(input_tokens=10, output_tokens=5, cached_tokens=2)),
            final_turn(usage=Usage(input_tokens=12, output_tokens=3)),
        ]
    )
    result = run_loop(model, "s", FakeSandbox(), LoopBudget(max_steps=10))
    assert (result.input_tokens, result.output_tokens, result.cached_tokens) == (22, 8, 2)


@CORE
def test_loop_stops_at_max_steps():
    model = ScriptedBackend([bash_turn(f"echo {i}") for i in range(5)])
    sandbox = FakeSandbox()
    result = run_loop(model, "s", sandbox, LoopBudget(max_steps=2))
    assert result.stop_reason == "max_steps"
    assert result.turns == 2
    assert sandbox.commands == ["echo 0", "echo 1"]


@CORE
def test_loop_stops_at_max_cost():
    # 1 token = 1.0 EUR, so one input token reaches a cap of 1.0.
    model = ScriptedBackend([bash_turn("echo hi", usage=Usage(input_tokens=1))],
                            price=Price(input_per_mtok=1_000_000))
    sandbox = FakeSandbox()
    result = run_loop(model, "s", sandbox, LoopBudget(max_steps=10, max_cost_eur=1.0))
    assert result.stop_reason == "max_cost"
    assert result.turns == 1
    assert result.cost_eur == pytest.approx(1.0)


@CORE
def test_loop_reports_model_error_when_script_exhausts():
    result = run_loop(ScriptedBackend([]), "s", FakeSandbox(), LoopBudget())
    assert result.stop_reason == "model_error"
    assert result.error


@CORE
def test_loop_history_is_unpruned():
    model = ScriptedBackend([bash_turn("echo hi"), final_turn()])
    run_loop(model, "s", FakeSandbox(outputs=["hi\n"]), LoopBudget(max_steps=10))
    first, second = model.requests[0][0], model.requests[1][0]
    assert second[: len(first)] == first  # every request extends the last
    assert second[-1].role == "tool" and second[-1].tool_call_id == "c1"
    assert "hi" in second[-1].content  # the sandbox output reached the model
    assert model.requests[0][1][0].name == "bash"  # the bash tool was advertised


@CORE
def test_loop_malformed_tool_arguments_do_not_crash():
    bad = Completion(
        message=Message(
            role="assistant",
            tool_calls=(ToolCall(id="c1", name="bash", arguments="{not json"),),
        )
    )
    model = ScriptedBackend([bad, final_turn()])
    sandbox = FakeSandbox()
    result = run_loop(model, "s", sandbox, LoopBudget(max_steps=10))
    assert result.stop_reason == "completed"
    assert sandbox.commands == []  # nothing was executed on unparseable arguments


@CORE
def test_mini_agent_maps_the_loop_result_to_an_agent_result():
    agent = MiniAgent(model_factory=lambda: ScriptedBackend([final_turn(usage=Usage(4, 6))]))
    out = agent.run(TaskInput(statement="s"), FakeSandbox(), Budget(max_steps=5), seed=0)
    assert out.stop_reason == "completed"
    assert (out.turns, out.input_tokens, out.output_tokens) == (1, 4, 6)
