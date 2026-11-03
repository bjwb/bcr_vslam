# BCR Bot: RTAB-Map + Nav2 VoxelLayer

`rtabmap_voxel_nav.launch.py`는 Nav2와 이 패키지의 `remapper.py`로 RGB-D
주행을 구성합니다. `config/rtabmap_voxel_nav.yaml`과
`rviz/rtabmap_voxel_nav.rviz`도 `vslam_bringup`에서 설치합니다.

## 실행

각 터미널에서 `source ~/jwb_ws/install/setup.bash`를 실행합니다.
로봇/시뮬레이터가 센서, odometry, TF를 먼저 발행하고 있어야 합니다.
시뮬레이터가 이미 실행 중이면 다시 실행하지 않습니다.

```bash
ros2 launch vslam_bringup ign.launch.py camera_enabled:=true stereo_camera_enabled:=false
```

현재 `rtabmap_robust.launch.py`가 실행 중이면, 해당 RTAB-Map에 Nav2만 연결합니다.
이 경우 기존 RTAB-Map의 SLAM/localization 모드와 DB 설정이 유지됩니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py start_rtabmap:=false
```

RTAB-Map을 함께 시작하여 저장 DB로 위치 추정하며 주행하려면 다음을 사용합니다.
먼저 따로 실행 중인 RTAB-Map launch를 종료하고 시뮬레이터는 계속 실행합니다.
기본 DB는 `~/.ros/bcr_bot_rtabmap_robust.db`이며, 이 모드에서는 읽기 전용입니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py
```

다른 저장 DB를 선택할 수도 있습니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py database_path:=/absolute/path/map.db
```

## 기존 DB를 필터링한 지도로 주행

다시 주행하며 SLAM할 필요 없이, 기존 DB의 저장된 위치와 RGB-D로 바닥을
재분류한 2D 지도를 사용할 수 있습니다. DB/위치 추정은 유지하고 Nav2의
전역 지도 입력만 선택합니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py \
  grid_map_yaml:=$(ros2 pkg prefix --share vslam_bringup)/config/maps/rtabmap_filtered_008.yaml
```

이 지도는 `bcr_bot_rtabmap_robust.db`의 저장된 최적화 위치 390개에서,
`Grid/NormalsSegmentation=false`, `Grid/MaxGroundHeight=0.08`,
`Grid/MaxObstacleHeight=1.5`로 생성했습니다. 해당 DB로 위치 추정할 때 사용합니다.
다른 DB에는 그 DB와 같은 좌표계를 사용하는 지도를 지정해야 합니다.

`/rtabmap/map`에는 기존 RTAB-Map 지도가 남고, `/rtabmap/filtered_map`에
필터 지도를 별도로 발행합니다. Nav2 static layer와 RViz Map 표시는
필터 지도로 연결됩니다. RTAB-Map GUI의 원본 DB/그래프 표시는 유지됩니다.
실시간 voxel 장애물 입력은 계속 사용합니다. `grid_map_yaml`을 생략하면
기존의 실시간 RTAB-Map 지도를 사용합니다.

이 파일은 고정된 저장 지도이므로, 새 지도를 계속 만드는 mapping 모드에서는
`grid_map_yaml`을 생략합니다.

## 새 지도 매핑

새 지도를 그리며 주행하려면 아래처럼 별도 DB 이름을 지정합니다.
이미 존재하는 DB를 지정하면 그 DB에 이어서 기록합니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py \
  localization:=false database_path:=$HOME/.ros/bcr_bot_voxel_mapping.db
