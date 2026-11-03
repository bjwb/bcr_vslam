"""Planar RGB-D SLAM using BCR Bot's camera and external odometry.

Start the robot/simulator and its sensor bridges before this launch file.
The camera bridge should publish images and CameraInfo in kinect_camera_optical.

Usage:
    ros2 launch vslam_bringup rtabmap_robust.launch.py
    ros2 launch vslam_bringup rtabmap_robust.launch.py database_path:=/path/to/new.db
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    defaults = {
        'use_sim_time': ('true', 'Use the Gazebo simulation clock.'),
        'frame_id': ('base_footprint', 'Robot base frame.'),
        'rgb_topic': (
            '/bcr_bot/kinect_camera/image', 'Registered RGB image topic.'),
        'depth_topic': (
            '/bcr_bot/kinect_camera/depth_image', 'Registered depth image topic.'),
        'camera_info_topic': (
            '/bcr_bot/kinect_camera/camera_info', 'Camera calibration topic.'),
        'visual_odometry': ('false', 'Launch visual odometry instead of using external odometry.'),
        'icp_odometry': ('false', 'Launch ICP odometry.'),
        'odom_topic': ('/bcr_bot/odom', 'External odometry topic.'),
        'odom_frame_id': ('', 'Leave empty to use odom_topic; set a frame to use TF odometry.'),
        'approx_sync': ('true', 'Approximately synchronize RGB, depth and odometry.'),
        'qos': ('1', 'Sensor QoS: 1=Reliable, 2=Best Effort.'),
        'wait_for_transform': ('0.5', 'Seconds to wait for sensor-time TF transforms.'),
        'database_path': (
            os.path.expanduser('~/.ros/bcr_bot_rtabmap_robust.db'),
            'SLAM database; existing files are resumed, never automatically deleted.'),
        'args': (
            '--Reg/Force3DoF true --Optimizer/Robust true',
            'RTAB-Map core arguments: planar constraints and robust graph optimization.'),
        'rtabmap_viz': ('true', 'Launch the RTAB-Map visualization GUI.'),
        'rviz': ('false', 'Launch RViz.'),
    }

    declarations = [
        DeclareLaunchArgument(name, default_value=value, description=description)
        for name, (value, description) in defaults.items()
    ]
    rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('rtabmap_launch'),
            'launch', 'rtabmap.launch.py')),
        launch_arguments={
            name: LaunchConfiguration(name) for name in defaults
        }.items(),
    )
    return LaunchDescription([*declarations, rtabmap])
