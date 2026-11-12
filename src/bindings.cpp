#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "RGBVideoGrid.hpp"

namespace py = pybind11;

PYBIND11_MODULE(lbm_video_engine, m) {
    py::class_<VideoFeedbackCollision>(m, "VideoFeedbackCollision")
        .def(py::init<double, double>(), py::arg("gain") = 1.05, py::arg("limit") = 1.5);

    py::class_<RGBVideoGrid>(m, "RGBVideoGrid")
        .def(py::init<int, int, double, double, double, 
                      const VideoFeedbackCollision&, 
                      const VideoFeedbackCollision&, 
                      const VideoFeedbackCollision&>(),
             py::arg("width"), py::arg("height"), 
             py::arg("tau_r"), py::arg("tau_g"), py::arg("tau_b"),
             py::arg("col_r"), py::arg("col_g"), py::arg("col_b"))
        .def("step", &RGBVideoGrid::step)
        .def("initialize_random_perturbation", &RGBVideoGrid::initialize_random_perturbation)
        .def("set_relaxation_times", &RGBVideoGrid::set_relaxation_times)
        .def("set_affine_transform", &RGBVideoGrid::set_affine_transform,
             py::arg("zoom") = 1.0, py::arg("rotation") = 0.0,
             py::arg("shift_x") = 0.0, py::arg("shift_y") = 0.0)
        .def("perturb_region", &RGBVideoGrid::perturb_region,
             py::arg("cx"), py::arg("cy"), py::arg("radius") = 8.0,
             py::arg("amplitude") = 0.25, py::arg("ux") = 0.0, py::arg("uy") = 0.0)
        .def("get_rgb_density_field", [](const RGBVideoGrid &self) {
            auto rgb = self.get_rgb_density_field();
            return py::array_t<double>(rgb.size(), rgb.data());
        })
        .def("inject_rgb_frame", [](RGBVideoGrid &self,
                                    py::array_t<double, py::array::c_style | py::array::forcecast> frame,
                                    double alpha,
                                    double contrast) {
            py::buffer_info buf = frame.request();
            const size_t expected = static_cast<size_t>(self.get_width() * self.get_height() * 3);
            if (static_cast<size_t>(buf.size) != expected) {
                throw std::runtime_error("inject_rgb_frame: expected flat or (H, W, 3) array matching grid dimensions");
            }
            self.inject_rgb_frame(static_cast<const double*>(buf.ptr), alpha, contrast);
            }, py::arg("frame"), py::arg("alpha") = 0.08, py::arg("contrast") = 0.35);
}
