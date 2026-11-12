#include <vector>
#include <memory>
#include "IModule.hpp"

class LatticeGrid {
private:
    int width, height;
    std::vector<double> f_curr;
    std::vector<double> f_next;
    
    // Direction vectors for D2Q9 streaming
    const int cx[9] = {0, 1, 0, -1, 0, 1, -1, -1, 1};
    const int cy[9] = {0, 0, 1, 0, -1, 1, 1, -1, -1};

    std::unique_ptr<ICollisionModel> collision_model;
    std::unique_ptr<IForceModule> force_module;

public:
    LatticeGrid(int w, int h) : width(w), height(h) {
        f_curr.resize(w * h * 9, 0.0);
        f_next.resize(w * h * 9, 0.0);
    }

    // Hot-swap modules at runtime for modular extensibility
    void set_collision_model(std::unique_ptr<ICollisionModel> model) {
        collision_model = std::move(model);
    }

    void set_force_module(std::unique_ptr<IForceModule> module) {
        force_module = std::move(module);
    }

    void step() {
        // 1. Collision Step
        if (collision_model) {
            // collision_model->collide(...)
        }

        // 2. Forcing / Feedback Injection Step
        if (force_module) {
            // force_module->apply_force(...)
        }

        // 3. Streaming Step (Propagate populations to neighboring nodes with periodic/bounce-back boundaries)
        stream();
    }

private:
    void stream() {
        // Standard D2Q9 pull/push streaming implementation optimized for cache locality
    }
};
