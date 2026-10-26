from . import creator_schedule_kr, creator_schedule_sv


CREATORS_SCHEDULE = {
    "kr": creator_schedule_kr.create_schedule,
    "sv": creator_schedule_sv.create_schedule
}


SCHEDULE_RULES = {
    "kr": {
        "Понедельник": creator_schedule_kr.enforce_rule_monday,
        "Четверг": creator_schedule_kr.enforce_rule_thursday,
    },
    "sv": {
        "Понедельник": creator_schedule_sv.enforce_rule_monday,
        "Четверг": creator_schedule_sv.enforce_rule_thursday,
    },
}
