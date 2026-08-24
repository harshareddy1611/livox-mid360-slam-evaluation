"""
Block until a topic goes idle (no new message for --idle seconds), meaning
the publisher has caught up / drained its backlog. Used after bag playback
ends to let a slower-than-real-time node (e.g. GLIM) finish processing
before we kill it, instead of a fixed sleep.
"""
import argparse
import time
import sys

import rclpy
from rclpy.node import Node
from rosidl_runtime_py.utilities import get_message
from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--msg-type", default="nav_msgs/msg/Odometry")
    ap.add_argument("--idle", type=float, default=5.0, help="seconds of silence = drained")
    ap.add_argument("--max-wait", type=float, default=400.0, help="safety ceiling in seconds")
    args = ap.parse_args()

    rclpy.init()
    node = Node("wait_for_topic_drain")
    msg_cls = get_message(args.msg_type)

    state = {"last_msg_time": time.time(), "count": 0}

    def cb(msg):
        state["last_msg_time"] = time.time()
        state["count"] += 1

    qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
    node.create_subscription(msg_cls, args.topic, cb, qos)

    start = time.time()
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.5)
        now = time.time()
        if now - start > args.max_wait:
            print(f"wait_for_topic_drain: hit max-wait ({args.max_wait}s), giving up. msgs={state['count']}")
            break
        if now - state["last_msg_time"] > args.idle:
            print(f"wait_for_topic_drain: idle for {args.idle}s, assuming drained. msgs={state['count']}")
            break

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
