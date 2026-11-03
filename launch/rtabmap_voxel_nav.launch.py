"""RTAB-Map localization/mapping with Nav2 and RGB-D voxel costmaps.

Start ign.launch.py first. When rtabmap_robust.launch.py is already running,
set start_rtabmap:=false to attach Nav2 to that instance.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription,
    OpaqueFunction, TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def _setup(context):
    def value(name):
        return LaunchConfiguration(name).perform(context)

    def enabled(name):
        return value(name).lower() in ('true', '1', 'yes')

    sim_time = enabled('use_sim_time')
    localization = enabled('localization')
    start_rtabmap = enabled('start_rtabmap')
    database = os.path.expanduser(value('database_path'))
    grid_map_yaml = os.path.expanduser(value('grid_map_yaml'))
    navigation_map_topic = value('grid_map_topic') if grid_map_yaml else value('map_topic')
    if grid_map_yaml and not os.path.isfile(grid_map_yaml):
        raise RuntimeError(f'Navigation grid YAML does not exist: {grid_map_yaml}')
    if grid_map_yaml and navigation_map_topic == value('map_topic'):
        raise RuntimeError('grid_map_topic must differ from the RTAB-Map map_topic.')
    if start_rtabmap and localization and not os.path.isfile(database):
        raise RuntimeError(
            f'Localization database does not exist: {database}. '
            'Choose an existing database or set localization:=false.')

    params = RewrittenYaml(
        source_file=value('params_file'),
        param_rewrites={
            'odom_topic': value('odom_topic'),
            'map_topic': navigation_map_topic,
            'local_costmap.local_costmap.ros__parameters.voxel_layer.camera.topic':
                value('points_topic'),
            'global_costmap.global_costmap.ros__parameters.voxel_layer.camera.topic':
                value('points_topic'),
        },
        convert_types=True,
    )

    # An optional filtered map supplies navigation geometry; RTAB-Map still
    # supplies localization/TF and publishes its original map on map_topic.
    grid_map_actions = []
    if grid_map_yaml:
        grid_map_actions = [
            Node(
                package='nav2_map_server', executable='map_server',
                name='filtered_map_server', namespace='rtabmap', output='screen',
                parameters=[{
                    'use_sim_time': sim_time,
                    'yaml_filename': os.path.abspath(grid_map_yaml),
                    'topic_name': navigation_map_topic,
                    'frame_id': 'map',
                }],
            ),
            Node(
                package='nav2_lifecycle_manager', executable='lifecycle_manager',
                name='lifecycle_manager_filtered_map', namespace='rtabmap',
                output='screen', parameters=[{
                    'use_sim_time': sim_time,
                    'autostart': enabled('autostart'),
                    'node_names': ['/rtabmap/filtered_map_server'],
                }],
            ),
        ]

    rtabmap = Node(
        package='rtabmap_slam', executable='rtabmap', name='rtabmap',
        namespace='rtabmap', output='screen',
        condition=IfCondition(LaunchConfiguration('start_rtabmap')),
        parameters=[{
            'use_sim_time': sim_time,
            'frame_id': 'base_footprint',
            'map_frame_id': 'map',
            'odom_frame_id': '',
            'database_path': database,
            'initial_pose': value('initial_pose'),
            'subscribe_rgb': True,
            'subscribe_depth': True,
            'subscribe_scan': False,
            'subscribe_scan_cloud': False,
            'approx_sync': True,
            'qos_image': 1,
            'qos_camera_info': 1,
            'qos_odom': 1,
            'wait_for_transform': 0.5,
            'map_always_update': True,
            'latch': True,
            'publish_tf': True,
            'use_action_for_goal': False,
            'Mem/IncrementalMemory': 'false' if localization else 'true',
            'Mem/InitWMWithAllNodes': 'true',
            'Mem/LocalizationReadOnly': 'true' if localization else 'false',
            'Reg/Force3DoF': 'true',
            'Optimizer/Robust': 'true',
            'Grid/NormalsSegmentation': 'false',  # 높이 기준으로 바닥 분리
            'Grid/MaxGroundHeight': '0.08',       # 바닥으로 취급할 최대 높이
            'Grid/MaxObstacleHeight': '1.5',       # 장애물로 사용할 최대 높이
        }],
        remappings=[
            ('rgb/image', '/bcr_bot/kinect_camera/image'),
            ('depth/image', '/bcr_bot/kinect_camera/depth_image'),
            ('rgb/camera_info', '/bcr_bot/kinect_camera/camera_info'),
            ('odom', value('odom_topic')),
            ('map', value('map_topic')),
            ('initialpose', '/initialpose'),
            ('goal_out', '/goal_pose'),
        ],
    )

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('nav2_bringup'),
            'launch', 'navigation_launch.py')),
        launch_arguments={
            'namespace': '',
            'use_sim_time': value('use_sim_time'),
            'autostart': value('autostart'),
            'params_file': params,
            'use_composition': 'False',
        }.items(),
    )

    # navigation_launch.py smooths controller commands onto /cmd_vel.
    # Relay commands to the simulator's command topic.
    velocity_relay = Node(
        package='vslam_bringup', executable='remapper.py',
        name='rtabmap_nav_cmd_vel', output='screen',
        parameters=[{'use_sim_time': sim_time}],
        remappings=[('bcr_bot/cmd_vel', value('cmd_vel_topic'))],
    )
    rviz = Node(
        package='rviz2', executable='rviz2', name='rtabmap_nav_rviz',
        condition=IfCondition(LaunchConfiguration('rviz')),
        arguments=['-d', value('rviz_config')],
        remappings=[('/rtabmap/map', navigation_map_topic)],
        parameters=[{'use_sim_time': sim_time}], output='screen',
    )
    rtabmap_viz = Node(
        package='rtabmap_viz', executable='rtabmap_viz',
        name='rtabmap_viz', namespace='rtabmap', output='screen',
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
        arguments=[os.path.expanduser(value('gui_cfg'))],
        parameters=[{
            'use_sim_time': sim_time,
            'frame_id': 'base_footprint',
            'odom_frame_id': '',
            'subscribe_rgb': True,
            'subscribe_depth': True,
            'subscribe_odom_info': False,
            'subscribe_scan': False,
            'subscribe_scan_cloud': False,
            'approx_sync': True,
            'qos_image': 1,
            'qos_camera_info': 1,
            'qos_odom': 1,
            'wait_for_transform': 0.5,
        }],
        remappings=[
            ('rgb/image', '/bcr_bot/kinect_camera/image'),
            ('depth/image', '/bcr_bot/kinect_camera/depth_image'),
            ('rgb/camera_info', '/bcr_bot/kinect_camera/camera_info'),
            ('odom', value('odom_topic')),
        ],
    )
    voxel_cloud = Node(
        package='nav2_costmap_2d', executable='nav2_costmap_2d_cloud',
        name='voxel_cloud', namespace='local_costmap',
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[{'use_sim_time': sim_time}], output='log',
    )
    actions = [rtabmap, *grid_map_actions, navigation,
               velocity_relay, rviz, rtabmap_viz, voxel_cloud]
    if start_rtabmap and localization:
        # Publish the saved grid after Nav2's static layer has subscribed.
        actions.append(TimerAction(period=5.0, actions=[ExecuteProcess(
            cmd=['ros2', 'service', 'call', '/rtabmap/rtabmap/publish_map',
                 'rtabmap_msgs/srv/PublishMap',
                 '{global_map: true, optimized: true, graph_only: false}'],
            output='log',
        )]))
    return actions


def generate_launch_description():
    share = get_package_share_directory('vslam_bringup')
    defaults = {
        'use_sim_time': ('true', 'Use the simulator clock.'),
        'autostart': ('true', 'Activate the Nav2 lifecycle nodes.'),
        'start_rtabmap': ('true', 'Start RTAB-Map; false attaches to an existing instance.'),
        'localization': ('true', 'Use a saved DB; false maps while navigating.'),
        'database_path': (os.path.expanduser('~/.ros/bcr_bot_rtabmap_robust.db'),
                          'RTAB-Map DB; localization opens it read-only.'),
        'initial_pose': ('', 'Optional initial map pose: x y z roll pitch yaw.'),
        'points_topic': ('/bcr_bot/kinect_camera/points', 'PointCloud2 input for both voxel layers.'),
        'map_topic': ('/rtabmap/map', 'RTAB-Map occupancy grid for the static layer.'),
        'grid_map_yaml': ('', 'Optional filtered grid YAML for Nav2/RViz; empty uses the RTAB-Map grid.'),
        'grid_map_topic': ('/rtabmap/filtered_map', 'Separate topic for the optional filtered navigation grid.'),
        'odom_topic': ('/bcr_bot/odom', 'Robot odometry.'),
        'cmd_vel_topic': ('/bcr_bot/cmd_vel', 'Final Twist command output.'),
        'params_file': (os.path.join(share, 'config', 'rtabmap_voxel_nav.yaml'), 'Nav2 parameters.'),
        'rtabmap_viz': ('true', 'Open the RTAB-Map GUI, also when attaching to an existing instance.'),
        'gui_cfg': (os.path.expanduser('~/.ros/rtabmap_gui.ini'), 'RTAB-Map GUI configuration file.'),
        'rviz': ('true', 'Open the navigation and voxel visualization.'),
        'rviz_config': (os.path.join(share, 'rviz', 'rtabmap_voxel_nav.rviz'), 'RViz configuration.'),
    }
    return LaunchDescription([
        *[DeclareLaunchArgument(k, default_value=v, description=d)
          for k, (v, d) in defaults.items()],
        OpaqueFunction(function=_setup),
    ])
