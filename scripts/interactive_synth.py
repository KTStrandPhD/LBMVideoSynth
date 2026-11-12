import os
import sys
import numpy as np
import pygame

try:
    import cv2
except ImportError:
    cv2 = None

# Add build directory to path to load the compiled C++ extension
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../build")))
import lbm_video_engine as lbm

WIDTH, HEIGHT = 256, 256
INITIAL_SCALE = 2
MIN_WIN_WIDTH = 740
UI_HEIGHT = 128


def rgb_to_tau(r, g, b, tau_min=0.52, tau_max=2.0):
    """Maps 0-255 RGB values to individual tau relaxation times within safe bounds."""
    tau_r = tau_min + (r / 255.0) * (tau_max - tau_min)
    tau_g = tau_min + (g / 255.0) * (tau_max - tau_min)
    tau_b = tau_min + (b / 255.0) * (tau_max - tau_min)
    return tau_r, tau_g, tau_b


def get_triangle_vertices(cx, cy, radius):
    p_r = (cx, cy - radius)
    p_g = (cx - int(radius * 0.866), cy + int(radius * 0.5))
    p_b = (cx + int(radius * 0.866), cy + int(radius * 0.5))
    return p_r, p_g, p_b


def rgb_to_barycentric_coords(r, g, b, p_r, p_g, p_b):
    total = float(r) + float(g) + float(b)
    if total == 0.0:
        total = 1.0
    w_r, w_g, w_b = r / total, g / total, b / total
    mx = int(w_r * p_r[0] + w_g * p_g[0] + w_b * p_b[0])
    my = int(w_r * p_r[1] + w_g * p_g[1] + w_b * p_b[1])
    return mx, my


def barycentric_weights_from_point(pt, p1, p2, p3):
    x, y = pt
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if denominator == 0:
        return 1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0

    w1 = max(0.0, min(1.0, ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / denominator))
    w2 = max(0.0, min(1.0, ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / denominator))
    w3 = max(0.0, min(1.0, 1.0 - w1 - w2))

    total = w1 + w2 + w3
    if total > 0.0:
        w1 /= total
        w2 /= total
        w3 /= total
    return w1, w2, w3


def draw_rgb_triangle_picker(surface, cx, cy, radius, current_rgb, font):
    p_r, p_g, p_b = get_triangle_vertices(cx, cy, radius)
    pygame.draw.polygon(surface, (100, 100, 100), [p_r, p_g, p_b], 2)

    surface.blit(font.render("R", True, (255, 100, 100)), (p_r[0] - 4, p_r[1] - 15))
    surface.blit(font.render("G", True, (100, 255, 100)), (p_g[0] - 13, p_g[1] + 2))
    surface.blit(font.render("B", True, (100, 100, 255)), (p_b[0] + 4, p_b[1] + 2))

    mx, my = rgb_to_barycentric_coords(
        current_rgb[0], current_rgb[1], current_rgb[2], p_r, p_g, p_b
    )
    pygame.draw.circle(surface, (20, 20, 20), (mx, my), 6)
    pygame.draw.circle(surface, (255, 255, 255), (mx, my), 4)

    swatch_rect = pygame.Rect(cx + radius + 35, cy - 25, 48, 48)
    pygame.draw.rect(surface, current_rgb, swatch_rect)
    pygame.draw.rect(surface, (200, 200, 200), swatch_rect, 2)


def read_video_frame(cap, is_webcam):
    """Reads, resizes, and normalizes a video/webcam frame to (HEIGHT, WIDTH, 3) float64."""
    if cap is None or not cap.isOpened():
        return None
    ret, frame = cap.read()
    if not ret:
        if not is_webcam:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        if not ret:
            return None

    frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    if is_webcam:
        frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0
    return np.ascontiguousarray(frame_rgb)


