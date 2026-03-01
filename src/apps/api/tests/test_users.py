from http import HTTPMethod
from http import HTTPStatus

from apps.api.schemas.users import GetCurrentUserOut
from tests.api import ApiTestCase
from tests.factories import UserFactory
from utils.errors.http_ import HttpUnauthorizedError
from utils.errors.http_ import http_compare_error


class TestGetCurrentUser(ApiTestCase):
    class Meta:
        url_name = "get_current_user"
        method_name = HTTPMethod.GET

    async def test_success(self):
        user = await UserFactory.create_async()
        self.authorize(user.id)

        url = self.reverse_url()
        resp = await self.request(url)
        assert resp.status_code == HTTPStatus.OK

        data = resp.json()
        data = GetCurrentUserOut.from_raw(data)
        assert data.id == user.id

    async def test_different_users(self):
        url = self.reverse_url()

        user1, user2 = await UserFactory.create_batch_async(2)
        self.authorize(user1.id)

        resp = await self.request(url)
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        data = GetCurrentUserOut.from_raw(data)
        assert data.id == user1.id

        self.unauthorize()

        # Check that another user gets different data
        self.authorize(user2.id)

        resp = await self.request(url)
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        data = GetCurrentUserOut.from_raw(data)
        assert data.id == user2.id

    async def test_unauthorized(self):
        url = self.reverse_url()
        resp = await self.request(url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED
        assert http_compare_error(
            HttpUnauthorizedError(),
            resp.json(),
        )
