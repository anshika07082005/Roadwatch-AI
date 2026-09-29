from pathlib import Path
from app.services.video_analyzer import VideoAnalyzer

input_video = Path("sample_videos/sample.mp4")
output_video = Path("outputs/sample_annotated.mp4")

if not input_video.exists():
    raise SystemExit(
        "Place a traffic video at sample_videos/sample.mp4 before running this script."
    )

result = VideoAnalyzer().process_video(input_video, output_video)
print(result["summary"])
