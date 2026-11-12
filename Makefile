CXX = g++
CXXFLAGS = -O3 -march=native -Wall -shared -std=c++17 -fPIC

# Automatically query Python and pybind11 include paths and extension suffix
INCLUDES = $(shell python3 -m pybind11 --includes) -Isrc
EXT_SUFFIX = $(shell python3-config --extension-suffix)

# Directories and Targets
BUILD_DIR = build
SRC_DIR = src
TARGET = $(BUILD_DIR)/lbm_video_engine$(EXT_SUFFIX)

# Source files (add additional .cpp files here as the project grows)
SRCS = $(SRC_DIR)/bindings.cpp $(SRC_DIR)/LatticeGrid.cpp

.PHONY: all clean test_bin

all: $(TARGET)

$(TARGET): $(SRCS) | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(SRCS) -o $(TARGET)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Optional target to keep compiling your standalone C++ test binary
test_bin: $(SRC_DIR)/main.cpp $(SRC_DIR)/LatticeGrid.cpp
	$(CXX) -O3 -march=native -std=c++17 -Isrc $^ -o test_synth

clean:
	rm -rf $(BUILD_DIR) test_synth
