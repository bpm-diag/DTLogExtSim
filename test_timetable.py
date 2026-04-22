from datetime import datetime, timedelta
from datetime import time as dt_time

def test_original(from_time, to_time, from_day, to_day, current_time):
    current_hour_minute_second = dt_time(current_time.hour, current_time.minute, current_time.second)
    timeFlag=False
    if from_time > to_time:
        if not (to_time >= current_hour_minute_second or current_hour_minute_second >= from_time):
            return False
        timeFlag=True  
    elif not from_time <= current_hour_minute_second <= to_time:
        return False
    
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    if (days.index(to_day) < days.index(from_day)) and timeFlag:
        if not (days.index(to_day) > days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
            return False
    elif days.index(to_day) < days.index(from_day) and not timeFlag:
        if not (days.index(to_day) >= days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
            return False
    elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) < days.index(to_day))) and timeFlag:
        return False
    elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) <= days.index(to_day))) and not timeFlag:
        return False
    return True

def test_new(from_time, to_time, from_day, to_day, current_time):
    current_hour_minute_second = dt_time(current_time.hour, current_time.minute, current_time.second)
    current_day_idx = current_time.weekday()
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    from_day_idx = days.index(from_day)
    to_day_idx = days.index(to_day)
    
    timeFlag=False
    if from_time > to_time:
        if not (to_time >= current_hour_minute_second or current_hour_minute_second >= from_time):
            return False
        timeFlag=True  
    elif not from_time <= current_hour_minute_second <= to_time:
        return False

    if (to_day_idx < from_day_idx) and timeFlag:
        if not (to_day_idx > current_day_idx or current_day_idx >= from_day_idx):
            return False
    elif (to_day_idx < from_day_idx) and not timeFlag:
        if not (to_day_idx >= current_day_idx or current_day_idx >= from_day_idx):
            return False
    elif (not (from_day_idx <= current_day_idx < to_day_idx)) and timeFlag:
        return False
    elif (not (from_day_idx <= current_day_idx <= to_day_idx)) and not timeFlag:
        return False
    return True

import random
for i in range(10000):
    start = datetime(2026, 4, 1, 0, 0, 0)
    current = start + timedelta(seconds=random.randint(0, 10000000))
    ft = dt_time(random.randint(0,23), random.randint(0,59))
    tt = dt_time(random.randint(0,23), random.randint(0,59))
    days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
    fd = random.choice(days)
    td = random.choice(days)
    res_orig = test_original(ft, tt, fd, td, current)
    res_new = test_new(ft, tt, fd, td, current)
    if res_orig != res_new:
        print(f"DIFF! ft={ft} tt={tt} fd={fd} td={td} current={current} orig={res_orig} new={res_new}")
        exit(1)
print("ALL MATCH")
