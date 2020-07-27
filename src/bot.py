from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

# Main bot code
class MyBot(BaseAgent):

  # Default constructor
  def __init__(self, name, team, index):
    super().__init__(name, team, index)
    self.active_sequence: Sequence = None
    self.boost_pad_tracker = BoostPadTracker()

  # Track boost pad information
  def initialize_agent(self): self.boost_pad_tracker.initialize_boosts(self.get_field_info())

  # Main controller function - called many times per second
  def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

    # Get currently active boost pad info
    self.boost_pad_tracker.update_boost_status(packet)

    # Continue sequences from previous call
    if self.active_sequence and not self.active_sequence.done:
      controls = self.active_sequence.tick(packet)
      if controls is not None: return controls

    # Gather information about car and ball
    my_car = packet.game_cars[self.index]
    car_location = Vec3(my_car.physics.location)
    car_velocity = Vec3(my_car.physics.velocity)
    ball_location = Vec3(packet.game_ball.physics.location)

    if car_location.dist(ball_location) > 1500:
      # Set path of car to future ball location
      ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
      ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 2)
      target_location = Vec3(ball_in_future.physics.location)
      self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())
    else:
      target_location = ball_location

    # Draw rendering lines
    self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
    self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
    self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

    # Front flip if car is moving at a certain speed
    if 750 < car_velocity.length() < 800: return self.begin_front_flip(packet)

    controls = SimpleControllerState()
    controls.steer = steer_toward_target(my_car, target_location)
    controls.throttle = 1.0

    return controls

  # Car flip function
  def begin_front_flip(self, packet):

    # Do a front flip
    self.active_sequence = Sequence([
      ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
      ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
      ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
      ControlStep(duration=0.8, controls=SimpleControllerState()),
    ])

    # Return the controls associated with the beginning of the sequence
    return self.active_sequence.tick(packet)
