from jobly.commands.pipeline import determine_pipeline_status


def test_large_enrichment_backlog_does_not_fail_pipeline():
    assert determine_pipeline_status(
        crawl_failures=0,
        enrichment_failures=0,
        enrichment_backlog=95_000,
    ) == "success"


def test_stage_failures_produce_partial_success():
    assert determine_pipeline_status(
        crawl_failures=1,
        enrichment_failures=0,
        enrichment_backlog=0,
    ) == "partial_success"
