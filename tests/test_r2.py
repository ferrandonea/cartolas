"""Tests unitarios para cartolas/r2.py."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cartolas import r2


class TestGetR2Client:
    def test_returns_none_when_missing_credentials(self, caplog):
        with patch.multiple(
            "cartolas.r2.config",
            R2_ENDPOINT_URL="",
            R2_BUCKET_NAME="",
            R2_ACCESS_KEY_ID="",
            R2_SECRET_ACCESS_KEY="",
        ):
            with caplog.at_level(logging.WARNING, logger="cartolas.r2"):
                result = r2.get_r2_client()

        assert result is None
        assert "Credenciales R2 no configuradas" in caplog.text

    def test_returns_client_when_credentials_present(self):
        mock_client = MagicMock()
        with patch.multiple(
            "cartolas.r2.config",
            R2_ENDPOINT_URL="https://endpoint.example.com",
            R2_BUCKET_NAME="my-bucket",
            R2_ACCESS_KEY_ID="key-id",
            R2_SECRET_ACCESS_KEY="secret-key",
        ), patch("boto3.client", return_value=mock_client):
            result = r2.get_r2_client()

        assert result is mock_client


class TestUploadToR2:
    def test_returns_true_on_success(self, tmp_path):
        parquet = tmp_path / "cartolas_2024.parquet"
        parquet.write_bytes(b"fake")
        mock_client = MagicMock()

        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.config.R2_BUCKET_NAME", "my-bucket"
        ):
            result = r2.upload_to_r2(parquet, key_prefix="yearly")

        assert result is True
        mock_client.upload_file.assert_called_once_with(
            str(parquet), "my-bucket", "yearly/cartolas_2024.parquet"
        )

    def test_returns_false_after_three_retries(self, tmp_path, caplog):
        parquet = tmp_path / "cartolas_2024.parquet"
        parquet.write_bytes(b"fake")
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("connection error")

        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.config.R2_BUCKET_NAME", "my-bucket"
        ), patch("time.sleep"), caplog.at_level(logging.WARNING, logger="cartolas.r2"):
            result = r2.upload_to_r2(parquet, key_prefix="yearly")

        assert result is False
        assert mock_client.upload_file.call_count == 3
        assert "Fallo al subir" in caplog.text

    def test_returns_false_when_client_is_none(self, tmp_path, caplog):
        parquet = tmp_path / "cartolas_2024.parquet"
        parquet.write_bytes(b"fake")

        with patch("cartolas.r2.get_r2_client", return_value=None), caplog.at_level(
            logging.WARNING, logger="cartolas.r2"
        ):
            result = r2.upload_to_r2(parquet, key_prefix="yearly")

        assert result is False
        assert "cliente no disponible" in caplog.text


class TestSyncAllToR2:
    def test_calls_upload_once_per_parquet(self, tmp_path):
        for year in (2022, 2023, 2024):
            (tmp_path / f"cartolas_{year}.parquet").write_bytes(b"fake")

        mock_client = MagicMock()
        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.upload_to_r2", return_value=True
        ) as mock_upload:
            result = r2.sync_all_to_r2(tmp_path)

        assert result is True
        assert mock_upload.call_count == 3

    def test_returns_true_when_no_parquets(self, tmp_path):
        mock_client = MagicMock()
        with patch("cartolas.r2.get_r2_client", return_value=mock_client):
            result = r2.sync_all_to_r2(tmp_path)

        assert result is True

    def test_returns_false_when_client_none(self, tmp_path):
        (tmp_path / "cartolas_2024.parquet").write_bytes(b"fake")
        with patch("cartolas.r2.get_r2_client", return_value=None):
            result = r2.sync_all_to_r2(tmp_path)

        assert result is False


class TestDownloadFromR2:
    def test_downloads_to_correct_path(self, tmp_path):
        mock_client = MagicMock()

        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.config.R2_BUCKET_NAME", "my-bucket"
        ):
            result = r2.download_from_r2(2024, tmp_path)

        assert result is True
        mock_client.download_file.assert_called_once_with(
            "my-bucket", "yearly/cartolas_2024.parquet", str(tmp_path / "cartolas_2024.parquet")
        )

    def test_returns_false_when_client_none(self, tmp_path):
        with patch("cartolas.r2.get_r2_client", return_value=None):
            result = r2.download_from_r2(2024, tmp_path)

        assert result is False

    def test_returns_false_on_client_error(self, tmp_path):
        mock_client = MagicMock()
        # ClientError debe ser una clase real para que except la evalúe sin TypeError
        FakeClientError = type("ClientError", (Exception,), {"response": {"Error": {"Code": "404"}}})
        mock_client.exceptions.ClientError = FakeClientError
        mock_client.download_file.side_effect = FakeClientError()

        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.config.R2_BUCKET_NAME", "my-bucket"
        ):
            result = r2.download_from_r2(2024, tmp_path)

        assert result is False


class TestDownloadAllFromR2:
    def test_downloads_all_objects_under_yearly_prefix(self, tmp_path):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "yearly/cartolas_2022.parquet"}, {"Key": "yearly/cartolas_2023.parquet"}]}
        ]

        with patch("cartolas.r2.get_r2_client", return_value=mock_client), patch(
            "cartolas.r2.config.R2_BUCKET_NAME", "my-bucket"
        ):
            result = r2.download_all_from_r2(tmp_path)

        assert result is True
        assert mock_client.download_file.call_count == 2
        mock_client.download_file.assert_any_call(
            "my-bucket", "yearly/cartolas_2022.parquet", str(tmp_path / "cartolas_2022.parquet")
        )
        mock_client.download_file.assert_any_call(
            "my-bucket", "yearly/cartolas_2023.parquet", str(tmp_path / "cartolas_2023.parquet")
        )

    def test_returns_true_when_no_objects(self, tmp_path):
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]

        with patch("cartolas.r2.get_r2_client", return_value=mock_client):
            result = r2.download_all_from_r2(tmp_path)

        assert result is True
        mock_client.download_file.assert_not_called()

    def test_returns_false_when_client_none(self, tmp_path):
        with patch("cartolas.r2.get_r2_client", return_value=None):
            result = r2.download_all_from_r2(tmp_path)

        assert result is False
