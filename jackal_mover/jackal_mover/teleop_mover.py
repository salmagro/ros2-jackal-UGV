import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped, Twist
from sensor_msgs.msg import JointState
import tf2_ros
import math

class TeleopMover(Node):
    def __init__(self):
        super().__init__('teleop_mover')

        # Publishers
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)

        # Subscriptions
        self.subscription = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Timer (20 Hz)
        self.timer = self.create_timer(0.05, self.timer_callback)

        # Pose y velocidades
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0

        # Parámetros de ruedas según URDF
        self.wheel_radius = 0.098      # radio = 9.8 cm
        self.wheel_base   = 2 * 0.187795  # separación entre ejes izquierdo/derecho

        # Posiciones angulares de cada rueda
        self.front_left_wheel_pos  = 0.0
        self.front_right_wheel_pos = 0.0
        self.rear_left_wheel_pos   = 0.0
        self.rear_right_wheel_pos  = 0.0

        self.get_logger().info("Teleop_mover been started.")

    def cmd_vel_callback(self, msg: Twist):
        self.linear_velocity  = msg.linear.x
        self.angular_velocity = msg.angular.z

    def timer_callback(self):
        dt = 0.05  # segundos

        # 1) Integrar velocidades para obtener nueva pose
        self.x     += self.linear_velocity * math.cos(self.theta) * dt
        self.y     += self.linear_velocity * math.sin(self.theta) * dt
        self.theta += self.angular_velocity * dt

        # 2) Publicar TF de map → base_link
        t = TransformStamped()
        t.header.stamp    = self.get_clock().now().to_msg()
        t.header.frame_id = 'map'
        t.child_frame_id  = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0

        qz = math.sin(self.theta * 0.5)
        qw = math.cos(self.theta * 0.5)
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)

        # 3) Calcular velocidades de rueda
        v_left  = self.linear_velocity - self.angular_velocity * (self.wheel_base / 2.0)
        v_right = self.linear_velocity + self.angular_velocity * (self.wheel_base / 2.0)

        # Solo actualizamos ángulo si nos estamos moviendo
        if abs(v_left) > 1e-6 or abs(v_right) > 1e-6:
            delta_left  = (v_left  / self.wheel_radius) * dt
            delta_right = (v_right / self.wheel_radius) * dt

            self.front_left_wheel_pos  += delta_left
            self.rear_left_wheel_pos   += delta_left
            self.front_right_wheel_pos += delta_right
            self.rear_right_wheel_pos  += delta_right

        # 4) Publicar JointState con las cuatro ruedas
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name     = [
            'front_left_wheel',
            'rear_left_wheel',
            'front_right_wheel',
            'rear_right_wheel'
        ]
        js.position = [
            self.front_left_wheel_pos,
            self.rear_left_wheel_pos,
            self.front_right_wheel_pos,
            self.rear_right_wheel_pos
        ]
        self.joint_state_pub.publish(js)

def main():
    rclpy.init()
    node = TeleopMover()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
