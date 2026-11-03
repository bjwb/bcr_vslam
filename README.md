# vslam_bringup

BCR Bot의 RGB-D spawn/bridge, RTAB-Map SLAM과 Nav2 실행을 위한 ROS 2 패키지입니다.
로봇 URDF, mesh, 시뮬레이션 world는 `bcr_bot` 패키지에서 가져옵니다.
`bcr_bot`에는 Gazebo Fortress/Harmonic의 Kinect 센서를 `rgbd_camera`로
변경한 모델이 필요합니다.

## 빌드

ROS 2와 Nav2 환경을 불러온 터미널에서 실행합니다. 두 저장소는 같은
워크스페이스의 `src/` 아래에 둡니다.

```bash
cd ~/jwb_ws
rosdep install --from-paths src/bcr_bot src/vslam_bringup --ignore-src -r -y
colcon build --packages-select bcr_bot vslam_bringup
source install/setup.bash
```

## 실행

각 터미널에서 `source ~/jwb_ws/install/setup.bash`를 실행합니다.

Gazebo Fortress에서 로봇과 RGB-D bridge를 시작합니다.

```bash
ros2 launch vslam_bringup ign.launch.py camera_enabled:=true stereo_camera_enabled:=false
```

Gazebo Harmonic에서는 같은 인자로 `gz.launch.py`를 사용합니다.
시뮬레이터가 이미 실행 중이면 world launch 대신 아래 spawn launch를 사용합니다.
이미 로봇과 센서 bridge가 실행 중이면 spawn도 다시 실행하지 않습니다.

```bash
ros2 launch vslam_bringup bcr_bot_ign_spawn.launch.py
# Harmonic: bcr_bot_gz_spawn.launch.py
```

RTAB-Map으로 RGB-D 지도를 만듭니다. 기존 DB를 지정하면 이어서 기록하므로,
새 매핑을 시작할 때는 사용하지 않은 DB 경로를 지정합니다.

```bash
ros2 launch vslam_bringup rtabmap_robust.launch.py \
  database_path:=$HOME/.ros/bcr_bot_rtabmap_robust.db
```

저장 DB로 위치를 추정하며 Nav2를 실행하려면 별도로 실행한 RTAB-Map launch를
종료한 뒤 아래 명령을 사용합니다. DB는 읽기 전용으로 열립니다.

```bash
ros2 launch vslam_bringup rtabmap_voxel_nav.launch.py
```

이미 실행 중인 RTAB-Map에 Nav2를 연결하려면 `start_rtabmap:=false`를 지정합니다.

## 파일

- `launch/ign.launch.py`, `launch/gz.launch.py`: world 실행 및 RGB-D 로봇 spawn.
- `launch/bcr_bot_*_spawn.launch.py`: 로봇 spawn, TF 및 Gazebo/ROS sensor bridge.
- `launch/rtabmap_robust.launch.py`: 외부 odometry를 사용하는 RGB-D SLAM.
- `launch/rtabmap_voxel_nav.launch.py`: RTAB-Map과 Nav2 voxel costmap.
- `config/`, `rviz/`, `scripts/`: Nav2 설정, 필터 지도, RViz 설정 및 속도 relay.

카메라 토픽은 [RGB-D 카메라](docs/rgbd_camera.md), localization/매핑 및
필터 지도 사용법은 [RTAB-Map + Nav2](docs/rtabmap_voxel_nav.md)를 참조합니다.

spawn/world launch와 `remapper.py`는 Apache-2.0 라이선스의
[bcr_bot](https://github.com/blackcoffeerobotics/bcr_bot)에서 가져와 이 패키지에
맞게 수정했습니다. 모델과 world는 `bcr_bot`을 통해 설치합니다.
