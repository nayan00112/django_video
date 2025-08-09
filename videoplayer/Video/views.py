

import os
import subprocess
from django.conf import settings
from django.shortcuts import render, redirect
from .models import VideoModel
from .forms import VideoForm
import uuid

def home(request):
    videos = VideoModel.objects.all()
    return render(request, 'videos/home.html', {'videos': videos})

def upload_video(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
            # Convert to HLS
            process_video_to_hls(video)
            return redirect('home')
    else:
        form = VideoForm()
    return render(request, 'videos/upload.html', {'form': form})



def process_video_to_hls(video_obj):
    input_path = os.path.join(settings.MEDIA_ROOT, video_obj.original_file.name)

    # Output folder
    base_folder = f'hls_videos/{uuid.uuid4().hex}'
    full_output_path = os.path.join(settings.MEDIA_ROOT, base_folder)
    os.makedirs(full_output_path, exist_ok=True)

    # Define renditions: (resolution, video_bitrate, audio_bitrate, bandwidth_estimate)
    renditions = [
        ("640x360", "800k", "96k",  1000000),  # ~1 Mbps
        ("854x480", "1400k", "128k", 1800000), # ~1.8 Mbps
        ("1280x720", "2800k", "128k", 4000000) # ~4 Mbps
    ]

    # Prepare ffmpeg arguments
    var_stream_map = []
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-preset", "veryfast", "-g", "48", "-sc_threshold", "0"
    ]

    master_pl_content = "#EXTM3U\n"

    for i, (resolution, v_bitrate, a_bitrate, bandwidth) in enumerate(renditions):
        out_dir = os.path.join(full_output_path, f"v{i}")
        os.makedirs(out_dir, exist_ok=True)

        ffmpeg_cmd += [
            "-map", "0:v:0", "-map", "0:a:0",
            f"-s:v:{i}", resolution,
            f"-b:v:{i}", v_bitrate,
            f"-maxrate:v:{i}", v_bitrate,
            f"-bufsize:v:{i}", "3000k",
            f"-b:a:{i}", a_bitrate
        ]
        var_stream_map.append(f"v:{i},a:{i}")
        master_pl_content += f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},RESOLUTION={resolution}\n" \
                             f"v{i}/playlist.m3u8\n"

    # Final ffmpeg params for HLS
    ffmpeg_cmd += [
        "-f", "hls",
        "-hls_time", "4",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", os.path.join(full_output_path, "v%v/segment_%03d.ts"),
        "-master_pl_name", os.path.join(full_output_path, "master.m3u8"),
        "-var_stream_map", " ".join(var_stream_map),
        os.path.join(full_output_path, "v%v/playlist.m3u8")
    ]

    # Run ffmpeg
    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Save master.m3u8 (ensures BANDWIDTH values are correct)
    with open(os.path.join(full_output_path, "master.m3u8"), "w") as f:
        f.write(master_pl_content)

    # Save HLS folder path to DB
    video_obj.hls_folder = base_folder
    video_obj.save()


# def process_video_to_hls(video_obj):
#     input_path = os.path.join(settings.MEDIA_ROOT, video_obj.original_file.name)
#     base_folder = f'hls_videos/{uuid.uuid4().hex}'
#     full_output_path = os.path.join(settings.MEDIA_ROOT, base_folder)

#     os.makedirs(full_output_path, exist_ok=True)

#     bitrates = {
#         "360p": (640*360, 800000),   # width*height, bandwidth
#         "480p": (854*480, 1400000),
#         "720p": (1280*720, 2800000),
#     }

#     resolutions = {
#         "360p": "640x360",
#         "480p": "854x480",
#         "720p": "1280x720",
#     }

#     master_playlist_path = os.path.join(full_output_path, 'master.m3u8')
#     master_playlist_content = ""

#     for label, resolution in resolutions.items():
#         out_folder = os.path.join(full_output_path, label)
#         os.makedirs(out_folder, exist_ok=True)
#         output_file = os.path.join(out_folder, 'index.m3u8')

#         command = [
#             'ffmpeg',
#             '-i', input_path,
#             '-vf', f'scale={resolution}',
#             '-c:a', 'aac',
#             '-ar', '48000',
#             '-c:v', 'h264',
#             '-profile:v', 'main',
#             '-crf', '20',
#             '-sc_threshold', '0',
#             '-g', '48',
#             '-keyint_min', '48',
#             '-hls_time', '4',
#             '-hls_playlist_type', 'vod',
#             '-b:v', '1500k',
#             '-maxrate', '2000k',
#             '-bufsize', '3000k',
#             '-hls_segment_filename', os.path.join(out_folder, 'segment_%03d.ts'),
#             output_file
#         ]

#         subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#         # Add to master playlist
#         master_playlist_content += f"#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION={resolution}\n{label}/index.m3u8\n"

#     # Write master.m3u8
#     with open(master_playlist_path, 'w') as f:
#         f.write("#EXTM3U\n")
#         f.write(master_playlist_content)

#     # Save path to DB
#     video_obj.hls_folder = base_folder
#     video_obj.save()
