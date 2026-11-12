#pragma once
#include <vector>
#include <array>
#include <random>
#include <algorithm>
#include "AffineTransform.hpp"

template <typename CollisionPolicy, typename ForcingPolicy>
class LatticeGrid {
  private:
      int width, height;
      std::vector<double> f_curr;
      std::vector<double> f_next;
      std::vector<double> f_eq;
      std::vector<double> f_warp_buf;
      
      double omega; // Relaxation frequency (1 / tau)

      // D2Q9 lattice velocity directions and weights
      const std::array<int, 9> cx = {0,  1,  0, -1,  0,  1, -1, -1,  1};
      const std::array<int, 9> cy = {0,  0,  1,  0, -1,  1,  1, -1, -1};
      const std::array<double, 9> w = {4.0/9.0, 1.0/9.0, 1.0/9.0, 1.0/9.0, 1.0/9.0, 
                                      1.0/36.0, 1.0/36.0, 1.0/36.0, 1.0/36.0};

      CollisionPolicy collision_policy;
      ForcingPolicy forcing_policy;

  public:
      LatticeGrid(int w, int h, double relaxation_time, CollisionPolicy col_pol = CollisionPolicy(), ForcingPolicy force_pol = ForcingPolicy())
          : width(w), height(h), omega(1.0 / relaxation_time), 
            collision_policy(col_pol), forcing_policy(force_pol) {
          int size = w * h * 9;
          f_curr.resize(size, 0.0);
          f_next.resize(size, 0.0);
          f_eq.resize(size, 0.0);
      }

      // Main simulation step executed entirely with static dispatch
      void step() {
          compute_macroscopic_and_equilibrium();
          
          // Static policy collision
          collision_policy.apply(f_curr, f_eq, width, height, omega);
          
          // Static policy forcing/feedback
          forcing_policy.apply(f_curr, width, height);
          
          // Streaming step
          stream();
      }

      // Method 1: Initialize with uniform density and random perturbation (classic spinodal seed)
    void initialize_random_perturbation(double base_rho = 1.0, double perturbation_amplitude = 0.01) {
        std::mt19937 generator(1337); // Fixed seed for reproducibility or use std::random_device
        std::uniform_real_distribution<double> distribution(-perturbation_amplitude, perturbation_amplitude);

        int size = width * height;
        for (int idx = 0; idx < size; ++idx) {
            int base_idx = idx * 9;
            // Add small random noise to local density
            double local_rho = base_rho + distribution(generator);
            
            // Initialize populations to local equilibrium with zero velocity
            for (int i = 0; i < 9; ++i) {
                f_curr[base_idx + i] = w[i] * local_rho;
            }
        }
    }

    // Method 2: Initialize from an external 2D buffer (e.g., image/video frame input)
    void initialize_from_buffer(const std::vector<double>& input_buffer, double base_rho = 1.0) {
        // Maps external pixel values (0.0 to 1.0) to density variations
        int size = width * height;
        for (int idx = 0; idx < size; ++idx) {
            int base_idx = idx * 9;
            double local_rho = base_rho + (input_buffer[idx] - 0.5) * 0.1;

            for (int i = 0; i < 9; ++i) {
                f_curr[base_idx + i] = w[i] * local_rho;
            }
        }
    }

    void perturb_region(int cx, int cy, double radius, double delta_rho, double ux = 0.0, double uy = 0.0) {
      static constexpr double w[9] = {
          4.0 / 9.0,
          1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
          1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0
      };
      static constexpr int ex[9] = {0, 1, -1, 0,  0, 1, -1,  1, -1};
      static constexpr int ey[9] = {0, 0,  0, 1, -1, 1,  1, -1, -1};

      const int r_bound = static_cast<int>(std::ceil(radius * 2.5));
      const double two_sigma_sq = 2.0 * radius * radius;
      const double u_sq = ux * ux + uy * uy;

      for (int dy = -r_bound; dy <= r_bound; ++dy) {
          for (int dx = -r_bound; dx <= r_bound; ++dx) {
              const double dist_sq = static_cast<double>(dx * dx + dy * dy);
              if (dist_sq > r_bound * r_bound) continue;

              // Gaussian spatial envelope
              const double env = std::exp(-dist_sq / two_sigma_sq);
              const double local_rho = delta_rho * env;
              const double local_ux = ux * env;
              const double local_uy = uy * env;

              // Periodic boundary wrap
              int gx = (cx + dx) % width;
              if (gx < 0) gx += width;
              int gy = (cy + dy) % height;
              if (gy < 0) gy += height;

              const int base_idx = (gy * width + gx) * 9;

              for (int q = 0; q < 9; ++q) {
                  const double eu = ex[q] * local_ux + ey[q] * local_uy;
                  const double df = w[q] * local_rho * (
                      1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * (u_sq * env * env)
                  );
                  f_curr[base_idx + q] = std::max(0.0, f_curr[base_idx + q] + df);
              }
          }
      }
    }

