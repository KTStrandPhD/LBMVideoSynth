#pragma once
#include <vector>
#include <cmath>

class StandardBGKCollision {
  public:
      inline void apply(std::vector<double>& f_curr, const std::vector<double>& f_eq, int width, int height, double omega) {
          int num_elements = width * height * 9;
          for (int i = 0; i < num_elements; ++i) {
              f_curr[i] = f_curr[i] - omega * (f_curr[i] - f_eq[i]);
          }
      }
  };

class VideoFeedbackCollision {
  private:
      double feedback_gain;
      double saturation_limit;

  public:
      VideoFeedbackCollision(double gain = 1.2, double limit = 2.0) 
          : feedback_gain(gain), saturation_limit(limit) {}

      inline void apply(std::vector<double>& f_curr, const std::vector<double>& f_eq, int width, int height, double omega) {
          int num_nodes = width * height;
          for (int node = 0; node < num_nodes; ++node) {
              int base_idx = node * 9;
              
              // Apply collision + nonlinear feedback transformation across populations
              for (int i = 0; i < 9; ++i) {
                  double collided = f_curr[base_idx + i] - omega * (f_curr[base_idx + i] - f_eq[base_idx + i]);
                  
                  // Smooth sigmoidal clipping modeling analog video mixer saturation
                  f_curr[base_idx + i] = saturation_limit * std::tanh(collided * feedback_gain / saturation_limit);
              }
          }
      }
};
