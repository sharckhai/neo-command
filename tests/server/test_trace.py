from server.tracing import TraceEvent, TraceRecorder


def test_trace_recorder_captures_steps():
    recorder = TraceRecorder()
    recorder.add_step("sql.query", {"sql": "select 1"}, {"rows": 1})
    trace = recorder.snapshot()
    assert trace[0].name == "sql.query"
    assert trace[0].output["rows"] == 1
