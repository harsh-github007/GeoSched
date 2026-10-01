#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/original/src/GeoSim"
"${CXX:-clang++}" -O2 -pthread -std=c++11 -DGEO ConfigAccessor.cpp DataCenterProxy.cpp Job.cpp main.cpp DataCenter.cpp GoogleTrace.cpp Node.cpp common.cpp -o GeoSim
printf 'Built cost-aware GeoSim. Run from original/src/GeoSim with ./GeoSim.\n'
