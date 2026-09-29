from app.dashboard import render_dashboard


def test_dashboard_renders_exactly_six_required_panels() -> None:
    html = render_dashboard(records=[])

    for title in (
        "Latency &amp; TTFT",
        "Request traffic",
        "Errors &amp; retrieval",
        "Cost",
        "Tokens",
        "Quality proxy",
    ):
        assert title in html
    assert html.count('<article class="panel') == 6
    assert "Last 60 minutes" in html
    assert "Refresh 30s" in html
