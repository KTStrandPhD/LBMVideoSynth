#pragma once

#include <cmath>

struct AffineParams {
    double zoom = 1.0;       // > 1.0 zooms in (outward tunnel), < 1.0 zooms out
    double rotation = 0.0;   // Angle in radians per step
    double shift_x = 0.0;    // Horizontal drift in lattice units per step
    double shift_y = 0.0;    // Vertical drift in lattice units per step

    bool is_identity() const {
        return std::abs(zoom - 1.0) < 1e-7 &&
               std::abs(rotation) < 1e-7 &&
               std::abs(shift_x) < 1e-7 &&
               std::abs(shift_y) < 1e-7;
    }
};
