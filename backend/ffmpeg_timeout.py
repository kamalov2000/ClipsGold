"""
FFmpeg timeout wrapper to prevent infinite hangs on corrupted files.
Wraps FFmpeg commands with asyncio.wait_for() timeout protection.
"""

import asyncio
import subprocess
from typing import List
from pathlib import Path


class FFmpegTimeoutError(Exception):
    """Raised when FFmpeg execution exceeds timeout limit"""
    pass


async def run_ffmpeg_with_timeout(
    cmd: List[str],
    timeout: int = 300,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run FFmpeg command with timeout protection.
    
    Args:
        cmd: FFmpeg command as list of strings
        timeout: Maximum execution time in seconds (default: 300s / 5 minutes)
        capture_output: Whether to capture stdout/stderr
    
    Returns:
        subprocess.CompletedProcess if successful
    
    Raises:
        FFmpegTimeoutError: If execution exceeds timeout
        subprocess.CalledProcessError: If FFmpeg exits with non-zero code
    """
    print(f"⏱ FFmpeg timeout: {timeout}s")
    
    try:
        if capture_output:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=5.0  # 5s to start process
            )
        else:
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(*cmd),
                timeout=5.0
            )
        
        # Wait for process completion with timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore') if stderr else ''
            raise subprocess.CalledProcessError(
                process.returncode,
                cmd,
                output=stdout,
                stderr=stderr
            )
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr
        )
    
    except asyncio.TimeoutError:
        # Kill the process
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        
        raise FFmpegTimeoutError(
            f"FFmpeg execution exceeded {timeout}s timeout. "
            f"This usually indicates a corrupted video file or invalid filter parameters."
        )


def run_ffmpeg_sync_with_timeout(
    cmd: List[str],
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """
    Synchronous FFmpeg wrapper with timeout (for thread execution).
    
    Args:
        cmd: FFmpeg command as list of strings
        timeout: Maximum execution time in seconds (default: 300s / 5 minutes)
    
    Returns:
        subprocess.CompletedProcess if successful
    
    Raises:
        subprocess.TimeoutExpired: If execution exceeds timeout
        subprocess.CalledProcessError: If FFmpeg exits with non-zero code
    """
    print(f"⏱ FFmpeg timeout: {timeout}s (sync)")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=True
        )
        return result
    except subprocess.TimeoutExpired:
        raise subprocess.TimeoutExpired(
            cmd, timeout,
            f"FFmpeg execution exceeded {timeout}s timeout"
        )