```

RViz의 **2D Pose Estimate**로 저장 지도 위의 초기 위치를 지정하고,
**Nav2 Goal** 도구로 목표 위치와 방향을 지정합니다. 위치 추정과 지도 정합을
확인한 후 목표를 지정합니다. MapGraph, RTAB Node IDs, Marked Voxels 표시를
설정에 포함했습니다. 노드 ID/그래프는 RTAB-Map이 해당 토픽을 발행할 때 보입니다.

RTAB-Map GUI도 기본으로 함께 열립니다. `rtabmap_viz:=false`로 끌 수 있으며,
RViz는 별도로 `rviz:=false`로 끕니다. `start_rtabmap:=false`여도 GUI는 기존
`/rtabmap/rtabmap`에 연결합니다. 기존 launch가 이미 GUI를 띄웠다면 새 launch에는
`rtabmap_viz:=false`를 지정해 그 창을 계속 사용합니다.

`bcr_bot`의 `nav2.launch.py`와 이 launch는 각각 Nav2 서버와 속도 relay를 시작하므로
하나만 실행합니다. `map -> odom` TF는 RTAB-Map이 담당합니다.

## 연결과 설정

| 역할 | 토픽/모듈 |
|---|---|
| 저장 지도 / SLAM 지도 | `/rtabmap/map` |
| 장애물 센서 | `/bcr_bot/kinect_camera/points`, `PointCloud2` |
| odometry | `/bcr_bot/odom`, child frame `base_footprint` |
| 전역 경로 | NavFn A*, `/plan` |
| 경로 추종 | RotationShim + RegulatedPurePursuit |
| 최종 속도 | `/cmd_vel` → `remapper.py` → `/bcr_bot/cmd_vel` |
| voxel 표시 | `/local_costmap/voxel_grid` → `/local_costmap/voxel_marked_cloud` |

전역 costmap은 static + voxel + inflation, 지역 costmap은 voxel + inflation입니다.
voxel layer는 3차원 장애물을 누적/소거하여 2차원 costmap에 반영합니다.
바닥 위를 주행하는 로봇의 경로는 2차원입니다.

초기값은 높이 0.08–1.5 m, 수직 voxel 16개 × 0.10 m, 수평 해상도 0.05 m,
최대 직진 속도 0.2 m/s입니다. 높이는 각 costmap의 기준 좌표계에서 측정합니다.
`base_footprint`에 맞춘 직사각형 footprint와 0.7 m inflation을 사용합니다.
낮은 장애물도 검출해야 하면 YAML의 `min_obstacle_height`를 조정합니다.

카메라 이미지/CameraInfo의 frame은 `kinect_camera_optical`, Gazebo의 X축 전방
raw points frame은 `kinect_camera`여야 합니다. 현재 Ignition bridge의 설정과
일치하며, PointCloud2의 frame을 optical로 임의 변경하지 않습니다.

`use_sim_time`, `autostart`, `start_rtabmap`, `localization`, `database_path`,
`initial_pose`, `points_topic`, `map_topic`, `grid_map_yaml`, `grid_map_topic`,
`odom_topic`, `cmd_vel_topic`,
`params_file`, `rtabmap_viz`, `gui_cfg`, `rviz`, `rviz_config`를 launch 인자로 바꿀 수 있습니다.
`initial_pose` 형식은 `'x y z roll pitch yaw'`입니다.
`start_rtabmap:=false`이면 `localization`, `database_path`, `initial_pose`는
이미 실행 중인 RTAB-Map의 설정을 바꾸지 않습니다.

## 검증

저장소 분리 후 두 패키지의 `colcon build`, 6개 launch의 `--show-args`,
Fortress/Harmonic RGB-D 모델의 Xacro 확장, 설치된 spawn/설정/지도/relay 경로를
확인했습니다. 이 과정에서 시뮬레이터나 Nav2 프로세스는 시작하지 않았습니다.

아래는 분리 전 ROS 2 Humble / Nav2 1.1.20 구성에서 기록한 검증입니다.
별도 ROS domain에서 합성 지도/TF/odometry/PointCloud2로 확인했습니다.

- Nav2 lifecycle 모듈 7개 활성화.
- 두 costmap에서 카메라 장애물이 lethal cost로 반영되고 바닥 샘플은 제외됨.
- 장애물을 우회하는 전역 경로 생성, controller 및 속도 relay 출력, 모의 로봇 이동.
- 저장 DB localization에서 지도/그래프 발행, `/initialpose` 연결,
  종료 후 원본 DB SHA-256 동일.

실제 Gazebo 로봇에 목표를 보내 주행시키는 검증은 수행하지 않았습니다.
