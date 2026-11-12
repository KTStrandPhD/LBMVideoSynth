import os
import sys
import numpy as np
import pygame

# Add build directory to path to load the compiled C++ extension
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../build")))
import lbm_video_engine as lbm

WIDTH, HEIGHT = 256, 256
SCALE = 2
UI_HEIGHT = 110


def rgb_to_tau(r, g, b, tau_min=0.500001, tau_max=2.0):
    """Maps 0-255 RGB values to individual tau relaxation times within safe bounds."""
    tau_r = tau_min + (r / 255.0) * (tau_max - tau_min)
    tau_g = tau_min + (g / 255.0) * (tau_max - tau_min)
    tau_b = tau_min + (b / 255.0) * (tau_max - tau_min)
    return tau_r, tau_g, tau_b


def get_triangle_vertices(cx, cy, radius):
    """Computes the 3 vertices (Red, Green, Blue) of an equilateral triangle."""
    p_r = (cx, cy - radius)                                  # Top: Red
    p_g = (cx - int(radius * 0.866), cy + int(radius * 0.5)) # Bottom-Left: Green
    p_b = (cx + int(radius * 0.866), cy + int(radius * 0.5)) # Bottom-Right: Blue
    return p_r, p_g, p_b


def rgb_to_barycentric_coords(r, g, b, p_r, p_g, p_b):
    """Calculates the pixel coordinate (mx, my) inside the triangle based on RGB weights."""
    total = float(r) + float(g) + float(b)
    if total == 0.0:
        total = 1.0
    w_r = r / total
    w_g = g / total
    w_b = b / total

    mx = int(w_r * p_r[0] + w_g * p_g[0] + w_b * p_b[0])
    my = int(w_r * p_r[1] + w_g * p_g[1] + w_b * p_b[1])
    return mx, my


def barycentric_weights_from_point(pt, p1, p2, p3):
    """Computes normalized barycentric RGB weights from a point inside the triangle."""
    x, y = pt
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if denominator == 0:
        return 1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0

    w1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / denominator
    w2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / denominator
    w3 = 1.0 - w1 - w2

    w1 = max(0.0, min(1.0, w1))
    w2 = max(0.0, min(1.0, w2))
    w3 = max(0.0, min(1.0, w3))

    total = w1 + w2 + w3
    if total > 0.0:
        w1 /= total
        w2 /= total
        w3 /= total
    return w1, w2, w3


def draw_rgb_triangle_picker(surface, cx, cy, radius, current_rgb, font):
    """Draws the RGB triangle, vertex labels, choice marker button, and color swatch."""
    p_r, p_g, p_b = get_triangle_vertices(cx, cy, radius)

    pygame.draw.polygon(surface, (100, 100, 100), [p_r, p_g, p_b], 2)

    surface.blit(font.render("R", True, (255, 100, 100)), (p_r[0] - 4, p_r[1] - 15))
    surface.blit(font.render("G", True, (100, 255, 100)), (p_g[0] - 13, p_g[1] + 2))
    surface.blit(font.render("B", True, (100, 100, 255)), (p_b[0] + 4, p_b[1] + 2))

    # Position marker button on the triangle
    mx, my = rgb_to_barycentric_coords(
        current_rgb[0], current_rgb[1], current_rgb[2], p_r, p_g, p_b
    )
    pygame.draw.circle(surface, (20, 20, 20), (mx, my), 6)
    pygame.draw.circle(surface, (255, 255, 255), (mx, my), 4)

    # Active color swatch
    swatch_rect = pygame.Rect(cx + radius + 35, cy - 25, 48, 48)
    pygame.draw.rect(surface, current_rgb, swatch_rect)
    pygame.draw.rect(surface, (200, 200, 200), swatch_rect, 2)


