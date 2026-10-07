from evaluation import run


def test_auc_perfect_and_tied_rankings():
    assert run.auc([(90, 1), (80, 1), (20, 0), (10, 0)]) == 1.0
    assert run.auc([(50, 1), (50, 0)]) == 0.5
    assert run.auc([(10, 1), (90, 0)]) == 0.0
    assert run.auc([(10, 1)]) is None


def test_brief_metrics_counts_cited_lines_and_invalid_numbers():
    report = """# Acme Brief

## Company Overview
Acme builds payment software for small businesses in India [1].
It was founded in 2015 and is headquartered in Pune [2, 7].
The company is known for its friendly engineering culture overall.

## Sources
[1] https://example.com/a
[2] https://example.com/b

## Verification Notes
No issues found.
"""
    metrics = run.brief_metrics(report, source_count=2)
    assert metrics["claim_lines"] == 3
    assert metrics["cited_lines"] == 2
    assert metrics["citations"] == 3
    assert metrics["invalid_citations"] == 1  # [7] has no matching source
    assert metrics["reviewer_found_issues"] is False


def test_dataset_is_labelled_and_filter_metrics_are_consistent():
    jobs = run.load_jobs()
    result = run.run_filter(jobs)
    c = result["confusion"]
    assert c["tp"] + c["fp"] + c["fn"] + c["tn"] == result["labelled"]
    assert result["relevant"] > 0
    assert all(j["label"] in (0, 1, None) for j in jobs)
