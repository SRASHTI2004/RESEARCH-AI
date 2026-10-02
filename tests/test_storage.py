from app.core import storage


def test_not_configured_when_credentials_blank(monkeypatch):
    monkeypatch.setattr("app.core.storage.settings.storage_endpoint_url", "")
    assert storage.is_configured() is False


def test_upload_skipped_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.core.storage.settings.storage_endpoint_url", "")
    assert storage.upload_report("job-1", "# report") is None


def test_get_download_url_skipped_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.core.storage.settings.storage_endpoint_url", "")
    assert storage.get_download_url("reports/job-1.md") is None


class _FakeClient:
    def __init__(self, *, bucket_exists: bool = True):
        self.bucket_exists = bucket_exists
        self.created_bucket = False
        self.put_calls: list[dict] = []
        self.presign_calls: list[dict] = []

    def head_bucket(self, Bucket):  # noqa: N803 (matches boto3's actual kwarg casing)
        if not self.bucket_exists:
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    def create_bucket(self, Bucket):  # noqa: N803
        self.created_bucket = True

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def generate_presigned_url(self, operation, Params, ExpiresIn):  # noqa: N803
        self.presign_calls.append({"operation": operation, "Params": Params, "ExpiresIn": ExpiresIn})
        return f"https://storage.example.com/{Params['Key']}?signed=1"


def _configure(monkeypatch):
    monkeypatch.setattr("app.core.storage.settings.storage_endpoint_url", "http://minio:9000")
    monkeypatch.setattr("app.core.storage.settings.storage_access_key", "key")
    monkeypatch.setattr("app.core.storage.settings.storage_secret_key", "secret")
    monkeypatch.setattr("app.core.storage.settings.storage_bucket_name", "test-bucket")


def test_upload_report_creates_bucket_if_missing(monkeypatch):
    _configure(monkeypatch)
    fake = _FakeClient(bucket_exists=False)
    monkeypatch.setattr("app.core.storage._client", lambda: fake)

    key = storage.upload_report("job-1", "# hello")

    assert key == "reports/job-1.md"
    assert fake.created_bucket is True
    assert fake.put_calls[0]["Key"] == "reports/job-1.md"
    assert fake.put_calls[0]["Body"] == b"# hello"


def test_upload_report_skips_bucket_creation_if_it_exists(monkeypatch):
    _configure(monkeypatch)
    fake = _FakeClient(bucket_exists=True)
    monkeypatch.setattr("app.core.storage._client", lambda: fake)

    storage.upload_report("job-1", "# hello")

    assert fake.created_bucket is False


def test_upload_report_returns_none_on_client_error(monkeypatch):
    _configure(monkeypatch)

    class _BoomClient(_FakeClient):
        def put_object(self, **kwargs):
            from botocore.exceptions import ClientError

            raise ClientError({"Error": {"Code": "500"}}, "PutObject")

    monkeypatch.setattr("app.core.storage._client", lambda: _BoomClient())

    assert storage.upload_report("job-1", "# hello") is None


def test_get_download_url_returns_presigned_url(monkeypatch):
    _configure(monkeypatch)
    fake = _FakeClient()
    monkeypatch.setattr("app.core.storage._client", lambda: fake)

    url = storage.get_download_url("reports/job-1.md")

    assert url == "https://storage.example.com/reports/job-1.md?signed=1"
    assert fake.presign_calls[0]["ExpiresIn"] == 3600
