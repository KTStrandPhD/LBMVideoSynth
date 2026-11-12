#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include "LatticeGrid.hpp"
#include "CollisionRules.hpp"
#include "ForcingRules.hpp"

void save_ppm(const std::string& filename, const std::vector<double>& density, int width, int height) {
    std::ofstream file(filename, std::ios::binary);
    file << "P6\n" << width << " " << height << "\n255\n";
    
    double min_d = density[0], max_d = density[0];
    for (double d : density) {
        if (d < min_d) min_d = d;
        if (d > max_d) max_d = d;
    }
    double range = (max_d - min_d > 1e-5) ? (max_d - min_d) : 1.0;

    std::vector<unsigned char> img(width * height * 3);
    for (size_t i = 0; i < density.size(); ++i) {
        unsigned char val = static_cast<unsigned char>(((density[i] - min_d) / range) * 255.0);
        img[i * 3 + 0] = val; // R
        img[i * 3 + 1] = val; // G
        img[i * 3 + 2] = val; // B
    }
    file.write(reinterpret_cast<char*>(img.data()), img.size());
}

int main() {
    std::cout << "Initializing Slow-Evolution LBM Video Synth..." << std::endl;

    const int width = 256;
    const int height = 256;
    const int total_steps = 400; // More steps for a slower, smoother evolution

    // Tune tau closer to 1.0 to slow down collision relaxation kinetics
    const double relaxation_time = 0.85; 

    // Gentle feedback gain to prevent instant saturation and let snow coarsen smoothly
    VideoFeedbackCollision collision_policy(1.05, 1.5);
    NoForcePolicy force_policy;

    LatticeGrid<VideoFeedbackCollision, NoForcePolicy> sim(
        width, height, relaxation_time, collision_policy, force_policy
    );

    // Initialize with a fine-grained random noise seed ("snowy" look)
    std::cout << "Seeding fine-grained snowy noise..." << std::endl;
    sim.initialize_random_perturbation(1.0, 0.03);

    std::cout << "Running simulation and exporting every frame..." << std::endl;
    for (int step = 0; step < total_steps; ++step) {
        sim.step();

        // Save every single frame for maximum smoothness
        std::string filename = "frame_" + std::to_string(step) + ".ppm";
        save_ppm(filename, sim.get_density_field(), width, height);

        if (step % 50 == 0) {
            std::cout << " -> Progress: Step " << step << "/" << total_steps << std::endl;
        }
    }

    std::cout << "Export complete! Generated " << total_steps << " frames." << std::endl;
    return 0;
}
