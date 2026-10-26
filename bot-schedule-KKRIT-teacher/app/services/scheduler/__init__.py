from datetime import datetime, timedelta

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler_di import ContextSchedulerDecorator
from tzlocal import get_localzone

# from .collect_data import collect_all_data
# from .schedule import find_schedule
from .send_schedule import send_schedule


def start_jobs(scheduler: AsyncIOScheduler):
    scheduler.add_job(
        send_schedule,
        trigger="cron",
        minute="*/1", second=0,
        next_run_time=datetime.now(),
        max_instances=1,
        jobstore="memory"
    )
    # scheduler.add_job(find_schedule, "cron", minute="*/5", second=0, next_run_time=datetime.now() + timedelta(minutes=1), jobstore="memory")
    # scheduler.add_job(collect_all_data, "cron", day=1, next_run_time=datetime.now(), jobstore="memory")


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
