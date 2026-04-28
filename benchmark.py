import timeit
from jinja2 import Environment

template_slow = """
{% set max_age = 7200 %}
{% set s1 = states('sensor.lincoln_s_temp_temperature') | float(none) %}
{% set s1_fresh = s1 is not none and (now() - states.sensor.lincoln_s_temp_temperature.last_changed).total_seconds() < max_age %}
{% set s2 = states('sensor.lincoln_s_room_temperature_temperature') | float(none) %}
{% set s2_fresh = s2 is not none and (now() - states.sensor.lincoln_s_room_temperature_temperature.last_changed).total_seconds() < max_age %}
{% set s3 = states('sensor.lincoln_temp_temperature') | float(none) %}
{% set s3_fresh = s3 is not none and (now() - states.sensor.lincoln_temp_temperature.last_changed).total_seconds() < max_age %}
"""

template_fast = """
{% set max_age = 7200 %}
{% set obj1 = states.sensor.lincoln_s_temp_temperature %}
{% set s1 = obj1.state | float(none) %}
{% set s1_fresh = s1 is not none and (now() - obj1.last_changed).total_seconds() < max_age %}
{% set obj2 = states.sensor.lincoln_s_room_temperature_temperature %}
{% set s2 = obj2.state | float(none) %}
{% set s2_fresh = s2 is not none and (now() - obj2.last_changed).total_seconds() < max_age %}
{% set obj3 = states.sensor.lincoln_temp_temperature %}
{% set s3 = obj3.state | float(none) %}
{% set s3_fresh = s3 is not none and (now() - obj3.last_changed).total_seconds() < max_age %}
"""

class MockDateTime:
    def total_seconds(self):
        return 1000
    def __sub__(self, other):
        return self

class MockState:
    def __init__(self, state):
        self.state = state
        self.last_changed = MockDateTime()

def now():
    return MockDateTime()

states_dict = {
    'sensor.lincoln_s_temp_temperature': MockState('20.5'),
    'sensor.lincoln_s_room_temperature_temperature': MockState('21.0'),
    'sensor.lincoln_temp_temperature': MockState('22.2'),
}

def states_func(entity_id):
    for _ in range(100): pass # Simulate HA overhead
    return states_dict.get(entity_id, MockState('unknown')).state

env = Environment()

class StatesObj:
    def __init__(self, d):
        self.d = d
    def __call__(self, entity_id):
        return states_func(entity_id)
    def __getitem__(self, key):
        for _ in range(100): pass
        return self.d.get(key)
    def __getattr__(self, name):
        if name == 'sensor':
            return self
        for _ in range(100): pass
        return self.d.get('sensor.' + name)

states = StatesObj(states_dict)

def float_filter(val, default=None):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

env.filters['float'] = float_filter
env.globals['now'] = now
env.globals['states'] = states

t_slow = env.from_string(template_slow)
t_fast = env.from_string(template_fast)

def run_slow():
    t_slow.render()

def run_fast():
    t_fast.render()

slow_time = timeit.timeit(run_slow, number=100000)
fast_time = timeit.timeit(run_fast, number=100000)

print(f"Baseline (slow): {slow_time:.4f}s")
print(f"Optimized (fast): {fast_time:.4f}s")
print(f"Improvement: {(slow_time - fast_time) / slow_time * 100:.2f}%")
