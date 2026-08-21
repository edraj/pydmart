import asyncio
import os

from pydmart.enums import ResourceType
from pydmart.models import DmartException
from pydmart.service import DmartService

DMART_URL = os.getenv("DMART_URL", "http://localhost:8282")
DMART_USER = os.getenv("DMART_USER", "dmart")
DMART_PASSWORD = os.getenv("DMART_PASSWORD", "Test1234")

dmartService = DmartService(DMART_URL)

async def main():
    try:
        await dmartService.login(DMART_USER, DMART_PASSWORD)
    except DmartException as e:
        print(f"Login error: {e}")
        return

    try:

        query_result = await dmartService.retrieve_entry(
            resource_type=ResourceType.content,
            space_name="acme",
            subpath="/ussd",
            shortname='7801223789',
            retrieve_json_payload=True
        )
        print(query_result)
    except DmartException as e:
        print(f"XError: {e}")

    # actionRequest = ActionRequest(
    #     space_name='managements',
    #     request_type=RequestType.create,
    #     records=[
    #         ActionRequestRecord(
    #             resource_type=ResourceType.user,
    #             shortname='dmart',
    #             subpath="users",
    #             attributes={
    #                 "password": 'Test1234',
    #                 "email": ["dmart@dmart.cc"],
    #                 "is_active": True,
    #                 "role": ["trainee"]
    #             }
    #         )
    #     ]
    # )
    #
    # try:
    #     x = await dmartService.request(actionRequest)
    # except DmartException as e:
    #     print(f"XError: {e}")

asyncio.run(main())
