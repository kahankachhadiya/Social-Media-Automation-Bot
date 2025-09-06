import sys
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
import json

def insert_animated_corner_photo(
    video_path, image_path, output_path, direction="right", duration=0.5, scale=0.75
):
    video = VideoFileClip(video_path)
    video_w, video_h = video.size
    video_duration = video.duration

    # Max size in bottom corner
    max_w = int((video_w // 2) * scale)
    max_h = int((video_h // 2) * scale)

    image = ImageClip(image_path).resize(height=max_h)
    if image.w > max_w:
        image = image.resize(width=max_w)

    img_w, img_h = image.size

    if direction == "left":
        target_x = 0
        start_x = -img_w
        end_x = -img_w
    elif direction == "right":
        target_x = video_w - img_w
        start_x = video_w
        end_x = video_w
    else:
        raise ValueError("Direction must be 'left' or 'right'")

    target_y = video_h - img_h

    def animated_pos(t):
        if t < duration:
            return (start_x + (target_x - start_x) * (t / duration), target_y)
        elif t > video_duration - duration:
            t_slide = t - (video_duration - duration)
            return (target_x + (end_x - target_x) * (t_slide / duration), target_y)
        else:
            return (target_x, target_y)

    animated_image = image.set_position(animated_pos).set_duration(video_duration)

    final = CompositeVideoClip([video, animated_image])
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")

    # Return JSON output
    print(json.dumps({
        "status": "success",
        "output_path": output_path
    }))


if __name__ == "__main__":
    # Parse command-line arguments
    _, video_path, image_path, output_path, direction, duration, scale = sys.argv

    # Call main logic
    insert_animated_corner_photo(
        video_path=video_path,
        image_path=image_path,
        output_path=output_path,
        direction=direction,
        duration=float(duration),
        scale=float(scale)
    )
