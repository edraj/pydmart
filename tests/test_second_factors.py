"""Second factors (dmart >= 1.8.1): the second step's fields on login, the step
a sign-in asks for, key-only sign-in, and an authenticator app's setup."""
import pytest
from aioresponses import aioresponses
from yarl import URL

from pydmart.enums import DmartErrorCode
from pydmart.models import DmartException
from pydmart.service import DmartService

from helpers import BASE_URL, make_login_response

LOGIN = f"{BASE_URL}/user/login"


def sent(m, method, url, index=0):
    return m.requests[(method, URL(url))][index].kwargs["json"]


def step_answer(info):
    return {"status": "failed", "error": {"type": "auth", "code": DmartErrorCode.OTP_NEEDED,
                                          "message": "Enter the code", "info": info}}


class TestSecondFactors:
    @pytest.mark.asyncio
    async def test_login_sends_the_second_step(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(LOGIN, payload=make_login_response("t1"))
                m.post(LOGIN, payload=make_login_response("t2"))
                await svc.login("ali", "pw", totp="123456")
                assert sent(m, "POST", LOGIN) == {"shortname": "ali", "password": "pw", "totp": "123456"}
                answer = {"challenge_id": "c1", "credential": {"id": "k"}}
                await svc.login("ali", "pw", webauthn=answer)
                assert sent(m, "POST", LOGIN, 1) == {"shortname": "ali", "password": "pw", "webauthn": answer}
                assert svc.auth_token == "t2"

    @pytest.mark.asyncio
    async def test_the_step_a_sign_in_asks_for(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                m.post(LOGIN, status=401, payload=step_answer([{"factors": ["totp", "recovery"]}]))
                with pytest.raises(DmartException) as raised:
                    await svc.login("ali", "pw")
                assert raised.value.error.code == DmartErrorCode.OTP_NEEDED
                assert raised.value.second_factor == {"factors": ["totp", "recovery"]}
                m.post(LOGIN, status=401, payload=step_answer([]))
                with pytest.raises(DmartException) as plain:
                    await svc.login("ali", "pw")
                assert plain.value.second_factor is None

    @pytest.mark.asyncio
    async def test_key_only_sign_in_sends_no_password(self):
        async with DmartService(BASE_URL) as svc:
            with aioresponses() as m:
                options = f"{BASE_URL}/user/passkeys/login-options"
                m.post(options, payload={"status": "success", "attributes": {"challenge_id": "k1", "options": {"rpId": "dmart.test"}}})
                m.post(LOGIN, payload=make_login_response("tk"))
                challenge = await svc.key_only_challenge(shortname="ali")
                assert challenge["challenge_id"] == "k1"
                assert sent(m, "POST", options) == {"shortname": "ali"}
                answer = {"challenge_id": "k1", "credential": {"id": "k"}}
                await svc.login_with_key_alone(answer, shortname="ali")
                assert sent(m, "POST", LOGIN) == {"shortname": "ali", "webauthn": answer}
                assert svc.auth_token == "tk"

    @pytest.mark.asyncio
    async def test_an_authenticator_apps_setup(self):
        async with DmartService(BASE_URL) as svc:
            svc.auth_token = "tok"
            with aioresponses() as m:
                begin, confirm = f"{BASE_URL}/user/totp/begin", f"{BASE_URL}/user/totp/confirm"
                m.post(begin, payload={"status": "success", "attributes": {"setup_id": "s1", "secret": "GEZD", "uri": "otpauth://totp/x"}})
                m.post(confirm, payload={"status": "success", "attributes": {"recovery_codes": ["AAAAA-BBBBB"]}})
                m.get(f"{BASE_URL}/user/passkeys", payload={"status": "success", "attributes": {"totp": True, "passkeys": []}})
                setup = await svc.totp_begin(password="pw")
                assert setup["setup_id"] == "s1"
                assert sent(m, "POST", begin) == {"password": "pw"}
                assert await svc.totp_confirm("s1", "123456") == ["AAAAA-BBBBB"]
                assert sent(m, "POST", confirm) == {"setup_id": "s1", "code": "123456"}
                assert (await svc.get_second_factors())["totp"] is True
