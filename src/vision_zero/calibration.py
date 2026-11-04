"""Camera ground-plane calibration from surveyed landmark correspondences."""


def fit_homography(image_points: list[list[float]], ground_points_m: list[list[float]],
                   *, maximum_rms_error_m: float = 1.0) -> dict:
    if len(image_points) != len(ground_points_m) or len(image_points) < 4:
        raise ValueError("At least four paired image and ground-plane points are required")
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install opencv-python-headless and numpy for calibration") from exc
    source = np.asarray(image_points, dtype=np.float64)
    target = np.asarray(ground_points_m, dtype=np.float64)
    if source.shape[1:] != (2,) or target.shape[1:] != (2,):
        raise ValueError("Calibration points must be two-dimensional coordinate pairs")
    if np.linalg.matrix_rank(source - source.mean(axis=0)) < 2 or np.linalg.matrix_rank(target - target.mean(axis=0)) < 2:
        raise ValueError("Calibration landmarks are collinear or degenerate")
    matrix, inliers = cv2.findHomography(source, target, cv2.RANSAC)
    if matrix is None:
        raise ValueError("Could not estimate homography from supplied landmarks")
    projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
    errors = np.linalg.norm(projected - target, axis=1)
    rms = float(np.sqrt(np.mean(errors ** 2)))
    if rms > maximum_rms_error_m:
        raise ValueError(f"Calibration reprojection RMS {rms:.3f} m exceeds limit {maximum_rms_error_m:.3f} m")
    return {
        "homography": matrix.tolist(),
        "coordinate_system": "metric_m",
        "landmark_count": len(image_points),
        "inlier_count": int(inliers.sum()) if inliers is not None else len(image_points),
        "rms_error_m": rms,
        "maximum_rms_error_m": maximum_rms_error_m,
    }
