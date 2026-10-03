from datetime import UTC, datetime, timedelta

from app.models.job import Job, SourceRun
from app.repositories import job_repository as repo
from app.services import job_ingest_service as ingest
from tests.factories import FakeSource, make_posting


def test_ingest_stores_new_jobs_with_filter_and_flags(db_session, profile):
    good = make_posting()
    senior = make_posting(external_id="acme:2", title="Senior Software Engineer")
    scammy = make_posting(
        external_id="acme:3",
        title="Junior Developer",
        description=f"{make_posting().description} Contact us on WhatsApp.",
    )
    summary, created = ingest.run_ingest(
        db_session, [FakeSource("greenhouse", [good, senior, scammy])], profile
    )

    assert summary.new == 3 and summary.new_passing == 2
    by_title = {j.title: j for j in created}
    assert by_title["Software Engineer"].passed_prefilter
    assert by_title["Software Engineer"].rule_score > 0
    assert not by_title["Senior Software Engineer"].passed_prefilter
    assert "seniority" in by_title["Senior Software Engineer"].prefilter_reason
    assert any("WhatsApp" in f for f in by_title["Junior Developer"].red_flags)


def test_second_run_only_updates_last_seen(db_session, profile):
    source = FakeSource("greenhouse", [make_posting()])
    ingest.run_ingest(db_session, [source], profile)
    first = db_session.query(Job).one()
    first_seen = first.first_seen_at

    summary, created = ingest.run_ingest(db_session, [source], profile, force=True)

    assert created == [] and summary.new == 0 and summary.updated == 1
    job = db_session.query(Job).one()
    assert job.first_seen_at == first_seen
    assert job.last_seen_at >= first_seen


def test_dedupe_prefers_official_board_over_aggregator(db_session, profile):
    aggregator_copy = make_posting(
        source="remotive",
        external_id="777",
        url="https://remotive.com/remote-jobs/x-777",
        official_source=False,
        description="short",
    )
    official = make_posting(title="Software Engineer (Remote)")

    ingest.run_ingest(
        db_session, [FakeSource("remotive", [aggregator_copy]), FakeSource("greenhouse", [official])], profile
    )

    job = db_session.query(Job).one()
    assert job.source == "greenhouse" and job.official_source is True


def test_official_listing_seen_later_replaces_aggregator_copy(db_session, profile):
    aggregator_copy = make_posting(
        source="remotive", external_id="777", url="https://remotive.com/x", official_source=False
    )
    ingest.run_ingest(db_session, [FakeSource("remotive", [aggregator_copy])], profile)
    ingest.run_ingest(db_session, [FakeSource("greenhouse", [make_posting()])], profile)

    job = db_session.query(Job).one()
    assert job.source == "greenhouse"
    assert job.url.startswith("https://boards.greenhouse.io/")


def test_failing_source_is_isolated_and_recorded(db_session, profile):
    summary, created = ingest.run_ingest(
        db_session,
        [
            FakeSource("remoteok", error=RuntimeError("503 Service Unavailable")),
            FakeSource("lever", [make_posting(source="lever")]),
        ],
        profile,
    )

    assert len(created) == 1
    assert summary.sources_failed == {"remoteok": "503 Service Unavailable"}
    runs = {r.source: r for r in repo.latest_runs(db_session)}
    assert runs["remoteok"].status == "error" and "503" in runs["remoteok"].message
    assert runs["lever"].status == "ok" and runs["lever"].new_count == 1


def test_min_interval_skips_recently_fetched_source_unless_forced(db_session, profile):
    db_session.add(
        SourceRun(source="remotive", status="ok", started_at=datetime.now(UTC) - timedelta(hours=1))
    )
    db_session.commit()
    source = FakeSource("remotive", [make_posting(source="remotive", official_source=False)])
    source.min_interval_hours = 8

    summary, _ = ingest.run_ingest(db_session, [source], profile)
    assert source.calls == 0 and "remotive" in summary.sources_skipped

    ingest.run_ingest(db_session, [source], profile, force=True)
    assert source.calls == 1


def test_unconfigured_source_is_skipped(db_session, profile):
    source = FakeSource("adzuna", [make_posting()])
    source.is_configured = lambda: False  # type: ignore[method-assign]
    summary, _ = ingest.run_ingest(db_session, [source], profile)
    assert source.calls == 0 and summary.sources_skipped == {"adzuna": "not configured"}


def test_refilter_applies_updated_profile(db_session, profile):
    ingest.run_ingest(
        db_session, [FakeSource("greenhouse", [make_posting(location="Chennai, India")])], profile
    )
    assert db_session.query(Job).one().passed_prefilter

    profile.locations.accept_any_india_city = False
    assert ingest.refilter_all(db_session, profile) == 1
    assert not db_session.query(Job).one().passed_prefilter


def test_postings_without_title_or_url_are_dropped():
    kept = ingest.dedupe([make_posting(url=""), make_posting(title="", external_id="2"), make_posting()])
    assert len(kept) == 1
