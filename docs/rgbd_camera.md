## RGB-D camera in Fortress and Harmonic

The `camera_enabled` option enables the RGB-D sensor attached to the existing
`kinect_camera` link. It produces registered RGB and depth images from one sensor
at 640 x 480 and a configured update rate of 30 Hz, with clipping from 0.05 to 8 m.

After changing the model or launch files, rebuild both packages and restart the
simulation so that the updated sensor is spawned:

```bash
cd ~/ros2_ws
colcon build --packages-select bcr_bot vslam_bringup
source install/setup.bash
ros2 launch vslam_bringup ign.launch.py camera_enabled:=true stereo_camera_enabled:=false
```

For Harmonic, use `gz.launch.py` with the same camera options.

| ROS 2 topic | Message type | Content |
|---|---|---|
| `/bcr_bot/kinect_camera/image` | `sensor_msgs/msg/Image` | RGB image (`rgb8`) |
| `/bcr_bot/kinect_camera/depth_image` | `sensor_msgs/msg/Image` | Depth image (`32FC1`, meters) |
| `/bcr_bot/kinect_camera/camera_info` | `sensor_msgs/msg/CameraInfo` | Shared camera calibration |
| `/bcr_bot/kinect_camera/points` | `sensor_msgs/msg/PointCloud2` | Colored point cloud |

The former depth-only image topic `/bcr_bot/kinect_camera` is replaced by
`/bcr_bot/kinect_camera/depth_image`. The CameraInfo and point-cloud topic names
are retained. RGB-D bridging runs only when `camera_enabled` is true. The bridge
uses lazy subscriptions so image and point-cloud data is transferred only when
a ROS subscriber requests it.

Check image metadata without printing the pixel arrays:

```bash
ros2 topic echo /bcr_bot/kinect_camera/image --once --no-arr
ros2 topic echo /bcr_bot/kinect_camera/depth_image --once --no-arr
ros2 topic echo /bcr_bot/kinect_camera/camera_info --once
```

For the ORB-SLAM3 ROS 2 wrapper, select `sensor_config:=rgbd` and set the ROS
parameters to:

```yaml
rgb_image_topic_name: /bcr_bot/kinect_camera/image
depth_image_topic_name: /bcr_bot/kinect_camera/depth_image
```

The ORB-SLAM3 calibration file must match this camera, using the intrinsics in
CameraInfo, 640 x 480 resolution, and the configured 30 Hz rate. The Gazebo RGB
stream uses RGB channel order (`Camera.RGB: 1` in the legacy ORB-SLAM3 settings
format), and its floating-point depth is already in meters (`DepthMapFactor: 1.0`).
