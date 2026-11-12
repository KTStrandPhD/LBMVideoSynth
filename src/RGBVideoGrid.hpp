#pragma once

#include <vector>
#include "LatticeGrid.hpp"
#include "CollisionRules.hpp"
#include "ForcingRules.hpp"

class RGBVideoGrid {
private:
    int width, height;
    using SingleGrid = LatticeGrid<VideoFeedbackCollision, NoForcePolicy>;
    
    AffineParams warp_params;

    SingleGrid grid_r;
    SingleGrid grid_g;
    SingleGrid grid_b;

public:
    RGBVideoGrid(int w, int h, 
                 double tau_r, double tau_g, double tau_b,
                 const VideoFeedbackCollision& col_r,
                 const VideoFeedbackCollision& col_g,
                 const VideoFeedbackCollision& col_b)
        : width(w), height(h),
          grid_r(w, h, tau_r, col_r, NoForcePolicy()),
          grid_g(w, h, tau_g, col_g, NoForcePolicy()),
          grid_b(w, h, tau_b, col_b, NoForcePolicy()) {}

    void initialize_random_perturbation(double base_rho = 1.0, double amp = 0.03) {
        // Slightly offset initial seeds per channel for rich chromatic variation
        grid_r.initialize_random_perturbation(base_rho, amp);
        grid_g.initialize_random_perturbation(base_rho, amp * 1.02);
        grid_b.initialize_random_perturbation(base_rho, amp * 0.98);
    }

    void perturb_region(int cx, int cy, double radius, double amplitude, double ux = 0.0, double uy = 0.0) {
      grid_r.perturb_region(cx, cy, radius, amplitude, ux, uy);
      grid_g.perturb_region(cx, cy, radius, amplitude * 0.85, ux, uy);
      grid_b.perturb_region(cx, cy, radius, amplitude * 0.70, ux, uy);
    }

    void set_affine_transform(double zoom, double rotation, double shift_x, double shift_y) {
        warp_params.zoom = zoom;
        warp_params.rotation = rotation;
        warp_params.shift_x = shift_x;
        warp_params.shift_y = shift_y;
    }

    void step() {
        grid_r.step();
        grid_g.step();
        grid_b.step();

        if (!warp_params.is_identity()) {
            grid_r.apply_affine_transform(warp_params);
            grid_g.apply_affine_transform(warp_params);
            grid_b.apply_affine_transform(warp_params);
        }
    }

    void inject_rgb_frame(const double* rgb_norm,
                      const double* ux_field,
                      const double* uy_field,
                      double alpha,
                      double contrast = 0.45) {
      if (alpha <= 0.0) return;

      const size_t num_cells = static_cast<size_t>(width) * static_cast<size_t>(height);
      std::vector<double> rho_r(num_cells);
      std::vector<double> rho_g(num_cells);
      std::vector<double> rho_b(num_cells);

      for (size_t i = 0; i < num_cells; ++i) {
          rho_r[i] = 1.0 + contrast * (rgb_norm[i * 3 + 0] - 0.5);
          rho_g[i] = 1.0 + contrast * (rgb_norm[i * 3 + 1] - 0.5);
          rho_b[i] = 1.0 + contrast * (rgb_norm[i * 3 + 2] - 0.5);
      }

      grid_r.inject_equilibrium_field(rho_r.data(), ux_field, uy_field, alpha);
      grid_g.inject_equilibrium_field(rho_g.data(), ux_field, uy_field, alpha);
      grid_b.inject_equilibrium_field(rho_b.data(), ux_field, uy_field, alpha);
    }

    void set_relaxation_times(double tau_r, double tau_g, double tau_b) {
        grid_r.set_relaxation_time(tau_r);
        grid_g.set_relaxation_time(tau_g);
        grid_b.set_relaxation_time(tau_b);
    }

    int get_width() const { return width; }
    int get_height() const { return height; }

    // Interleave R, G, B density fields into a single flat buffer (Size: Width * Height * 3)
    std::vector<double> get_rgb_density_field() const {
        auto dens_r = grid_r.get_density_field();
        auto dens_g = grid_g.get_density_field();
        auto dens_b = grid_b.get_density_field();

        std::vector<double> rgb(width * height * 3);
        for (size_t i = 0; i < static_size_t(width * height); ++i) {
            rgb[i * 3 + 0] = dens_r[i]; // Red
            rgb[i * 3 + 1] = dens_g[i]; // Green
            rgb[i * 3 + 2] = dens_b[i]; // Blue
        }
        return rgb;
    }

private:
    static constexpr size_t static_size_t(int val) { return static_cast<size_t>(val); }
};