def main():
    pygame.init()
    sim_height_px = HEIGHT * SCALE
    win_width = WIDTH * SCALE
    win_height = sim_height_px + UI_HEIGHT
    screen = pygame.display.set_mode((win_width, win_height))
    pygame.display.set_caption("LBM RGB Video Synthesizer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 18)

    # Initial RGB color state driving channel relaxation times
    current_color = [180, 100, 220]
    tau_r, tau_g, tau_b = rgb_to_tau(*current_color)

    col_r = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)
    col_g = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)
    col_b = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)

    sim = lbm.RGBVideoGrid(WIDTH, HEIGHT, tau_r, tau_g, tau_b, col_r, col_g, col_b)
    sim.initialize_random_perturbation(1.0, 0.03)

    # Initial spatial affine warp parameters
    zoom = 1.005
    rotation = 0.008
    shift_x = 0.0
    shift_y = 0.0
    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)

    # Interactive state flags
    tri_cx, tri_cy, tri_radius = 65, sim_height_px + 58, 38
    interacting_triangle = False
    poking_canvas = False
    prev_mouse_pos = None

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        p_r, p_g, p_b = get_triangle_vertices(tri_cx, tri_cy, tri_radius)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                if mouse_pos[1] < sim_height_px:
                    # Poke simulation canvas: Left-click adds density, Right-click carves a void
                    poking_canvas = True
                    prev_mouse_pos = mouse_pos
                    lx = mouse_pos[0] // SCALE
                    ly = mouse_pos[1] // SCALE
                    amp = 0.25 if event.button == 1 else -0.25
                    sim.perturb_region(lx, ly, radius=8.0, amplitude=amp, ux=0.0, uy=0.0)
                elif event.button == 1:
                    bounding_rect = pygame.Rect(
                        tri_cx - tri_radius - 8,
                        tri_cy - tri_radius - 8,
                        (tri_radius + 8) * 2,
                        (tri_radius + 8) * 2,
                    )
                    if bounding_rect.collidepoint(mouse_pos):
                        interacting_triangle = True
                        w_r, w_g, w_b = barycentric_weights_from_point(mouse_pos, p_r, p_g, p_b)
                        current_color = [int(w_r * 255), int(w_g * 255), int(w_b * 255)]
                        tau_r, tau_g, tau_b = rgb_to_tau(*current_color)
                        sim.set_relaxation_times(tau_r, tau_g, tau_b)

            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3):
                interacting_triangle = False
                poking_canvas = False
                prev_mouse_pos = None

            elif event.type == pygame.MOUSEMOTION:
                if interacting_triangle:
                    w_r, w_g, w_b = barycentric_weights_from_point(mouse_pos, p_r, p_g, p_b)
                    current_color = [int(w_r * 255), int(w_g * 255), int(w_b * 255)]
                    tau_r, tau_g, tau_b = rgb_to_tau(*current_color)
                    sim.set_relaxation_times(tau_r, tau_g, tau_b)

                elif poking_canvas and prev_mouse_pos is not None and mouse_pos[1] < sim_height_px:
                    lx = mouse_pos[0] // SCALE
                    ly = mouse_pos[1] // SCALE
                    dx = (mouse_pos[0] - prev_mouse_pos[0]) / SCALE
                    dy = (mouse_pos[1] - prev_mouse_pos[1]) / SCALE
                    ux = max(-0.15, min(0.15, dx * 0.02))
                    uy = max(-0.15, min(0.15, dy * 0.02))
                    amp = 0.12 if pygame.mouse.get_pressed()[0] else -0.12
                    sim.perturb_region(lx, ly, radius=7.0, amplitude=amp, ux=ux, uy=uy)
                    prev_mouse_pos = mouse_pos

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Reset stochastic seed
                elif event.key == pygame.K_r:
                    sim.initialize_random_perturbation(1.0, 0.03)

                # RGB vertex presets
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    if event.key == pygame.K_1:
                        current_color = [255, 30, 30]
                    elif event.key == pygame.K_2:
                        current_color = [30, 255, 30]
                    elif event.key == pygame.K_3:
                        current_color = [30, 30, 255]
                    tau_r, tau_g, tau_b = rgb_to_tau(*current_color)
                    sim.set_relaxation_times(tau_r, tau_g, tau_b)

                # Spatial affine warp controls
                elif event.key == pygame.K_w:
                    zoom = min(1.10, zoom + 0.002)
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_s:
                    zoom = max(0.90, zoom - 0.002)
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_q:
                    rotation -= 0.002
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_e:
                    rotation += 0.002
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_LEFT:
                    shift_x -= 0.25
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_RIGHT:
                    shift_x += 0.25
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_UP:
                    shift_y -= 0.25
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_DOWN:
                    shift_y += 0.25
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)
                elif event.key == pygame.K_0:
                    zoom, rotation, shift_x, shift_y = 1.0, 0.0, 0.0, 0.0
                    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)

        # Advance simulation
        sim.step()

        # Retrieve and normalize RGB density fields independently
        rgb_flat = sim.get_rgb_density_field()
        rgb_grid = rgb_flat.reshape((HEIGHT, WIDTH, 3))

        norm_channels = []
        for c in range(3):
            ch = rgb_grid[:, :, c]
            c_min, c_max = ch.min(), ch.max()
            rng = (c_max - c_min) if (c_max - c_min) > 1e-5 else 1.0
            norm_channels.append(((ch - c_min) / rng * 255.0).astype(np.uint8))

        norm_rgb = np.stack(norm_channels, axis=-1)
        sim_surface = pygame.surfarray.make_surface(norm_rgb.swapaxes(0, 1))
        if SCALE > 1:
            sim_surface = pygame.transform.scale(sim_surface, (win_width, sim_height_px))

        # Render simulation and UI panel
        screen.fill((28, 28, 32))
        screen.blit(sim_surface, (0, 0))

        draw_rgb_triangle_picker(
            screen, tri_cx, tri_cy, tri_radius, tuple(current_color), font
        )

        text_x = tri_cx + tri_radius + 98
        tau_txt = font.render(
            f"Tau R: {tau_r:.3f} | G: {tau_g:.3f} | B: {tau_b:.3f}  [1/2/3: Presets, R: Seed]",
            True,
            (215, 215, 215),
        )
        warp_txt = font.render(
            f"Zoom: {zoom:.3f} (W/S) | Rot: {rotation:.3f} (Q/E) | Pan: ({shift_x:.2f}, {shift_y:.2f}) | 0: Reset",
            True,
            (165, 200, 235),
        )
        poke_txt = font.render(
            "Canvas Click/Drag: Left = Density Pulse & Stir | Right = Void Cavity & Stir",
            True,
            (150, 160, 175),
        )
        screen.blit(tau_txt, (text_x, tri_cy - 26))
        screen.blit(warp_txt, (text_x, tri_cy - 2))
        screen.blit(poke_txt, (text_x, tri_cy + 22))

        pygame.display.flip()
        clock.tick(60)
        pygame.display.set_caption(f"LBM RGB Synth | FPS: {clock.get_fps():.1f}")

    pygame.quit()


if __name__ == "__main__":
    main()
