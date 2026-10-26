from datetime import datetime

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler_di import ContextSchedulerDecorator
from tzlocal import get_localzone

from app.services.scheduler.checker_schedule import checker_schedule
# from app.services.scheduler.collect_data import collect_all_data
# from app.services.scheduler.parsing_schedule import parsing_schedule


def start_jobs(scheduler: AsyncIOScheduler):
    scheduler.add_job(
        checker_schedule,
        trigger="cron",
        minute="*/5", second=0,
        next_run_time=datetime.now(),
        max_instances=1,
        jobstore="memory"
    )
    # scheduler.add_job(
    #     parsing_schedule,
    #     trigger="cron",
    #     minute="*/5", second=5,
    #     max_instances=1,
    #     jobstore="memory"
    # )
    # scheduler.add_job(
    #     collect_all_data,
    #     # trigger="cron",
    #     # day=1,
    #     next_run_time=datetime.now(),
    #     max_instances=1,
    #     jobstore="memory",
    #     kwargs={"type_update_data": "once"}
    # )


def run_scheduler(redis_connect: dict, ctx: dict = None, timezone=None):
    job_stores = {
        "default": RedisJobStore(
            **redis_connect,
            jobs_key="dispatched_trips_jobs",
            run_times_key="dispatched_trips_running"
        ),
        "memory": MemoryJobStore()
    }

    scheduler = ContextSchedulerDecorator(
        AsyncIOScheduler(
            jobstores=job_stores, timezone=timezone or str(get_localzone())
        )
    )

    for instance, _class in {} or ctx.items():
        scheduler.ctx.add_instance(instance, _class)

    start_jobs(scheduler)
    scheduler.start()

    return scheduler
