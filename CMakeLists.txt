cmake_minimum_required(VERSION 3.5)
project(vslam_bringup)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config rviz docs
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS scripts/remapper.py
  DESTINATION lib/${PROJECT_NAME}
)

install(FILES README.md LICENSE
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
