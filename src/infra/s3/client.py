from minio import Minio


class BaseBucketClient:
    class Config:
        bucket_name: str

    def __init__(
        self,
        url: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            url,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def _check_bucket(self):
        found = self._client.bucket_exists(self.Config.bucket_name)

        if not found:
            self._client.make_bucket(self.Config.bucket_name)

    def upload_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = "application/ octet-stream",
        metadata: dict[str, str | list[str] | tuple[str]] | None = None,
    ) -> None:
        self._check_bucket()

        self._client.fput_object(
            self.Config.bucket_name,
            object_name,
            file_path,
            content_type,
            metadata,
        )

    def upload_data(
        self,
        object_name: str,
        data,
        content_type: str | None = None,
        length: int = -1,
        part_size: int = 10 * 1024 * 1024,
    ):
        if not content_type:
            content_type = "application/octet-stream"

        self._check_bucket()

        return self._client.put_object(
            self.Config.bucket_name,
            object_name,
            data,
            length=length,
            part_size=part_size,
            content_type=content_type,
        )

    def remove(self, object_name: str):
        self._check_bucket()

        return self._client.remove_object(self.Config.bucket_name, object_name)
