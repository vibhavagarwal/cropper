"""Explicit save: writes only the jobs the user marked to keep, to the
chosen output folder. Nothing else in the app ever writes to disk."""
import os


def save_kept_jobs(jobs, output_folder: str) -> list:
    os.makedirs(output_folder, exist_ok=True)
    written = []
    for job in jobs:
        if not job.keep or job.error or job.rendered is None:
            continue
        stem = os.path.splitext(job.filename)[0]
        dst = os.path.join(output_folder, f"{stem}_cropper.jpg")
        try:
            job.rendered.convert("L").save(dst, quality=92, optimize=True)
            written.append(dst)
        except OSError:
            continue
    return written