def compute_layout(win_width, win_height):
    """Computes dynamic simulation canvas rectangle and bottom-anchored UI positions."""
    avail_h = max(128, win_height - UI_HEIGHT)
    sim_size = min(win_width, avail_h)
    sim_x = (win_width - sim_size) // 2
    sim_y = (avail_h - sim_size) // 2
    ui_top = win_height - UI_HEIGHT
    return sim_x, sim_y, sim_size, ui_top


def main():
    pygame.init()
    win_width = max(WIDTH * INITIAL_SCALE, MIN_WIN_WIDTH)
    win_height = (HEIGHT * INITIAL_SCALE) + UI_HEIGHT
    screen = pygame.display.set_mode((win_width, win_height), pygame.RESIZABLE)
    pygame.display.set_caption("LBM RGB Video Synthesizer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 18)

    # Initial RGB color state
    current_color = [180, 100, 220]
    tau_r, tau_g, tau_b = rgb_to_tau(*current_color)

    col_r = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)
    col_g = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)
    col_b = lbm.VideoFeedbackCollision(gain=1.05, limit=1.5)

    sim = lbm.RGBVideoGrid(WIDTH, HEIGHT, tau_r, tau_g, tau_b, col_r, col_g, col_b)
    sim.initialize_random_perturbation(1.0, 0.03)

    # Spatial affine warp state
    zoom, rotation, shift_x, shift_y = 1.005, 0.008, 0.0, 0.0
    sim.set_affine_transform(zoom, rotation, shift_x, shift_y)

    # External video / webcam state
    video_source = sys.argv[1] if len(sys.argv) > 1 else 0
    is_webcam = isinstance(video_source, int)
    cap = None
    feed_active = False
    feed_alpha = 0.08
    snap_burst = False

    if not is_webcam and cv2 is not None:
        cap = cv2.VideoCapture(video_source)
        feed_active = cap.isOpened()

    interacting_triangle = False
    poking_canvas = False
    prev_mouse_pos = None

    running = True
    while running:
        win_width, win_height = screen.get_size()
        sim_x, sim_y, sim_size, ui_top = compute_layout(win_width, win_height)
        sim_rect = pygame.Rect(sim_x, sim_y, sim_size, sim_size)

        tri_cx, tri_cy, tri_radius = 65, ui_top + 64, 38
        mouse_pos = pygame.mouse.get_pos()
        p_r, p_g, p_b = get_triangle_vertices(tri_cx, tri_cy, tri_radius)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                win_width = max(360, event.w)
                win_height = max(256 + UI_HEIGHT, event.h)
                screen = pygame.display.set_mode((win_width, win_height), pygame.RESIZABLE)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                if sim_rect.collidepoint(mouse_pos):
                    poking_canvas = True
                    prev_mouse_pos = mouse_pos
                    lx = int((mouse_pos[0] - sim_x) * WIDTH / sim_size)
                    ly = int((mouse_pos[1] - sim_y) * HEIGHT / sim_size)
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
                elif poking_canvas and prev_mouse_pos is not None and sim_rect.collidepoint(mouse_pos):
                    lx = int((mouse_pos[0] - sim_x) * WIDTH / sim_size)
                    ly = int((mouse_pos[1] - sim_y) * HEIGHT / sim_size)
                    dx = (mouse_pos[0] - prev_mouse_pos[0]) * WIDTH / sim_size
                    dy = (mouse_pos[1] - prev_mouse_pos[1]) * HEIGHT / sim_size
                    ux = max(-0.15, min(0.15, dx * 0.02))
                    uy = max(-0.15, min(0.15, dy * 0.02))
                    amp = 0.12 if pygame.mouse.get_pressed()[0] else -0.12
                    sim.perturb_region(lx, ly, radius=7.0, amplitude=amp, ux=ux, uy=uy)
                    prev_mouse_pos = mouse_pos

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    sim.initialize_random_perturbation(1.0, 0.03)
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    if event.key == pygame.K_1:
                        current_color = [255, 30, 30]
                    elif event.key == pygame.K_2:
                        current_color = [30, 255, 30]
                    elif event.key == pygame.K_3:
                        current_color = [30, 30, 255]
                    tau_r, tau_g, tau_b = rgb_to_tau(*current_color)
                    sim.set_relaxation_times(tau_r, tau_g, tau_b)

                # External video / webcam controls
                elif event.key == pygame.K_c and cv2 is not None:
                    if not feed_active:
                        if cap is None:
                            cap = cv2.VideoCapture(video_source)
                        feed_active = cap.isOpened()
                    else:
                        feed_active = False
                        if is_webcam and cap is not None:
                            cap.release()
                            cap = None
                elif event.key == pygame.K_LEFTBRACKET:
                    feed_alpha = max(0.01, feed_alpha - 0.02)
                elif event.key == pygame.K_RIGHTBRACKET:
                    feed_alpha = min(0.60, feed_alpha + 0.02)
                elif event.key == pygame.K_SPACE:
                    snap_burst = True

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

        # Inject live webcam / video frame if active or snap-burst triggered
        if (feed_active or snap_burst) and cv2 is not None:
            temp_cap = cap if cap is not None else cv2.VideoCapture(video_source)
            frame_rgb = read_video_frame(temp_cap, is_webcam)
            if frame_rgb is not None:
                alpha_to_use = 0.85 if snap_burst else feed_alpha
                sim.inject_rgb_frame(frame_rgb, alpha=alpha_to_use, contrast=0.35)
            if cap is None and temp_cap is not None:
                temp_cap.release()
            snap_burst = False

        # Advance simulation
        sim.step()

        # Render RGB density fields
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
        if sim_size != WIDTH:
            sim_surface = pygame.transform.scale(sim_surface, (sim_size, sim_size))

        # Draw background, UI divider, simulation canvas, and controls
        screen.fill((22, 22, 26))
        pygame.draw.rect(screen, (30, 30, 36), pygame.Rect(0, ui_top, win_width, UI_HEIGHT))
        pygame.draw.line(screen, (55, 55, 65), (0, ui_top), (win_width, ui_top), 1)
        screen.blit(sim_surface, (sim_x, sim_y))

        draw_rgb_triangle_picker(
            screen, tri_cx, tri_cy, tri_radius, tuple(current_color), font
        )

        text_x = tri_cx + tri_radius + 98
        feed_status = f"ON (alpha={feed_alpha:.2f})" if feed_active else "OFF"
        tau_txt = font.render(
            f"Tau R: {tau_r:.3f} | G: {tau_g:.3f} | B: {tau_b:.3f}  [1/2/3: Presets, R: Seed]",
            True, (215, 215, 215),
        )
        warp_txt = font.render(
            f"Zoom: {zoom:.3f} (W/S) | Rot: {rotation:.3f} (Q/E) | Pan: ({shift_x:.2f}, {shift_y:.2f}) | 0: Reset",
            True, (165, 200, 235),
        )
        feed_txt = font.render(
            f"Video Feed [C]: {feed_status} | Mix: [/] | Space: Snap Frame Stamp",
            True, (175, 225, 185),
        )
        poke_txt = font.render(
            "Canvas Drag: Left = Density Pulse & Stir | Right = Void Cavity & Stir",
            True, (150, 160, 175),
        )
        screen.blit(tau_txt, (text_x, tri_cy - 34))
        screen.blit(warp_txt, (text_x, tri_cy - 12))
        screen.blit(feed_txt, (text_x, tri_cy + 10))
        screen.blit(poke_txt, (text_x, tri_cy + 32))

        pygame.display.flip()
        clock.tick(60)
        pygame.display.set_caption(f"LBM RGB Synth | FPS: {clock.get_fps():.1f}")

    if cap is not None:
        cap.release()
    pygame.quit()


if __name__ == "__main__":
    main()
