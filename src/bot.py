from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.sequence import Sequence, ControlStep
from util.vec import Vec3

import re


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.last_chat_time = 0
        self.command_queue = None

    # -----------------------------
    # MAIN LOOP
    # -----------------------------
    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        # Continue any active shot sequence
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Check for new chat commands
        self.read_player_chat(packet)

        # If a command is waiting, execute it
        if self.command_queue is not None:
            self.execute_command(self.command_queue, packet)
            self.command_queue = None

        # Default behavior (drive toward ball)
        controls = SimpleControllerState()
        controls.throttle = 1
        return controls

    # -----------------------------
    # CHAT LISTENER
    # -----------------------------
    def read_player_chat(self, packet):
        """
        Reads text chat messages and extracts commands.
        Only reacts to YOUR messages.
        """
        messages = packet.game_chat
        for i in range(messages.num_messages):
            msg = messages.messages[i]
            if msg.player_index == self.index:  # Only your messages
                text = msg.message.decode("utf-8").lower()

                # Prevent double‑reading same message
                if msg.time_sent > self.last_chat_time:
                    self.last_chat_time = msg.time_sent
                    self.command_queue = text

    # -----------------------------
    # COMMAND PARSER
    # -----------------------------
    def execute_command(self, text, packet):

        # --- Speed‑based shots ---
        if "ground pinch" in text:
            speed = self.extract_number(text)
            return self.begin_ground_pinch(packet, speed)

        if "ceiling pinch" in text:
            speed = self.extract_number(text)
            return self.begin_ceiling_pinch(packet, speed)

        if "kuxir pinch" in text:
            speed = self.extract_number(text)
            return self.begin_kuxir_pinch(packet, speed)

        # --- Count‑based shots ---
        if "heli resets" in text:
            count = self.extract_number(text)
            return self.begin_heli_resets(packet, count)

        # --- Named shots ---
        if text == "air dribble":
            return self.begin_air_dribble(packet)

        if text == "flip reset":
            return self.begin_flip_reset(packet)

        if text == "double flip reset":
            return self.begin_multi_reset(packet, 2)

        if text == "triple flip reset":
            return self.begin_multi_reset(packet, 3)

        if text == "quad reset":
            return self.begin_multi_reset(packet, 4)

        if text == "flip reset musty":
            return self.begin_flip_reset_musty(packet)

        if text == "flip reset musty off backboard into a psycho":
            return self.begin_psycho(packet)

    # -----------------------------
    # HELPERS
    # -----------------------------
    def extract_number(self, text):
        nums = re.findall(r"\d+", text)
        return int(nums[0]) if nums else 100

    # -----------------------------
    # SHOT SEQUENCES
    # -----------------------------
    def begin_air_dribble(self, packet):
        self.send_quick_chat(False, QuickChatSelection.Information_IGotIt)
        self.active_sequence = Sequence([
            ControlStep(0.2, SimpleControllerState(jump=True)),
            ControlStep(0.1, SimpleControllerState(jump=False)),
            ControlStep(1.5, SimpleControllerState(boost=True, pitch=-0.3)),
        ])
        return self.active_sequence.tick(packet)

    def begin_flip_reset(self, packet):
        self.active_sequence = Sequence([
            ControlStep(0.15, SimpleControllerState(jump=True)),
            ControlStep(0.05, SimpleControllerState(jump=False)),
            ControlStep(0.4, SimpleControllerState(pitch=-1)),
            ControlStep(0.1, SimpleControllerState(jump=True)),  # reset
        ])
        return self.active_sequence.tick(packet)

    def begin_multi_reset(self, packet, count):
        steps = []
        for _ in range(count):
            steps.extend([
                ControlStep(0.15, SimpleControllerState(jump=True)),
                ControlStep(0.05, SimpleControllerState(jump=False)),
                ControlStep(0.4, SimpleControllerState(pitch=-1)),
                ControlStep(0.1, SimpleControllerState(jump=True)),
            ])
        self.active_sequence = Sequence(steps)
        return self.active_sequence.tick(packet)

    def begin_flip_reset_musty(self, packet):
        self.active_sequence = Sequence([
            ControlStep(0.15, SimpleControllerState(jump=True)),
            ControlStep(0.05, SimpleControllerState(jump=False)),
            ControlStep(0.4, SimpleControllerState(pitch=-1)),
            ControlStep(0.1, SimpleControllerState(jump=True)),  # reset
            ControlStep(0.2, SimpleControllerState(pitch=1, yaw=1)),  # musty flick
        ])
        return self.active_sequence.tick(packet)

    def begin_psycho(self, packet):
        self.active_sequence = Sequence([
            ControlStep(0.15, SimpleControllerState(jump=True)),
            ControlStep(0.05, SimpleControllerState(jump=False)),
            ControlStep(0.4, SimpleControllerState(pitch=-1)),
            ControlStep(0.1, SimpleControllerState(jump=True)),  # reset
            ControlStep(0.2, SimpleControllerState(pitch=1, yaw=1)),  # musty
            ControlStep(0.8, SimpleControllerState(roll=1)),  # psycho spin
        ])
        return self.active_sequence.tick(packet)

    # -----------------------------
    # SPEED‑BASED SHOTS
    # -----------------------------
    def begin_ground_pinch(self, packet, speed):
        power = min(max(speed / 150, 0.3), 1.0)
        self.active_sequence = Sequence([
            ControlStep(0.1, SimpleControllerState(jump=True)),
            ControlStep(0.05, SimpleControllerState(jump=False)),
            ControlStep(0.3, SimpleControllerState(boost=True, pitch=-0.5)),
            ControlStep(0.1, SimpleControllerState(roll=1, yaw=1, throttle=power)),
        ])
        return self.active_sequence.tick(packet)

    def begin_ceiling_pinch(self, packet, speed):
        power = min(max(speed / 150, 0.3), 1.0)
        self.active_sequence = Sequence([
            ControlStep(0.3, SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(0.8, SimpleControllerState()),  # fall from ceiling
            ControlStep(0.1, SimpleControllerState(roll=1, throttle=power)),
        ])
        return self.active_sequence.tick(packet)

    def begin_kuxir_pinch(self, packet, speed):
        power = min(max(speed / 150, 0.3), 1.0)
        self.active_sequence = Sequence([
            ControlStep(0.2, SimpleControllerState(jump=True)),
            ControlStep(0.1, SimpleControllerState(jump=False)),
            ControlStep(0.3, SimpleControllerState(roll=-1, yaw=-1, throttle=power)),
        ])
        return self.active_sequence.tick(packet)

    # -----------------------------
    # HELI RESETS
    # -----------------------------
    def begin_heli_resets(self, packet, count):
        steps = []
        for _ in range(count):
            steps.extend([
                ControlStep(0.15, SimpleControllerState(jump=True)),
                ControlStep(0.05, SimpleControllerState(jump=False)),
                ControlStep(0.4, SimpleControllerState(roll=1, pitch=-1)),
                ControlStep(0.1, SimpleControllerState(jump=True)),
            ])
        self.active_sequence = Sequence(steps)
        return self.active_sequence.tick(packet)
