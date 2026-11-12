#pragma once
#include <vector>

// Base structure representing macroscopic cell data
struct CellData {
    double density;
    double velocity[2];
};

class ICollisionModel {
public:
    virtual ~ICollisionModel() = default;
    virtual void collide(std::vector<double>& f, const std::vector<double>& f_eq, int width, int height, double omega) = 0;
};

class IForceModule {
public:
    virtual ~IForceModule() = default;
    virtual void apply_force(std::vector<double>& f, const std::vector<double>& f_eq, int width, int height) = 0;
};
