class World:
    """
    A simple interactive world simulation.
    The player must perform actions in order to reveal the secret message on the fridge.
    """

    def __init__(self, secret_number: int, message_on_the_fridge: str):
        self._secret_number = secret_number
        self._message_on_the_fridge = message_on_the_fridge

        # World state
        self.door_locked = True
        self.door_open = False
        self.is_inside = False
        self.light_on = False
        self.in_kitchen = False

    # --- Core interaction methods ---

    def unlock_door(self, code: int) -> str:
        if not self.door_locked:
            return "The door is already unlocked."
        if code == self._secret_number:
            self.door_locked = False
            return "You unlocked the door."
        return "The code is incorrect."

    def lock_door(self) -> str:
        if self.door_locked:
            return "The door is already locked."
        self.door_locked = True
        self.door_open = False
        return "You locked the door."

    def open_door(self) -> str:
        if self.door_locked:
            return "The door is locked."
        if self.door_open:
            return "The door is already open."
        self.door_open = True
        return "You opened the door."

    def close_door(self) -> str:
        if not self.door_open:
            return "The door is already closed."
        self.door_open = False
        return "You closed the door."

    def go_inside(self) -> str:
        if self.is_inside:
            return "You are already inside the house."
        if not self.door_open:
            return "The door is closed."
        self.is_inside = True
        return "You went inside the house."

    def go_outside(self) -> str:
        if not self.is_inside:
            return "You are already outside."
        self.is_inside = False
        self.in_kitchen = False
        self.light_on = False
        return "You went outside the house."

    def turn_on_light(self) -> str:
        if not self.is_inside:
            return "You are outside, there are no lights here."
        if self.light_on:
            return "The light is already on."
        self.light_on = True
        return "You turned on the light."

    def turn_off_light(self) -> str:
        if not self.is_inside:
            return "You are outside, there are no lights here."
        if not self.light_on:
            return "The light is already off."
        self.light_on = False
        return "You turned off the light."

    def go_to_kitchen(self) -> str:
        if not self.is_inside:
            return "You are outside, there is no kitchen here."
        if not self.light_on:
            return "It's too dark to see where you're going."
        if self.in_kitchen:
            return "You are already in the kitchen."
        self.in_kitchen = True
        return "You went to the kitchen."

    def read_fridge_message(self) -> str:
        if not self.in_kitchen:
            return "You need to be in the kitchen to read the fridge."
        if not self.light_on:
            return "It's too dark to read the message."
        return f'The message on the fridge says: "{self._message_on_the_fridge}"'

    # --- Developer tools (optional) ---
    def get_secret_number(self) -> int:
        """ For debugging or testing. """
        return self._secret_number

    def describe_state(self) -> str:
        """ Returns a summary of the current world state (for debugging). """
        return (
            f"Door locked: {self.door_locked}\n"
            f"Door open: {self.door_open}\n"
            f"Inside: {self.is_inside}\n"
            f"Light on: {self.light_on}\n"
            f"In kitchen: {self.in_kitchen}"
        )


# Example usage:
if __name__ == "__main__":
    world = World(secret_number=42, message_on_the_fridge="Remember to buy some more milk.")

    print(world.unlock_door(11))
    print(world.unlock_door(42))
    print(world.open_door())
    print(world.go_inside())
    print(world.turn_on_light())
    print(world.go_to_kitchen())
    print(world.read_fridge_message())