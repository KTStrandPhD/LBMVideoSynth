#pragma once
#include <vector>

class NoForcePolicy {
public:
    inline void apply(std::vector<double>& f, int width, int height) {
        // Do nothing
    }
};

class ExternalNoiseForcePolicy {
public:
    inline void apply(std::vector<double>& f, int width, int height) {
        // Inject external forces or stochastic noise for video texture generation
    }
};
