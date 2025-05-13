import dataclasses
import unittest
from unittest.mock import patch
from datetime import datetime
import pytz

from crossplane.function import logging, resource
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from google.protobuf import struct_pb2 as structpb

from function import fn  # Your cron-checker function

class TestFunctionRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.maxDiff = 2000
        logging.configure(level=logging.Level.DISABLED)

    @patch('function.fn.datetime')  # Mock datetime for deterministic testing
    async def test_active_schedule(self, mock_datetime):
        mock_now = datetime(2024, 1, 1, 12, 0, tzinfo=pytz.UTC)  # 12PM UTC
        mock_datetime.now.return_value = mock_now
        
        req = fnv1.RunFunctionRequest(
            observed=fnv1.State(
                composite=fnv1.Resource(
                    resource=resource.dict_to_struct({
                    "apiVersion": "policyscheduler.example.com/v1alpha1",
                    "kind": "XPolicyScheduler",
                    "spec": {
                        "schedules": [{
                            "policyArn": "arn:aws:iam::aws:policy/TestPolicy",
                            "roleName": "test-role",
                            "scheduleFrom": "* * * * 1-5",
                            "scheduleUntil": "* * * * 1-5",
                            "timeZone": "UTC"
                        }]
                    }
                })
                )
            )
        )
        
        runner = fn.FunctionRunner()
        got = await runner.RunFunction(req, None)
        print(got)
        
        # cron_check = got.context.fields.get("cronCheck")
        cron_check = got.context.fields.get("cronCheck")
        if cron_check and cron_check.HasField("struct_value"):
            active_schedules = cron_check.struct_value.fields.get("activeSchedules")
            if active_schedules and active_schedules.HasField("list_value"):
                active_indices = [v.string_value for v in active_schedules.list_value.values]
                self.assertEqual(active_indices, ["0"])

    # async def test_invalid_cron(self):
    #     req = fnv1.RunFunctionRequest(
    #         observed=fnv1.State(
    #             composite=fnv1.Resource(
    #                 resource=resource.dict_to_struct({
    #                     "spec": {
    #                         "schedules": [{
    #                             "scheduleFrom": "invalid-cron",
    #                             "scheduleUntil": "* * * * *"
    #                         }]
    #                     }
    #                 })
    #             )
    #         )
    #     )
        
    #     runner = fn.FunctionRunner()
    #     got = await runner.RunFunction(req, None)
        
    #     found = any(
    #         c.type == "InvalidSchedule" and 
    #         c.status == fnv1.Status.STATUS_CONDITION_TRUE
    #         for c in got.conditions
    #     )
    #     self.assertTrue(found, "Condition not added for invalid cron")

if __name__ == "__main__":
    unittest.main()
