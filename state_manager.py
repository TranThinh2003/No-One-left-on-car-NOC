class StateManager:
    def __init__(self):
        # Vehicle movement state
        self.vehicle_moving = False
        self.vehicle_stopped = False
        # Door state
        self.door_open = False
        # Engine state
        self.engine_on = False

    def start_vehicle(self):
        self.vehicle_moving = True
        self.vehicle_stopped = False
        self.engine_on = True

    def stop_vehicle(self):
        self.vehicle_moving = False
        self.vehicle_stopped = True

    def open_door(self):
        self.door_open = True

    def close_door(self):
        self.door_open = False

    def turn_off_engine(self):
        self.engine_on = False
