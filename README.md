# VideoSynthLBM

A real-time analog video feedback synthesizer powered by a D2Q9 Lattice Boltzmann Method (LBM) solver in C++17 and an interactive Python/Pygame interface bridged via `pybind11`.

By pairing BGK lattice hydrodynamics with a nonlinear $\tanh$ saturation operator, independent RGB channel relaxation times, spatial affine coordinate warping, and localized Gaussian perturbations, the engine simulates self-organizing spinodal patterns, chromatic dispersion, and optical CRT feedback tunnels in real time.

---

## Project Structure

```text
VideoSynthLBM/
├── Makefile                    # Builds the C++17 pybind11 shared library
├── build/                      # Compiled lbm_video_engine*.so module
├── src/
│   ├── LatticeGrid.hpp/.cpp    # Core D2Q9 solver, affine warp, & perturbation kernels
│   ├── CollisionRules.hpp      # Nonlinear sigmoidal video feedback collision policy
│   ├── ForcingRules.hpp        # External forcing policy interface
│   ├── AffineTransform.hpp     # Optical zoom, rotation, and pan parameter struct
│   ├── RGBVideoGrid.hpp        # Tri-channel (R, G, B) wrapper for chromatic synthesis
│   └── bindings.cpp            # Zero-copy pybind11 NumPy bindings
├── scripts/
│   ├── interactive_synth.py    # Real-time Pygame GUI & interactive synthesizer
│   └── visualize.py            # Offline batch simulation & GIF/MP4 renderer
├── testoutput/                 # Saved baseline test animations (.gif / .mp4)
└── latex/paper/                # Accompanying APS/PRE theoretical manuscript
```

---

## Building & Running

### Dependencies
* C++17 compiler (`g++`) and `make`
* Python 3 with `pybind11`, `numpy`, and `pygame` (plus `imageio`/`matplotlib` if running `visualize.py`)

### Build the C++ Engine
```bash
touch src/bindings.cpp && make
```

### Launch the Interactive Synthesizer
```bash
python3 scripts/interactive_synth.py
```

---

## Interactive Synthesizer Controls

| Control | Input | Function |
| :--- | :--- | :--- |
| **RGB Triangle Picker** | Left-click / drag inside triangle | Maps barycentric RGB weights to channel relaxation times $(\tau_R, \tau_G, \tau_B) \in [0.500001, 2.0]$ |
| **Channel Presets** | `1`, `2`, `3` | Jump to Red-, Green-, or Blue-biased relaxation profiles |
| **Re-seed Noise** | `R` | Re-initialize all three lattices with fresh stochastic density perturbations |
| **Optical Zoom** | `W` / `S` | Increase or decrease per-frame affine zoom (`0.90` to `1.10`) |
| **Vortex Rotation** | `Q` / `E` | Adjust per-frame angular twist (radians/step) |
| **Spatial Pan** | `Arrow Keys` | Shift optical feedback drift horizontally or vertically |
| **Reset Warp** | `0` | Reset affine transformation back to identity (`zoom=1.0`, `rot=0.0`, `pan=0`) |
| **Density Pulse & Stir** | Left-click / drag on canvas | Inject a localized Gaussian density bump and impart velocity along cursor motion |
| **Void Cavity & Stir** | Right-click / drag on canvas | Carve a localized dark void and stir surrounding spinodal domains |
| **Quit** | `Esc` | Exit the synthesizer |

---

## Current Test Cases

1. **Offline Baseline Coarsening (`scripts/visualize.py`)**
   * Runs a $256 \times 256$ single-channel grid for $400$ steps at $\tau = 0.85$, feedback gain $g_{\mathrm{fb}} = 1.05$, saturation limit $L_{\mathrm{sat}} = 1.50$, and initial perturbation $\delta\rho = 0.03$.
   * Verifies smooth transition from uncorrelated high-frequency noise into lamellar spinodal domains, exporting `testoutput/output_slow_synth.gif` and `testoutput/output_slow_synth.mp4`.

2. **Chromatic Dispersion & Barycentric $\tau$ Tuning (`interactive_synth.py`)**
   * Runs three coupled `LatticeGrid` instances (`RGBVideoGrid`) with distinct relaxation times mapped from the interactive RGB triangle.
   * Demonstrates differential phase-coarsening rates across color channels, producing organic RGB edge fringing.

3. **Optical Feedback Tunnel & Vortex Warping (`interactive_synth.py`)**
   * Applies inverse-mapped bilinear interpolation (`AffineTransform.hpp`) with default `zoom = 1.005` and `rotation = 0.008` rad/step across periodic boundaries.
   * Pulls coarsening domains into continuous, rotating CRT feedback tunnels.

4. **Hydrodynamic Impulse & Fluid Stirring (`interactive_synth.py`)**
   * Injects localized Gaussian density and momentum perturbations (`perturb_region`) via mouse clicks and drags, confirming outward ripple propagation and shear deformation of existing domains.