    void apply_affine_transform(const AffineParams& params) {
      if (params.is_identity()) return;

      if (f_warp_buf.size() != f_curr.size()) {
          f_warp_buf.resize(f_curr.size());
      }

      const double cx = width * 0.5;
      const double cy = height * 0.5;
      const double inv_zoom = 1.0 / params.zoom;
      const double cos_t = std::cos(params.rotation);
      const double sin_t = std::sin(params.rotation);

      for (int y = 0; y < height; ++y) {
          const double dy = y - cy;
          for (int x = 0; x < width; ++x) {
              const double dx = x - cx;

              // Inverse affine transform (maps destination pixel back to source)
              double src_x = inv_zoom * (dx * cos_t + dy * sin_t) + cx - params.shift_x;
              double src_y = inv_zoom * (-dx * sin_t + dy * cos_t) + cy - params.shift_y;

              // Periodic boundary wrapping
              src_x = std::fmod(src_x, static_cast<double>(width));
              if (src_x < 0.0) src_x += width;
              src_y = std::fmod(src_y, static_cast<double>(height));
              if (src_y < 0.0) src_y += height;

              // Bilinear interpolation indices and weights
              const int x0 = static_cast<int>(src_x);
              const int y0 = static_cast<int>(src_y);
              const int x1 = (x0 + 1) % width;
              const int y1 = (y0 + 1) % height;

              const double wx = src_x - x0;
              const double wy = src_y - y0;
              const double w00 = (1.0 - wx) * (1.0 - wy);
              const double w10 = wx * (1.0 - wy);
              const double w01 = (1.0 - wx) * wy;
              const double w11 = wx * wy;

              const int dst_base = (y * width + x) * 9;
              const int idx00 = (y0 * width + x0) * 9;
              const int idx10 = (y0 * width + x1) * 9;
              const int idx01 = (y1 * width + x0) * 9;
              const int idx11 = (y1 * width + x1) * 9;

              for (int q = 0; q < 9; ++q) {
                  f_warp_buf[dst_base + q] =
                      w00 * f_curr[idx00 + q] +
                      w10 * f_curr[idx10 + q] +
                      w01 * f_curr[idx01 + q] +
                      w11 * f_curr[idx11 + q];
              }
          }
      }

      std::swap(f_curr, f_warp_buf);
    }

    void inject_density_field(const double* target_rho, double alpha) {
      if (alpha <= 0.0) return;
      if (alpha > 1.0) alpha = 1.0;

      static constexpr double w[9] = {
          4.0 / 9.0,
          1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
          1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0
      };

      const double keep = 1.0 - alpha;
      const int num_cells = width * height;

      for (int idx = 0; idx < num_cells; ++idx) {
          const double rho_in = target_rho[idx];
          const int base = idx * 9;
          for (int q = 0; q < 9; ++q) {
              f_curr[base + q] = keep * f_curr[base + q] + alpha * w[q] * rho_in;
          }
      }
    }

    void inject_equilibrium_field(const double* target_rho,
                              const double* ux_field,
                              const double* uy_field,
                              double alpha) {
      if (alpha <= 0.0) return;
      if (alpha > 1.0) alpha = 1.0;

      static constexpr double w[9] = {
          4.0 / 9.0,
          1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0, 1.0 / 9.0,
          1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0, 1.0 / 36.0
      };
      static constexpr int ex[9] = {0, 1, -1, 0,  0, 1, -1,  1, -1};
      static constexpr int ey[9] = {0, 0,  0, 1, -1, 1,  1, -1, -1};

      const double keep = 1.0 - alpha;
      const int num_cells = width * height;

      for (int idx = 0; idx < num_cells; ++idx) {
          const double rho_in = target_rho[idx];
          const double ux = ux_field ? ux_field[idx] : 0.0;
          const double uy = uy_field ? uy_field[idx] : 0.0;
          const double u_sq = ux * ux + uy * uy;

          const int base = idx * 9;
          for (int q = 0; q < 9; ++q) {
              const double eu = ex[q] * ux + ey[q] * uy;
              const double feq = w[q] * rho_in * (
                  1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * u_sq
              );
              f_curr[base + q] = keep * f_curr[base + q] + alpha * feq;
          }
      }
    }

    // Extract current macroscopic density field across all nodes
    std::vector<double> get_density_field() const {
        std::vector<double> density(width * height, 0.0);
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                int node_idx = y * width + x;
                int base_idx = node_idx * 9;
                
                double rho = 0.0;
                for (int i = 0; i < 9; ++i) {
                    rho += f_curr[base_idx + i];
                }
                density[node_idx] = rho;
            }
        }
        return density;
    }

    void set_feedback_gain(double gain) {
      // Updates collision policy parameters dynamically at runtime
    }

    void set_relaxation_time(double tau) {
      omega = 1.0 / tau;
    }

    int get_width() const { return width; }
    int get_height() const { return height; }

  private:
      inline void compute_macroscopic_and_equilibrium() {
          // Standard D2Q9 density, velocity, and equilibrium calculation
          for (int y = 0; y < height; ++y) {
              for (int x = 0; x < width; ++x) {
                  int base_idx = (y * width + x) * 9;
                  
                  double rho = 0.0;
                  double mx = 0.0;
                  double my = 0.0;

                  for (int i = 0; i < 9; ++i) {
                      double f_val = f_curr[base_idx + i];
                      rho += f_val;
                      mx += f_val * cx[i];
                      my += f_val * cy[i];
                  }

                  double ux = (rho > 0.0) ? (mx / rho) : 0.0;
                  double uy = (rho > 0.0) ? (my / rho) : 0.0;
                  double u_sq = ux * ux + uy * uy;

                  for (int i = 0; i < 9; ++i) {
                      double cu = cx[i] * ux + cy[i] * uy;
                      f_eq[base_idx + i] = w[i] * rho * (1.0 + 3.0 * cu + 4.5 * cu * cu - 1.5 * u_sq);
                  }
              }
          }
      }

      inline void stream() {
          // Pull streaming implementation with periodic boundaries
          for (int y = 0; y < height; ++y) {
              for (int x = 0; x < width; ++x) {
                  int target_idx = y * width + x;
                  
                  for (int i = 0; i < 9; ++i) {
                      int prev_x = (x - cx[i] + width) % width;
                      int prev_y = (y - cy[i] + height) % height;
                      int source_idx = prev_y * width + prev_x;

                      f_next[(target_idx * 9) + i] = f_curr[(source_idx * 9) + i];
                  }
              }
          }
          f_curr.swap(f_next);
      }
};
