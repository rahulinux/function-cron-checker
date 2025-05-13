"""A Crossplane composition function with cron schedule checking."""

import grpc
from crossplane.function import logging, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1
from croniter import croniter
from datetime import datetime
import pytz

class FunctionRunner(grpcv1.FunctionRunnerService):
    """Handles gRPC requests with cron schedule checks."""
    
    def __init__(self):
        self.log = logging.get_logger()

    async def RunFunction(
        self, 
        request: fnv1.RunFunctionRequest, 
        context: grpc.aio.ServicerContext
    ) -> fnv1.RunFunctionResponse:
        self.log.info("Running cron schedule checker function")
        rsp = response.to(request)
        
        try:
            composite = request.observed.composite.resource
            schedules = composite['spec']['schedules']
            
            active = []
            from_time = None
            for idx, schedule in enumerate(schedules):
                schedule = dict(schedule)
                try:
                    tz = pytz.timezone(schedule.get('timeZone', 'UTC'))
                    now = datetime.now(tz)
                    
                    # Validate cron expressions
                    croniter.is_valid(schedule['scheduleFrom'])
                    croniter.is_valid(schedule['scheduleUntil'])
                    
                    # Check schedule window
                    from_iter = croniter(schedule['scheduleFrom'], now)
                    from_time = from_iter.get_prev(datetime)
                    until_iter = croniter(schedule['scheduleUntil'], from_time)
                    until_time = until_iter.get_next(datetime)
                    # breakpoint()
                    if from_time <= now < until_time:
                        active.append(str(idx))
                        
                except Exception as e:
                    rsp.conditions.append(fnv1.Condition(
                        type="InvalidSchedule",
                        status=fnv1.Status.STATUS_CONDITION_TRUE,
                        reason=str(e),
                        message=f"Schedule {idx} error: {e} {now} {from_time}"
                    ))

            # Set active schedules in context
            rsp.context.update({
                "cronCheck": {
                    "activeSchedules": active
                }
            })
            
        except KeyError as e:
            rsp.conditions.append(fnv1.Condition(
                type="InvalidInput",
                status=fnv1.Status.STATUS_CONDITION_TRUE,
                reason="Missing field",
                message=f"Missing {str(e)} in composite"
            ))

        return rsp
