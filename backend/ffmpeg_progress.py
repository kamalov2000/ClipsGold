"""
FFmpeg progress tracking utility.
Parses FFmpeg stderr output to extract progress information.

On Windows, asyncio.create_subprocess_exec can raise NotImplementedError
(SelectorEventLoop does not support subprocesses). Use run_ffmpeg_sync_with_progress
from a thread instead.
"""

import re
import subprocess
from pathlib import Path
from typing import Optional, Callable
import asyncio

try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False


def _sentry_ffmpeg_breadcrumb(cmd: list, returncode: int, stderr_tail: list) -> None:
    """Capture FFmpeg failure as a Sentry breadcrumb with the exact CLI command."""
    if not _SENTRY_AVAILABLE:
        return
    sentry_sdk.add_breadcrumb(
        category="ffmpeg",
        message=f"FFmpeg exited with code {returncode}",
        data={
            "command": " ".join(str(c) for c in cmd),
            "exit_code": returncode,
            "stderr_tail": "\n".join(stderr_tail[-10:]),
        },
        level="error",
    )


def parse_ffmpeg_progress(line: str) -> Optional[dict]:
    """
    Parse FFmpeg stderr line to extract progress information.
    
    FFmpeg outputs progress in format:
    frame=  123 fps= 30 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.5x
    
    Returns:
        dict with keys: frame, fps, time_seconds, bitrate, speed
        or None if line doesn't contain progress info
    """
    # Match frame number
    frame_match = re.search(r'frame=\s*(\d+)', line)
    # Match time in format HH:MM:SS.MS
    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
    # Match fps
    fps_match = re.search(r'fps=\s*([\d.]+)', line)
    # Match speed
    speed_match = re.search(r'speed=\s*([\d.]+)x', line)
    
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = float(time_match.group(3))
        time_seconds = hours * 3600 + minutes * 60 + seconds
        
        return {
            'frame': int(frame_match.group(1)) if frame_match else 0,
            'fps': float(fps_match.group(1)) if fps_match else 0,
            'time_seconds': time_seconds,
            'speed': float(speed_match.group(1)) if speed_match else 0
        }
    
    return None


def run_ffmpeg_sync_with_progress(
    cmd: list,
    duration: float,
    task_id: str,
    async_progress_callback: Callable,
    loop: asyncio.AbstractEventLoop,
) -> subprocess.CompletedProcess:
    """
    Run FFmpeg synchronously with subprocess.Popen and report progress by
    scheduling the async callback on the given event loop. Safe to call from
    a thread (e.g. via asyncio.to_thread). Use this on Windows where
    create_subprocess_exec may raise NotImplementedError.
    """
    print(f"\n🎬 Starting FFmpeg with progress tracking (task: {task_id})")
    print(f"   Expected duration: {duration:.1f}s")
    print(f"   Command: {' '.join(str(c) for c in cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stderr_output = []
    last_progress = 0

    while True:
        line = process.stderr.readline()
        if not line:
            break
        line_str = line.decode("utf-8", errors="ignore").strip()
        stderr_output.append(line_str)

        progress_info = parse_ffmpeg_progress(line_str)
        if progress_info and duration > 0:
            current_time = progress_info["time_seconds"]
            percentage = min(int((current_time / duration) * 100), 99)
            if percentage > last_progress:
                last_progress = percentage
                if async_progress_callback:
                    future = asyncio.run_coroutine_threadsafe(
                        async_progress_callback(
                            task_id,
                            {
                                "status": "processing",
                                "progress": percentage,
                                "frame": progress_info["frame"],
                                "fps": progress_info["fps"],
                                "time": current_time,
                                "speed": progress_info["speed"],
                            },
                        ),
                        loop,
                    )
                    try:
                        future.result(timeout=2.0)
                    except Exception:
                        pass
                print(
                    f"   Progress: {percentage}% (frame: {progress_info['frame']}, fps: {progress_info['fps']:.1f}, speed: {progress_info['speed']:.1f}x)"
                )

    process.wait()
    if process.returncode != 0:
        print(f"\n❌ FFmpeg FAILED (exit {process.returncode}) — FULL stderr ({len(stderr_output)} lines):")
        for ln in stderr_output:
            print(f"   {ln}")
        _sentry_ffmpeg_breadcrumb(cmd, process.returncode, stderr_output[-10:])
    if async_progress_callback:
        future = asyncio.run_coroutine_threadsafe(
            async_progress_callback(task_id, {"status": "complete", "progress": 100}),
            loop,
        )
        try:
            future.result(timeout=2.0)
        except Exception:
            pass
    print(f"✓ FFmpeg completed (task: {task_id}, exit={process.returncode})")
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout=b"",
        stderr="\n".join(stderr_output).encode(),
    )


async def run_ffmpeg_with_progress(
    cmd: list,
    duration: float,
    task_id: str,
    progress_callback: Optional[Callable] = None
) -> subprocess.CompletedProcess:
    """
    Run FFmpeg command and track progress.
    
    Args:
        cmd: FFmpeg command as list
        duration: Expected duration of output video in seconds
        task_id: Unique task identifier for progress tracking
        progress_callback: Async function to call with progress updates
    
    Returns:
        CompletedProcess result
    """
    print(f"\n🎬 Starting FFmpeg with progress tracking (task: {task_id})")
    print(f"   Expected duration: {duration:.1f}s")
    print(f"   Command: {' '.join(str(c) for c in cmd)}")
    
    # Start FFmpeg process — 1 MB line buffer prevents ValueError when FFmpeg
    # emits very long lines (filter-graph dumps, codec info, etc.)
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024,
    )

    stderr_output = []
    last_progress = 0

    # Read stderr line by line
    while True:
        try:
            line = await process.stderr.readline()
        except Exception:
            break
        if not line:
            break

        try:
            line_str = line.decode('utf-8', errors='ignore').strip()
        except Exception:
            continue
        stderr_output.append(line_str)

        # Parse progress
        try:
            progress_info = parse_ffmpeg_progress(line_str)
        except Exception:
            continue
        if progress_info and duration > 0:
            current_time = progress_info['time_seconds']
            percentage = min(int((current_time / duration) * 100), 99)
            
            # Only send updates when percentage changes (avoid spam)
            if percentage > last_progress:
                last_progress = percentage
                
                if progress_callback:
                    await progress_callback(task_id, {
                        'status': 'processing',
                        'progress': percentage,
                        'frame': progress_info['frame'],
                        'fps': progress_info['fps'],
                        'time': current_time,
                        'speed': progress_info['speed']
                    })
                
                print(f"   Progress: {percentage}% (frame: {progress_info['frame']}, fps: {progress_info['fps']:.1f}, speed: {progress_info['speed']:.1f}x)")
    
    # Wait for process to complete
    await process.wait()
    
    if process.returncode != 0:
        print(f"\n❌ FFmpeg FAILED (exit {process.returncode}) — FULL stderr ({len(stderr_output)} lines):")
        for ln in stderr_output:
            print(f"   {ln}")
        _sentry_ffmpeg_breadcrumb(cmd, process.returncode, stderr_output[-10:])

    # Send 100% completion
    if progress_callback:
        await progress_callback(task_id, {
            'status': 'complete',
            'progress': 100
        })
    
    print(f"✓ FFmpeg completed (task: {task_id}, exit={process.returncode})")
    
    # Return result similar to subprocess.run
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=process.returncode,
        stdout=b'',
        stderr='\n'.join(stderr_output).encode()
    )


def run_ffmpeg_with_progress_sync(
    cmd: list,
    duration: float,
    task_id: str,
    progress_callback: Optional[Callable] = None
) -> subprocess.CompletedProcess:
    """
    Synchronous wrapper for run_ffmpeg_with_progress.
    Creates event loop if needed.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        run_ffmpeg_with_progress(cmd, duration, task_id, progress_callback)
    )
